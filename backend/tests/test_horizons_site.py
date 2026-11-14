"""Phase 2 Task 1: topocentric Horizons azimuth/elevation. No network."""

from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest

from app.core.errors import InvalidInputError, JplUnavailableError
from app.providers.horizons_site import (
    ObserverSite,
    SkyTrack,
    build_site_query,
    crosscheck_against_analytic,
    fetch_sky,
    fetch_site_track,
    parse_site_csv,
    step_minutes,
)

from jpl_fakes import AU, SITE_HEADER, FakeHorizonsSite

LAT, LON, ELEV_M = -89.78, 204.27, 1734.0
SITE = ObserverSite.at(LAT, LON, ELEV_M, 2.0, site_id="shackleton-rim")
START = datetime(2026, 12, 1, tzinfo=timezone.utc)

# Verbatim shape of the live service (2026-11-14), with our observer echoed back.
LIVE_SAMPLE = f"""\
 API VERSION: 1.3
 API SOURCE: NASA/JPL Horizons API

*******************************************************************************
 Target body name: Sun (10)                        {{source: DE441}}
 Center-site name: (user defined site below)
 Center geodetic : 204.270000, -89.780000, 1.736000           {{E-lon(deg),Lat(deg),Alt(km)}}
 Center pole/equ : MEAN_ME (high precision)        {{East-longitude positive}}
{SITE_HEADER}
$$SOE
 2026-Dec-01 00:00,*,i,  75.799377,     1.524114,  0.98633152463993, -1.2238326,
 2026-Dec-01 00:30,*,i,  75.546062,     1.524939,  0.98631679885693, -1.2238816,
$$EOE
"""


# ------------------------------------------------------------------- inputs --


def test_observer_site_validates_and_normalises_longitude():
    custom = ObserverSite.at(-89.45, -137.31, 1955.0, 2.0)
    assert custom.longitude_deg == pytest.approx(-137.31)  # stored in [-180, 180)
    assert custom.altitude_km == pytest.approx(1.957)
    with pytest.raises(InvalidInputError):
        ObserverSite.at(90.0, 0.0)  # exact pole: azimuth undefined
    with pytest.raises(InvalidInputError):
        ObserverSite.at(-89.0, 0.0, -30_000.0)  # below Horizons' -20 km floor
    with pytest.raises(InvalidInputError):
        ObserverSite.at(-89.0, 0.0, 2000.0, 500.0)  # 500 m mast is not a lander


@pytest.mark.parametrize("text,expected", [("30 m", 30.0), ("1 h", 60.0), ("90 min", 90.0), ("1 d", 1440.0)])
def test_step_minutes(text, expected):
    assert step_minutes(text) == expected


@pytest.mark.parametrize("bad", ["", "30", "half hour", "0 m", "-5 m"])
def test_step_rejects_unusable_intervals(bad):
    with pytest.raises(InvalidInputError):
        step_minutes(bad)


# -------------------------------------------------------------------- query --


def test_query_is_a_topocentric_geodetic_observer_table():
    url = build_site_query(body="sun", site=SITE, start=START, stop=START + timedelta(hours=6), step="30 m")
    q = parse_qs(urlparse(url).query)
    assert q["CENTER"] == ["'coord@301'"]
    assert q["COORD_TYPE"] == ["'GEODETIC'"]
    assert q["SITE_COORD"] == ["'204.270000,-89.780000,1.736000'"]
    assert q["COMMAND"] == ["'10'"]
    assert q["QUANTITIES"] == ["'4,20'"]
    assert q["APPARENT"] == ["'AIRLESS'"]  # geometric elevation, no refraction
    assert q["CSV_FORMAT"] == ["'YES'"] and q["ANG_FORMAT"] == ["'DEG'"]
    assert q["START_TIME"] == ["'2026-12-01 00:00'"]
    assert q["STOP_TIME"] == ["'2026-12-01 06:00'"]

    earth = build_site_query(body="earth", site=SITE, start=START, stop=START + timedelta(hours=1))
    assert parse_qs(urlparse(earth).query)["COMMAND"] == ["'399'"]


def test_west_longitude_is_sent_east_positive():
    west = ObserverSite.at(-89.45, -137.31, 1955.0)
    url = build_site_query(body="sun", site=west, start=START, stop=START + timedelta(hours=1))
    assert parse_qs(urlparse(url).query)["SITE_COORD"][0].startswith("'222.690000,")


# ------------------------------------------------------------------ parsing --


def test_parses_the_live_horizons_layout():
    track = parse_site_csv(LIVE_SAMPLE, site=SITE, body="sun")
    assert len(track) == 2
    assert track.times_utc[0] == START
    assert track.azimuth_deg[0] == pytest.approx(75.799377)
    assert track.elevation_deg[0] == pytest.approx(1.524114)
    assert track.elevation_deg[1] == pytest.approx(1.524939)
    assert track.range_km[0] == pytest.approx(0.98633152463993 * AU, rel=1e-9)
    assert track.info["frame"].startswith("MEAN_ME")
    assert track.step_minutes == pytest.approx(30.0)


def test_api_error_text_is_rejected():
    with pytest.raises(ValueError, match="no observer table"):
        parse_site_csv("API ERROR: one or more query parameter was not recognized", site=SITE, body="sun")


def test_missing_azimuth_column_is_rejected():
    text = LIVE_SAMPLE.replace("Azi_(a-app), Elev_(a-app)", "R.A._(a-app), DEC_(a-app)")
    with pytest.raises(ValueError, match="azi"):
        parse_site_csv(text, site=SITE, body="sun")


def test_an_answer_for_a_different_observer_is_rejected():
    text = LIVE_SAMPLE.replace("204.270000, -89.780000, 1.736000", "12.000000, 34.000000, 0.000000")
    with pytest.raises(ValueError, match="not the requested"):
        parse_site_csv(text, site=SITE, body="sun")


def test_an_answer_for_a_different_target_is_rejected():
    text = LIVE_SAMPLE.replace("Target body name: Sun (10)", "Target body name: Earth (399)")
    with pytest.raises(ValueError, match="Earth data but sun"):
        parse_site_csv(text, site=SITE, body="sun")


def test_non_increasing_timestamps_are_rejected():
    text = LIVE_SAMPLE.replace(" 2026-Dec-01 00:30", " 2026-Dec-01 00:00")
    with pytest.raises(ValueError, match="strictly increasing"):
        parse_site_csv(text, site=SITE, body="sun")


# ----------------------------------------------------------------- fetching --


def test_fetch_both_bodies_with_matching_timestamps():
    fake = FakeHorizonsSite()
    tracks = fetch_sky(SITE, START, START + timedelta(hours=6), "30 m", fetch=fake)
    assert set(tracks) == {"sun", "earth"}
    assert len(fake.calls) == 2
    assert tracks["sun"].times_utc == tracks["earth"].times_utc
    assert len(tracks["sun"]) == 13
    assert tracks["sun"].query_url.startswith("https://ssd.jpl.nasa.gov/api/horizons.api?")
    for track in tracks.values():
        check = crosscheck_against_analytic(track, tolerance_deg=0.5)
        assert check.passed, check.as_dict()
        assert check.max_elevation_deg < 0.1


@pytest.mark.parametrize("fail,needle", [
    ("network", "Could not reach JPL Horizons"),
    ("http500", "HTTP 500"),
    ("api_error", "Could not use the JPL Horizons response"),
])
def test_failures_raise_jpl_unavailable(fail, needle):
    with pytest.raises(JplUnavailableError, match=needle):
        fetch_site_track("sun", SITE, START, START + timedelta(hours=1), "30 m",
                         fetch=FakeHorizonsSite(fail=fail))


def test_missing_values_raise_instead_of_becoming_zero():
    with pytest.raises(JplUnavailableError, match="n.a."):
        fetch_site_track("earth", SITE, START, START + timedelta(hours=1), "30 m",
                         fetch=FakeHorizonsSite(na_row=0))


def test_window_step_and_row_guards():
    fake = FakeHorizonsSite()
    with pytest.raises(InvalidInputError):
        fetch_site_track("sun", SITE, START, START, "30 m", fetch=fake)
    with pytest.raises(InvalidInputError, match="longer than the requested window"):
        build_site_query(body="sun", site=SITE, start=START, stop=START + timedelta(minutes=10), step="1 h")
    with pytest.raises(InvalidInputError, match="truncates"):
        fetch_site_track("sun", SITE, START, START + timedelta(days=120), "1 m", fetch=fake)
    with pytest.raises(InvalidInputError):
        fetch_site_track("moon", SITE, START, START + timedelta(hours=1), fetch=fake)


# --------------------------------------------------------------- crosscheck --


def test_crosscheck_detects_a_systematic_offset():
    track = fetch_site_track("sun", SITE, START, START + timedelta(hours=2), "30 m", fetch=FakeHorizonsSite())
    shifted = SkyTrack(
        body="sun",
        site=track.site,
        times_utc=track.times_utc,
        azimuth_deg=track.azimuth_deg,
        elevation_deg=track.elevation_deg + 1.0,
        range_km=track.range_km,
    )
    check = crosscheck_against_analytic(shifted, tolerance_deg=0.5)
    assert not check.passed
    assert check.max_elevation_deg == pytest.approx(1.0, abs=0.1)
    assert check.as_dict()["passed"] is False
