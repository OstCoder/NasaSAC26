"""Phase 3 Task 10: cross-check terrain shadow against NASA's PSR catalogue.

NASA's LROC south-pole PSR product (``data/reference/psrs.json``, traced from
the LOLA permanent-shadow masks of Mazarico et al. 2011) labels ground that
never sees direct sunlight. This script asks LunaNav's own terrain model the
same question at every mapped PSR larger than ``MIN_AREA_KM2`` that lies inside
the DEM with ``MIN_RANGE_KM`` of ground around it:

1. ray-march the committed 80 m/pix LOLA wide DEM from the PSR centroid
   (2 m observer, lunar curvature, 150 km range, 1 deg azimuths), then
2. compare the Sun's topocentric elevation against that skyline for every day
   of a full year (2026-12-01 + 364 days), and
3. record whether any sample clears the terrain.

A PSR where the model finds sunlight is a disagreement worth investigating -
it is written down, never hidden. The script writes
``data/reference/illumination_crosscheck.json``; the committed document is what
the test suite reads, so CI needs neither rasterio nor the 189 MB DEM.

Run from ``backend/``:  python scripts/check_psr_illumination.py
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from app.core.coords import MOON_MEAN_RADIUS_KM, topocentric_az_el
from app.core.settings import get_settings
from app.providers.ephemeris_analytic import AnalyticMeeusEphemeris
from app.services.horizon import build_horizon_mask_from_dem
from app.services.psr import get_psr_catalogue
from app.services.terrain_inventory import (
    WIDE_DEM_FILE,
    WIDE_MAX_RANGE_M,
    WIDE_REFERENCE,
    read_dem,
    site_xy_m,
)

SCHEMA = "lunanav.illumination_crosscheck.v1"
GENERATOR = "backend/scripts/check_psr_illumination.py"
ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "data" / "reference" / "illumination_crosscheck.json"
MIN_AREA_KM2 = 100.0
MIN_PSRS = 6
MIN_RANGE_KM = 30.0
AZIMUTH_STEP_DEG = 1.0
OBSERVER_HEIGHT_M = 2.0
SAMPLE_STEP_DAYS = 1
SPAN_START = datetime(2026, 12, 1, tzinfo=timezone.utc)
SPAN_DAYS = 365

NOTES = [
    "This compares a shadow/no-shadow classification, not an illumination percentage: "
    "NASA maps the PSR as permanently shadowed, LunaNav tests whether the Sun ever clears "
    "the LOLA skyline at its centroid.",
    "Sun positions use LunaNav's analytic (Meeus) model, whose elevation agreement with "
    "Horizons is a few hundredths of a degree; the agreement margins here are degrees, "
    "so the classification is insensitive to that error.",
    "The 80 m/pix wide DEM resolves crater rims and massifs hundreds of metres across. A "
    "ridge narrower than ~80 m, or terrain beyond the ray-march, could in principle shadow "
    "a point the model calls lit, so the agreement is a lower bound on obstruction, not a "
    "polygon-wide proof.",
    "The wide DEM stops ~304 km from the pole, so each row records the range actually "
    "marched; edge_limited rows stop short of 150 km and are not treated as full coverage.",
    "A PSR centroid is representative of its polygon interior only for compact regions; "
    "elongated PSRs can include lit ground near an end, which is why the check samples the "
    "recorded centroid and reports the margin rather than claiming a polygon-wide proof.",
    "Terrain shadow is not power, and this check says nothing about Earth visibility or "
    "communications.",
]


def _sun_elevations(times: list[datetime], lat_deg: float, lon_deg: float, altitude_km: float):
    ephemeris = AnalyticMeeusEphemeris(times[0] - timedelta(days=2), times[-1] + timedelta(days=2))
    vectors = ephemeris.body_vectors_km("sun", times)
    return topocentric_az_el(lat_deg, lon_deg, vectors, MOON_MEAN_RADIUS_KM, altitude_km)


def main() -> int:
    settings = get_settings()
    wide = json.loads((ROOT / WIDE_REFERENCE).read_text())
    cache_dir = Path(settings.datasets.get("cache_dir", "data/cache"))
    if not cache_dir.is_absolute():
        cache_dir = ROOT / cache_dir
    dem_path = cache_dir / "lola_wide" / WIDE_DEM_FILE
    info, dem = read_dem(dem_path)
    if info["sha256"] != wide["dem"]["sha256"]:
        raise SystemExit(f"{dem_path} checksum {info['sha256']} does not match wide_dem.json")
    bounds = info["bounds_m"]
    x0_m, y0_m, pixel_m = bounds["left"], bounds["top"], info["pixel_m"]

    catalogue = get_psr_catalogue()
    selected = sorted(
        (p for p in catalogue.all() if p.area_km2 >= MIN_AREA_KM2),
        key=lambda p: (-p.area_km2, p.psr_id),
    )
    if len(selected) < MIN_PSRS:
        raise SystemExit(f"only {len(selected)} PSRs >= {MIN_AREA_KM2} km2; need {MIN_PSRS}")

    times = [SPAN_START + timedelta(days=day) for day in range(SPAN_DAYS)]
    rows = []
    sunlit_total = 0
    skipped_outside_dem = 0
    skipped_short_range = 0
    skipped_no_height = 0
    for psr in selected:
        lat, lon = psr.centroid_latitude_deg, psr.centroid_longitude_deg
        x_m, y_m = site_xy_m(lat, lon)
        col_f = (x_m - x0_m) / pixel_m
        row_f = (y0_m - y_m) / pixel_m
        if not (0.0 <= col_f <= info["width"] - 1 and 0.0 <= row_f <= info["height"] - 1):
            skipped_outside_dem += 1
            continue
        # The wide DEM stops at ~304 km from the pole, so cap the march at the
        # distance to its edge instead of reading clipped cells as sky.
        edge_km = min(
            x_m - bounds["left"], bounds["right"] - x_m,
            y_m - bounds["bottom"], bounds["top"] - y_m,
        ) / 1000.0
        range_km = min(WIDE_MAX_RANGE_M / 1000.0, edge_km)
        if range_km < MIN_RANGE_KM:
            skipped_short_range += 1
            continue
        col, row = int(round(col_f)), int(round(row_f))
        surface_m = float(dem[row, col])
        if not math.isfinite(surface_m):
            skipped_no_height += 1
            continue
        mask = build_horizon_mask_from_dem(
            dem, x0_m, y0_m, pixel_m, x_m, y_m,
            obs_height_m=OBSERVER_HEIGHT_M,
            azimuth_step_deg=AZIMUTH_STEP_DEG,
            max_range_m=range_km * 1000.0,
            source="LOLA 80 m/pix wide DEM ray-march",
        )
        azimuth_deg, elevation_deg = _sun_elevations(
            times, lat, lon, (surface_m + OBSERVER_HEIGHT_M) / 1000.0)
        skyline = np.asarray(mask.elevation_at(azimuth_deg), float)
        clearance = np.asarray(elevation_deg, float) - skyline
        sunlit = int(np.count_nonzero(clearance > 0.0))
        sunlit_total += sunlit
        peak = int(np.nanargmax(mask.elevation_deg))
        rows.append({
            "psr_id": psr.psr_id,
            "near_crater": psr.near_crater or None,
            "area_km2": round(psr.area_km2, 3),
            "latitude_deg": round(lat, 5),
            "longitude_deg": round(lon, 5),
            "max_range_km": round(range_km, 1),
            "edge_limited": range_km < WIDE_MAX_RANGE_M / 1000.0,
            "max_skyline_deg": round(float(mask.elevation_deg[peak]), 4),
            "max_skyline_azimuth_deg": round(float(mask.azimuth_deg[peak]) % 360.0, 1),
            "max_sun_elevation_deg": round(float(np.max(elevation_deg)), 4),
            "max_clearance_deg": round(float(np.max(clearance)), 4),
            "sunlit_samples": sunlit,
            "shadowed": sunlit == 0,
        })

    if len(rows) < MIN_PSRS:
        raise SystemExit(f"only {len(rows)} PSRs have {MIN_RANGE_KM} km of DEM around "
                         f"them; need {MIN_PSRS}")
    accounted = len(rows) + skipped_outside_dem + skipped_short_range + skipped_no_height
    if accounted != len(selected):
        raise SystemExit(f"selection accounting mismatch: {accounted} != {len(selected)}")

    margins = [row["max_clearance_deg"] for row in rows]
    document = {
        "schema": SCHEMA,
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "generator": GENERATOR,
        "purpose": (
            "Phase 3 Task 10: check the terrain visibility calculation against NASA "
            "illumination reference data where comparable - the LROC/LOLA permanent "
            "shadow classification."
        ),
        "sources": {
            "psr_catalogue": {
                "provider": "NASA/GSFC/Arizona State University LROC team",
                "product": catalogue.meta.get("source", {}).get("product"),
                "derived_from": catalogue.meta.get("source", {}).get("derived_from"),
                "version": catalogue.meta.get("version"),
                "psrs_in_catalogue": len(catalogue),
            },
            "terrain": {
                "label": wide["source"]["label"],
                "provider": wide["source"]["provider"],
                "url": wide["source"]["url"],
                "file": WIDE_DEM_FILE,
                "pixel_m": info["pixel_m"],
                "sha256": info["sha256"],
            },
            "ephemeris": "LunaNav analytic (Meeus) Sun positions, topocentric at each PSR",
        },
        "method": {
            "min_area_km2": MIN_AREA_KM2,
            "psr_point": "recorded polygon centroid",
            "observer_height_m": OBSERVER_HEIGHT_M,
            "azimuth_step_deg": AZIMUTH_STEP_DEG,
            "max_range_m": WIDE_MAX_RANGE_M,
            "range_rule": (
                "Each ray-march is capped at the distance to the 80 m/pix wide DEM edge "
                f"and skipped below {MIN_RANGE_KM:g} km; rows record max_range_km."
            ),
            "curvature": "lunar curvature included in the ray-march",
            "span_start_utc": SPAN_START.isoformat(),
            "span_days": SPAN_DAYS,
            "sample_step_days": SAMPLE_STEP_DAYS,
            "test": "Sun elevation minus skyline elevation > 0 for any sample means lit",
        },
        "summary": {
            "psrs_eligible": len(selected),
            "psrs_checked": len(rows),
            "psrs_shadowed": sum(1 for row in rows if row["shadowed"]),
            "psrs_outside_dem": skipped_outside_dem,
            "psrs_insufficient_range": skipped_short_range,
            "psrs_no_height": skipped_no_height,
            "full_range_rows": sum(1 for row in rows if not row["edge_limited"]),
            "edge_limited_rows": sum(1 for row in rows if row["edge_limited"]),
            "sunlit_samples": sunlit_total,
            "worst_margin_deg": max(margins),
            "median_margin_deg": round(float(np.median(margins)), 4),
            "status": "pass" if sunlit_total == 0 else "fail",
        },
        "psrs": rows,
        "notes": NOTES,
    }
    OUTPUT.write_text(json.dumps(document, indent=1, sort_keys=False) + "\n")
    print(f"{document['summary']['status']}: {len(rows)} PSRs, "
          f"{sunlit_total} sunlit samples, worst margin {max(margins):.3f} deg -> {OUTPUT}")
    return 0 if sunlit_total == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
