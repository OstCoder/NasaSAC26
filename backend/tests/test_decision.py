"""Phase 5: decision support composes checks and ranks only eligible sites.

The evaluator must never turn a failure or an undecided value into a favourable
rank. These tests use the same HTTP client and committed demo data as the rest
of the suite.
"""

from fastapi.testclient import TestClient

from app.models.schemas import DecisionWeights
from app.main import app
from app.services.decision import _score_eligible

client = TestClient(app)

BASE = {
    "landing_utc": "2026-12-01T00:00:00Z",
    "duration_hours": 168,
    "site_ids": ["shackleton-rim", "connecting-ridge", "de-gerlache-rim"],
}
EASY = {
    "min_sun_visible_pct": 0,
    "min_earth_visible_pct": 0,
    "max_earth_blackout_hours": 8000,
    "max_darkness_hours": 8000,
    "power_demand_w": 0,
}


def _payload(**thresholds):
    return {**BASE, "thresholds": {**EASY, **thresholds}}


def test_decision_evaluates_every_candidate_with_all_checks():
    response = client.post("/api/decision", json=BASE)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["schema"] == "lunanav.mission_decision.v1"
    assert body["landing_utc"] == "2026-12-01T00:00:00Z"
    assert len(body["sites"]) == 3
    assert [site["site_id"] for site in body["sites"]] == BASE["site_ids"]
    for site in body["sites"]:
        assert {check["id"] for check in site["checks"]} == {
            "min_sun_visible_pct",
            "min_earth_visible_pct",
            "max_earth_blackout_hours",
            "max_darkness_hours",
            "power_system_survives",
        }
        assert site["power"]["available"] is True
        assert site["power"]["battery"] is not None
        assert site["satisfied"] in (True, False, None)
        assert site["rank"] is None if site["satisfied"] is not True else site["rank"] is not None
    assert body["recommendation"]["status"] in ("ranked", "no_eligible_site")
    assert "safe, approved, or flight-ready" in " ".join(body["notes"])


def test_only_passing_candidates_are_ranked():
    body = client.post("/api/decision", json=_payload()).json()
    ranked = [site for site in body["sites"] if site["rank"] is not None]

    assert all(site["rank"] is None for site in body["sites"] if site["satisfied"] is not True)
    if ranked:
        assert sorted(site["rank"] for site in ranked) == list(range(1, len(ranked) + 1))
        assert body["recommendation"]["status"] == "ranked"
        assert body["recommendation"]["ranked_site_ids"] == [
            site["site_id"] for site in sorted(ranked, key=lambda site: site["rank"])
        ]
        assert all(0 <= site["score"] <= 100 for site in ranked)
    else:
        assert body["recommendation"]["status"] == "no_eligible_site"


def test_ranked_rows_use_normalised_measured_values():
    rows = [
        {"site_id": "A", "satisfied": True, "rank": None, "score": None, "_order": 0,
         "_raw": {"sun_visible_pct": 80.0, "earth_visible_pct": 40.0,
                  "longest_earth_blackout_hours": 10.0, "psr_distance_km": 8.0}},
        {"site_id": "B", "satisfied": True, "rank": None, "score": None, "_order": 1,
         "_raw": {"sun_visible_pct": 60.0, "earth_visible_pct": 60.0,
                  "longest_earth_blackout_hours": 4.0, "psr_distance_km": 2.0}},
        {"site_id": "C", "satisfied": False, "rank": None, "score": None, "_order": 2,
         "_raw": {"sun_visible_pct": 100.0, "earth_visible_pct": 100.0,
                  "longest_earth_blackout_hours": 0.0, "psr_distance_km": 1.0}},
    ]
    _score_eligible(rows, DecisionWeights(sunlight=0.4, earth_visibility=0.3,
                                          communication=0.2, science=0.1))

    assert rows[2]["rank"] is None and rows[2]["score"] is None
    assert {rows[0]["rank"], rows[1]["rank"]} == {1, 2}
    assert rows[1]["score"] > rows[0]["score"]  # better Earth, blackout and PSR proximity
    assert rows[1]["score_components"]["communication"] == 1.0
    assert rows[0]["score_components"]["communication"] == 0.0


def test_failed_or_undecided_sites_never_receive_a_rank():
    body = client.post("/api/decision", json=_payload(
        min_sun_visible_pct=100,
        min_earth_visible_pct=100,
        max_earth_blackout_hours=0,
        max_darkness_hours=0,
        power_demand_w=100000,
    )).json()
    assert all(site["satisfied"] is False for site in body["sites"])
    assert all(site["rank"] is None and site["score"] is None for site in body["sites"])
    assert body["recommendation"]["status"] == "no_eligible_site"
    assert body["recommendation"]["top_site_id"] is None


def test_power_demand_changes_the_battery_check():
    easy = client.post("/api/decision", json=_payload()).json()
    heavy = client.post("/api/decision", json=_payload(power_demand_w=100000)).json()

    easy_checks = {site["site_id"]: {c["id"]: c for c in site["checks"]} for site in easy["sites"]}
    heavy_checks = {site["site_id"]: {c["id"]: c for c in site["checks"]} for site in heavy["sites"]}
    for site_id in easy_checks:
        assert easy_checks[site_id]["power_system_survives"]["status"] == "met"
        assert heavy_checks[site_id]["power_system_survives"]["status"] == "not_met"
    assert heavy["recommendation"]["status"] == "no_eligible_site"


def test_advisory_blackout_is_visible_but_does_not_gate_ranking():
    body = client.post("/api/decision", json={
        **BASE,
        "landing_utc": "2026-12-01T00:00:00Z",
        "thresholds": {
            "min_sun_visible_pct": 0,
            "min_earth_visible_pct": 0,
            "max_earth_blackout_hours": 12,
            "max_darkness_hours": 16,
            "power_demand_w": 40,
        },
        "optional_checks": ["max_earth_blackout_hours"],
    }).json()
    ranked = [site for site in body["sites"] if site["rank"] is not None]
    assert len(ranked) == 1
    assert ranked[0]["site_id"] == "connecting-ridge"
    blackout = next(c for c in ranked[0]["checks"] if c["id"] == "max_earth_blackout_hours")
    assert blackout["required"] is False
    assert blackout["status"] in ("unknown", "not_met")


def test_non_preset_date_reports_power_as_undecided():
    body = client.post("/api/decision", json={
        **BASE,
        "landing_utc": "2026-12-05T00:00:00Z",
        "thresholds": EASY,
    }).json()
    assert all(site["power"]["available"] is False for site in body["sites"])
    power_checks = [
        next(c for c in site["checks"] if c["id"] == "power_system_survives")
        for site in body["sites"]
    ]
    assert all(check["status"] == "unknown" for check in power_checks)
    assert all(site["rank"] is None for site in body["sites"])
    assert body["recommendation"]["status"] == "no_eligible_site"


def test_psr_context_and_limitations_are_explicit():
    body = client.post("/api/decision", json=_payload()).json()
    for site in body["sites"]:
        assert site["nearest_psr"] is not None
        assert site["nearest_psr"]["distance_km"] > 0
    notes = " ".join(body["notes"]).lower()
    assert "not proof of water ice" in notes
    assert "not a universal nasa" in notes


def test_science_priority_explains_psr_proximity_without_overclaiming():
    body = client.post("/api/decision", json={
        **_payload(),
        "weights": {"sunlight": 0.3, "earth_visibility": 0.2, "communication": 0.1, "science": 0.4},
    }).json()
    for site in body["sites"]:
        reason = " ".join(site["reasons"])
        assert "Science priority includes" in reason
        assert "not water-ice or rover-access evidence" in reason


def test_decision_accepts_a_custom_panel_orientation():
    body = client.post("/api/decision", json={
        **_payload(),
        "panel_design": "fixed",
        "panel_tilt_deg": 45,
        "panel_azimuth_deg": 180,
    }).json()
    assert body["sites"]
    for site in body["sites"]:
        assert site["power"]["available"] is True
        assert site["power"]["panel_design"] == "fixed"
        assert site["power"]["panel_tilt_deg"] == 45
        assert site["power"]["panel_azimuth_deg"] == 180


def test_invalid_weights_are_rejected():
    payload = {
        **BASE,
        "weights": {"sunlight": 0, "earth_visibility": 0, "communication": 0, "science": 0},
    }
    assert client.post("/api/decision", json=payload).status_code == 422


def test_decision_is_deterministic():
    first = client.post("/api/decision", json=_payload()).json()
    second = client.post("/api/decision", json=_payload()).json()
    assert first == second


# The suite runs in Demo Mode, whose synthetic skylines make both long-duration
# checks censored. Mark those two advisory so the test exercises date/load
# ranking rather than the (correct) refusal to pass an undecidable check.
MILESTONE_THRESHOLDS = {
    "min_sun_visible_pct": 0,
    "min_earth_visible_pct": 20,
    "max_earth_blackout_hours": 12,
    "max_darkness_hours": 16,
    "power_demand_w": 40,
}
MILESTONE_PAYLOAD = {
    **BASE,
    "optional_checks": ["max_earth_blackout_hours", "max_darkness_hours"],
    "thresholds": MILESTONE_THRESHOLDS,
}


def test_changing_the_landing_date_changes_the_recommendation():
    """Milestone: a planner changes the date and sees the best eligible site."""
    initial = client.post("/api/decision", json={
        **MILESTONE_PAYLOAD,
        "landing_utc": "2026-12-01T00:00:00Z",
    }).json()
    alternative = client.post("/api/decision", json={
        **MILESTONE_PAYLOAD,
        "landing_utc": "2026-12-11T00:00:00Z",
    }).json()

    assert initial["recommendation"]["status"] == "no_eligible_site"
    assert all(site["rank"] is None for site in initial["sites"])

    assert alternative["recommendation"]["status"] == "ranked"
    assert alternative["recommendation"]["top_site_id"] == "de-gerlache-rim"
    assert alternative["recommendation"]["ranked_site_ids"] == [
        "de-gerlache-rim", "connecting-ridge",
    ]
    top = next(site for site in alternative["sites"] if site["site_id"] == "de-gerlache-rim")
    assert top["rank"] == 1
    assert top["satisfied"] is True
    assert top["metrics"]["earth_visible_pct"] >= 20
    assert any("Rank 1 of" in reason for reason in top["reasons"])


def test_changing_the_power_requirement_changes_the_recommendation():
    """Milestone: a changed spacecraft load can remove the only eligible site."""
    nominal = client.post("/api/decision", json={
        **MILESTONE_PAYLOAD,
        "landing_utc": "2026-12-11T00:00:00Z",
        "thresholds": {**MILESTONE_THRESHOLDS, "power_demand_w": 40},
    }).json()
    overloaded = client.post("/api/decision", json={
        **MILESTONE_PAYLOAD,
        "landing_utc": "2026-12-11T00:00:00Z",
        "thresholds": {**MILESTONE_THRESHOLDS, "power_demand_w": 100_000},
    }).json()

    assert nominal["recommendation"]["top_site_id"] == "de-gerlache-rim"
    assert overloaded["recommendation"]["status"] == "no_eligible_site"
    assert all(site["rank"] is None for site in overloaded["sites"])
    assert all(
        next(check for check in site["checks"] if check["id"] == "power_system_survives")["status"]
        == "not_met"
        for site in overloaded["sites"]
    )
