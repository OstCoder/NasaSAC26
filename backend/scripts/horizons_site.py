"""Retrieve Sun and Earth azimuth/elevation from JPL Horizons for a lunar site.

Phase 2, Task 1 deliverable (CLI). The module it drives is
``app/providers/horizons_site.py``.

Usage (from backend/, needs internet):

    python scripts/horizons_site.py --site shackleton-rim \
        --start 2026-12-01T00:00Z --stop 2026-12-08T00:00Z --step "1 h" \
        --out ../data/scientific/site_sky/shackleton-rim.json

    python scripts/horizons_site.py --lat -89.45 --lon 222.69 --elevation-m 1955 \
        --start 2026-12-11T00:00Z --stop 2026-12-12T00:00Z --step "30 m"

Each run prints the series and compares every sample with LunaNav's independent
analytic model, so a frame, sign or column problem shows up immediately instead
of silently producing a plausible table. ``--out`` writes one JSON record per
timestamp (``site_id``, ``timestamp_utc``, ``sun``, ``earth``), which is the
structure Phase 2 Task 2 builds on.

Exit status: 0 when both bodies were retrieved and passed the cross-check,
1 when the download failed, the data was rejected, or the cross-check failed.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.errors import LunaNavError  # noqa: E402
from app.core.timeutil import parse_utc, to_iso  # noqa: E402
from app.providers.horizons_site import (  # noqa: E402
    ObserverSite,
    SkyTrack,
    crosscheck_against_analytic,
    fetch_sky,
)
from app.services.sites import get_site_repository  # noqa: E402

SCHEMA = "lunanav.site_sky.v1"
DEFAULT_OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "scientific" / "site_sky"
BODY_ORDER = ("sun", "earth")
EXAMPLES = """examples:
  python scripts/horizons_site.py --site shackleton-rim \\
      --start 2026-12-01T00:00Z --stop 2026-12-08T00:00Z --step "1 h" \\
      --out ../data/scientific/site_sky/shackleton-rim.json
  python scripts/horizons_site.py --lat -89.45 --lon 222.69 --elevation-m 1955 \\
      --start 2026-12-11T00:00Z --stop 2026-12-12T00:00Z --step "30 m"
"""


def resolve_observer(args) -> tuple[ObserverSite, dict]:
    """Catalogue site by id, or explicit coordinates."""
    if args.site:
        site = get_site_repository().get(args.site)
        elevation = args.elevation_m if args.elevation_m is not None else site.elevation_m
        if elevation is None:
            raise SystemExit(f"site {args.site!r} has no recorded elevation; pass --elevation-m")
        observer = ObserverSite.at(
            site.latitude_deg, site.longitude_deg, elevation, args.height_m, site_id=site.id
        )
        return observer, {"site_id": site.id, "name": site.name}
    if args.lat is None or args.lon is None:
        raise SystemExit("pass --site ID, or both --lat and --lon")
    elevation = args.elevation_m if args.elevation_m is not None else 0.0
    observer = ObserverSite.at(args.lat, args.lon, elevation, args.height_m)
    return observer, {"site_id": None, "name": f"Custom ({args.lat:.4f}, {args.lon:.4f})"}


def merged_samples(tracks: dict[str, SkyTrack], site_id: str | None) -> tuple[list[dict], int]:
    """One record per timestamp where both bodies have a value (Task 2's shape)."""
    per_time: dict[datetime, dict] = {}
    for body, track in tracks.items():
        ranges = track.range_km if track.range_km is not None else [None] * len(track)
        for when, az, el, distance in zip(track.times_utc, track.azimuth_deg, track.elevation_deg, ranges):
            sample = {"azimuth_deg": round(float(az), 6), "elevation_deg": round(float(el), 6)}
            if distance is not None:
                sample["range_km"] = round(float(distance), 3)
            per_time.setdefault(when, {})[body] = sample
    complete = [t for t in sorted(per_time) if all(b in per_time[t] for b in BODY_ORDER)]
    records = [{"site_id": site_id, "timestamp_utc": to_iso(t), **per_time[t]} for t in complete]
    return records, len(per_time) - len(complete)


def build_payload(
    observer: ObserverSite,
    label: dict,
    tracks: dict[str, SkyTrack],
    checks: dict,
    start: datetime,
    stop: datetime,
    step: str,
) -> dict:
    samples, dropped = merged_samples(tracks, label.get("site_id"))
    return {
        "schema": SCHEMA,
        "generated_utc": to_iso(datetime.now(start.tzinfo)),
        "site": {**label, **observer.as_dict()},
        "request": {
            "start_utc": to_iso(start),
            "stop_utc": to_iso(stop),
            "step": step,
            "bodies": list(BODY_ORDER),
            "queries": {body: track.query_url for body, track in tracks.items()},
        },
        "source": (
            "NASA JPL Horizons API observer table: CENTER='coord@301', "
            "COORD_TYPE='GEODETIC', QUANTITIES='4,20' (apparent az/el, airless)"
        ),
        "conventions": {
            "longitude": "selenographic, east-positive",
            "azimuth_deg": "degrees clockwise from local lunar north, [0, 360)",
            "elevation_deg": "degrees above the local horizontal, airless (no refraction), no terrain",
            "altitude_km": "height above the 1737.4 km IAU mean sphere (site elevation + observer height)",
        },
        "crosscheck": {body: check.as_dict() for body, check in checks.items()},
        "samples": samples,
        "incomplete_timestamps_dropped": dropped,
    }


def print_table(tracks: dict[str, SkyTrack], limit: int = 8) -> None:
    sun, earth = tracks["sun"], tracks["earth"]
    earth_at = dict(zip(earth.times_utc, zip(earth.azimuth_deg, earth.elevation_deg)))
    print(f"  {'UTC':20s} {'sun az':>9s} {'sun el':>9s} {'earth az':>9s} {'earth el':>9s}")
    rows = list(zip(sun.times_utc, sun.azimuth_deg, sun.elevation_deg))[:limit]
    for when, az, el in rows:
        e_az, e_el = earth_at.get(when, (float("nan"), float("nan")))
        print(f"  {to_iso(when):20s} {az:9.4f} {el:9.4f} {e_az:9.4f} {e_el:9.4f}")
    if len(sun) > len(rows):
        print(f"  ... {len(sun) - len(rows)} more samples")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Fetch Sun and Earth azimuth/elevation from JPL Horizons for a lunar site.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EXAMPLES,
    )
    ap.add_argument("--site", help="Phase 1 catalogue site id, e.g. shackleton-rim")
    ap.add_argument("--lat", type=float, help="selenographic latitude (deg, for a custom site)")
    ap.add_argument("--lon", type=float, help="selenographic longitude (deg, east-positive)")
    ap.add_argument("--elevation-m", type=float, help="site elevation above the 1737.4 km sphere (m)")
    ap.add_argument("--height-m", type=float, default=2.0, help="observer height above terrain (m)")
    ap.add_argument("--start", required=True, help="start time, UTC with offset, e.g. 2026-12-01T00:00Z")
    ap.add_argument("--stop", required=True, help="stop time, UTC with offset, e.g. 2026-12-02T00:00Z")
    ap.add_argument("--step", default="30 m", help="sampling interval, e.g. '30 m', '1 h' (default: 30 m)")
    ap.add_argument("--out", type=Path, help="write the JSON series here (default: print only)")
    ap.add_argument(
        "--tolerance",
        type=float,
        default=0.5,
        help="max allowed cross-check difference in degrees (default: 0.5)",
    )
    args = ap.parse_args(argv)

    try:
        observer, label = resolve_observer(args)
        start, stop = parse_utc(args.start), parse_utc(args.stop)
        tracks = fetch_sky(observer, start, stop, args.step)
    except LunaNavError as exc:
        print(f"FAILED: {exc.message}", file=sys.stderr)
        return 1

    print(f"JPL Horizons, observer {observer.latitude_deg:.4f}, {observer.longitude_deg:.4f}, "
          f"{observer.altitude_km:.3f} km ({to_iso(start)} to {to_iso(stop)}, step {args.step})")
    checks = {}
    passed = True
    for body, track in tracks.items():
        check = crosscheck_against_analytic(track, tolerance_deg=args.tolerance)
        checks[body] = check
        passed = passed and check.passed
        print(f"  {body:5s} {len(track):5d} samples  cross-check vs analytic: "
              f"max d-az {check.max_azimuth_deg:.3f} deg, max d-el {check.max_elevation_deg:.3f} deg "
              f"({check.tolerance_deg} deg allowed) {'ok' if check.passed else 'FAILED'}")

    print_table(tracks)
    if args.out:
        payload = build_payload(observer, label, tracks, checks, start, stop, args.step)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"wrote {args.out} ({len(payload['samples'])} samples, schema {SCHEMA})")
    if not passed:
        print("Cross-check failed: the downloaded geometry disagrees with the analytic model.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
