"""Phase 2 Task 5: the validation report, its checks and its failure modes."""

import importlib.util
import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from app.core.settings import get_settings
from app.services.dataset_catalogue import build_catalogue, reset_cache
from app.services.nasa_validation import (
    REFERENCE_SCHEMA,
    SCHEMA,
    TASK5_ITEMS,
    build_report,
    problems,
)

ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "backend" / "scripts" / "validate_nasa_data.py"


@pytest.fixture(scope="module")
def report():
    return build_report()


def test_report_covers_every_task5_item(report):
    assert report["schema"] == SCHEMA
    assert [item["id"] for item in report["task5_items"]] == [key for key, _ in TASK5_ITEMS]
    assert {item["check"] for item in report["task5_items"]} == {c["id"] for c in report["checks"]}
    assert len(report["checks"]) == 10
    assert all(check["detail"] for check in report["checks"])


def test_committed_datasets_pass_every_check(report):
    assert report["summary"]["status"] == "pass", problems(report)
    assert problems(report) == []
    assert report["summary"]["records_checked"] == 1014
    assert set(report["sites"]) == set(get_settings().raw["mission"]["candidate_sites"])


def test_check_numbers_match_the_measured_data(report):
    by_id = {check["id"]: check for check in report["checks"]}
    positions = by_id["sun_earth_positions"]["metrics"]
    assert positions["bodies"]["sun"]["max_elevation_difference_deg"] < 0.05
    assert positions["bodies"]["earth"]["max_elevation_difference_deg"] < 0.05
    assert positions["bodies"]["sun"]["samples"] == 1014
    reference = by_id["horizons_reference"]["metrics"]
    assert reference["rows"] == 180
    assert reference["requests"] == 6
    assert reference["max_elevation_difference_deg"] <= 0.002
    units = by_id["units"]["metrics"]
    assert units["degree_hypothesis_max_error_deg"] < units["radian_hypothesis_max_error_deg"]
    assert 1.46e8 <= units["sun_range_km_median"] <= 1.53e8
    assert 3.5e5 <= units["earth_range_km_median"] <= 4.1e5
    utc = by_id["utc_time"]["metrics"]
    assert utc["step_s"] == 3600.0
    assert utc["samples"] == 1014
    assert by_id["same_site_different_dates"]["metrics"]["days_between_landings"] == 10
    assert by_id["different_sites_same_time"]["metrics"]["sun_elevation_spread_deg"] > 0.05


def test_live_evidence_is_recorded_not_claimed(report):
    live = report["live"]
    assert live["performed"] is True
    assert live["retrieved_utc"].endswith("Z")
    assert all(check["passed"] for check in live["checks"]), live
    reproduction = next(check for check in live["checks"] if check["id"] == "reproduction")
    assert reproduction["metrics"]["samples"] == 18
    assert reproduction["metrics"]["max_elevation_difference_deg"] == 0.0
    echoed = next(check for check in live["checks"] if check["id"] == "echoed_observer")
    assert len(echoed["metrics"]["echoes"]) == 6


def test_reference_rows_are_the_horizons_observer_table():
    reference = json.loads(
        (ROOT / "data" / "reference" / "horizons_reference.json").read_text()
    )
    assert reference["schema"] == REFERENCE_SCHEMA
    assert reference["rows"] == sum(len(request["rows"]) for request in reference["requests"])
    assert reference["excluded_outside_windows"] == 30  # 8-10 Dec, between the two windows
    for request in reference["requests"]:
        assert "CENTER='coord%40301'" in request["query_url"] or "CENTER=%27coord%40301%27" in request["query_url"]
        assert request["header"]["center"]
        assert request["header"]["frame"]
        assert request["rows"]
    stamps = {row["timestamp_utc"] for row in reference["requests"][0]["rows"]}
    assert "2026-12-01T00:00:00Z" in stamps and "2026-12-18T00:00:00Z" in stamps


def test_a_tampered_value_fails_the_check(tmp_path):
    source = ROOT / "data" / "scientific" / "site_series"
    for path in source.glob("*.json"):
        shutil.copy(path, tmp_path / path.name)
    target = tmp_path / "shackleton-rim-initial.json"
    payload = json.loads(target.read_text())
    payload["series"][5]["earth"]["elevation_deg"] += 1.0
    target.write_text(json.dumps(payload))

    settings = replace(
        get_settings(),
        datasets={**get_settings().datasets, "site_series_index": tmp_path / "index.json"},
    )
    report = build_report(settings=settings, live={"performed": False})
    failed = {check["id"] for check in report["checks"] if not check["passed"]}
    assert "sun_earth_positions" in failed
    assert report["summary"]["status"] == "fail"
    assert any("earth" in problem for problem in problems(report))


def test_a_missing_reference_is_a_failure_not_a_skip(tmp_path):
    settings = replace(
        get_settings(),
        datasets={**get_settings().datasets, "horizons_reference": tmp_path / "absent.json"},
    )
    report = build_report(settings=settings, live={"performed": False})
    check = next(c for c in report["checks"] if c["id"] == "horizons_reference")
    assert check["passed"] is False
    assert "missing" in check["problems"][0]


def test_offline_cli_passes_and_prints_machine_readable_json(capsys):
    spec = importlib.util.spec_from_file_location("validate_nasa_data", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main(["--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == SCHEMA
    assert payload["summary"]["status"] == "pass"


def test_catalogue_indexes_the_validation_evidence():
    reset_cache()
    catalogue = build_catalogue()
    by_id = {entry["id"]: entry for entry in catalogue["datasets"]}
    assert catalogue["problems"] == []
    assert by_id["horizons_reference"]["records"] == 180
    assert by_id["horizons_reference"]["available"] is True
    assert by_id["nasa_validation"]["details"]["status"] == "pass"
    assert by_id["nasa_validation"]["records"] == 10
    assert by_id["nasa_validation"]["sources"]


def test_api_serves_the_validation_report(client):
    response = client.get("/api/validation")
    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == SCHEMA
    assert body["summary"]["status"] == "pass"
    assert client.get("/api/validation?force=true").status_code == 200
