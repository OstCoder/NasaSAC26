"""Build the LOLA horizon masks for the mission candidates (Phase 2, Task 6).

Each mask is the skyline elevation every 1 deg of azimuth, ray-marched from the
site over the cached 5 m/pixel PGDA DEM out to the largest radius that stays
inside the raster (6.3-7.7 km), with lunar curvature included and the observer
2 m above the sampled ground. Output:

    data/scientific/horizon_masks/<site-id>.json

Usage (from backend/, needs the DEM cache and `pip install rasterio`):

    python scripts/build_site_horizon_masks.py
    python scripts/build_site_horizon_masks.py --verify-only   # offline check

The masks are committed: they are ~8 kB each and are what makes Scientific Mode
and terrain obstruction work without re-downloading 120 MB of DEM. The DEMs
stay in data/cache/ (git-ignored), described by data/reference/site_terrain.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.errors import LunaNavError  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.core.timeutil import to_iso  # noqa: E402
from app.services.horizon import build_horizon_mask_from_dem  # noqa: E402
from app.services.site_data import MASK_SCHEMA  # noqa: E402
from app.services.terrain_inventory import (  # noqa: E402
    file_sha256,
    read_dem,
    site_xy_m,
)

ROOT = Path(__file__).resolve().parents[2]
TERRAIN = ROOT / "data" / "reference" / "site_terrain.json"
CACHE = ROOT / "data" / "cache" / "lola_5mpp"
DEFAULT_OUT = ROOT / "data" / "scientific" / "horizon_masks"

AZIMUTH_STEP_DEG = 1.0
OBSERVER_HEIGHT_M = 2.0
# The terrain inventory measured the skyline at ground level (0 m eye). A 2 m
# observer sees near-field rims lower - by atan(2 m / distance) - which can be
# degrees for terrain a few metres away, so a mask may be lower, never higher.
INVENTORY_MAX_DROP_DEG = 15.0

LIMITATIONS = [
    "Radius is limited to the distance from the site to the nearest DEM edge "
    "(6.3-7.7 km): terrain beyond that - massifs and crater walls at 20-100 km - is not included, "
    "so the mask is a lower bound on obstruction.",
    "5 m/pixel horizontal resolution, ~0.3 m RMS height uncertainty (Barker et al. 2021). "
    "Rocks and lander-scale roughness are not resolved.",
    "Stereographic scale distortion (<0.2 % poleward of 85 S) and the 2 m observer height are "
    "the only approximations in the ray-march; lunar curvature is included.",
    "A clear skyline is not a landing certification and says nothing about thermal "
    "conditions, surface hazards or power.",
]


def _entry(terrain: dict, site_id: str) -> dict:
    try:
        return terrain["sites"][site_id]
    except KeyError as exc:
        raise SystemExit(f"{site_id!r} has no terrain reference entry") from exc


def build_mask(site_id: str, entry: dict, heights: np.ndarray,
               out_dir: Path) -> dict:
    dem = entry["dem"]
    bounds = dem["bounds_m"]
    x_m, y_m = site_xy_m(entry["latitude_deg"], entry["longitude_deg"])
    radius_m = float(entry["coverage"]["radius_km"]) * 1000.0
    mask = build_horizon_mask_from_dem(
        heights, bounds["left"], bounds["top"], float(dem["pixel_m"]), x_m, y_m,
        obs_height_m=OBSERVER_HEIGHT_M,
        azimuth_step_deg=AZIMUTH_STEP_DEG,
        max_range_m=radius_m,
        source=(f"LOLA 5 m/pix {dem['file']} ray-march to {radius_m / 1000:.3f} km, "
                f"observer {OBSERVER_HEIGHT_M:.0f} m, lunar curvature included"),
    )
    elevation = np.asarray(mask.elevation_deg, float)
    top = int(np.argmax(elevation))
    document = {
        "schema": MASK_SCHEMA,
        "site_id": site_id,
        "name": entry.get("name"),
        "latitude_deg": entry["latitude_deg"],
        "longitude_deg": entry["longitude_deg"],
        "elevation_m": entry["site_pixel"]["elevation_m"],
        "observer_height_m": OBSERVER_HEIGHT_M,
        "source": mask.source,
        "generated_utc": to_iso(datetime.now(timezone.utc)),
        "generator": "backend/scripts/build_site_horizon_masks.py",
        "dem": {
            "file": dem["file"],
            "sha256": dem["sha256"],
            "pixel_m": dem["pixel_m"],
            "bounds_m": bounds,
        },
        "max_range_m": round(radius_m, 3),
        "azimuth_step_deg": AZIMUTH_STEP_DEG,
        "inventory": {
            "max_obstruction_deg": entry["terrain"]["max_obstruction_deg"],
            "max_obstruction_azimuth_deg": entry["terrain"]["max_obstruction_azimuth_deg"],
            "observer_height_m": 0.0,
        },
        "summary": {
            "max_obstruction_deg": round(float(elevation.max()), 4),
            "max_obstruction_azimuth_deg": round(float(mask.azimuth_deg[top]), 1),
            "min_obstruction_deg": round(float(elevation.min()), 4),
            "mean_obstruction_deg": round(float(elevation.mean()), 4),
        },
        "azimuth_deg": [float(value) for value in mask.azimuth_deg],
        "elevation_deg": [round(float(value), 4) for value in elevation],
        "limitations": LIMITATIONS,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{site_id}.json").write_text(json.dumps(document, indent=1) + "\n")
    return document


def build(site_ids: list[str] | None = None, out_dir: Path = DEFAULT_OUT) -> list[dict]:
    settings = get_settings()
    terrain = json.loads(TERRAIN.read_text())
    wanted = site_ids or list(settings.raw["mission"]["candidate_sites"])
    documents = []
    for site_id in wanted:
        entry = _entry(terrain, site_id)
        path = CACHE / entry["dem"]["file"]
        if not path.exists():
            raise SystemExit(
                f"missing {path}; fetch the DEMs first with "
                "`python scripts/inspect_site_terrain.py --download`"
            )
        info, heights = read_dem(path)
        if info["sha256"] != entry["dem"]["sha256"]:
            raise SystemExit(
                f"{path.name} checksum {info['sha256']} does not match the terrain reference "
                f"{entry['dem']['sha256']} - refusing to build a mask from a different file"
            )
        document = build_mask(site_id, entry, heights, out_dir)
        print(f"{site_id}: {len(document['azimuth_deg'])} azimuths, "
              f"max obstruction {document['summary']['max_obstruction_deg']} deg at "
              f"{document['summary']['max_obstruction_azimuth_deg']} deg, "
              f"range {document['max_range_m'] / 1000:.3f} km")
        documents.append(document)
    return documents


def verify(out_dir: Path = DEFAULT_OUT) -> int:
    """Check the committed masks against the terrain reference. Reads files only."""
    terrain = json.loads(TERRAIN.read_text())
    candidates = list(get_settings().raw["mission"]["candidate_sites"])
    problems: list[str] = []
    files = sorted(out_dir.glob("*.json")) if out_dir.exists() else []
    if {path.stem for path in files} != set(candidates):
        problems.append(
            f"{out_dir.name} holds {sorted(path.stem for path in files)}, "
            f"candidates are {sorted(candidates)}"
        )
    print(f"{'site':22s} {'points':>6s} {'radius':>7s} {'max obs':>8s}  checks")
    for site_id in candidates:
        path = out_dir / f"{site_id}.json"
        issues: list[str] = []
        if not path.exists():
            problems.append(f"{site_id}: missing mask")
            print(f"{site_id:22s} {'-':>6s} {'-':>7s} {'-':>8s}  FAILED: missing")
            continue
        document = json.loads(path.read_text())
        entry = _entry(terrain, site_id)
        azimuth = np.asarray(document.get("azimuth_deg") or [], float)
        elevation = np.asarray(document.get("elevation_deg") or [], float)
        if document.get("schema") != MASK_SCHEMA:
            issues.append(f"schema {document.get('schema')!r}")
        if document.get("site_id") != site_id:
            issues.append(f"site_id {document.get('site_id')!r}")
        if azimuth.size != elevation.size or azimuth.size != int(360 / AZIMUTH_STEP_DEG):
            issues.append(f"{azimuth.size} azimuth points")
        if not np.all(np.isfinite(elevation)):
            issues.append("non-finite elevation")
        if np.any(np.diff(azimuth) <= 0) or azimuth[0] != 0.0 or azimuth[-1] >= 360.0:
            issues.append("azimuth grid is not 0..360")
        for key, tol in (("latitude_deg", 1e-6), ("longitude_deg", 1e-6)):
            if abs(float(document.get(key, 1e9)) - float(entry[key])) > tol:
                issues.append(f"{key} disagrees with the terrain reference")
        if abs(float(document.get("elevation_m", 1e9)) - float(entry["site_pixel"]["elevation_m"])) > 0.05:
            issues.append("site elevation disagrees with the terrain reference")
        dem = document.get("dem") or {}
        if dem.get("file") != entry["dem"]["file"] or dem.get("sha256") != entry["dem"]["sha256"]:
            issues.append("DEM file/checksum disagrees with the terrain reference")
        want_range = float(entry["coverage"]["radius_km"]) * 1000.0
        if abs(float(document.get("max_range_m", -1)) - want_range) > 1e-6:
            issues.append(f"max_range_m {document.get('max_range_m')} != {want_range:.3f}")
        measured = float(np.max(elevation)) if elevation.size else None
        inventory = float(entry["terrain"]["max_obstruction_deg"])
        recorded = (document.get("inventory") or {}).get("max_obstruction_deg")
        if recorded != inventory:
            issues.append(f"inventory record {recorded!r} != {inventory}")
        # A 2 m eye can only lower the skyline relative to the ground-level inventory.
        if measured is None or not (inventory - INVENTORY_MAX_DROP_DEG <= measured <= inventory + 1e-6):
            issues.append(f"max obstruction {measured} deg vs ground-level inventory {inventory} deg")
        if document.get("summary", {}).get("max_obstruction_deg") != round(measured, 4):
            issues.append("recorded summary does not match the elevation array")
        if not document.get("limitations"):
            issues.append("no limitations recorded")
        problems.extend(f"{site_id}: {issue}" for issue in issues)
        print(f"{site_id:22s} {azimuth.size:6d} {want_range / 1000:6.2f}k "
              f"{measured if measured is None else round(measured, 2):8.2f}  "
              f"{'ok' if not issues else 'FAILED: ' + '; '.join(issues)}")
    print("all horizon masks verified" if not problems else f"{len(problems)} problem(s) found")
    for problem in problems:
        print(f"  FAILED: {problem}", file=sys.stderr)
    return 0 if not problems else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build LOLA horizon masks for the mission candidates.")
    ap.add_argument("--site", action="append", help="site id (repeatable; default: candidates)")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--verify-only", action="store_true",
                    help="check the committed masks against the terrain reference (offline)")
    args = ap.parse_args(argv)
    if args.verify_only:
        return verify(args.out_dir)
    try:
        documents = build(args.site, args.out_dir)
    except LunaNavError as exc:
        print(f"FAILED: {exc.message}", file=sys.stderr)
        return 1
    print(f"wrote {len(documents)} mask(s) to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
