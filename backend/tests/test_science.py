"""Phase 6 science endpoints and the PSR distance contract."""

from __future__ import annotations

import pytest

from app.core.coords import great_circle_km
from app.services.psr import get_psr_catalogue
from app.services.science import nearest_psr_response, psr_catalogue_response, site_context_response


def test_science_psr_catalogue_carries_source_and_geometry():
    body = psr_catalogue_response()
    assert body["schema"] == "lunanav.science_psr_catalogue.v1"
    assert body["catalogue_count"] == 653
    assert body["count"] == 390  # the default map coverage is poleward of 80 S
    assert "LROC" in body["source"]["provider"]
    assert body["projection"]["sphere_radius_km"] == 1737.4
    assert body["area_threshold_km2"] == 5.0
    assert len(body["psrs"][0]["rings"][0]) > 3
    assert body["limits"]


def test_nearest_psr_for_a_candidate_has_both_distance_bases():
    body = nearest_psr_response(site_id="shackleton-rim")
    nearest = body["nearest_psr"]
    assert nearest["psr_id"] == "SP_896450_1282030"
    assert nearest["boundary_distance_km"] == pytest.approx(2.479, abs=1e-3)
    assert nearest["centroid_distance_km"] == pytest.approx(
        great_circle_km(body["query"]["latitude_deg"], body["query"]["longitude_deg"],
                        nearest["centroid_latitude_deg"],
                        nearest["centroid_longitude_deg"]), abs=0.01)
    assert nearest["distance_uncertainty_km"] == 0.06
    assert nearest["inside"] is False
    assert body["water_ice"]["confirmed"] is None
    assert body["water_ice"]["status"] == "not_assessed"
    assert any("not proof" in limit or "not a" in limit for limit in body["limits"])


def test_a_point_inside_a_mapped_psr_has_zero_boundary_distance():
    catalogue = get_psr_catalogue()
    psr = max(catalogue.all(), key=lambda item: item.area_km2)
    body = nearest_psr_response(
        latitude_deg=psr.centroid_latitude_deg,
        longitude_deg=psr.centroid_longitude_deg,
        radius_km=1.0,
    )
    assert body["nearest_psr"]["psr_id"] == psr.psr_id
    assert body["nearest_psr"]["boundary_distance_km"] == 0.0
    assert body["nearest_psr"]["inside"] is True
    assert body["status"] == "inside"


def test_nearby_list_is_empty_when_no_psr_is_within_radius_but_nearest_remains():
    body = nearest_psr_response(site_id="connecting-ridge", radius_km=1.0)
    assert body["nearest_psr"]["psr_id"] == "SP_895060_2806850"
    assert body["nearby_count"] == 0
    assert body["nearby_psrs"] == []
    assert body["status"] == "mapped"


def test_site_context_is_explicit_about_unknown_water_ice_and_terrain():
    body = site_context_response("shackleton-rim")
    assert body["schema"] == "lunanav.science_context.v1"
    assert body["site"]["site_id"] == "shackleton-rim"
    assert body["nearest_psr"]["psr_id"] == "SP_896450_1282030"
    assert body["terrain"]["available"] is True
    assert body["terrain"]["coverage"]["near"]["pixel_m"] == 5.0
    assert body["science"]["water_ice_confirmed"] is None
    assert body["science"]["water_ice_status"] == "not_assessed"
    assert body["science"]["water_ice_evidence"] == []
    assert body["visibility_windows"]["initial"]["available"] is True
    assert body["visibility_windows"]["alternative"]["available"] is True
    assert any("not evidence of absence" in note for note in body["notes"])


def test_science_routes_expose_the_same_contract(client):
    catalogue = client.get("/api/science/psrs", params={"max_latitude_deg": -89})
    assert catalogue.status_code == 200, catalogue.text
    assert catalogue.json()["count"] > 0

    nearest = client.get("/api/science/nearest-psr",
                         params={"site_id": "de-gerlache-rim"})
    assert nearest.status_code == 200, nearest.text
    assert nearest.json()["nearest_psr"]["boundary_distance_km"] == pytest.approx(12.106, abs=1e-3)

    context = client.get("/api/science/site-context",
                         params={"site_id": "de-gerlache-rim"})
    assert context.status_code == 200, context.text
    assert context.json()["science"]["water_ice_confirmed"] is None

    mesh = client.get("/api/terrain/mesh", params={"site_id": "de-gerlache-rim"})
    dem = client.get("/api/terrain-dem", params={"site_id": "de-gerlache-rim"})
    assert mesh.status_code == dem.status_code == 200
    assert mesh.json()["source"] == dem.json()["source"]


def test_science_routes_reject_ambiguous_or_missing_queries(client):
    assert client.get("/api/science/nearest-psr").status_code == 422
    assert client.get("/api/science/nearest-psr", params={
        "site_id": "shackleton-rim", "latitude_deg": -89.7,
        "longitude_deg": 200,
    }).status_code == 422
    assert client.get("/api/science/nearest-psr",
                      params={"site_id": "nowhere"}).status_code == 404
    assert client.get("/api/science/site-context",
                      params={"site_id": "nowhere"}).status_code == 404
