"""Phase 3 visibility from the committed series and two-tier masks."""

import pytest

from app.services.phase3 import SCHEMA, all_windows_summary, visibility_response

NON_TERRAIN_KEYS = {"sun", "earth", "both"}


def test_visibility_uses_the_committed_track_and_mask():
    report = visibility_response(site_id="shackleton-rim", window="initial")
    assert report["schema"] == SCHEMA
    assert report["window"]["samples"] == 169
    assert len(report["series"]) == 169
    assert report["mask"]["max_range_km"] == 150.0
    assert report["mask"]["provenance"] == "scientific_sourced"
    assert report["mask"]["tiers"]["near"]["pixel_m"] == 5.0
    assert report["mask"]["tiers"]["far"]["pixel_m"] == 80.0
    assert report["rule"]["sun"] == "center_above_terrain"
    assert all(report["checks"].values())


def test_every_record_carries_skyline_clearance_and_a_boolean():
    report = visibility_response(site_id="connecting-ridge")
    heights = [record["sun"]["skyline_deg"] for record in report["series"]]
    assert min(heights) >= -5.0 and max(heights) < 20.0
    for record in report["series"]:
        for body in ("sun", "earth"):
            block = record[body]
            assert block["clearance_deg"] == pytest.approx(
                block["elevation_deg"] - block["skyline_deg"], abs=1e-4)
            assert block["visible"] is (block["clearance_deg"] > 0)
        assert 0.0 <= record["sun"]["disk_fraction"] <= 1.0


def test_summary_matches_the_intervals_it_claims():
    report = visibility_response(site_id="de-gerlache-rim")
    summary = report["summary"]
    sun_hours = sum(i["duration_hours"] for i in report["intervals"]["sun_visible"])
    earth_hours = sum(i["duration_hours"] for i in report["intervals"]["earth_visible"])
    both_hours = sum(i["duration_hours"] for i in report["intervals"]["both_visible"])
    assert summary["sun_visible_hours"] == pytest.approx(sun_hours, abs=0.01)
    assert summary["earth_visible_hours"] == pytest.approx(earth_hours, abs=0.01)
    assert summary["both_visible_hours"] == pytest.approx(both_hours, abs=0.01)
    assert summary["both_visible_hours"] <= min(summary["sun_visible_hours"],
                                                summary["earth_visible_hours"]) + 0.01
    assert 0.0 <= summary["both_visible_pct"] <= 100.0
    # A window can have a long Earth blackout; it must be reported, not clipped away.
    assert summary["longest_earth_blackout_hours"] is not None


def test_the_far_tier_is_what_makes_the_mask_wide():
    for site_id in ("shackleton-rim", "connecting-ridge", "de-gerlache-rim"):
        report = visibility_response(site_id=site_id)
        tiers = report["mask"]["tiers"]
        assert tiers["near"]["max_range_m"] < 8_000.0
        assert tiers["far"]["max_range_m"] == 150_000.0
        assert tiers["far"]["max_obstruction_deg"] <= tiers["near"]["max_obstruction_deg"] + 1e-9


def test_every_candidate_and_window_is_available_offline():
    payload = all_windows_summary()
    assert [site["site_id"] for site in payload["sites"]] == [
        "shackleton-rim", "connecting-ridge", "de-gerlache-rim"]
    for site in payload["sites"]:
        for window in ("initial", "alternative"):
            entry = site["windows"][window]
            assert entry["available"] is True
            assert entry["samples"] == 169
            assert entry["mask_max_range_km"] == 150.0


def test_api_phase3_and_unknown_inputs(client):
    response = client.get("/api/phase3?site_id=shackleton-rim")
    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == SCHEMA
    assert {"sun_only", "earth_only"} <= set(body["intervals"])
    assert {"next_sunrise_utc", "next_sunset_utc",
            "next_earthrise_utc", "next_earthset_utc"} <= set(body["transitions"])
    assert client.get("/api/phase3?site_id=nope").status_code == 404
    assert client.get("/api/phase3?site_id=shackleton-rim&window=nope").status_code == 422
    windows = client.get("/api/phase3/windows")
    assert windows.status_code == 200
    assert len(windows.json()["sites"]) == 3


def test_only_sun_and_only_earth_periods_partition_visible_time():
    report = visibility_response(site_id="de-gerlache-rim", window="alternative")
    intervals = report["intervals"]
    summary = report["summary"]

    assert {"sun_only", "earth_only"} <= set(intervals)
    # Task 6's four cases partition each body's visible time.
    assert summary["sun_only_hours"] + summary["both_visible_hours"] == pytest.approx(
        summary["sun_visible_hours"], abs=0.01)
    assert summary["earth_only_hours"] + summary["both_visible_hours"] == pytest.approx(
        summary["earth_visible_hours"], abs=0.01)

    def overlaps(a, b):
        return any(x["start_utc"] < y["end_utc"] and y["start_utc"] < x["end_utc"]
                   for x in a for y in b)

    assert not overlaps(intervals["sun_only"], intervals["earth_visible"])
    assert not overlaps(intervals["earth_only"], intervals["sun_visible"])


def test_total_darkness_and_next_transitions_are_reported():
    report = visibility_response(site_id="connecting-ridge", window="alternative")
    summary = report["summary"]

    assert summary["sun_blocked_hours"] + summary["sun_visible_hours"] == pytest.approx(
        168.0, abs=0.01)
    earth_windows = report["intervals"]["earth_visible"]
    assert summary["longest_earth_visible_hours"] == pytest.approx(
        max(window["duration_hours"] for window in earth_windows), abs=0.01)

    transitions = report["transitions"]
    keys = ("next_sunset_utc", "next_sunrise_utc", "next_earthset_utc", "next_earthrise_utc")
    assert set(keys) <= set(transitions)
    start, stop = report["window"]["start_utc"], report["window"]["stop_utc"]
    for key in keys:
        value = transitions[key]
        assert value is None or start < value < stop


@pytest.mark.parametrize("site_id", ["shackleton-rim", "connecting-ridge", "de-gerlache-rim"])
@pytest.mark.parametrize("window", ["initial", "alternative"])
def test_every_window_partitions_sun_and_earth_time(site_id, window):
    report = visibility_response(site_id=site_id, window=window)
    summary = report["summary"]

    assert summary["sun_only_hours"] + summary["both_visible_hours"] == pytest.approx(
        summary["sun_visible_hours"], abs=0.01)
    assert summary["earth_only_hours"] + summary["both_visible_hours"] == pytest.approx(
        summary["earth_visible_hours"], abs=0.01)
    assert summary["sun_blocked_hours"] + summary["sun_visible_hours"] == pytest.approx(
        168.0, abs=0.01)


def test_a_fully_shadowed_window_has_no_transition_inside_it():
    report = visibility_response(site_id="shackleton-rim", window="initial")

    assert report["summary"]["sun_visible_hours"] == 0.0
    assert report["summary"]["sun_blocked_hours"] == pytest.approx(168.0, abs=0.01)
    assert report["transitions"]["next_sunrise_utc"] is None
