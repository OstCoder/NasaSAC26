"""Terrain horizon obstructions and terrain-adjusted visibility."""

from pathlib import Path

import pytest

from app.core.errors import InvalidInputError
from app.providers.terrain import LolaOrFlatHorizonProvider
from app.services.phase3 import visibility_response
from app.services.site_data import mask_payload
from app.services.terrain_horizon import (
    SCHEMA,
    _custom_terrain_response,
    terrain_horizon_response,
)

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = ("shackleton-rim", "connecting-ridge", "de-gerlache-rim")
WIDE_CACHE = ROOT / "data" / "cache" / "lola_wide" / "LDEM_80S_80MPP_ADJ.TIF"
HORIZON_DIR = ROOT / "data" / "scientific" / "horizon_masks"
WIDE_REFERENCE = ROOT / "data" / "reference" / "wide_dem.json"


def test_full_skyline_profile_for_a_verified_site():
    report = terrain_horizon_response(site_id="shackleton-rim")
    terrain = report["terrain"]

    assert report["schema"] == SCHEMA
    assert terrain["available"] is True
    assert terrain["basis"] == "terrain"
    assert terrain["geometric_only"] is False
    assert terrain["observer_height_m"] == 2.0
    assert terrain["azimuth_step_deg"] == 1.0
    assert len(terrain["profile"]["azimuth_deg"]) == 360
    assert len(terrain["profile"]["elevation_deg"]) == 360
    assert terrain["profile"]["azimuth_deg"][:3] == [0.0, 1.0, 2.0]
    assert terrain["summary"]["max_obstruction_deg"] == pytest.approx(9.4281)


@pytest.mark.parametrize("site_id", CANDIDATES)
def test_profile_is_the_committed_mask_and_matches_phase3(site_id):
    payload = mask_payload(site_id)
    terrain = terrain_horizon_response(site_id=site_id)["terrain"]

    assert terrain["profile"]["elevation_deg"] == pytest.approx(payload["elevation_deg"], abs=1e-6)
    assert terrain["summary"]["max_obstruction_deg"] == payload["summary"]["max_obstruction_deg"]
    assert terrain["summary"]["max_obstruction_azimuth_deg"] == (
        payload["summary"]["max_obstruction_azimuth_deg"])
    assert terrain["provenance"] == "scientific_sourced"
    assert terrain["observer_height_m"] == payload["observer_height_m"]


def test_elevation_and_coverage_are_explicit():
    payload = mask_payload("shackleton-rim")
    report = terrain_horizon_response(site_id="shackleton-rim")
    terrain = report["terrain"]
    coverage = terrain["coverage"]

    assert report["site"]["elevation_m"] == terrain["surface_elevation_m"]
    assert coverage["curvature_applied"] is True
    assert coverage["curvature_radius_m"] == 1_737_400.0
    assert coverage["near"]["pixel_m"] == payload["tiers"]["near"]["pixel_m"]
    assert coverage["far"]["pixel_m"] == payload["tiers"]["far"]["pixel_m"]
    assert coverage["far"]["max_range_m"] == 150_000
    assert coverage["max_sampled_range_km"] == 150.0


def test_coverage_limits_and_uncertainty_are_documented():
    terrain = terrain_horizon_response(site_id="shackleton-rim")["terrain"]
    limits = " ".join(terrain["limits"]).lower()

    assert "80 m" in limits
    assert "150 km" in limits
    assert terrain["uncertainty"]["observer_height_m"] == 2.0
    assert terrain["uncertainty"]["observer_height_uncertainty_m"] > 0
    assert terrain["uncertainty"]["azimuth_step_deg"] == 1.0
    assert terrain["uncertainty"]["near_pixel_m"] == 5.0
    assert terrain["uncertainty"]["far_pixel_m"] == 80.0


@pytest.mark.parametrize("body", ["sun", "earth"])
def test_both_bodies_are_compared_against_the_skyline(body):
    report = terrain_horizon_response(site_id="connecting-ridge")
    phase3 = visibility_response(site_id="connecting-ridge")
    block = report["comparison"][body]

    assert block["samples"] == len(phase3["series"]) == 169
    assert block["above_skyline"] + block["below_skyline"] == block["samples"]
    assert block["agrees_with_visibility"] is True
    assert block["blocked_by_terrain"] == sum(
        record[body]["elevation_deg"] > 0 and not record[body]["visible"]
        for record in phase3["series"])
    assert block["above_skyline_pct"] == pytest.approx(
        100.0 * block["above_skyline"] / block["samples"], abs=1e-4)
    assert block["skyline_min_deg"] <= block["skyline_max_deg"]


def test_terrain_changes_the_geometric_answer():
    report = terrain_horizon_response(site_id="shackleton-rim")

    assert report["checks"]["terrain_changes_the_answer"] is True
    assert report["comparison"]["sun"]["blocked_by_terrain"] > 0


def test_adjusted_visibility_is_delegated_to_phase3():
    report = terrain_horizon_response(site_id="shackleton-rim", window="alternative")
    phase3 = visibility_response(site_id="shackleton-rim", window="alternative")

    assert report["visibility"]["available"] is True
    assert report["visibility"]["summary"] == phase3["summary"]
    assert report["visibility"]["intervals"] == phase3["intervals"]
    assert report["visibility"]["window"]["key"] == "alternative"
    assert report["visibility"]["series_endpoint"] == (
        "/api/phase3?site_id=shackleton-rim&window=alternative")
    assert report["checks"]["skyline_matches_mask"] is True


def test_custom_coordinates_outside_wide_dem_are_geometric_only():
    report = terrain_horizon_response(latitude_deg=-45.0, longitude_deg=0.0)
    terrain = report["terrain"]

    assert terrain["available"] is False
    assert terrain["basis"] == "geometric"
    assert terrain["geometric_only"] is True
    assert len(terrain["profile"]["elevation_deg"]) == 360
    assert set(terrain["profile"]["elevation_deg"]) == {0.0}
    assert terrain["summary"]["max_obstruction_deg"] == 0.0
    assert report["visibility"]["available"] is False
    assert report["visibility"]["reason"]
    assert report["comparison"]["sun"] is None
    assert report["checks"]["geometric_only_flagged"] is True
    assert report["provenance"]["expected_terrain_provenance"] == "scientific_sourced"


@pytest.mark.skipif(not WIDE_CACHE.exists(), reason="wide LOLA DEM cache is not present")
def test_custom_polar_point_uses_the_wide_lola_dem():
    provider = LolaOrFlatHorizonProvider(HORIZON_DIR, WIDE_REFERENCE, WIDE_CACHE.parent)
    mask = provider.horizon_mask(-87.0, 0.0)
    report = _custom_terrain_response(
        latitude_deg=-87.0, longitude_deg=0.0, window="initial", mask=mask)
    terrain = report["terrain"]

    assert mask.provenance.value == "scientific_sourced"
    assert terrain["available"] is True
    assert terrain["basis"] == "terrain"
    assert terrain["geometric_only"] is False
    assert "wide polar DEM" in terrain["source"]
    assert len(terrain["profile"]["elevation_deg"]) == 360
    assert max(terrain["profile"]["elevation_deg"]) > 0
    assert terrain["summary"]["max_obstruction_deg"] > 0
    assert report["visibility"]["available"] is False
    assert report["checks"]["terrain_profile_available"] is True
    assert report["provenance"]["terrain_provenance"] == "scientific_sourced"
    assert provider.horizon_mask(-45.0, 0.0).provenance.value == "geometric_only"


def test_partial_coordinates_are_rejected():
    with pytest.raises(InvalidInputError):
        terrain_horizon_response(latitude_deg=-89.9)
    with pytest.raises(InvalidInputError):
        terrain_horizon_response(longitude_deg=0.0)


def test_http_route_serves_the_report(client):
    response = client.get("/api/terrain-horizon", params={"site_id": "de-gerlache-rim"})

    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == SCHEMA
    assert body["terrain"]["geometric_only"] is False
    assert body["terrain"]["summary"]["max_obstruction_deg"] == pytest.approx(1.2837, abs=1e-4)


def test_http_route_accepts_custom_coordinates(client):
    response = client.get(
        "/api/terrain-horizon", params={"latitude_deg": -45.0, "longitude_deg": 12.5})

    assert response.status_code == 200
    assert response.json()["terrain"]["geometric_only"] is True


def test_http_errors(client):
    assert client.get("/api/terrain-horizon", params={"site_id": "nowhere"}).status_code == 404
    assert client.get(
        "/api/terrain-horizon",
        params={"site_id": "shackleton-rim", "window": "lunar-eclipse"}).status_code == 422
    assert client.get("/api/terrain-horizon", params={"latitude_deg": -89.9}).status_code == 422


def test_custom_point_uses_the_same_coordinate_rules_as_a_scenario():
    """The exact pole has no local north, so it has no horizon at an azimuth either."""
    with pytest.raises(InvalidInputError, match="pole"):
        terrain_horizon_response(latitude_deg=-90.0, longitude_deg=0.0)

    # Longitude wraps into [-180, 180) exactly as it does for a scenario location.
    report = terrain_horizon_response(latitude_deg=-87.5, longitude_deg=-348.0)
    assert report["site"]["longitude_deg"] == pytest.approx(12.0)
    with pytest.raises(InvalidInputError):
        terrain_horizon_response(latitude_deg=-87.5, longitude_deg=400.0)


def test_http_route_rejects_an_exact_pole(client):
    response = client.get(
        "/api/terrain-horizon", params={"latitude_deg": -90.0, "longitude_deg": 0.0})

    assert response.status_code == 422
    assert "pole" in response.json()["message"].lower()
