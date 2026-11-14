"""Phase 2 Task 4: one catalogue over sites, series, terrain and references."""

import pytest

from app.services.dataset_catalogue import (
    SCHEMA,
    build_catalogue,
    reset_cache,
    series_file_problems,
    series_site_problems,
    site_record_problems,
)


@pytest.fixture(scope="module")
def catalogue():
    reset_cache()
    return build_catalogue()


def test_every_dataset_is_listed_with_units_and_conventions(catalogue):
    assert catalogue["schema"] == SCHEMA
    ids = {entry["id"] for entry in catalogue["datasets"]}
    assert {"sites", "site_series", "site_terrain", "site_elevations",
            "psr_catalogue", "craters", "ephemeris", "horizon_masks", "cache"} <= ids
    for entry in catalogue["datasets"]:
        assert entry["path"]
        assert entry["kind"] in {"sites", "observations", "terrain", "reference", "cache"}
        assert entry["longitude_convention"].startswith("selenographic east-positive")
        assert entry["units"]["angle"] == "degrees"
        assert entry["units"]["time"].startswith("UTC")


def test_cross_dataset_checks_pass_and_counts_match_the_files(catalogue):
    assert catalogue["problems"] == []
    by_id = {entry["id"]: entry for entry in catalogue["datasets"]}
    assert by_id["sites"]["records"] >= 3
    assert by_id["site_series"]["records"] == 1014
    assert by_id["site_terrain"]["records"] == 3
    assert by_id["site_series"]["available"] is True
    assert by_id["site_terrain"]["available"] is True
    assert by_id["site_series"]["sources"]
    assert by_id["site_terrain"]["sources"]


def test_datasets_that_do_not_exist_say_so_instead_of_vanishing(catalogue):
    by_id = {entry["id"]: entry for entry in catalogue["datasets"]}
    ephemeris = by_id["ephemeris"]
    assert ephemeris["available"] is False
    assert ephemeris["unavailable_reason"]
    # Task 6 built the masks, so this dataset is now present rather than absent.
    masks = by_id["horizon_masks"]
    assert masks["available"] is True
    assert masks["records"] == 3
    assert len(masks["details"]["files"]) == 3
    # The masks are checked, not just counted: 360 points, far tier, wide DEM.
    assert masks["details"]["wide_dem"]["available"] is True
    assert masks["details"]["wide_dem"]["pixel_m"] == 80.0
    assert set(masks["details"]["sites"]) == {"shackleton-rim", "connecting-ridge",
                                               "de-gerlache-rim"}
    for entry in masks["details"]["sites"].values():
        assert entry["max_range_km"] == 150.0
        assert entry["far_pixel_m"] == 80.0
        assert 0.0 <= entry["max_obstruction_deg"] < 90.0
    assert by_id["site_series"]["details"]["step"] == "1 h"


def test_cache_is_described_without_inventing_content(catalogue):
    cache = next(entry for entry in catalogue["datasets"] if entry["id"] == "cache")
    months = cache["details"]["horizons_months"]
    assert isinstance(months, list)
    assert all(len(month) == 7 and month[4] == "-" for month in months)
    assert isinstance(cache["details"]["trek_tiles"], int)
    assert "not" in cache["details"]["policy"]


def test_site_records_are_validated():
    good = {"id": "x", "latitude_deg": -89.0, "longitude_deg": -155.73,
            "elevation_m": 100.0, "source": "test"}
    assert site_record_problems(good) == []
    assert site_record_problems({**good, "latitude_deg": -95.0})
    assert site_record_problems({**good, "longitude_deg": 400.0})
    assert site_record_problems({**good, "elevation_m": float("nan")})
    assert site_record_problems({**good, "source": "  "})


def test_series_must_describe_the_catalogue_point():
    catalogue_site = {"id": "shackleton-rim", "latitude_deg": -89.78,
                      "longitude_deg": -155.73, "elevation_m": 1734.05}
    ok = {"latitude_deg": -89.78, "longitude_deg": -155.73, "elevation_m": 1734.05}
    assert series_site_problems(ok, catalogue_site) == []
    assert series_site_problems({**ok, "latitude_deg": -89.7}, catalogue_site)
    assert series_site_problems({**ok, "elevation_m": 1736.0}, catalogue_site)
    # 204.27 E is the same meridian but the wrong stored convention.
    assert series_site_problems({**ok, "longitude_deg": 204.27}, catalogue_site)


def test_series_file_must_be_the_file_the_index_claims():
    payload = {
        "schema": "lunanav.site_series.v1",
        "site": {"site_id": "shackleton-rim"},
        "window": {"start_utc": "2026-12-01T00:00:00Z", "stop_utc": "2026-12-08T00:00:00Z"},
    }
    expected = {"start_utc": "2026-12-01T00:00:00Z", "stop_utc": "2026-12-08T00:00:00Z"}
    assert series_file_problems(payload, "shackleton-rim", "initial", expected) == []
    assert series_file_problems({**payload, "site": {"site_id": "connecting-ridge"}},
                                "shackleton-rim", "initial", expected)
    shifted = {**payload, "window": {"start_utc": "2026-12-02T00:00:00Z",
                                     "stop_utc": "2026-12-08T00:00:00Z"}}
    assert series_file_problems(shifted, "shackleton-rim", "initial", expected)
    assert series_file_problems({**payload, "schema": "v0"},
                                "shackleton-rim", "initial", expected)


def test_api_serves_the_catalogue(client):
    response = client.get("/api/datasets")
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema"] == SCHEMA
    assert payload["problems"] == []
    assert any(entry["id"] == "site_series" for entry in payload["datasets"])
