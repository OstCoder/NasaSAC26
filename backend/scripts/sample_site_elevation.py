"""Sample LOLA surface elevation (and slope / height uncertainty) at landing sites.

Uses the PGDA 5 m/pixel LOLA site DEMs:
  https://pgda.gsfc.nasa.gov/products/78  (Barker et al. 2021, PSS 203, 105119)
  Directory: https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/
  - *_surf.tif: surface height Z in metres relative to the 1737.4 km sphere
  - *_slp.tif: slope in degrees
  - *_toterr.tif: total height uncertainty (RMS) in metres
  - South polar stereographic (same convention as app.core.coords.polar_stereographic_xy),
    MOON_ME frame, ephemeris DE421.

The site codes follow Mazarico et al. (2011, Icarus 211, 1066), which is also
where the candidate coordinates come from, so each DEM is centred on the very
point it is sampled at (verified by the script).

Requires: rasterio (pip install rasterio). DEMs (~41 MB each) are downloaded
once into data/cache/lola_5mpp/ and reused.

Usage (from backend/):
  python scripts/sample_site_elevation.py            # download if needed + sample
  python scripts/sample_site_elevation.py --download
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so "import app" works

from app.core.coords import polar_stereographic_xy  # noqa: E402

BASE_URL = "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp"
CACHE = ROOT / "data" / "cache" / "lola_5mpp"

# site_id -> PGDA site code (Mazarico et al. 2011 numbering). Sites not listed
# here have no 5 m/pix PGDA DEM yet.
SITE_CODES = {
    "connecting-ridge": "Site01",
    "shackleton-rim": "Site04",
    "peak-near-shackleton": "Site07",
    "de-gerlache-rim": "Site11",
}

# products: (suffix, description)
PRODUCTS = {"surf": "surface height Z (m, relative to the 1737.4 km sphere)",
            "slp": "slope (degrees)",
            "toterr": "total height uncertainty, RMS (m)"}

# sample window: 25 x 25 pixels = 125 m x 125 m
WINDOW_PX = 25


def fetch(site_code: str, product: str, download: bool) -> Path:
    name = f"{site_code}_final_adj_5mpp_{product}.tif"
    dest = CACHE / name
    if dest.exists():
        return dest
    if not download:
        raise SystemExit(f"missing {dest}; run with --download to fetch {BASE_URL}/{site_code}/{name}")
    import urllib.request

    CACHE.mkdir(parents=True, exist_ok=True)
    url = f"{BASE_URL}/{site_code}/{name}"
    print(f"downloading {url} ...")
    urllib.request.urlretrieve(url, dest)
    return dest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--download", action="store_true", help="download missing DEMs")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "reference" / "site_elevations.json")
    args = ap.parse_args()

    try:
        import rasterio
        import rasterio.windows
    except ImportError:
        raise SystemExit("rasterio is required: pip install rasterio")

    sites = json.loads((ROOT / "data" / "demo" / "sites.json").read_text())["sites"]
    out = {
        "dataset": "LOLA 5 m/pix site-DEM samples at the candidate coordinates",
        "generated_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "source": {
            "provider": "NASA GSFC Planetary Geodynamics Laboratory (PGDA)",
            "product": "High-Resolution LOLA Topography for Lunar South Pole Sites (5 m/pix)",
            "page": "https://pgda.gsfc.nasa.gov/products/78",
            "data": "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/",
            "papers": [
                "Mazarico et al. 2011, Icarus 211, 1066-1081 (site locations)",
                "Barker et al. 2021, Planet. Space Sci. 203, 105119 (DEM production)",
            ],
        },
        "method": {
            "sampling": f"median of a {WINDOW_PX}x{WINDOW_PX} pixel window "
                        f"({WINDOW_PX * 5} m x {WINDOW_PX * 5} m) centred on the site coordinate; "
                        "'center_px' is the single pixel containing the coordinate",
            "projection": "app.core.coords.polar_stereographic_xy (radius 1737.4 km)",
            "products": PRODUCTS,
        },
        "samples": {},
    }

    for s in sites:
        code = SITE_CODES.get(s["id"])
        if code is None:
            continue
        lat, lon = s["latitude_deg"], s["longitude_deg"]
        x_km, y_km = polar_stereographic_xy(lat, lon)
        entry = {"pgda_site": code, "latitude_deg": lat, "longitude_deg": lon,
                 "xy_km": [round(x_km, 3), round(y_km, 3)], "products": {}}
        with rasterio.open(fetch(code, "surf", args.download)) as ds:
            row, col = ds.index(x_km * 1000.0, y_km * 1000.0)
            entry["dem_center_km"] = [round((ds.bounds.left + ds.bounds.right) / 2 / 1000, 3),
                                      round((ds.bounds.bottom + ds.bounds.top) / 2 / 1000, 3)]
            entry["dem_center_offset_km"] = [round(entry["dem_center_km"][0] - x_km, 3),
                                             round(entry["dem_center_km"][1] - y_km, 3)]
            for product in PRODUCTS:
                with rasterio.open(fetch(code, product, args.download)) as pds:
                    win = rasterio.windows.Window(col - WINDOW_PX // 2, row - WINDOW_PX // 2,
                                                  WINDOW_PX, WINDOW_PX)
                    vals = pds.read(1, window=win)
                    vals = vals[np.isfinite(vals)]
                    center = float(pds.read(1, window=rasterio.windows.Window(col, row, 1, 1))[0, 0])
                    entry["products"][product] = {
                        "median": round(float(np.median(vals)), 2),
                        "center_px": round(center, 2),
                        "std": round(float(vals.std()), 2),
                        "min": round(float(vals.min()), 2),
                        "max": round(float(vals.max()), 2),
                        "pixels": int(vals.size),
                    }
        out["samples"][s["id"]] = entry
        p = entry["products"]
        print(f"{s['id']:22s} elev {p['surf']['median']:8.1f} m  "
              f"slope {p['slp']['median']:5.2f} deg  unc {p['toterr']['median']:4.2f} m  "
              f"DEM centre offset {entry['dem_center_offset_km']} km")

    args.out.write_text(json.dumps(out, indent=1))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
