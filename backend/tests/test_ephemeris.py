"""Analytic ephemeris checked against Meeus' published worked examples."""

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from app.core.errors import DataUnavailableError, OutOfSupportedRangeError
from app.core.timeutil import time_grid
from app.providers.ephemeris_analytic import (
    AnalyticMeeusEphemeris,
    moon_geocentric,
    optical_libration,
    sun_geocentric,
)
from app.providers.ephemeris_tabulated import HorizonsTableEphemeris
from app.providers.horizons_format import build_query, parse_observer_csv

T_1992_APR_12 = np.array([(2448724.5 - 2451545.0) / 36525])


def test_moon_position_meeus_47a():
    m = moon_geocentric(T_1992_APR_12)
    assert m["lon"][0] == pytest.approx(133.162655, abs=0.01)
    assert m["lat"][0] == pytest.approx(-3.229126, abs=0.01)
    assert m["dist_km"][0] == pytest.approx(368409.7, abs=50)


def test_optical_libration_meeus_53a():
    m = moon_geocentric(T_1992_APR_12)
    l, b = optical_libration(m["lon"], m["lat"], m["Omega"], m["F"])
    assert l[0] == pytest.approx(-1.206, abs=0.02)
    assert b[0] == pytest.approx(4.194, abs=0.02)


def test_sun_position_meeus_25a():
    s = sun_geocentric(np.array([(2448908.5 - 2451545.0) / 36525]))
    assert s["lon"][0] == pytest.approx(199.90988, abs=0.001)
    assert s["dist_km"][0] / 149_597_870.7 == pytest.approx(0.99766, abs=1e-4)


@pytest.fixture
def eph():
    return AnalyticMeeusEphemeris(datetime(2026, 1, 1, tzinfo=timezone.utc),
                                  datetime(2030, 12, 31, tzinfo=timezone.utc))


def test_subsolar_latitude_bounded_and_earth_libration_bounded(eph):
    times = time_grid(datetime(2027, 1, 1, tzinfo=timezone.utc), 24 * 400, 360)
    sun = eph.sub_points("sun", times)
    earth = eph.sub_points("earth", times)
    assert np.max(np.abs(sun.sub_lat_deg)) < 1.6  # lunar equator inclination ~1.54 deg
    assert np.max(np.abs(earth.sub_lat_deg)) < 7.0  # latitude libration ~6.7 deg
    assert np.max(np.abs(earth.sub_lon_deg)) < 8.2  # longitude libration ~7.9 deg
    assert 3.5e5 < earth.distance_km.min() and earth.distance_km.max() < 4.1e5


def test_subsolar_longitude_tracks_lunar_phase(eph):
    # Phase angle from Earth-Sun-Moon geometry: at full Moon the sub-solar point is near
    # the sub-Earth point; at new Moon it is ~180 deg away.
    times = time_grid(datetime(2027, 1, 1, tzinfo=timezone.utc), 24 * 30, 60)
    s = eph.sub_points("sun", times)
    e = eph.sub_points("earth", times)
    sep = np.abs(((s.sub_lon_deg - e.sub_lon_deg) + 180) % 360 - 180)
    assert sep.min() < 10 and sep.max() > 170
    # Sub-solar longitude decreases (Sun moves west across the lunar sky) ~12.2 deg/day.
    rate = np.diff(np.unwrap(np.radians(s.sub_lon_deg))) / np.radians(1) * 24
    assert np.median(rate) == pytest.approx(-360 / 29.53, rel=0.05)


def test_out_of_range_raises(eph):
    with pytest.raises(OutOfSupportedRangeError):
        eph.sub_points("sun", [datetime(2040, 1, 1, tzinfo=timezone.utc)])


class TestTabulated:
    def test_missing_tables_report_unavailable(self, tmp_path):
        p = HorizonsTableEphemeris(tmp_path)
        info = p.info()
        assert not info.available and "fetch_horizons" in info.unavailable_reason
        with pytest.raises(DataUnavailableError):
            p.sub_points("sun", [datetime(2027, 1, 1, tzinfo=timezone.utc)])

    def test_interpolation_matches_source(self, tmp_path, eph, write_json):
        # Fixture tables are produced FROM the analytic model, purely to test I/O + interpolation.
        start = datetime(2027, 1, 1, tzinfo=timezone.utc)
        coarse = time_grid(start, 48, 30)
        for body in ("sun", "earth"):
            sp = eph.sub_points(body, coarse)
            write_json(tmp_path / f"{body}.json", {
                "body": body, "source": "TEST FIXTURE (analytic)",
                "times_utc": [t.strftime("%Y-%m-%dT%H:%M:%SZ") for t in coarse],
                "sub_lat_deg": sp.sub_lat_deg.tolist(), "sub_lon_deg": sp.sub_lon_deg.tolist(),
                "distance_km": sp.distance_km.tolist()})
        tab = HorizonsTableEphemeris(tmp_path)
        assert tab.available and tab.info().provenance.value == "scientific_sourced"
        fine = time_grid(start + timedelta(minutes=7), 40, 13)
        for body in ("sun", "earth"):
            a, b = eph.body_vectors_km(body, fine), tab.body_vectors_km(body, fine)
            ang = np.degrees(np.arccos(np.clip(np.sum(a * b, 1) / np.linalg.norm(a, axis=1)
                                               / np.linalg.norm(b, axis=1), -1, 1)))
            assert ang.max() < 0.01
        with pytest.raises(OutOfSupportedRangeError):
            tab.sub_points("sun", [start + timedelta(days=5)])


def test_horizons_query_and_parser():
    url = build_query("2027-01-01", "2027-01-02", "1 h")
    assert "QUANTITIES=%2714%2C15%2C19%2C20%27" in url and "CENTER=%27500%40399%27" in url
    # Synthetic text in the Horizons CSV layout (format test only, values invented).
    text = """header junk
 Date__(UT)__HR:MN, , , ObsSub-LON, ObsSub-LAT, SunSub-LON, SunSub-LAT, r, rdot, delta, deldot,
$$SOE
 2027-Jan-01 00:00, , , 5.10, -3.20, 120.00, 1.10, 0.98, 0.1, 0.00257, 0.2,
 2027-Jan-01 01:00, , , 5.00, -3.25, 199.50, 1.10, 0.98, 0.1, 0.00257, 0.2,
$$EOE
"""
    t = parse_observer_csv(text)
    assert t["earth"]["sub_lon_deg"] == pytest.approx([5.10, 5.00])
    assert t["sun"]["sub_lon_deg"][1] == pytest.approx(-160.5)
    assert t["earth"]["distance_km"][0] == pytest.approx(0.00257 * 149_597_870.7)
    assert t["sun"]["times_utc"][1] == "2027-01-01T01:00:00Z"
