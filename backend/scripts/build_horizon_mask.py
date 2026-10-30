"""Build a Scientific-Mode horizon mask from a LOLA polar stereographic DEM.

Usage (from backend/, requires `pip install rasterio`):
    python scripts/build_horizon_mask.py \
        --dem LDEM_875S_20M.tif --site-id malapert-massif --lat -85.99 --lon 2.9

Source DEMs: LRO LOLA polar gridded products at the PDS Geosciences Node
(https://pds-geosciences.wustl.edu/missions/lro/lola.htm). Use a product whose
extent covers the observer plus the ray-march range (default 150 km).

The DEM must be south polar stereographic in metres with heights in metres
(LOLA LDEM products store km offsets from 1737.4 km in some versions; pass
--scale 1000 if so). Output: data/scientific/horizon_masks/<site-id>.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.horizon import build_horizon_mask_from_dem  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "scientific" / "horizon_masks"
R_M = 1_737_400.0


def polar_stereo_xy(lat_deg: float, lon_deg: float) -> tuple[float, float]:
    """South polar stereographic (true scale at the pole), metres."""
    rho = 2 * R_M * np.tan(np.radians(90 + lat_deg) / 2)
    return rho * np.sin(np.radians(lon_deg)), rho * np.cos(np.radians(lon_deg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dem", required=True)
    ap.add_argument("--site-id", required=True)
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--height", type=float, default=2.0)
    ap.add_argument("--range-km", type=float, default=150)
    ap.add_argument("--scale", type=float, default=1.0)
    a = ap.parse_args()

    import rasterio  # optional dependency

    with rasterio.open(a.dem) as ds:
        dem = ds.read(1).astype(float) * a.scale
        if ds.nodata is not None:
            dem[dem == ds.nodata * a.scale] = np.nan
        tr = ds.transform
        x0, y0, px = tr.c, tr.f, tr.a
        print("CRS:", ds.crs, "— confirm it is lunar south polar stereographic, metres.")
    ox, oy = polar_stereo_xy(a.lat, a.lon)
    mask = build_horizon_mask_from_dem(
        dem, x0, y0, px, ox, oy, obs_height_m=a.height, max_range_m=a.range_km * 1000,
        source=f"LOLA DEM {Path(a.dem).name} ray-march ({a.range_km} km)",
    )
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{a.site_id}.json"
    out.write_text(json.dumps({
        "site_id": a.site_id, "latitude_deg": a.lat, "longitude_deg": a.lon,
        "source": mask.source, "dem": Path(a.dem).name, "observer_height_m": a.height,
        "azimuth_deg": mask.azimuth_deg.tolist(), "elevation_deg": mask.elevation_deg.round(4).tolist(),
    }))
    print("wrote", out)


if __name__ == "__main__":
    main()
