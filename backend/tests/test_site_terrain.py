"""The committed terrain inventory must agree with the site catalogue, the LOLA
elevation evidence and the DEM geometry it describes."""

import json
from pathlib import Path

import numpy as np
import pytest

from app.services.terrain_inventory import (
    PGDA_SITE_CODES,
    SCHEMA,
    coverage,
    dem_url,
    relief_summary,
    site_xy_m,
)

ROOT = Path(__file__).resolve().parents[2]
TERRAIN = json.loads((ROOT / "data" / "reference" / "site_terrain.json").read_text())
SITES = {s["id"]: s for s in json.loads((ROOT / "data" / "demo" / "sites.json").read_text())["sites"]}
EVIDENCE = json.loads((ROOT / "data" / "reference" / "site_elevations.json").read_text())["samples"]
CANDIDATES = json.loads((ROOT / "config" / "lunanav.config.json").read_text())["mission"]["candidate_sites"]


def test_schema_and_candidate_coverage():
    assert TERRAIN["schema"] == SCHEMA
    assert set(TERRAIN["sites"]) == set(CANDIDATES)
    for site_id in CANDIDATES:
        site = TERRAIN["sites"][site_id]
        catalogue = SITES[site_id]
        assert site["latitude_deg"] == catalogue["latitude_deg"]
        assert site["longitude_deg"] == catalogue["longitude_deg"]
        assert site["pgda_site"] == PGDA_SITE_CODES[site_id]


def test_dem_metadata_describes_the_published_product():
    for site_id in CANDIDATES:
        dem = TERRAIN["sites"][site_id]["dem"]
        assert dem["pixel_m"] == 5.0
        assert dem["width"] == dem["height"] == 3200
        assert dem["extent_km"] == [16.0, 16.0]
        assert dem["url"] == dem_url(TERRAIN["sites"][site_id]["pgda_site"])
        assert dem["bytes"] > 1_000_000
        assert len(dem["sha256"]) == 64 and int(dem["sha256"], 16) >= 0
        wkt = dem["crs_wkt"].replace(" ", "")
        assert "1737400" in wkt
        assert 'PARAMETER["latitude_of_origin",-90]' in wkt
        low, high = dem["elevation_range_m"]
        assert high > low


def test_coverage_is_reproducible_from_the_georeferencing():
    for site_id in CANDIDATES:
        site = TERRAIN["sites"][site_id]
        x_m, y_m = site_xy_m(site["latitude_deg"], site["longitude_deg"])
        assert site["xy_km"] == [round(x_m / 1000.0, 3), round(y_m / 1000.0, 3)]
        bounds = site["dem"]["bounds_m"]
        recomputed = coverage(bounds["left"], bounds["bottom"], bounds["right"],
                              bounds["top"], x_m, y_m)
        assert site["coverage"] == recomputed
        assert recomputed["site_inside"] is True
        assert 3.0 <= recomputed["radius_km"] <= 9.0
        assert site["terrain"]["radius_km"] == recomputed["radius_km"]


def test_site_elevations_agree_with_the_committed_evidence():
    for site_id in CANDIDATES:
        site = TERRAIN["sites"][site_id]
        center_px = EVIDENCE[site_id]["products"]["surf"]["center_px"]
        assert site["site_pixel"]["elevation_m"] == pytest.approx(center_px, abs=0.05)
        assert site["terrain"]["site_elevation_m"] == pytest.approx(center_px, abs=0.05)
        assert SITES[site_id]["elevation_m"] == pytest.approx(
            EVIDENCE[site_id]["products"]["surf"]["median"], abs=0.05)


def test_obstruction_geometry_is_physical():
    for site_id in CANDIDATES:
        terrain = TERRAIN["sites"][site_id]["terrain"]
        # A skyline can sit below the tangent plane (looking into a crater), so only
        # the maximum is bounded below by zero.
        assert -90.0 < terrain["min_obstruction_deg"] <= terrain["max_obstruction_deg"] < 90.0
        assert terrain["max_obstruction_deg"] > 0.0
        assert 0.0 <= terrain["max_obstruction_azimuth_deg"] < 360.0
        assert terrain["elevation_min_m"] <= terrain["site_elevation_m"] <= terrain["elevation_max_m"]
        assert terrain["data_gaps"]["nan_fraction"] is not None


def test_relief_summary_recovers_a_known_slope():
    # Height rises 10 m per 100 m toward +y, so the maximum skyline angle is atan(0.1).
    n, pixel = 60, 5.0
    rows = np.mgrid[0:n, 0:n][0]
    y = 160.0 - (rows + 0.5) * pixel
    dem = 0.1 * y
    out = relief_summary(dem, -140.0, 160.0, pixel, 10.0, 10.0, 100.0)
    assert out["max_obstruction_deg"] == pytest.approx(np.degrees(np.arctan(0.1)), abs=0.01)
    assert out["data_gaps"]["nan_pixels"] == 0


def test_flat_terrain_has_no_obstruction():
    # Flat ground still sinks slightly with distance because lunar curvature is
    # included, so the angles are marginally negative, not exactly zero.
    out = relief_summary(np.zeros((40, 40)), -100.0, 100.0, 5.0, 5.0, 5.0, 50.0)
    assert out["max_obstruction_deg"] == pytest.approx(0.0, abs=0.01)
    assert out["min_obstruction_deg"] == pytest.approx(0.0, abs=0.01)


def test_data_gaps_are_counted_not_substituted():
    dem = np.zeros((40, 40))
    dem[:8, :] = np.nan  # a no-data strip inside the sampled disc
    out = relief_summary(dem, -100.0, 100.0, 5.0, 5.0, 5.0, 200.0)
    assert out["data_gaps"]["nan_pixels"] > 0
    assert out["data_gaps"]["nan_fraction"] == pytest.approx(
        out["data_gaps"]["nan_pixels"] / out["pixels_in_radius"])


def test_sources_and_limitations_are_documented():
    assert "16 km" in TERRAIN["limitations"]["extent"]
    assert "LDEM_875S_20M" in TERRAIN["limitations"]["wider_context"]
    source_ids = {s["id"] for s in TERRAIN["sources"]}
    assert {"pgda-lola-5mpp", "moon-trek-lola", "lroc-quickmap"} <= source_ids
    names = " ".join(r["name"] for r in TERRAIN["resources_checked"]).lower()
    assert "quickmap" in names and "moon trek" in names
    for resource in TERRAIN["resources_checked"]:
        assert resource["url"].startswith("https://")
    assert TERRAIN["conventions"]["height_datum"].startswith("metres above the 1737.4 km")
