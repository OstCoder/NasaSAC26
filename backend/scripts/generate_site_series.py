"""Generate the Phase 2 Task 2 Sun/Earth series for the Phase 1 candidate sites.

Usage (from backend/, needs internet):

    python scripts/generate_site_series.py                 # all candidates, both windows, 1 h
    python scripts/generate_site_series.py --window initial --site shackleton-rim
    python scripts/generate_site_series.py --verify-only    # re-check the committed files offline

For every candidate site it fetches the apparent Sun and Earth azimuth/elevation
from JPL Horizons for the initial (1-8 December 2026) and delayed (11-18
December 2026) mission periods, cross-checks each body against LunaNav's
independent analytic model, and writes one file per site and window plus an
index:

    data/scientific/site_series/<site>-<initial|alternative>.json
    data/scientific/site_series/index.json

Every file is validated before it is written: the sample count must match the
window and step, timestamps must be chronological and shared by both bodies,
and no azimuth/elevation may be missing. A failed cross-check or a short series
stops the run instead of writing unverified data.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.errors import LunaNavError  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.core.timeutil import to_iso  # noqa: E402
from app.providers.horizons_site import (  # noqa: E402
    ObserverSite,
    crosscheck_against_analytic,
    fetch_sky,
    step_minutes,
)
from app.services.site_series import (  # noqa: E402
    expected_samples,
    mission_windows,
    series_checks,
    series_payload,
)
from app.services.sites import get_site_repository  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "data" / "scientific" / "site_series"
INDEX_SCHEMA = "lunanav.site_series_index.v1"

EXAMPLES = """examples:
  python scripts/generate_site_series.py
  python scripts/generate_site_series.py --window alternative --site connecting-ridge
  python scripts/generate_site_series.py --verify-only
"""


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Generate the Phase 2 Task 2 Sun/Earth series for the mission candidate sites.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EXAMPLES,
    )
    ap.add_argument("--window", choices=("all", "initial", "alternative"), default="all")
    ap.add_argument("--site", action="append", help="site id (repeatable; default: mission candidates)")
    ap.add_argument("--step", default="1 h", help="sampling interval, e.g. '1 h' (default: 1 h)")
    ap.add_argument("--height-m", type=float, default=2.0, help="observer height above terrain (m)")
    ap.add_argument("--tolerance", type=float, default=0.5,
                    help="max allowed analytic cross-check difference in degrees (default: 0.5)")
    ap.add_argument("--timeout", type=float, default=90.0, help="per-request timeout in seconds")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help="output directory")
    ap.add_argument("--verify-only", action="store_true",
                    help="re-check the files listed in index.json without the network")
    return ap.parse_args(argv)


def verify(out_dir: Path) -> int:
    index_path = out_dir / "index.json"
    if not index_path.exists():
        print(f"FAILED: {index_path} does not exist; run without --verify-only first", file=sys.stderr)
        return 1
    index = json.loads(index_path.read_text())
    problems = 0
    print(f"{'site':22s} {'window':11s} {'samples':>7s}  checks")
    for entry in index.get("sites", []):
        for key, name in entry.get("files", {}).items():
            path = out_dir / name
            if not path.exists():
                print(f"{entry['site_id']:22s} {key:11s} {'-':>7s}  MISSING {name}")
                problems += 1
                continue
            records = json.loads(path.read_text()).get("series", [])
            checks = series_checks(records)
            want = index.get("windows", {}).get(key, {}).get("expected_samples")
            ok = all(checks.values()) and len(records) == want
            problems += not ok
            print(f"{entry['site_id']:22s} {key:11s} {len(records):7d}  "
                  f"{'ok' if ok else 'FAILED ' + str(checks)}")
    print("all series verified" if not problems else f"{problems} problem(s) found")
    return 0 if not problems else 1


def generate(args: argparse.Namespace) -> int:
    settings = get_settings()
    windows = [w for w in mission_windows(settings) if args.window in ("all", w.key)]
    candidates = list(settings.raw["mission"]["candidate_sites"])
    site_ids = args.site or candidates
    repo = get_site_repository()
    minutes = step_minutes(args.step)
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    for site_id in site_ids:
        site = repo.get(site_id)
        if site.elevation_m is None:
            print(f"FAILED: site {site_id!r} has no recorded elevation", file=sys.stderr)
            return 1
        observer = ObserverSite.at(
            site.latitude_deg, site.longitude_deg, site.elevation_m, args.height_m, site_id=site_id
        )
        entry = {"site_id": site_id, "name": site.name, "files": {}, "samples": {}, "crosscheck": {}}
        for window in windows:
            want = expected_samples(window, minutes)
            print(f"{site_id} {window.key}: {to_iso(window.start)} .. {to_iso(window.end)} "
                  f"({want} samples at {args.step})", flush=True)
            try:
                tracks = fetch_sky(observer, window.start, window.end, args.step, timeout_s=args.timeout)
            except LunaNavError as exc:
                print(f"FAILED: {site_id} {window.key}: {exc.message}", file=sys.stderr)
                return 1
            checks = {
                body: crosscheck_against_analytic(track, tolerance_deg=args.tolerance)
                for body, track in tracks.items()
            }
            failed = [body for body, check in checks.items() if not check.passed]
            if failed:
                print(f"FAILED: {site_id} {window.key} cross-check failed for {failed}", file=sys.stderr)
                return 1
            payload = series_payload(
                observer=observer, label={"site_id": site_id, "name": site.name},
                tracks=tracks, crosschecks=checks,
                start=window.start, stop=window.end, step=args.step, window=window,
            )
            records = payload["series"]
            if len(records) != want or not all(payload["checks"].values()):
                print(f"FAILED: {site_id} {window.key}: {len(records)} samples (expected {want}), "
                      f"checks {payload['checks']}", file=sys.stderr)
                return 1
            path = out_dir / f"{site_id}-{window.key}.json"
            path.write_text(json.dumps(payload, indent=2) + "\n")
            entry["files"][window.key] = path.name
            entry["samples"][window.key] = len(records)
            entry["crosscheck"][window.key] = {b: check.as_dict() for b, check in checks.items()}
            print(f"  wrote {path.name}: {len(records)} samples, "
                  f"max d-az {max(c.max_azimuth_deg for c in checks.values()):.3f} deg, "
                  f"max d-el {max(c.max_elevation_deg for c in checks.values()):.3f} deg")
        entries.append(entry)

    index = {
        "schema": INDEX_SCHEMA,
        "generated_utc": to_iso(datetime.now(timezone.utc)),
        "step": args.step,
        "partial": len(windows) != 2 or list(site_ids) != candidates,
        "windows": {
            w.key: {**w.as_dict(), "expected_samples": expected_samples(w, minutes)} for w in windows
        },
        "sites": entries,
        "total_samples": sum(sum(entry["samples"].values()) for entry in entries),
    }
    (out_dir / "index.json").write_text(json.dumps(index, indent=2) + "\n")
    print(f"wrote {out_dir / 'index.json'}: {index['total_samples']} samples, "
          f"{len(entries)} sites, {len(windows)} windows")
    return 0


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.verify_only:
        return verify(args.out_dir)
    try:
        return generate(args)
    except LunaNavError as exc:
        print(f"FAILED: {exc.message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
