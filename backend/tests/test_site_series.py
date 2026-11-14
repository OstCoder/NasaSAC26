"""Phase 2 Task 2: series assembly, mission windows and the stored guarantees."""

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from app.core.settings import get_settings
from app.core.timeutil import to_iso
from app.providers.horizons_site import CrossCheck, ObserverSite, SkyTrack
from app.services.site_series import (
    SCHEMA,
    SeriesWindow,
    expected_samples,
    merged_samples,
    mission_windows,
    series_checks,
    series_payload,
)

SITE = ObserverSite.at(-89.78, 204.27, 1734.0, 2.0, site_id="shackleton-rim")
T0 = datetime(2026, 12, 1, tzinfo=timezone.utc)


def track(body: str, times: list[datetime]) -> SkyTrack:
    n = len(times)
    return SkyTrack(
        body=body,
        site=SITE,
        times_utc=tuple(times),
        azimuth_deg=np.full(n, 10.0),
        elevation_deg=np.full(n, -1.5),
        range_km=np.full(n, 380_000.0),
    )


def test_mission_windows_come_from_the_mission_config():
    windows = mission_windows(get_settings())
    assert [w.key for w in windows] == ["initial", "alternative"]
    assert windows[0].start == datetime(2026, 12, 1, tzinfo=timezone.utc)
    assert windows[0].end == datetime(2026, 12, 8, tzinfo=timezone.utc)
    assert windows[1].start == datetime(2026, 12, 11, tzinfo=timezone.utc)
    assert windows[1].end == datetime(2026, 12, 18, tzinfo=timezone.utc)
    assert expected_samples(windows[0], 60.0) == 169  # 7 days at 1 h, inclusive


def test_merged_samples_and_the_coverage_guarantees():
    times = [T0 + timedelta(hours=i) for i in range(3)]
    records, dropped = merged_samples(
        {"sun": track("sun", times), "earth": track("earth", times[1:])}, "shackleton-rim"
    )
    assert dropped == 1  # the first timestamp has no Earth value, so it is dropped
    assert [r["timestamp_utc"] for r in records] == [to_iso(t) for t in times[1:]]
    assert all(set(r) == {"site_id", "timestamp_utc", "sun", "earth"} for r in records)
    assert all(all(series_checks(records).values()) for _ in [0])


def test_checks_flag_missing_values_and_disorder():
    good = [
        {"timestamp_utc": to_iso(T0), "sun": {"azimuth_deg": 1.0, "elevation_deg": 2.0},
         "earth": {"azimuth_deg": 3.0, "elevation_deg": 4.0}},
        {"timestamp_utc": to_iso(T0 + timedelta(hours=1)), "sun": {"azimuth_deg": 5.0, "elevation_deg": 6.0},
         "earth": {"azimuth_deg": 7.0, "elevation_deg": 8.0}},
    ]
    assert all(series_checks(good).values())

    missing = [dict(good[0]), {**good[1], "earth": {"azimuth_deg": None, "elevation_deg": 4.0}}]
    assert series_checks(missing)["no_missing_values"] is False

    assert series_checks(list(reversed(good)))["chronological"] is False
    assert series_checks([])["non_empty"] is False


def test_payload_is_self_describing_and_carries_the_window():
    times = [T0 + timedelta(hours=i) for i in range(2)]
    tracks = {"sun": track("sun", times), "earth": track("earth", times)}
    checks = {
        body: CrossCheck(body=body, samples=2, max_azimuth_deg=0.01, max_elevation_deg=0.02,
                         rms_elevation_deg=0.01, tolerance_deg=0.5)
        for body in tracks
    }
    window = SeriesWindow("initial", "Initial analysis period", T0, T0 + timedelta(days=7))
    payload = series_payload(
        observer=SITE, label={"site_id": "shackleton-rim", "name": "Shackleton Crater Rim"},
        tracks=tracks, crosschecks=checks, start=window.start, stop=window.end,
        step="1 h", window=window,
    )
    assert payload["schema"] == SCHEMA
    assert payload["site"]["site_id"] == "shackleton-rim"
    assert payload["window"]["key"] == "initial"
    assert payload["request"]["step"] == "1 h"
    assert payload["conventions"]["azimuth_deg"].startswith("degrees clockwise")
    assert all(payload["checks"].values())
    assert payload["crosscheck"]["sun"]["passed"] is True
    assert payload["incomplete_timestamps_dropped"] == 0
    assert len(payload["series"]) == 2
    assert payload["series"][0]["sun"]["azimuth_deg"] == pytest.approx(10.0)
