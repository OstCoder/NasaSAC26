"""Terrain inventory: what a LOLA DEM actually covers around a landing site.

For visibility work the useful question is not "do we have a DEM" but "how much
ground does this file cover, at what resolution, in which frame, and how far can
a ray-march go before it runs off the edge". This module answers that from the
files themselves, so ``data/reference/site_terrain.json`` and ``docs/TERRAIN.md``
are derived rather than typed by hand.

``relief_summary`` works on any height array (no rasterio needed, so it is unit
testable); ``read_dem`` loads a GeoTIFF and needs the optional rasterio extra.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from app.core.coords import polar_stereographic_xy
from app.services.horizon import build_horizon_mask_from_dem

SCHEMA = "lunanav.site_terrain.v1"
MOON_RADIUS_M = 1_737_400.0

PROJECTION = (
    "south polar stereographic (latitude of origin -90, central meridian 0, "
    "sphere radius 1737.4 km), metres; north-up raster, row 0 at the top"
)
HEIGHT_DATUM = "metres above the 1737.4 km reference sphere (LOLA Z)"

# NASA PGDA site numbering (Mazarico et al. 2011); absent ids have no 5 m/pix DEM.
PGDA_SITE_CODES = {
    "connecting-ridge": "Site01",
    "shackleton-rim": "Site04",
    "peak-near-shackleton": "Site07",
    "de-gerlache-rim": "Site11",
}
PGDA_BASE_URL = "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp"

# Wide-area far tier (Phase 2 Task 6): the 5 m site DEMs are only 16 km across, so
# masks used to stop 6-8 km out. This 80 m/pix product covers 80 S to the pole
# (~304 km radius), enough to ray-march to 150 km.
WIDE_DEM_FILE = "LDEM_80S_80MPP_ADJ.TIF"
WIDE_DEM_URL = "https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_80MPP_ADJ.TIF"
WIDE_LANDING_URL = "https://pgda.gsfc.nasa.gov/products/90"
WIDE_PIXEL_M = 80.0
WIDE_LAT_LIMIT_DEG = -80.0
WIDE_MAX_RANGE_M = 150_000.0
WIDE_REFERENCE = "data/reference/wide_dem.json"

PRODUCTS = {
    "surf": "surface height Z (m above the 1737.4 km sphere)",
    "slp": "slope (degrees)",
    "toterr": "total height uncertainty, RMS (m)",
}


def dem_filename(site_code: str, product: str = "surf") -> str:
    return f"{site_code}_final_adj_5mpp_{product}.tif"


def dem_url(site_code: str, product: str = "surf") -> str:
    return f"{PGDA_BASE_URL}/{site_code}/{dem_filename(site_code, product)}"


def file_sha256(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def site_xy_m(lat_deg: float, lon_deg: float) -> tuple[float, float]:
    """Site position in the DEM's plane, metres (same convention as the DEM grid)."""
    x_km, y_km = polar_stereographic_xy(lat_deg, lon_deg)
    return x_km * 1000.0, y_km * 1000.0


def coverage(left: float, bottom: float, right: float, top: float, x_m: float, y_m: float) -> dict:
    """Where the site sits in the raster and how far a ray may travel from it.

    ``radius_km`` is the distance to the nearest edge: the largest radius for
    which every azimuth still lies inside the file.
    """
    edges = {
        "west": (x_m - left) / 1000.0,
        "east": (right - x_m) / 1000.0,
        "south": (y_m - bottom) / 1000.0,
        "north": (top - y_m) / 1000.0,
    }
    inside = left <= x_m <= right and bottom <= y_m <= top
    return {
        "site_inside": bool(inside),
        "radius_km": round(max(0.0, min(edges.values())), 3) if inside else 0.0,
        "edge_distance_km": {k: round(v, 3) for k, v in edges.items()},
    }


def relief_summary(
    dem_m: np.ndarray,
    x0_m: float,
    y0_m: float,
    pixel_m: float,
    obs_x_m: float,
    obs_y_m: float,
    max_range_m: float,
    azimuth_step_deg: float = 1.0,
) -> dict:
    """Skyline and relief statistics around the observer, out to ``max_range_m``.

    The obstruction angles come from the same ray-march
    (``services.horizon.build_horizon_mask_from_dem``) that Phase 3 uses for
    horizon masks, with lunar curvature included and the observer at ground
    level, so they are directly comparable with Sun and Earth elevations.
    """
    dem = np.asarray(dem_m, float)
    rows, cols = dem.shape

    col = (obs_x_m - x0_m) / pixel_m
    row = (y0_m - obs_y_m) / pixel_m
    site_elevation = float(dem[np.clip(int(np.floor(row)), 0, rows - 1),
                                np.clip(int(np.floor(col)), 0, cols - 1)])

    mask = build_horizon_mask_from_dem(
        dem, x0_m, y0_m, pixel_m, obs_x_m, obs_y_m,
        obs_height_m=0.0, azimuth_step_deg=azimuth_step_deg,
        max_range_m=max_range_m, radius_m=MOON_RADIUS_M,
        source="LOLA 5 m/pix site DEM ray-march",
    )
    elev = np.asarray(mask.elevation_deg, float)
    az = np.asarray(mask.azimuth_deg, float)
    top = int(np.nanargmax(elev))

    # Height statistics over the disc the ray-march actually covers.
    xs = x0_m + (np.arange(cols) + 0.5) * pixel_m
    ys = y0_m - (np.arange(rows) + 0.5) * pixel_m
    dist = np.hypot(xs[None, :] - obs_x_m, ys[:, None] - obs_y_m)
    disc = dist <= max_range_m
    vals = dem[disc]
    finite = vals[np.isfinite(vals)]
    gaps = int(vals.size - finite.size)

    return {
        "radius_km": round(max_range_m / 1000.0, 3),
        "azimuth_step_deg": azimuth_step_deg,
        "pixel_m": float(pixel_m),
        "site_elevation_m": round(site_elevation, 2),
        "elevation_min_m": round(float(finite.min()), 2) if finite.size else None,
        "elevation_max_m": round(float(finite.max()), 2) if finite.size else None,
        "elevation_median_m": round(float(np.median(finite)), 2) if finite.size else None,
        "max_obstruction_deg": round(float(elev[top]), 4),
        "max_obstruction_azimuth_deg": round(float(az[top]) % 360.0, 1),
        "min_obstruction_deg": round(float(np.nanmin(elev)), 4),
        "pixels_in_radius": int(vals.size),
        "data_gaps": {
            "nan_pixels": gaps,
            "nan_fraction": round(gaps / vals.size, 6) if vals.size else None,
        },
    }


def read_dem(path: Path | str) -> tuple[dict, np.ndarray]:
    """Georeferencing metadata plus the height array of a GeoTIFF DEM."""
    import rasterio  # optional dependency

    path = Path(path)
    with rasterio.open(path) as ds:
        heights = ds.read(1).astype(float)
        if ds.nodata is not None and np.isfinite(ds.nodata):
            heights[heights == ds.nodata] = np.nan
        finite = heights[np.isfinite(heights)]
        info = {
            "file": path.name,
            "driver": ds.driver,
            "width": int(ds.width),
            "height": int(ds.height),
            "dtype": ds.dtypes[0],
            "pixel_m": float(ds.res[0]),
            "extent_km": [round(ds.width * ds.res[0] / 1000.0, 3),
                          round(ds.height * ds.res[1] / 1000.0, 3)],
            "crs_wkt": ds.crs.to_wkt() if ds.crs else None,
            "bounds_m": {
                "left": float(ds.bounds.left),
                "bottom": float(ds.bounds.bottom),
                "right": float(ds.bounds.right),
                "top": float(ds.bounds.top),
            },
            "nodata": "nan" if ds.nodata is None or not np.isfinite(ds.nodata) else ds.nodata,
            "elevation_range_m": [round(float(finite.min()), 2), round(float(finite.max()), 2)]
            if finite.size else None,
        }
    info["bytes"] = path.stat().st_size
    info["sha256"] = file_sha256(path)
    return info, heights


def terrain_payload(
    *,
    generated_utc: str,
    sites: dict,
    sources: list,
    resources_checked: list,
    limitations: dict,
) -> dict:
    """The committed on-disk document (schema ``lunanav.site_terrain.v1``)."""
    return {
        "schema": SCHEMA,
        "dataset": "LOLA terrain at the three mission candidates",
        "generated_utc": generated_utc,
        "generator": "backend/scripts/inspect_site_terrain.py",
        "conventions": {
            "frame": "Moon Mean Earth / Polar Axis, IAU selenographic planetocentric, "
                     "longitude east-positive in [-180, 180)",
            "projection": PROJECTION,
            "height_datum": HEIGHT_DATUM,
            "units": "metres for heights and grid coordinates, kilometres for distances and extents",
            "azimuth": "degrees clockwise from local lunar north, 0 <= az < 360",
            "obstruction_deg": (
                "angle from the local horizontal to the skyline for a ground-level (0 m) "
                "observer, lunar curvature included; the terrain-aware horizon masks use the "
                "same skyline sampled from the 2 m observer the Sun/Earth track uses"
            ),
        },
        "sources": sources,
        "resources_checked": resources_checked,
        "sites": sites,
        "limitations": limitations,
    }
