"""Record the wide-area LOLA DEM that extends the site horizon masks.

The PGDA 5 m/pixel site DEMs are only 16 km wide, so a mask built from one alone
stops 6-8 km from the site. This script describes the 80 m/pixel south-polar DEM
that covers 80 S to the pole (+/-304 km), which `build_site_horizon_masks.py`
ray-marches from where the finer DEM ends out to 150 km.

Output: data/reference/wide_dem.json (`schema: lunanav.wide_terrain.v1`), with
the file's metadata, checksum, height convention and each candidate's height in
the wide grid compared with its 5 m/pixel value. The DEM itself (~181 MB) stays
in data/cache/lola_wide/ (git ignored).

Usage (from backend/):
    python scripts/inspect_wide_terrain.py --download     # fetch if missing, write the reference
    python scripts/inspect_wide_terrain.py --verify-only  # re-derive from the cache, compare offline
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.terrain_inventory import (  # noqa: E402
    MOON_RADIUS_M,
    site_xy_m,
    terrain_payload,  # noqa: F401 - imported for its conventions, not called
)

SCHEMA = "lunanav.wide_terrain.v1"
FILE = "LDEM_80S_80MPP_ADJ.TIF"
URL = "https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_80MPP_ADJ.TIF"
LANDING = "https://pgda.gsfc.nasa.gov/products/90"
CACHE = ROOT / "data" / "cache" / "lola_wide"
DEFAULT_OUT = ROOT / "data" / "reference" / "wide_dem.json"
TERRAIN = ROOT / "data" / "reference" / "site_terrain.json"
CONFIG = ROOT / "config" / "lunanav.config.json"
PIXEL_M = 80.0
LAT_LIMIT_DEG = -80.0
FAR_RANGE_M = 150_000.0
SITE_TOLERANCE_M = 250.0

LIMITATIONS = {
    "resolution": (
        "80 m/pixel, so the far tier resolves hills, crater rims and massifs hundreds of metres "
        "across, not boulders or the landing ellipse."
    ),
    "range": (
        "The ray-march stops at 150 km. Terrain beyond that can still block a body at the horizon, "
        "but at these sites its elevation angle is below the near-field skyline."
    ),
    "datum": (
        "Heights are metres above the 1737.4 km sphere (the Moon has no geoid). The file's height "
        "convention is detected from the data and recorded in `height`."
    ),
    "two_tiers": (
        "The mask takes the maximum of the 5 m near tier (to the site DEM edge) and this 80 m far "
        "tier (to 150 km). A coarser grid can miss a narrow ridge, so the far tier is a lower "
        "bound on obstruction beyond ~8 km, not an exact skyline."
    ),
    "scope": "Terrain obstruction only; no power, communications, thermal or hazard meaning.",
}


def _sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(path: Path, timeout: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    print(f"downloading {URL}")
    with urllib.request.urlopen(URL, timeout=timeout) as res, open(tmp, "wb") as fh:  # noqa: S310
        while chunk := res.read(1 << 22):
            fh.write(chunk)
    tmp.replace(path)


def _site_height(ds, x_m: float, y_m: float) -> tuple[float, str]:
    """Height at the site from the nearest 80 m cell, and the raw stored value."""
    row, col = ds.index(x_m, y_m)
    if not (0 <= row < ds.height and 0 <= col < ds.width):
        raise SystemExit(f"site ({x_m:.0f}, {y_m:.0f}) m lies outside {Path(ds.name).name}")
    raw = float(ds.read(1, window=((row, row + 1), (col, col + 1)))[0, 0])
    return raw, f"nearest 80 m cell row {row}, col {col}"


def build(args) -> dict:
    path = CACHE / FILE
    if not path.exists():
        if not args.download:
            raise SystemExit(
                f"missing {path}; run `python scripts/inspect_wide_terrain.py --download` "
                f"to fetch {URL} (~181 MB)"
            )
        _download(path, args.timeout)

    import rasterio  # optional dependency

    terrain = json.loads(TERRAIN.read_text())
    config = json.loads(CONFIG.read_text())
    candidates = config["mission"]["candidate_sites"]
    with rasterio.open(path) as ds:
        if abs(float(ds.res[0]) - PIXEL_M) > 1e-6:
            raise SystemExit(f"{path.name}: pixel {ds.res[0]} m, expected {PIXEL_M}")
        if not ds.crs or "1737400" not in ds.crs.to_wkt().replace(" ", ""):
            raise SystemExit(f"{path.name}: CRS is not the 1737.4 km lunar sphere frame")
        bounds = {"left": float(ds.bounds.left), "bottom": float(ds.bounds.bottom),
                  "right": float(ds.bounds.right), "top": float(ds.bounds.top)}
        preview = ds.read(1, out_shape=(1024, 1024)).astype(float)
        if ds.nodata is not None and np.isfinite(ds.nodata):
            preview[preview == ds.nodata] = np.nan
        finite = preview[np.isfinite(preview)]
        samples, offset, raw_samples = {}, None, []
        for site_id in candidates:
            near = terrain["sites"][site_id]["site_pixel"]["elevation_m"]
            x_m, y_m = site_xy_m(terrain["sites"][site_id]["latitude_deg"],
                                 terrain["sites"][site_id]["longitude_deg"])
            raw, how = _site_height(ds, x_m, y_m)
            raw_samples.append(raw)
            # A PDS shape map stores radius (~1.737e6 m); a DEM stores height (~2e3 m).
            if abs(raw) > 1.0e6:
                height = raw - MOON_RADIUS_M
            else:
                height = raw
            samples[site_id] = {
                "xy_km": [round(x_m / 1000.0, 3), round(y_m / 1000.0, 3)],
                "wide_elevation_m": round(height, 3),
                "near_elevation_m": near,
                "difference_m": round(height - near, 3),
                "sample": how,
            }
        height_offset = float(np.median(raw_samples))
        is_radius = abs(height_offset) > 1.0e6
        reference = {
            "schema": SCHEMA,
            "dataset": "Wide-area LOLA south-polar DEM (far horizon tier)",
            "generated_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
            "generator": "backend/scripts/inspect_wide_terrain.py",
            "source": {
                "label": "LOLA 80 m/pix south polar DEM, LDEM_80S_80MPP_ADJ (80 S to the pole)",
                "provider": "NASA GSFC Planetary Geodynamics Laboratory (PGDA)",
                "url": LANDING,
                "data": URL,
                "citation": "Barker et al. 2023, Planet. Sci. J. 4, 183",
                "data_doi": "10.60903/gsfcpgda-lola-spole",
                "coverage": "80 S to the south pole (stereographic radius ~304 km)",
            },
            "dem": {
                "file": FILE,
                "driver": ds.driver,
                "width": int(ds.width),
                "height": int(ds.height),
                "dtype": ds.dtypes[0],
                "pixel_m": float(ds.res[0]),
                "extent_km": [round(ds.width * ds.res[0] / 1000.0, 3),
                              round(ds.height * ds.res[1] / 1000.0, 3)],
                "bounds_m": bounds,
                "crs_wkt": ds.crs.to_wkt(),
                "nodata": "nan" if ds.nodata is None or not np.isfinite(ds.nodata) else ds.nodata,
                "elevation_preview_range_m": [round(float(finite.min()), 2),
                                              round(float(finite.max()), 2)],
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "url": URL,
            },
            "height": {
                "raw_sample_m": round(float(height_offset), 1),
                "convention": ("radius above the Moon's centre (converted by subtracting 1737.4 km)"
                               if is_radius else "metres above the 1737.4 km reference sphere"),
                "offset_m": round(-MOON_RADIUS_M, 1) if is_radius else 0.0,
            },
            "sites": samples,
            "far_range_m": FAR_RANGE_M,
            "limitations": LIMITATIONS,
        }
    if not is_radius:
        worst = max(abs(s["difference_m"]) for s in samples.values())
        if worst > SITE_TOLERANCE_M:
            raise SystemExit(
                f"the wide DEM disagrees with the 5 m site elevations by up to {worst:.0f} m; "
                "the height convention or datum is not what this script assumes"
            )
    return reference


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--download", action="store_true", help="fetch the DEM if it is missing (~181 MB)")
    ap.add_argument("--verify-only", action="store_true",
                    help="re-derive from the cached DEM and compare with the committed reference")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--timeout", type=float, default=600.0)
    args = ap.parse_args(argv)

    if args.verify_only and not args.out.exists():
        print(f"FAIL: {args.out} does not exist", file=sys.stderr)
        return 1
    fresh = build(args)

    if args.verify_only:
        stored = json.loads(args.out.read_text())
        problems = []
        if stored.get("schema") != SCHEMA:
            problems.append(f"schema {stored.get('schema')!r}")
        for key in ("dem", "height", "sites", "far_range_m", "limitations"):
            if stored.get(key) != fresh[key]:
                problems.append(key)
        if problems:
            print(f"FAIL: {args.out} does not match the cached DEM: {', '.join(problems)}")
            return 1
        print(f"verified {args.out.name}: {len(fresh['sites'])} sites match the cached wide DEM "
              "(timestamps excluded)")
        return 0

    args.out.write_text(json.dumps(fresh, indent=1) + "\n")
    dem = fresh["dem"]
    print(f"wrote {args.out.name}: {dem['width']}x{dem['height']} px, {dem['pixel_m']} m/px, "
          f"{dem['extent_km'][0]:.0f} km across, heights {fresh['height']['convention']}")
    worst = max(abs(s["difference_m"]) for s in fresh["sites"].values())
    print(f"  widest site difference from the 5 m DEM: {worst:.1f} m; far range {FAR_RANGE_M/1000:.0f} km")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
