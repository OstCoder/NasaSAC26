"""Task 4 deliverables: the shared mission specification.

Guards that the config is the single source the docs and both applications agree
on, and that requirement checking combines a site scenario with the configured
thresholds instead of hardcoded numbers.

Files under test:
  config/lunanav.config.json          - mission, landing presets, requirements
  data/demo/sites.json                - the site catalogue and candidate order
  docs/SPECIFICATIONS.md              - the human-readable specification
  frontend/src/types/api.ts           - the mirrored API contract
"""

import json
from pathlib import Path

import pytest

from app.core.settings import RequirementThresholds, load_settings
from app.models.schemas import RequirementStatus, ScenarioInput
from app.services.comparison import ScenarioService
from app.services.requirements import RequirementService, status_at_least, status_at_most

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "lunanav.config.json"
SITES = ROOT / "data" / "demo" / "sites.json"
SPEC = ROOT / "docs" / "SPECIFICATIONS.md"
TYPES = ROOT / "frontend" / "src" / "types" / "api.ts"

CANDIDATES = ("shackleton-rim", "connecting-ridge", "de-gerlache-rim")
SCENARIO = {"location": {"site_id": "connecting-ridge"},
            "landing_utc": "2026-12-01T00:00:00Z", "duration_hours": 168}


@pytest.fixture(scope="module")
def config(client):
    return client.get("/api/config").json()


# ------------------------------------------------------- shared config -----

class TestSharedSpecification:
    def test_mission_is_the_finalized_one(self, config):
        mission = config["mission"]
        assert mission["name"] == "Polar Ice Scout"
        assert mission["duration_days"] == 7
        assert mission["spacecraft"]["power"] == "solar_panels_with_battery_storage"
        assert mission["spacecraft"]["communication"] == "direct_to_earth"
        assert mission["spacecraft"]["crewed"] is False
        assert "permanently shadowed regions" in mission["objective"]

    def test_requirements_are_served_from_config(self, config, settings):
        req = config["requirements"]
        assert req["min_sun_visible_pct"] == settings.requirements.min_sun_visible_pct == 60
        assert req["min_earth_visible_pct"] == settings.requirements.min_earth_visible_pct == 50
        assert req["max_earth_blackout_hours"] == settings.requirements.max_earth_blackout_hours == 12
        assert req["psr_proximity"] == "preferred"
        assert "not official NASA mission specifications" in req["basis"]

    def test_landing_presets_are_the_two_mission_dates(self, config, settings):
        presets = config["simulation"]["landing_presets"]
        assert [p["key"] for p in presets] == ["primary", "alternate"]
        assert [p["utc"] for p in presets] == ["2026-12-01T00:00:00Z", "2026-12-11T00:00:00Z"]
        assert [p.utc.isoformat().replace("+00:00", "Z") for p in settings.landing_presets] == \
            [p["utc"] for p in presets]
        # the default landing time is the primary preset, not a third date
        assert config["simulation"]["default_landing_utc"] == presets[0]["utc"]

    def test_presets_stay_inside_the_supported_window(self, settings):
        sim = settings.simulation
        assert sim.supported_start <= sim.default_landing <= sim.supported_end
        for preset in settings.landing_presets:
            assert sim.supported_start <= preset.utc <= sim.supported_end

    def test_candidate_list_matches_the_site_catalogue(self, config, client):
        on_disk = json.loads(SITES.read_text())["mission_candidates"]
        assert config["mission"]["candidate_sites"] == on_disk == list(CANDIDATES)
        served = {s["id"] for s in client.get("/api/sites").json()}
        assert set(on_disk) <= served

    def test_out_of_window_preset_is_rejected(self, tmp_path):
        raw = json.loads(CONFIG.read_text())
        raw["simulation"]["landing_presets"][1]["utc"] = "2031-01-01T00:00:00Z"
        bad = tmp_path / "lunanav.config.json"
        bad.write_text(json.dumps(raw))
        with pytest.raises(ValueError, match="outside the supported window"):
            load_settings(bad)

    def test_frontend_contract_mirrors_the_config(self, config):
        ts = TYPES.read_text()
        for field in ("landing_presets", "requirements", "min_sun_visible_pct",
                      "max_earth_blackout_hours", "RequirementEvaluation"):
            assert field in ts, f"frontend/src/types/api.ts is missing {field!r}"

    def test_specification_document_covers_the_deliverable(self):
        doc = SPEC.read_text()
        for needed in (*CANDIDATES, "Polar Ice Scout", "2026-12-01", "2026-12-11",
                       "60 %", "50 %", "12 h", "JPL Horizons", "LOLA", "PSR",
                       "Review and approval"):
            assert needed in doc, f"docs/SPECIFICATIONS.md is missing {needed!r}"


# --------------------------------------------------- requirement checks -----

class TestRequirementChecks:
    def test_evaluation_checks_every_threshold(self, client):
        r = client.post("/api/requirements", json=SCENARIO)
        assert r.status_code == 200, r.text
        body = r.json()
        assert [c["id"] for c in body["checks"]] == [
            "min_sun_visible_pct", "min_earth_visible_pct", "max_earth_blackout_hours"]
        assert {c["comparison"] for c in body["checks"]} == {"at_least", "at_most"}
        assert body["requirements_source"].endswith("requirements")
        assert body["satisfied"] in (True, False, None)
        assert any("not a site recommendation" in n for n in body["notes"])

    def test_checked_values_equal_the_scenario_metrics(self, client):
        body = client.post("/api/requirements", json=SCENARIO).json()
        metrics = {m["id"]: m for m in client.post("/api/scenario", json=SCENARIO).json()["metrics"]}
        for check in body["checks"]:
            metric = metrics[{"min_sun_visible_pct": "sun_visible_pct",
                              "min_earth_visible_pct": "earth_visible_pct",
                              "max_earth_blackout_hours": "longest_earth_blackout_hours"}[check["id"]]]
            assert check["value"] == metric["value"]

    def test_thresholds_come_from_the_caller_not_the_code(self):
        result = ScenarioService().run(ScenarioInput(**SCENARIO))
        strict = RequirementThresholds(
            min_sun_visible_pct=99.0, min_earth_visible_pct=99.0,
            max_earth_blackout_hours=0.0, psr_proximity="optional", basis="test",
        )
        ev = RequirementService().evaluate(result, strict)
        assert [c.threshold for c in ev.checks] == [99.0, 99.0, 0.0]
        assert ev.satisfied is False
        assert any(c.status is RequirementStatus.not_met for c in ev.checks)

    def test_psr_preference_is_reported_not_scored(self, client):
        body = client.post("/api/requirements", json=SCENARIO).json()
        assert body["psr_preference"] == "preferred"
        assert body["nearest_psr"] and body["nearest_psr"]["distance_km"] > 0
        assert any("preference, not a threshold" in n for n in body["notes"])
        assert all(c["id"] != "psr_proximity" for c in body["checks"])

    def test_caller_can_override_thresholds(self, client):
        payload = {
            **SCENARIO,
            "thresholds": {
                "min_sun_visible_pct": 100,
                "min_earth_visible_pct": 100,
                "max_earth_blackout_hours": 0,
            },
        }
        body = client.post("/api/requirements", json=payload).json()
        assert [c["threshold"] for c in body["checks"]] == [100.0, 100.0, 0.0]
        assert "user-adjusted" in body["requirements_source"]
        assert body["satisfied"] is False
        assert any("not NASA flight requirements" in n for n in body["notes"])

    def test_partial_override_keeps_configured_defaults(self, client, settings):
        body = client.post(
            "/api/requirements",
            json={**SCENARIO, "thresholds": {"max_earth_blackout_hours": 0}},
        ).json()
        by_id = {c["id"]: c for c in body["checks"]}
        assert by_id["max_earth_blackout_hours"]["threshold"] == 0
        assert by_id["min_sun_visible_pct"]["threshold"] == settings.requirements.min_sun_visible_pct
        assert by_id["min_earth_visible_pct"]["threshold"] == settings.requirements.min_earth_visible_pct

    def test_invalid_thresholds_are_rejected(self, client):
        r = client.post(
            "/api/requirements",
            json={**SCENARIO, "thresholds": {"min_sun_visible_pct": 150}},
        )
        assert r.status_code == 422

    def test_demo_mode_verdict_is_labelled(self, client):
        notes = client.post("/api/requirements", json=SCENARIO).json()["notes"]
        assert any("synthetic" in n and "not verified mission conditions" in n for n in notes)


# ------------------------------------------------- censored-value rules -----

@pytest.mark.parametrize("value,censored,expected", [
    (61.0, True, RequirementStatus.met),        # lower bound already clears the target
    (59.0, True, RequirementStatus.unknown),    # true value could reach it
    (59.0, False, RequirementStatus.not_met),
    (None, False, RequirementStatus.unknown),
])
def test_at_least(value, censored, expected):
    assert status_at_least(value, 60.0, censored) is expected


@pytest.mark.parametrize("value,censored,expected", [
    (11.0, False, RequirementStatus.met),
    (11.0, True, RequirementStatus.unknown),    # true blackout could be longer
    (13.0, True, RequirementStatus.not_met),
    (None, True, RequirementStatus.unknown),
])
def test_at_most(value, censored, expected):
    assert status_at_most(value, 12.0, censored) is expected
