"""Export compact site-DEM previews for the experimental 3D terrain view.

Phase 4 Task 6 wants the LOLA DEM around each candidate rendered in 3D. The
full 5 m/pix PGDA rasters are ~40 MB each and are not committed (data/cache/);
this script derives one small committed artifact per site instead:
a 128x128 metre-grid height sample of the site DEM (average-pooled), with the
source file, its SHA-256, the height convention and the stereo projection
recorded, so the number in the 3D view can be traced back to the raster.

Run from backend/ with the LOLA cache present:
    python scripts/export_site_dem_previews.py

Outputs data/scientific/site_dems/<site_id>.json. Safe to re-run: the output
is deterministic apart from generated_utc.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling

ROOT = Path(__file__).resolve().parents[2]
TERRAIN = ROOT / "data" / "reference" / "site_terrain.json"
CACHE = ROOT / "data" / "cache" / "lola_5mpp"
OUT_DIR = ROOT / "data" / "scientific" / "site_dems"

GRID = 128
SCHEMA = "lunanav.site_dem_preview.v1"
HEIGHT_CONVENTION = "metres above the 1737.4 km LOLA reference sphere (PGDA 5 m/pix site models, surf band)"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    terrain = json.loads(TERRAIN.read_text())
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated = 0
    for site_id, entry in terrain["sites"].items():
        source = CACHE / entry["dem"]["file"]
        if not source.exists():
            print(f"skip {site_id}: {source.name} not in cache "
                  "(run scripts/inspect_site_terrain.py --download)", file=sys.stderr)
            continue
        bounds = entry["dem"]["bounds_m"]
        with rasterio.open(source) as dataset:
            heights = dataset.read(1, out_shape=(GRID, GRID), resampling=Resampling.average)
            crs_wkt = dataset.crs.to_wkt() if dataset.crs else ""
        finite = np.isfinite(heights)
        filled = int((~finite).sum())
        if filled:
            fill = float(np.nanmin(heights)) if finite.any() else 0.0
            heights = np.where(finite, heights, fill)
        xy_m = (entry["xy_km"][0] * 1000.0, entry["xy_km"][1] * 1000.0)
        # cell size from the source raster, not the bounds (bounds match width*pixel exactly)
        cell_m = float(entry["dem"]["pixel_m"]) * entry["dem"]["width"] / GRID
        col = int(np.clip((xy_m[0] - bounds["left"]) / (bounds["right"] - bounds["left"]) * (GRID - 1), 0, GRID - 1))
        row = int(np.clip((bounds["top"] - xy_m[1]) / (bounds["top"] - bounds["bottom"]) * (GRID - 1), 0, GRID - 1))
        document = {
            "schema": SCHEMA,
            "site_id": site_id,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "generator": "backend/scripts/export_site_dem_previews.py",
            "source": {
                "label": f"LOLA 5 m/pix site DEM ({entry['pgda_site']}), surf band, average-pooled",
                "provider": "NASA GSFC Planetary Geodynamics Laboratory (PGDA)",
                "file": entry["dem"]["file"],
                "sha256": sha256(source),
                "citation": "Barker et al. 2023, Planet. Sci. J. 4, 183 (LOLA); site models via NASA Lunar Data Portal",
            },
            "height_convention": HEIGHT_CONVENTION,
            "grid": GRID,
            "cell_m": round(cell_m, 3),
            "extent_m": {
                "east_west": round(bounds["right"] - bounds["left"], 3),
                "north_south": round(bounds["top"] - bounds["bottom"], 3),
            },
            "bounds_m": bounds,
            "crs": "polar stereographic, latitude_of_origin -90, central_meridian 0 "
                   "(scale distortion < 0.2% at these latitudes; see docs/METHODOLOGY.md)",
            "crs_wkt": crs_wkt,
            "site_cell": {"col": col, "row": row},
            "site_height_m": round(float(heights[row, col]), 2),
            "nodata_fill_cells": filled,
            "heights_m": [[round(float(v), 1) for v in rowvals] for rowvals in heights],
        }
        out = OUT_DIR / f"{site_id}.json"
        out.write_text(json.dumps(document, indent=1) + "\n")
        print(f"wrote {out.relative_to(ROOT)} "
              f"({heights.min():.0f} to {heights.max():.0f} m, site cell {row},{col})")
        generated += 1
    print(f"{generated} site DEM previews")
    return 0 if generated else 1


if __name__ == "__main__":
    raise SystemExit(main())
