"""Inspect the terrain around each mission candidate and record what the DEMs cover.

Downloads the NASA PGDA 5 m/pixel LOLA site DEMs (products/78) for the three
mission candidates, then derives from the files themselves:

  * georeferencing: CRS, pixel size, extent, bounds, height range, checksum;
  * coverage: whether the site is inside the raster and how far a ray-march can
    travel before it leaves the file;
  * relief: skyline obstruction angle per azimuth out to that radius, using the
    same ray-march (curvature included) that Phase 3 horizon masks use;
  * capability of the Moon Trek LOLA layer at the site (coverage only - those
    8-bit tiles are display imagery and are never used for numbers).

Output: data/reference/site_terrain.json (committed; the DEMs themselves are
~41 MB each and stay in data/cache/, which git ignores).

Usage (from backend/):
    python scripts/inspect_site_terrain.py --download    # fetch missing DEMs, write the reference
    python scripts/inspect_site_terrain.py --verify-only # re-derive from the cache, compare with the file
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.terrain_inventory import (  # noqa: E402
    PGDA_BASE_URL,
    PGDA_SITE_CODES,
    PRODUCTS,
    coverage,
    dem_filename,
    dem_url,
    file_sha256,
    read_dem,
    relief_summary,
    site_xy_m,
    terrain_payload,
)

CACHE = ROOT / "data" / "cache" / "lola_5mpp"
DEFAULT_OUT = ROOT / "data" / "reference" / "site_terrain.json"
CONFIG = ROOT / "config" / "lunanav.config.json"

QUICKMAP_URL = "https://quickmap.lroc.asu.edu/"
TREK_URL = "https://trek.nasa.gov/moon/"
PGDA_PAGE = "https://pgda.gsfc.nasa.gov/products/78"

LIMITATIONS = {
    "extent": (
        "Each 5 m/pix site DEM is 16 km x 16 km, so the ray-march radius is limited to the "
        "distance from the site to the nearest edge (6-9 km). Terrain beyond that - including "
        "the massifs and crater walls that matter at 20-100 km - is NOT in these files."
    ),
    "resolution": "5 m/pixel horizontal, ~0.3 m RMS height uncertainty (Barker et al. 2021).",
    "observer_height": (
        "The obstruction angles here use a ground-level (0 m) observer. The Phase 3 horizon "
        "masks sample the same skyline from the 2 m eye used for the Sun/Earth track, which "
        "lowers near-field angles by atan(2 m / distance) - up to ~8 deg for a rim 15 m away. "
        "Use the masks, not these summary angles, for visibility."
    ),
    "wider_context": (
        "For horizons beyond ~9 km use a wider LOLA polar product in the same stereographic "
        "frame, e.g. LDEM_875S_20M (20 m/pix, south of 87.5 S) from the PDS Geosciences Node, "
        "and record it here before quoting angles from it."
    ),
    "singularities": (
        "Heights are relative to the 1737.4 km sphere, not to a geoid (the Moon has none). "
        "Slope and horizon angles assume local north points away from the pole; the pole itself "
        "is excluded (azimuth undefined)."
    ),
    "gaps": "NaN marks no-data cells at the raster edges; they are counted, never filled with zero.",
    "display_layers": (
        "Moon Trek LOLA tiles are 8-bit display imagery: they confirm layer coverage at the "
        "site and are never used for heights or angles."
    ),
    "scope": (
        "Terrain gives geometric obstruction only. It does not model lander height beyond the "
        "recorded observer, rocks, thermal conditions or landing hazards, and a clear skyline "
        "is not a landing certification."
    ),
}


def _check_url(name: str, url: str, timeout: float) -> dict:
    entry = {"name": name, "url": url, "checked_utc": dt.datetime.now(dt.timezone.utc)
             .replace(microsecond=0).isoformat()}
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "LunaNav/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as res:  # noqa: S310 - fixed https URLs
            entry["http_status"] = res.status
    except Exception as exc:  # reachability is reported, it does not abort the run
        entry["http_status"] = None
        entry["error"] = f"{type(exc).__name__}: {exc}"
    return entry


def _download(path: Path, url: str, timeout: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    print(f"  downloading {url}")
    with urllib.request.urlopen(url, timeout=timeout) as res, open(tmp, "wb") as fh:  # noqa: S310
        while chunk := res.read(1 << 20):
            fh.write(chunk)
    tmp.replace(path)


def _trek_check(site: dict) -> dict:
    """Confirm the Moon Trek LOLA layer actually has a tile at the site."""
    try:
        from app.services.imagery import get_imagery

        im = get_imagery()
        layer = im.layer("lola_dem")
        z = min(6, layer.max_zoom)
        cols, rows = 2 ** (z + 1), 2 ** z
        lon, lat = site["longitude_deg"], site["latitude_deg"]
        col = int((lon + 180.0) / 360.0 * cols) % cols
        row = min(int((90.0 - lat) / 180.0 * rows), rows - 1)
        tile = im.get_tile(layer, z, row, col)
        return {"layer": layer.id, "path": layer.path, "zoom": z, "row": row, "col": col,
                "available": tile is not None, "credit": layer.credit}
    except Exception as exc:
        return {"layer": "lola_dem", "available": None,
                "error": f"{type(exc).__name__}: {exc}"}


def build(args) -> dict:
    config = json.loads(CONFIG.read_text())
    candidates = config["mission"]["candidate_sites"]
    catalogue = {s["id"]: s for s in json.loads(
        (ROOT / "data" / "demo" / "sites.json").read_text())["sites"]}
    wanted = args.sites or candidates

    sites, resources = {}, []
    # --verify-only is a filesystem check and must not depend on the network.
    if not args.verify_only:
        resources.append(_check_url("NASA LROC QuickMap", QUICKMAP_URL, args.timeout))
        resources.append(_check_url("NASA Moon Trek", TREK_URL, args.timeout))
        resources.append(_check_url("NASA PGDA LOLA 5 m/pix south-pole DEMs", PGDA_PAGE, args.timeout))

    for site_id in wanted:
        if site_id not in PGDA_SITE_CODES:
            raise SystemExit(f"No PGDA 5 m/pix DEM published for {site_id!r} "
                             f"(known: {sorted(PGDA_SITE_CODES)})")
        site = catalogue[site_id]
        code = PGDA_SITE_CODES[site_id]
        url = dem_url(code)
        path = CACHE / dem_filename(code)
        print(f"{site_id} ({code})")
        if not path.exists():
            if not args.download:
                raise SystemExit(f"missing {path}; re-run with --download to fetch {url}")
            _download(path, url, args.timeout)
            resources.append(_check_url(f"{code} DEM file", url, args.timeout))

        info, heights = read_dem(path)
        x_m, y_m = site_xy_m(site["latitude_deg"], site["longitude_deg"])
        b = info["bounds_m"]
        cov = coverage(b["left"], b["bottom"], b["right"], b["top"], x_m, y_m)
        if not cov["site_inside"]:
            raise SystemExit(f"{site_id} lies outside {info['file']} - wrong DEM?")
        summary = relief_summary(heights, b["left"], b["top"], info["pixel_m"], x_m, y_m,
                                 cov["radius_km"] * 1000.0, args.azimuth_step)
        row = int((b["top"] - y_m) / info["pixel_m"])
        col = int((x_m - b["left"]) / info["pixel_m"])

        entry = {
            "name": site["name"],
            "pgda_site": code,
            "latitude_deg": site["latitude_deg"],
            "longitude_deg": site["longitude_deg"],
            "xy_km": [round(x_m / 1000.0, 3), round(y_m / 1000.0, 3)],
            "dem": {**info, "url": url, "product": PRODUCTS["surf"],
                    "products_available": {k: dem_url(code, k) for k in PRODUCTS}},
            "coverage": cov,
            "site_pixel": {"row": row, "col": col, "elevation_m": summary["site_elevation_m"]},
            "terrain": summary,
            "moon_trek": {"skipped": True} if (args.skip_trek or args.verify_only) else _trek_check(site),
        }
        sites[site_id] = entry
        print(f"  {info['file']}: {info['width']}x{info['height']} px, {info['pixel_m']} m/px, "
              f"extent {info['extent_km'][0]} km; site inside, usable radius {cov['radius_km']} km")
        print(f"  relief {summary['elevation_min_m']}..{summary['elevation_max_m']} m; "
              f"max obstruction {summary['max_obstruction_deg']} deg at "
              f"{summary['max_obstruction_azimuth_deg']} deg az; "
              f"gaps {summary['data_gaps']['nan_pixels']} px")
        if not args.skip_trek and entry["moon_trek"].get("available") is not None:
            print(f"  Moon Trek {entry['moon_trek']['layer']} tile available: "
                  f"{entry['moon_trek']['available']}")

    sources = [
        {"id": "pgda-lola-5mpp", "label": "LOLA 5 m/pix south-pole site DEMs (surface height)",
         "provider": "NASA GSFC Planetary Geodynamics Laboratory (PGDA)",
         "url": PGDA_PAGE, "data": PGDA_BASE_URL,
         "resolution": "5 m/pixel, 16 km x 16 km per site",
         "papers": ["Barker et al. 2021, Planet. Space Sci. 203, 105119",
                    "Mazarico et al. 2011, Icarus 211, 1066-1081 (site numbering)"]},
        {"id": "moon-trek-lola", "label": "Moon Trek LRO LOLA shaded relief / DEM layer",
         "provider": "NASA/JPL Moon Trek", "url": TREK_URL,
         "resolution": "128 pixels/degree global (~237 m at the equator), 8-bit display tiles",
         "usage": "layer coverage check only; never used for heights or angles"},
        {"id": "lroc-quickmap", "label": "LROC QuickMap (visual terrain inspection)",
         "provider": "NASA / Arizona State University LROC", "url": QUICKMAP_URL,
         "usage": "visual context for the same coordinates; no numeric values taken from it"},
        {"id": "lola-polar-20m", "label": "LOLA 20 m/pix polar DEM (wider-area follow-up)",
         "provider": "NASA PDS Geosciences Node",
         "url": "https://pds-geosciences.wustl.edu/missions/lro/lola.htm",
         "resolution": "20 m/pixel, south of 87.5 S",
         "usage": "referenced for horizons beyond the 16 km site DEMs; not yet ingested"},
    ]
    return terrain_payload(
        generated_utc=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        sites=sites, sources=sources, resources_checked=resources, limitations=LIMITATIONS,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sites", nargs="+", help="site ids (default: the mission candidates)")
    ap.add_argument("--download", action="store_true", help="fetch missing DEMs (~41 MB each)")
    ap.add_argument("--verify-only", action="store_true",
                    help="re-derive from the cached DEMs and compare with the committed file")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--azimuth-step", type=float, default=1.0)
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--skip-trek", action="store_true", help="do not contact Moon Trek")
    args = ap.parse_args()

    payload = build(args)

    if args.verify_only:
        if not args.out.exists():
            print(f"FAIL: {args.out} does not exist")
            return 1
        on_disk = json.loads(args.out.read_text())
        mismatched = []
        # Only DEM-derived fields are comparable: timestamps move and the Moon Trek
        # / reachability checks reflect the network at run time.
        derived = ("latitude_deg", "longitude_deg", "xy_km", "dem", "coverage",
                   "site_pixel", "terrain")
        for site_id, fresh in payload["sites"].items():
            stored = on_disk.get("sites", {}).get(site_id)
            if stored is None:
                mismatched.append(f"{site_id}: missing")
                continue
            for key in derived:
                if stored.get(key) != fresh[key]:
                    mismatched.append(f"{site_id}.{key}")
        if set(on_disk.get("sites", {})) != set(payload["sites"]):
            mismatched.append("site list")
        if mismatched:
            print(f"FAIL: {args.out} does not match the cached DEMs: {', '.join(mismatched)}")
            return 1
        print(f"verified {args.out}: {len(payload['sites'])} sites match the cached DEMs "
              "(timestamps and network checks excluded)")
        return 0

    args.out.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"wrote {args.out}: {len(payload['sites'])} sites")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
