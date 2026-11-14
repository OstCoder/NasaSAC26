"""Build the south-pole PSR catalogue from the LROC PSR boundary shapefile.

Source (NASA/LROC, public):
  https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_POLE_PSR_SOUTH
  Zip: NAC_POLE_PSR_SOUTH.ZIP (shapefile "LOLA_PSR_75S_120M_82S_060M_5KM2_FINAL")
  - Permanently shadowed regions (PSRs) larger than 5 km2, 75 S to 90 S,
    digitised by the LROC team from LOLA-derived permanent-shadow masks
    (Mazarico et al., 2011, Icarus 211, 1066).
  - Projection: south polar stereographic, sphere radius 1737.4 km,
    standard parallel -90, central meridian 0. Units: metres.

The output JSON stores each PSR with its rings in the same projected
kilometre frame as the frontend map (features/lunar-map/projection.ts), so
polygons can be drawn and distances computed without reprojection.

Requires: pyshp (pip install pyshp). Optionally a shapefile directory already
unzipped; otherwise pass --zip and it is downloaded and extracted.

Usage (from backend/):
  python scripts/build_psr_catalogue.py \
      --shapefile /path/to/LOLA_PSR_75S_120M_82S_060M_5KM2_FINAL.shp \
      --out ../data/reference/psrs.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import zipfile
from pathlib import Path

import numpy as np

try:
    import shapefile  # pyshp
except ImportError as exc:  # pragma: no cover
    raise SystemExit("pyshp is required: pip install pyshp") from exc

ROOT = Path(__file__).resolve().parents[2]
CRATERS = ROOT / "data" / "reference" / "moon_craters.json"

ZIP_URL = (
    "https://pds.lroc.im-ldi.com/data/LRO-L-LROC-5-RDR-V1.0/LROLRC_2001/"
    "EXTRAS/BROWSE/NAC_POLE/NAC_POLE_PSR_SOUTH/NAC_POLE_PSR_SOUTH.ZIP"
)

# Great-circle distance from a PSR centroid to a crater centre must be below
# (crater radius + this margin) for the PSR to be tagged with that crater.
NEAR_CRATER_MARGIN_KM = 6.0


def great_circle_km(lat1, lon1, lat2, lon2, radius_km=1737.4):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius_km * math.asin(math.sqrt(min(1.0, max(0.0, a))))


def ring_km(points_m: list[tuple[float, float]]) -> list[list[float]]:
    """Projected metres -> compact ring in km, dropping a repeated closing vertex."""
    pts = [(round(x / 1000.0, 3), round(y / 1000.0, 3)) for x, y in points_m]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    return [[x, y] for x, y in pts]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--shapefile", type=Path, default=None,
                    help="Path to ...FINAL.shp (without extension is also accepted)")
    ap.add_argument("--zip", type=Path, default=None,
                    help="Path to a local NAC_POLE_PSR_SOUTH.ZIP; downloaded if absent")
    ap.add_argument("--url", default=ZIP_URL)
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "reference" / "psrs.json")
    args = ap.parse_args()

    shp = args.shapefile
    if shp is None:
        zip_path = args.zip or (ROOT / "data" / "cache" / "NAC_POLE_PSR_SOUTH.ZIP")
        if not zip_path.exists():
            import urllib.request

            zip_path.parent.mkdir(parents=True, exist_ok=True)
            print(f"downloading {args.url} ...")
            urllib.request.urlretrieve(args.url, zip_path)
        dest = zip_path.parent / "psr_south"
        if not dest.exists():
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(dest)
        shp = next(dest.glob("*.shp"))

    reader = shapefile.Reader(str(shp.with_suffix("")) if shp.suffix else str(shp))
    craters = json.loads(CRATERS.read_text())["craters"]

    psrs = []
    for idx, sr in enumerate(reader.iterShapeRecords()):
        rec = sr.record.as_dict()
        shape = sr.shape
        parts = list(shape.parts) + [len(shape.points)]
        rings = [
            ring_km(shape.points[a:b]) for a, b in zip(parts[:-1], parts[1:]) if b - a >= 3
        ]
        if not rings:
            continue

        lat, lon = float(rec["latitude"]), float(rec["longitude"])
        near = None
        best_gap = None
        for c in craters:
            d = great_circle_km(lat, lon, c["latitude_deg"], c["longitude_deg"])
            gap = d - c["diameter_km"] / 2.0
            if gap <= NEAR_CRATER_MARGIN_KM and (best_gap is None or gap < best_gap):
                best_gap, near = gap, c["name"]

        psrs.append({
            "psr_id": rec["PSR_ID"],
            "area_km2": round(float(rec["area"]), 3),
            "perimeter_km": round(float(rec["perimeter"]), 3),
            "centroid_latitude_deg": round(lat, 4),
            "centroid_longitude_deg": round(((lon + 180.0) % 360.0) - 180.0, 4),
            "near_crater": near,
            "rings": rings,
        })

    psrs.sort(key=lambda p: p["psr_id"])
    out = {
        "dataset": "South-pole permanently shadowed regions (PSRs) larger than 5 km2",
        "version": "1.0.0",
        "generated_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "source": {
            "provider": "NASA/GSFC/Arizona State University LROC team",
            "product": "NAC_POLE_PSR_SOUTH companion shapefile (LOLA_PSR_75S_120M_82S_060M_5KM2_FINAL)",
            "page": "https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_POLE_PSR_SOUTH",
            "atlas": "http://lroc.sese.asu.edu/psr",
            "derived_from": "LOLA permanent-shadow masks (Mazarico et al. 2011, Icarus 211, 1066-1081)",
        },
        "projection": {
            "name": "south polar stereographic",
            "sphere_radius_km": 1737.4,
            "standard_parallel_deg": -90,
            "central_meridian_deg": 0,
            "ring_units": "km",
            "x": "rho*sin(lon_east_positive), 90E to the right",
            "y": "rho*cos(lon_east_positive), 0 meridian up",
        },
        "notes": [
            "Rings are closed by implicit wrap; the closing vertex is not repeated.",
            "Multi-part polygons are stored as independent rings; holes are not used by this product.",
            "Boundaries trace the LOLA permanent-shadow mask; the 5 km2 area threshold excludes smaller PSRs.",
            "near_crater names the IAU crater whose centre is closest (within crater radius + 6 km); "
            "it is a label, not a claim that the PSR lies inside that crater.",
        ],
        "count": len(psrs),
        "psrs": psrs,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, separators=(",", ":")))
    size_kb = args.out.stat().st_size / 1024
    print(f"wrote {args.out}: {len(psrs)} PSRs, {size_kb:.0f} KB")


if __name__ == "__main__":
    main()
