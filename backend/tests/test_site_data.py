"""Phase 2 Task 6: the data-access layer Phase 3 reads.

Two things matter here: every record has one documented shape, and a resample is
an interpolation inside the stored window that never invents a value outside it.
"""

import importlib.util
import json
import shutil
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

from app.core.errors import (
    DataUnavailableError,
    InvalidInputError,
    OutOfSupportedRangeError,
    UnknownSiteError,
)
from app.core.settings import get_settings
from app.services.site_data import (
    ACCESS_SCHEMA,
    FIELDS,
    MASK_SCHEMA,
    READINESS_SCHEMA,
    apply_mask,
    build_readiness,
    check_record,
    interpolate_circular,
    load_mask,
    load_series,
    mask_payload,
    sample_records,
    series_response,
)

ROOT = Path(__file__).resolve().parents[2]
SERIES = ROOT / "data" / "scientific" / "site_series"
TERRAIN = json.loads((ROOT / "data" / "reference" / "site_terrain.json").read_text())
MASK_SCRIPT = ROOT / "backend" / "scripts" / "build_site_horizon_masks.py"
CACHE = ROOT / "data" / "cache" / "lola_5mpp"
CANDIDATES = json.loads((ROOT / "config" / "lunanav.config.json").read_text())["mission"]["candidate_sites"]


def test_stored_track_loads_with_the_documented_shape():
    table = load_series("shackleton-rim", "initial")
    assert len(table) == 169
    assert table.step_minutes == 60.0
    assert table.start == datetime(2026, 12, 1, tzinfo=timezone.utc)
    assert table.stop == datetime(2026, 12, 8, tzinfo=timezone.utc)
    assert set(table.records[0]) == {"site_id", "timestamp_utc", "sun", "earth"}
    assert set(table.records[0]["sun"]) == {"azimuth_deg", "elevation_deg", "range_km"}
    assert table.records[0]["sun"]["azimuth_deg"] == pytest.approx(75.799377)
    assert np.isfinite(table.sun.azimuth_deg).all()
    assert np.isfinite(table.earth.elevation_deg).all()


def test_unknown_site_and_window_are_rejected():
    with pytest.raises(UnknownSiteError):
        load_series("nowhere", "initial")
    with pytest.raises(InvalidInputError):
        load_series("shackleton-rim", "third")
    with pytest.raises(InvalidInputError):
        series_response(site_id="shackleton-rim", start="2026-12-01T00:00:00Z")


def test_exact_timestamps_return_the_stored_values():
    table = load_series("shackleton-rim", "initial")
    records, meta = sample_records(table, table.start, table.times[2], 60.0)
    assert meta["interpolated"] is False
    assert meta["samples"] == 3
    assert [r["sun"]["elevation_deg"] for r in records] == [
        table.records[index]["sun"]["elevation_deg"] for index in range(3)
    ]


def test_half_hour_grid_interpolates_between_hourly_samples():
    table = load_series("shackleton-rim", "initial")
    records, meta = sample_records(table, table.start, table.start + timedelta(hours=1), 30.0)
    assert meta["interpolated"] is True
    assert len(records) == 3
    first = table.records[0]["sun"]["elevation_deg"]
    second = table.records[1]["sun"]["elevation_deg"]
    assert records[1]["sun"]["elevation_deg"] == pytest.approx((first + second) / 2, abs=1e-5)
    assert records[2]["sun"]["elevation_deg"] == second


def test_resampling_refuses_to_extrapolate():
    table = load_series("shackleton-rim", "initial")
    with pytest.raises(OutOfSupportedRangeError):
        sample_records(table, table.start - timedelta(minutes=1), table.times[1], 60.0)
    with pytest.raises(OutOfSupportedRangeError):
        sample_records(table, table.start, table.stop + timedelta(hours=1), 60.0)
    with pytest.raises(InvalidInputError):
        sample_records(table, table.start, table.times[1], 0)
    with pytest.raises(InvalidInputError):
        sample_records(table, table.start, table.start, 60.0)


def test_azimuth_interpolation_is_circular():
    hours = np.array([0.0, 1.0])
    angles = np.array([350.0, 10.0])
    assert interpolate_circular(hours, angles, np.array([0.5]))[0] == pytest.approx(0.0)
    assert interpolate_circular(hours, angles, np.array([0.0]))[0] == pytest.approx(350.0)
    assert interpolate_circular(hours, angles, np.array([1.0]))[0] == pytest.approx(10.0)


def test_record_contract_rejects_missing_extra_and_non_finite():
    record = load_series("shackleton-rim", "initial").records[0]
    check_record(record, "shackleton-rim")
    with pytest.raises(DataUnavailableError):
        check_record({**record, "extra": 1}, "shackleton-rim")
    with pytest.raises(DataUnavailableError):
        check_record({key: value for key, value in record.items() if key != "sun"})
    with pytest.raises(DataUnavailableError):
        check_record({**record, "sun": {"azimuth_deg": None, "elevation_deg": 1.0}})
    with pytest.raises(DataUnavailableError):
        check_record(record, "de-gerlache-rim")


def test_a_tampered_file_is_refused(tmp_path):
    for path in SERIES.glob("*.json"):
        shutil.copy(path, tmp_path / path.name)
    target = tmp_path / "shackleton-rim-initial.json"
    payload = json.loads(target.read_text())
    payload["series"][3]["sun"]["zenith_deg"] = 1.0
    target.write_text(json.dumps(payload))
    settings = replace(get_settings(),
                       datasets={**get_settings().datasets,
                                 "site_series_index": tmp_path / "index.json"})
    with pytest.raises(DataUnavailableError):
        load_series("shackleton-rim", "initial", settings)


def test_masks_match_the_terrain_inventory():
    for site_id in CANDIDATES:
        payload = mask_payload(site_id)
        assert payload["schema"] == MASK_SCHEMA
        assert len(payload["azimuth_deg"]) == 360
        assert payload["azimuth_deg"][0] == 0.0 and payload["azimuth_deg"][-1] == 359.0
        assert payload["max_range_m"] == pytest.approx(
            TERRAIN["sites"][site_id]["coverage"]["radius_km"] * 1000.0, abs=1e-6)
        inventory = TERRAIN["sites"][site_id]["terrain"]["max_obstruction_deg"]
        measured = payload["summary"]["max_obstruction_deg"]
        # The inventory was measured from the ground (0 m eye); a 2 m eye sees
        # near-field rims lower, so the mask may be below it but never above.
        assert payload["inventory"]["max_obstruction_deg"] == inventory
        assert payload["inventory"]["observer_height_m"] == 0.0
        assert payload["observer_height_m"] == 2.0
        assert measured <= inventory + 1e-6
        assert measured >= inventory - 15.0
        assert payload["limitations"]
        mask = load_mask(site_id)
        assert mask.provenance.value == "scientific_sourced"
        assert len(mask.azimuth_deg) == 360


def test_a_missing_mask_is_an_error_not_a_flat_horizon(tmp_path):
    settings = replace(get_settings(),
                       datasets={**get_settings().datasets,
                                 "scientific_horizon_dir": tmp_path})
    assert mask_payload("shackleton-rim", settings) is None
    with pytest.raises(DataUnavailableError):
        load_mask("shackleton-rim", settings)
    readiness = build_readiness(settings)
    assert readiness["summary"]["ready"] == 0
    assert readiness["summary"]["with_mask"] == 0
    assert all(site["problems"] for site in readiness["sites"])


def test_apply_mask_reports_clearance_without_deciding_visibility():
    table = load_series("shackleton-rim", "initial")
    mask = load_mask("shackleton-rim")
    result = apply_mask(list(table.records), mask)
    assert result["sun"]["clearance_deg"].shape == (169,)
    assert np.allclose(result["sun"]["clearance_deg"],
                       result["sun"]["elevation_deg"] - result["sun"]["skyline_deg"])
    assert np.array_equal(result["sun"]["above_skyline"],
                          result["sun"]["elevation_deg"] > result["sun"]["skyline_deg"])
    # The real skyline must block part of this track, otherwise it is not applied.
    assert (~result["sun"]["above_skyline"]).any()


def payload_mask(site: dict) -> dict:
    return mask_payload(site["site_id"])


def test_readiness_covers_every_candidate():
    report = build_readiness()
    assert report["schema"] == READINESS_SCHEMA
    assert [site["site_id"] for site in report["sites"]] == CANDIDATES
    assert report["summary"] == {"sites": 3, "ready": 3, "with_mask": 3, "missing": []}
    for site in report["sites"]:
        assert payload_mask(site)["observer_height_m"] == 2.0
        assert set(site["windows"]) == {"initial", "alternative"}
        assert site["windows"]["initial"]["records"] == 169
        assert site["windows"]["alternative"]["records"] == 169
        assert site["mask"]["max_range_km"] > 6.0
        assert site["ready"] is True and site["problems"] == []


def test_api_series_returns_the_file_shape(client):
    response = client.get("/api/series?site_id=shackleton-rim")
    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == ACCESS_SCHEMA
    assert body["records_schema"] == "lunanav.site_series.v1"
    assert body["fields"] == list(FIELDS)
    assert len(body["series"]) == 169
    assert body["series"][0]["timestamp_utc"] == "2026-12-01T00:00:00Z"
    assert body["series"][0]["sun"]["azimuth_deg"] == pytest.approx(75.799377)
    assert body["series"][0]["earth"]["elevation_deg"] == pytest.approx(-1.820125)
    assert body["mask"]["site_id"] == "shackleton-rim"
    assert body["request"]["interpolated"] is False
    assert all(body["checks"].values())


def test_api_series_resamples_and_rejects_bad_input(client):
    resampled = client.get("/api/series", params={
        "site_id": "connecting-ridge", "start": "2026-12-11T00:00:00Z",
        "stop": "2026-12-11T02:00:00Z", "step_minutes": 30,
    })
    assert resampled.status_code == 200
    body = resampled.json()
    assert len(body["series"]) == 5
    assert body["request"]["interpolated"] is True

    assert client.get("/api/series?site_id=nope").status_code == 404
    assert client.get("/api/series?site_id=shackleton-rim&window=nope").status_code == 422
    outside = client.get("/api/series", params={
        "site_id": "shackleton-rim", "start": "2026-11-01T00:00:00Z",
        "stop": "2026-11-02T00:00:00Z",
    })
    assert outside.status_code == 422
    # The error names the supported windows rather than clamping the request.
    assert "mission window" in outside.json()["message"]
    assert "2026-12-01T00:00:00Z" in outside.json()["message"]


def test_api_readiness(client):
    response = client.get("/api/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == READINESS_SCHEMA
    assert body["summary"]["ready"] == 3
    assert {site["site_id"] for site in body["sites"]} == set(CANDIDATES)


@pytest.mark.skipif(not any(CACHE.glob("Site*_surf.tif")), reason="LOLA DEM cache is not present")
def test_mask_rebuilds_exactly_from_the_cached_dem(tmp_path):
    spec = importlib.util.spec_from_file_location("build_site_horizon_masks", MASK_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fresh = module.build(["shackleton-rim"], tmp_path)[0]
    committed = json.loads(
        (ROOT / "data" / "scientific" / "horizon_masks" / "shackleton-rim.json").read_text()
    )
    assert fresh["azimuth_deg"] == committed["azimuth_deg"]
    assert fresh["elevation_deg"] == committed["elevation_deg"]
    assert fresh["summary"] == committed["summary"]
    assert fresh["dem"] == committed["dem"]


def test_mask_builder_verifies_offline(capsys):
    spec = importlib.util.spec_from_file_location("build_site_horizon_masks", MASK_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.verify() == 0
    assert "all horizon masks verified" in capsys.readouterr().out
