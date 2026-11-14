"""API contract, scenario comparison, rescheduler, and demo/scientific mode switching."""

import copy
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from app.core.errors import DataUnavailableError
from app.core.settings import load_settings
from app.core.timeutil import time_grid
from app.models.schemas import Mode, ProvenanceLevel, ResolvedLocation
from app.providers.ephemeris_analytic import AnalyticMeeusEphemeris
from app.providers.ephemeris_tabulated import HorizonsTableEphemeris
from app.providers.registry import ProviderBundle, build_bundle
from app.providers.terrain import LolaHorizonMaskProvider
from app.services.comparison import ScenarioComparisonService
from app.services.visibility import VisibilityCalculator

LANDING = "2027-01-15T12:00:00Z"


def scenario(site="malapert-massif", landing=LANDING, hours=336, **extra):
    return {"location": {"site_id": site}, "landing_utc": landing, "duration_hours": hours, **extra}


class TestBasics:
    def test_config_and_sites(self, client):
        cfg = client.get("/api/config").json()
        assert cfg["features"]["rescheduler"] is True
        assert cfg["simulation"]["supported_start_utc"].startswith("2026")
        sites = client.get("/api/sites").json()
        assert len(sites) >= 3 and {"id", "latitude_deg", "longitude_deg"} <= sites[0].keys()

    def test_mission_scenario_is_the_default(self, client):
        cfg = client.get("/api/config").json()
        mission, sim = cfg["mission"], cfg["simulation"]
        assert mission["name"] and mission["objective"]
        assert mission["duration_days"] * 24 == sim["default_duration_hours"]
        assert mission["landing_dates"]["initial"] == sim["default_landing_utc"]
        assert mission["landing_dates"]["alternative"] != mission["landing_dates"]["initial"]
        assert mission["spacecraft"] == {
            "power": "solar_panels_with_battery_storage",
            "communication": "direct_to_earth",
            "crewed": False,
        }
        site_ids = {s["id"] for s in client.get("/api/sites").json()}
        assert set(mission["candidate_sites"]) <= site_ids

    def test_mission_config_cannot_drift_from_defaults(self, settings, write_json, tmp_path):
        for mutate in (
            lambda m, s: m.update(duration_days=14),
            lambda m, s: m["landing_dates"].update(initial="2027-01-15T12:00:00Z"),
            lambda m, s: m["landing_dates"].update(alternative=m["landing_dates"]["initial"]),
            lambda m, s: m.update(candidate_sites=[]),
            lambda m, s: m["spacecraft"].pop("power"),
        ):
            raw = copy.deepcopy(settings.raw)
            mutate(raw["mission"], raw["simulation"])
            path = write_json(tmp_path / "bad_config.json", raw)
            with pytest.raises(ValueError):
                load_settings(path)

    def test_unknown_site_404(self, client):
        r = client.post("/api/scenario", json=scenario(site="atlantis"))
        assert r.status_code == 404 and r.json()["code"] == "UNKNOWN_SITE"


class TestScenario:
    def test_demo_result_is_labelled_synthetic(self, client):
        r = client.post("/api/scenario", json=scenario())
        assert r.status_code == 200, r.text
        body = r.json()
        prov = body["provenance"]
        assert prov["mode"] == "demo" and prov["overall"] == "synthetic"
        assert "DEMO MODE" in prov["label"]
        assert any("SYNTHETIC" in c for c in prov["caveats"])
        assert any("does not guarantee electrical power" in c for c in prov["caveats"])
        n = len(body["series"]["times_utc"])
        assert n == len(body["series"]["sun_visible"]) == len(body["series"]["earth_elevation_deg"])
        ids = {m["id"] for m in body["metrics"]}
        assert {"sun_visible_hours", "longest_earth_blackout_hours", "both_visible_pct"} <= ids

    def test_intervals_are_consistent(self, client):
        b = client.post("/api/scenario", json=scenario("de-gerlache-rim")).json()
        iv = b["intervals"]
        hours = lambda k: sum(x["duration_hours"] for x in iv[k])  # noqa: E731
        assert hours("sun_visible") + hours("sun_blocked") == pytest.approx(336, abs=0.01)
        assert hours("earth_visible") + hours("earth_blocked") == pytest.approx(336, abs=0.01)
        assert hours("both_visible") <= min(hours("sun_visible"), hours("earth_visible")) + 1e-6

    def test_custom_coordinates_flag_geometric_only(self, client):
        r = client.post("/api/scenario", json={"location": {"latitude_deg": -87.2, "longitude_deg": 45.0},
                                               "landing_utc": LANDING, "duration_hours": 48})
        assert r.status_code == 200
        b = r.json()
        assert b["location"]["is_custom"] is True
        assert b["provenance"]["overall"] == "geometric_only"
        assert any("flat geometric horizon" in c for c in b["provenance"]["caveats"])

    @pytest.mark.parametrize("loc", [{"latitude_deg": -95, "longitude_deg": 0},
                                     {"latitude_deg": -90, "longitude_deg": 0}, {}])
    def test_bad_coordinates(self, client, loc):
        r = client.post("/api/scenario", json={"location": loc, "landing_utc": LANDING, "duration_hours": 24})
        assert r.status_code == 422 and r.json()["code"] == "INVALID_INPUT"

    def test_unsupported_date_range(self, client):
        r = client.post("/api/scenario", json=scenario(landing="2035-01-01T00:00:00Z"))
        assert r.status_code == 422
        assert r.json()["code"] == "OUT_OF_SUPPORTED_RANGE"
        assert "supported_start_utc" in r.json()["details"]

    def test_window_running_past_range_end(self, client):
        r = client.post("/api/scenario", json=scenario(landing="2030-12-30T00:00:00Z", hours=240))
        assert r.json()["code"] == "OUT_OF_SUPPORTED_RANGE"

    def test_naive_timestamp_rejected(self, client):
        r = client.post("/api/scenario", json=scenario(landing="2027-01-15T12:00:00"))
        assert r.status_code == 422

    def test_duration_limits(self, client):
        assert client.post("/api/scenario", json=scenario(hours=5000)).status_code == 422
        assert client.post("/api/scenario", json=scenario(hours=0)).status_code == 422

    def test_step_is_coarsened_to_sample_cap(self, client, settings):
        r = client.post("/api/scenario", json=scenario(hours=1440, step_minutes=5)).json()
        assert len(r["series"]["times_utc"]) <= settings.simulation.max_samples + 1


class TestSnapshot:
    def test_snapshot_and_transition(self, client):
        r = client.post("/api/snapshot", json={"location": {"site_id": "de-gerlache-rim"},
                                               "time_utc": LANDING})
        assert r.status_code == 200
        s = r.json()
        for body in ("sun", "earth"):
            st = s[body]
            assert st["clearance_deg"] == pytest.approx(st["elevation_deg"] - st["terrain_horizon_deg"], abs=1e-3)
            assert st["visible"] == (st["clearance_deg"] > 0)
            if st["next_transition_utc"]:
                assert st["hours_until_transition"] > 0
                assert st["transition_kind"] == ("set" if st["visible"] else "rise")


class TestComparison:
    def test_compare_two_sites(self, client):
        r = client.post("/api/compare", json={"a": scenario("connecting-ridge"),
                                              "b": scenario("mons-mouton")})
        assert r.status_code == 200
        c = r.json()
        d = {x["id"]: x for x in c["deltas"]}
        sv = d["sun_visible_hours"]
        assert sv["delta"] == pytest.approx(sv["b"] - sv["a"], abs=1e-3)
        assert c["tradeoffs"] and any("not verified mission conditions" in t for t in c["tradeoffs"])
        text = " ".join(c["tradeoffs"] + [x["statement"] for x in c["deltas"]]).lower()
        for banned in ("recommend", "best site", "should land", "optimal"):
            assert banned not in text

    def test_identical_scenarios_have_zero_delta(self, client):
        c = client.post("/api/compare", json={"a": scenario(), "b": scenario()}).json()
        assert all(x["delta"] in (0, None) for x in c["deltas"])
        assert any("about the same" in t for t in c["tradeoffs"])

    def test_different_durations_noted(self, client):
        c = client.post("/api/compare", json={"a": scenario(hours=100), "b": scenario(hours=200)}).json()
        assert any("durations differ" in n for n in c["comparability_notes"])


class TestReschedule:
    def test_reschedule(self, client):
        r = client.post("/api/reschedule", json={
            "location": {"site_id": "de-gerlache-rim"},
            "original_landing_utc": LANDING, "proposed_landing_utc": "2027-01-22T12:00:00Z",
            "duration_hours": 240})
        assert r.status_code == 200
        b = r.json()
        assert b["shift_hours"] == pytest.approx(168)
        ids = [h["id"] for h in b["headline_changes"]]
        assert ids[:3] == ["sun_visible_hours", "earth_visible_hours", "both_visible_hours"]
        assert "longest_sun_blackout_hours" in ids and "longest_earth_blackout_hours" in ids
        assert b["comparison"]["a"]["label"] == "Original"


class TestModes:
    def test_scientific_mode_without_data_returns_503(self, client):
        r = client.post("/api/scenario", json=scenario(mode="scientific"))
        assert r.status_code == 503
        assert r.json()["code"] == "SCIENTIFIC_DATA_UNAVAILABLE"

    def test_providers_endpoint_reports_availability(self, client):
        demo = client.get("/api/providers?mode=demo").json()
        sci = client.get("/api/providers?mode=scientific").json()
        assert all(p["available"] for p in demo)
        assert sci[0]["id"] == "horizons_live"
        assert not sci[1]["available"] and "LOLA" in sci[1]["unavailable_reason"]

    def test_scientific_mode_with_data(self, tmp_path, settings, write_json):
        """With (fixture) Horizons tables + LOLA-format masks, scientific mode computes and labels results."""
        start = datetime(2027, 1, 14, tzinfo=timezone.utc)
        ana = AnalyticMeeusEphemeris(settings.simulation.supported_start, settings.simulation.supported_end)
        grid = time_grid(start, 24 * 5, 30)
        for body in ("sun", "earth"):
            sp = ana.sub_points(body, grid)
            write_json(tmp_path / "eph" / f"{body}.json", {
                "body": body, "times_utc": [t.strftime("%Y-%m-%dT%H:%M:%SZ") for t in grid],
                "sub_lat_deg": sp.sub_lat_deg.tolist(), "sub_lon_deg": sp.sub_lon_deg.tolist(),
                "distance_km": sp.distance_km.tolist()})
        write_json(tmp_path / "masks" / "x.json", {
            "site_id": "malapert-massif", "latitude_deg": -85.99, "longitude_deg": 2.9,
            "source": "TEST FIXTURE", "azimuth_deg": list(range(360)), "elevation_deg": [0.3] * 360})
        bundle = ProviderBundle(Mode.scientific, HorizonsTableEphemeris(tmp_path / "eph"),
                                LolaHorizonMaskProvider(tmp_path / "masks"))
        calc = VisibilityCalculator(bundle, settings)
        loc = ResolvedLocation(site_id="malapert-massif", name="M", latitude_deg=-85.99,
                               longitude_deg=2.9, is_custom=False, height_m=2)
        res = calc.scenario(loc, start + timedelta(hours=12), 48)
        assert res.provenance.overall == ProvenanceLevel.scientific_sourced
        assert res.provenance.effects.terrain_topography is True
        # Results agree with demo-mode geometry because the fixture tables came from the analytic model.
        demo = VisibilityCalculator(build_bundle(Mode.demo, settings), settings)
        d = demo.scenario(loc, start + timedelta(hours=12), 48)
        assert np.allclose(res.series.sun_elevation_deg, d.series.sun_elevation_deg, atol=0.01)

        # A custom location with no mask must fail loudly, not fall back to a flat horizon.
        other = loc.model_copy(update={"site_id": None, "latitude_deg": -87.0, "is_custom": True})
        with pytest.raises(DataUnavailableError):
            calc.scenario(other, start + timedelta(hours=12), 24)
        # Outside the table window -> out of range
        from app.core.errors import OutOfSupportedRangeError
        with pytest.raises(OutOfSupportedRangeError):
            calc.scenario(loc, start + timedelta(days=10), 24)


class TestLiveSkyAndCraters:
    def test_sky_now_is_current_and_names_its_source(self, client):
        before = datetime.now(timezone.utc).replace(microsecond=0)
        body = client.get("/api/sky/now?mode=demo").json()
        assert before <= datetime.fromisoformat(body["time_utc"].replace("Z", "+00:00")) <= datetime.now(timezone.utc)
        assert abs(body["sun"]["latitude_deg"]) < 2  # the Sun never strays far from the lunar equator
        assert abs(body["earth"]["latitude_deg"]) < 8
        assert body["source"]

    def test_sky_now_reports_jpl_failure_instead_of_substituting(self, client):
        r = client.get("/api/sky/now?mode=jpl")  # conftest points Horizons at a closed port
        assert r.status_code >= 500 and "sun" not in r.json()

    def test_craters_are_the_iau_values(self, client):
        craters = {c["name"]: c for c in client.get("/api/craters").json()}
        assert len(craters) > 1500
        assert craters["Shackleton"]["latitude_deg"] == pytest.approx(-89.67, abs=0.01)
        assert craters["Tycho"]["longitude_deg"] == pytest.approx(-11.2153, abs=0.01)  # 348.78 °E in the source
        assert craters["Haworth"]["diameter_km"] == pytest.approx(51.4, abs=0.1)
