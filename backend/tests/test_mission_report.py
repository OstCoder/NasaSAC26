"""Phase 3 Task 11 / Phase 4 Task 3: the mission report envelope."""

import json

import pytest

from app.services.mission_report import (
    SCHEMA,
    VERSION,
    mission_report,
    mission_report_json,
)
from app.services.phase3 import visibility_response
from app.services.requirements import CHECKS


def test_envelope_identifies_site_and_window():
    doc = mission_report(site_id="shackleton-rim")

    assert doc["schema"] == SCHEMA
    assert doc["version"] == VERSION
    assert doc["site"]["site_id"] == "shackleton-rim"
    assert doc["site"]["name"]
    assert isinstance(doc["site"]["latitude_deg"], float)
    assert isinstance(doc["site"]["longitude_deg"], float)
    assert doc["window"]["key"] == "initial"
    assert doc["window"]["start_utc"] < doc["window"]["stop_utc"]
    assert doc["window"]["samples"] == 169


def test_terrain_block_states_its_basis_and_coverage():
    doc = mission_report(site_id="connecting-ridge")
    terrain = doc["terrain"]

    assert terrain["basis"] == "terrain"
    assert terrain["geometric_only"] is False
    assert terrain["observer_height_m"] == 2.0
    assert terrain["max_obstruction_deg"] == pytest.approx(2.849, abs=1e-3)
    assert terrain["coverage"]["max_sampled_range_km"] == 150.0
    assert terrain["coverage"]["far"]["pixel_m"] == 80.0
    assert terrain["sun_blocked_by_terrain"] >= 0
    assert terrain["earth_above_skyline"] is not None


def test_visibility_numbers_match_phase3_exactly():
    doc = mission_report(site_id="shackleton-rim", window="alternative")
    report = visibility_response(site_id="shackleton-rim", window="alternative")
    summary = report["summary"]

    assert doc["sunlight"]["availability_percent"] == summary["sun_visible_pct"]
    assert doc["sunlight"]["longest_darkness_hours"] == summary["longest_sun_blackout_hours"]
    assert doc["earth"]["visibility_percent"] == summary["earth_visible_pct"]
    assert doc["earth"]["longest_blackout_hours"] == summary["longest_earth_blackout_hours"]
    assert doc["simultaneous_visibility"]["availability_percent"] == summary["both_visible_pct"]
    assert doc["sunlight"]["windows"] == report["intervals"]["sun_visible"]
    assert doc["earth"]["windows"] == report["intervals"]["earth_visible"]
    assert doc["simultaneous_visibility"]["windows"] == report["intervals"]["both_visible"]
    assert doc["metrics"] == report["metrics"]


def test_darkness_and_longest_window_fields_match_phase3():
    doc = mission_report(site_id="connecting-ridge", window="alternative")
    report = visibility_response(site_id="connecting-ridge", window="alternative")
    summary = report["summary"]

    assert doc["sunlight"]["darkness_hours"] == summary["sun_blocked_hours"]
    assert doc["sunlight"]["longest_sunlight_hours"] == summary["longest_sun_visible_hours"]
    assert doc["earth"]["longest_visible_hours"] == summary["longest_earth_visible_hours"]


def test_requirement_checks_reuse_the_shared_thresholds_and_logic():
    doc = mission_report(site_id="shackleton-rim")
    checks = doc["requirements"]["checks"]

    assert [check["id"] for check in checks] == [row[0] for row in CHECKS]
    assert doc["requirements"]["source"] == "config/lunanav.config.json -> requirements"
    for check in checks:
        assert set(check) == {
            "id", "label", "unit", "comparison", "threshold", "value", "status", "censored"}
        assert check["status"] in {"met", "not_met", "unknown"}
        assert check["comparison"] in {"at_least", "at_most"}
    assert doc["requirements"]["satisfied"] in {True, False, None}


def test_envelope_is_reproducible_byte_for_byte():
    first = mission_report_json(site_id="de-gerlache-rim")
    second = mission_report_json(site_id="de-gerlache-rim")

    assert first == second
    assert json.loads(first) == mission_report(site_id="de-gerlache-rim")
    assert '"generated_utc"' not in first
    # Sorted keys: the document starts with the alphabetically first top-level key.
    assert first.lstrip().splitlines()[1].strip().startswith('"')


def test_http_route_serves_the_envelope(client):
    response = client.get("/api/mission-report", params={"site_id": "shackleton-rim"})

    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == SCHEMA
    assert body["requirements"]["checks"]
    assert body["model"]["status"] == "calculated"


def test_http_errors(client):
    assert client.get("/api/mission-report", params={"site_id": "nowhere"}).status_code == 404
    assert client.get(
        "/api/mission-report",
        params={"site_id": "shackleton-rim", "window": "lunar-eclipse"}).status_code == 422
