"""Phase 3 Task 1: the point-source geometric Sun visibility rule."""

import numpy as np
import pytest

from app.services.geometric import (
    SCHEMA,
    SUN_ANGULAR_RADIUS_DEG,
    geometric_visibility,
    sun_visibility_response,
)


def test_positive_negative_and_zero_follow_the_rule_exactly():
    result = geometric_visibility(np.array([3.2, 1.5, -0.8, -2.1, 0.0, -0.0]))
    assert result.visible.tolist() == [True, True, False, False, False, False]


def test_the_rule_is_strictly_greater_than_zero():
    # A tiny positive value is visible and a tiny negative one is not; no epsilon.
    result = geometric_visibility(np.array([1e-9, -1e-9]))
    assert result.visible.tolist() == [True, False]


def test_near_horizon_samples_are_flagged_without_changing_the_boolean():
    result = geometric_visibility(np.array([0.1, -0.1, 0.0, 0.5]))
    assert result.visible.tolist() == [True, False, False, True]
    assert result.grazing.tolist() == [True, True, True, False]
    # At the horizon exactly half the disk is above it.
    assert result.disk_fraction[2] == pytest.approx(0.5)
    assert result.disk_fraction[0] > 0.5
    assert result.disk_fraction[1] < 0.5


def test_disk_fraction_is_information_only_and_saturates_outside_the_band():
    result = geometric_visibility(np.array([5.0, -5.0]))
    assert result.disk_fraction.tolist() == pytest.approx([1.0, 0.0])
    assert not result.grazing.any()


def test_non_finite_and_bad_shapes_are_refused():
    with pytest.raises(ValueError):
        geometric_visibility(np.array([1.0, np.nan]))
    with pytest.raises(ValueError):
        geometric_visibility(np.array([[1.0, 2.0]]))
    with pytest.raises(ValueError):
        geometric_visibility(np.array([1.0]), angular_radius_deg=-1.0)


def test_the_committed_track_is_calculated_end_to_end():
    report = sun_visibility_response(site_id="connecting-ridge", window="initial")
    assert report["schema"] == SCHEMA
    assert report["rule"]["name"] == "point_source_elevation_above_zero"
    assert report["rule"]["terrain_applied"] is False
    assert report["rule"]["angular_diameter_in_rule"] is False
    assert len(report["series"]) == 169
    assert all(report["checks"].values())

    elevations = [record["elevation_deg"] for record in report["series"]]
    assert all(record["visible"] is (record["elevation_deg"] > 0.0)
               for record in report["series"])
    visible = sum(record["visible"] for record in report["series"])
    assert report["summary"]["visible_samples"] == visible
    assert report["summary"]["visible_sample_pct"] == pytest.approx(100.0 * visible / 169, abs=1e-3)
    # Connecting Ridge is in sunlight for this window: the baseline should say so.
    assert visible > 0
    assert report["summary"]["grazing_samples"] == sum(
        1 for elevation in elevations if abs(elevation) <= SUN_ANGULAR_RADIUS_DEG)


def test_azimuth_and_elevation_are_preserved_from_task2():
    from app.services.site_data import load_series

    table = load_series("de-gerlache-rim", "alternative")
    report = sun_visibility_response(site_id="de-gerlache-rim", window="alternative")
    for index, record in enumerate(report["series"]):
        assert record["timestamp_utc"] == table.records[index]["timestamp_utc"]
        assert record["azimuth_deg"] == table.records[index]["sun"]["azimuth_deg"]
        assert record["elevation_deg"] == table.records[index]["sun"]["elevation_deg"]


def test_intervals_match_the_visible_samples():
    report = sun_visibility_response(site_id="shackleton-rim")
    visible_hours = sum(span["duration_hours"] for span in report["intervals"])
    assert report["summary"]["visible_hours"] == pytest.approx(visible_hours, abs=0.01)
    # Shackleton's rim blocks the Sun in this window, but the geometric baseline
    # can still be positive: the two questions must not be confused.
    assert report["summary"]["visible_samples"] > 0
    assert report["series"][0]["visible"] is True


def test_api_geometric_sun(client):
    response = client.get("/api/geometric-sun?site_id=shackleton-rim")
    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == SCHEMA
    assert len(body["series"]) == 169
    assert client.get("/api/geometric-sun?site_id=nope").status_code == 404
    assert client.get("/api/geometric-sun?site_id=shackleton-rim&window=nope").status_code == 422
