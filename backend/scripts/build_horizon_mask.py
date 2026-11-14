"""Build a Scientific-Mode horizon mask from any LOLA polar stereographic DEM.

This is the generic one-off entry point. The mission's committed masks come from
`build_site_horizon_masks.py`, which combines a 5 m/pixel site DEM with the 80
m/pixel wide polar DEM; use this script for a custom site or a single DEM.

Usage (from backend/, requires `pip install rasterio`):
    python scripts/build_horizon_mask.py \
        --dem LDEM_875S_20M.tif --site-id malapert-massif --lat -85.99 --lon 2.9

Source DEMs: the PGDA LOLA products (https://pgda.gsfc.nasa.gov/products/90 for
the wide polar DEMs, https://pgda.gsfc.nasa.gov/products/78 for 5 m/pixel site
DEMs). Heights must be metres above the 1737.4 km sphere; pass --offset -1737400
for a PDS shape map that stores radius, or --scale 1000 for a kilometre grid.

Output: data/scientific/horizon_masks/<site-id>.json in the same
`lunanav.horizon_mask.v1` format the API reads (360 azimuths, summary,
limitations, DEM checksum), so it passes `--verify-only` conventions.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.coords import polar_stereographic_xy  # noqa: E402
from app.core.timeutil import to_iso  # noqa: E402
from app.services.horizon import build_horizon_mask_from_dem  # noqa: E402
from app.services.site_data import MASK_SCHEMA  # noqa: E402
from app.services.terrain_inventory import file_sha256  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "scientific" / "horizon_masks"

LIMITATIONS = [
    "Single DEM, so the mask stops at that file's edge or the requested range, whichever is "
    "closer; check max_range_m before treating distant terrain as known.",
    "Resolution, height uncertainty and the observer height are those of the input product and "
    "the --height/--range-km values passed here.",
    "Lunar curvature is included; stereographic scale distortion (<0.2 % poleward of 85 S) is not.",
    "A clear skyline is not a landing certification and says nothing about power.",
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build one horizon mask from a lunar polar DEM.")
    ap.add_argument("--dem", required=True)
    ap.add_argument("--site-id", required=True)
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--height", type=float, default=2.0)
    ap.add_argument("--range-km", type=float, default=150)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--offset", type=float, default=0.0,
                    help="added after --scale, e.g. -1737400 for a radius shape map")
    ap.add_argument("--out-dir", type=Path, default=OUT)
    args = ap.parse_args(argv)

    import rasterio  # optional dependency

    dem_path = Path(args.dem)
    with rasterio.open(dem_path) as ds:
        dem = ds.read(1).astype(float) * args.scale + args.offset
        if ds.nodata is not None:
            dem[dem == ds.nodata * args.scale + args.offset] = np.nan
        transform = ds.transform
        x0, y0, pixel = transform.c, transform.f, transform.a
        bounds = {"left": float(ds.bounds.left), "bottom": float(ds.bounds.bottom),
                  "right": float(ds.bounds.right), "top": float(ds.bounds.top)}
        rows, cols = ds.height, ds.width
        print(f"CRS: {ds.crs} - confirm it is lunar south polar stereographic, metres")

    x_km, y_km = polar_stereographic_xy(args.lat, args.lon)
    ox, oy = x_km * 1000.0, y_km * 1000.0
    if not (bounds["left"] <= ox <= bounds["right"] and bounds["bottom"] <= oy <= bounds["top"]):
        raise SystemExit(f"({args.lat}, {args.lon}) is outside {dem_path.name}")
    row = int(np.clip((y0 - oy) / pixel, 0, rows - 1))
    col = int(np.clip((ox - x0) / pixel, 0, cols - 1))
    site_elevation = round(float(dem[row, col]), 2)
    mask = build_horizon_mask_from_dem(
        dem, x0, y0, pixel, ox, oy, obs_height_m=args.height,
        max_range_m=args.range_km * 1000.0,
        source=f"LOLA DEM {dem_path.name} ray-march ({args.range_km:g} km)",
    )
    elevation = np.asarray(mask.elevation_deg, float)
    top = int(np.argmax(elevation))
    document = {
        "schema": MASK_SCHEMA,
        "site_id": args.site_id,
        "name": args.site_id.replace("-", " ").title(),
        "latitude_deg": args.lat,
        "longitude_deg": args.lon,
        "elevation_m": site_elevation,
        "observer_height_m": args.height,
        "source": mask.source,
        "generated_utc": to_iso(datetime.now(timezone.utc)),
        "generator": "backend/scripts/build_horizon_mask.py",
        "dem": {
            "file": dem_path.name,
            "sha256": file_sha256(dem_path),
            "pixel_m": float(pixel),
            "bounds_m": bounds,
        },
        "max_range_m": float(args.range_km) * 1000.0,
        "azimuth_step_deg": 1.0,
        "tiers": {
            "near": {
                "dem": dem_path.name,
                "pixel_m": float(pixel),
                "min_range_m": 0.0,
                "max_range_m": float(args.range_km) * 1000.0,
                "max_obstruction_deg": round(float(elevation.max()), 4),
                "max_obstruction_azimuth_deg": round(float(mask.azimuth_deg[top]), 1),
            },
            "far": None,
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
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / f"{args.site_id}.json"
    out.write_text(json.dumps(document, indent=1) + "\n")
    print(f"wrote {out} ({document['summary']['max_obstruction_deg']} deg max at "
          f"{document['summary']['max_obstruction_azimuth_deg']} deg, range "
          f"{document['max_range_m'] / 1000:.0f} km)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
