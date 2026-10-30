"""Live JPL Horizons provider and JPL mode, using a fake Horizons server."""

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from app.core.errors import JplUnavailableError
from app.core.settings import get_settings
from app.core.timeutil import time_grid
from app.models.schemas import Mode
from app.providers.ephemeris_analytic import AnalyticMeeusEphemeris
from app.providers.ephemeris_horizons_live import HorizonsLiveEphemeris
from app.providers.registry import get_bundle

from jpl_fakes import FakeHorizons

T0 = datetime(2027, 1, 15, 12, tzinfo=timezone.utc)


def provider(tmp_path, fake):
    s = get_settings()
    return HorizonsLiveEphemeris(s.jpl, tmp_path, s.simulation.supported_start, s.simulation.supported_end, fetch=fake)


def test_fetches_month_caches_and_interpolates(tmp_path):
    fake = FakeHorizons()
    p = provider(tmp_path, fake)
    times = time_grid(T0, 48, 7)
    sp = p.sub_points("sun", times)
    assert len(fake.calls) == 1 and "COMMAND=%27301%27" in fake.calls[0]
    assert (tmp_path / "horizons" / "2027-01.json").exists()
    ref = AnalyticMeeusEphemeris(T0 - timedelta(days=1), T0 + timedelta(days=5)).sub_points("sun", times)
    assert np.allclose(sp.sub_lat_deg, ref.sub_lat_deg, atol=1e-3)
    assert p.last_crosscheck_deg["sun"] < 1e-3

    # Second provider instance reads the disk cache: no new request.
    fake2 = FakeHorizons()
    p2 = provider(tmp_path, fake2)
    p2.sub_points("earth", times)
    assert fake2.calls == []


def test_window_spanning_two_months_fetches_both(tmp_path):
    fake = FakeHorizons()
    p = provider(tmp_path, fake)
    p.sub_points("earth", time_grid(datetime(2027, 1, 28, tzinfo=timezone.utc), 24 * 6, 60))
    assert len(fake.calls) == 2


@pytest.mark.parametrize("fail,needle", [
    ("network", "Could not reach JPL Horizons"),
    ("http500", "HTTP 500"),
    ("api_error", "Cannot interpret date"),
])
def test_failures_raise_and_do_not_cache(tmp_path, fail, needle):
    p = provider(tmp_path, FakeHorizons(fail=fail))
    with pytest.raises(JplUnavailableError, match=needle):
        p.sub_points("sun", [T0])
    assert not list((tmp_path / "horizons").glob("*.json")) if (tmp_path / "horizons").exists() else True
    assert p.info().unavailable_reason


def test_crosscheck_rejects_sign_flipped_longitudes(tmp_path):
    p = provider(tmp_path, FakeHorizons(lon_sign=-1))
    with pytest.raises(JplUnavailableError, match="horizons_lon_sign"):
        p.sub_points("sun", [T0])
    assert not (tmp_path / "horizons" / "2027-01.json").exists()


class TestJplModeApi:
    @pytest.fixture(autouse=True)
    def fake_jpl(self, tmp_path):
        eph = get_bundle(Mode.jpl).ephemeris
        old_fetch, old_dir = eph._fetch, eph.cache_dir
        eph._fetch, eph.cache_dir, eph._months = FakeHorizons(), tmp_path / "horizons", {}
        yield eph
        eph._fetch, eph.cache_dir, eph._months = old_fetch, old_dir, {}

    def test_jpl_mode_scenario_is_sourced_geometry_without_terrain(self, client):
        r = client.post("/api/scenario", json={"location": {"site_id": "malapert-massif"},
                                               "landing_utc": "2027-01-15T12:00:00Z", "duration_hours": 72,
                                               "mode": "jpl"})
        assert r.status_code == 200, r.text
        prov = r.json()["provenance"]
        assert prov["mode"] == "jpl" and prov["ephemeris"]["id"] == "horizons_live"
        assert prov["overall"] == "geometric_only" and prov["label"].startswith("JPL LIVE")
        assert any("flat geometric horizon" in c for c in prov["caveats"])

    def test_snapshot_reports_sub_points(self, client):
        r = client.post("/api/snapshot", json={"location": {"site_id": "malapert-massif"},
                                               "time_utc": "2027-01-15T12:00:00Z", "mode": "jpl",
                                               "lookahead_hours": 48})
        assert r.status_code == 200, r.text
        s = r.json()
        assert -1.6 < s["sun"]["sub_point"]["latitude_deg"] < 1.6
        assert 3.5e5 < s["earth"]["sub_point"]["distance_km"] < 4.1e5

    def test_jpl_unreachable_is_a_503_with_direction(self, client, fake_jpl):
        fake_jpl._fetch = FakeHorizons(fail="network")
        r = client.post("/api/scenario", json={"location": {"site_id": "malapert-massif"},
                                               "landing_utc": "2028-06-15T12:00:00Z", "duration_hours": 24,
                                               "mode": "jpl"})
        assert r.status_code == 503 and r.json()["code"] == "JPL_UNAVAILABLE"
        assert "internet" in r.json()["message"]
