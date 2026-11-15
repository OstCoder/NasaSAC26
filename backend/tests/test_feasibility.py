"""Phase 4: the feasibility matrix composes committed answers, no new physics.

The matrix must agree with the services it reuses: the requirement checks use
``requirements.py``'s status rules and thresholds, the terrain numbers come
from ``phase3.visibility_response``, and the geometric baselines reuse the
Task 1/Task 2 ``> 0`` rule. These tests verify that composition rather than
re-deriving the physics.
"""

from fastapi.testclient import TestClient

from app.core.settings import get_settings
from app.main import app
from app.services.phase3 import visibility_response
from app.services.sites import get_site_repository

client = TestClient(app)

CHECK_IDS = {"min_sun_visible_pct", "min_earth_visible_pct", "max_earth_blackout_hours",
             "max_darkness_hours"}


def _matrix():
    from app.services.feasibility import feasibility_matrix
    return feasibility_matrix()


def test_matrix_covers_every_candidate_and_window():
    settings = get_settings()
    matrix = _matrix()
    sites = list(settings.raw["mission"]["candidate_sites"])
    assert len(matrix["rows"]) == 2 * len(sites)
    assert [(row["site_id"], row["window"]["key"]) for row in matrix["rows"]] == [
        (site, window) for site in sites for window in ("initial", "alternative")
    ]


def test_every_row_has_all_requirement_checks_with_config_thresholds():
    thresholds = get_settings().requirements
    for row in _matrix()["rows"]:
        assert row.get("available", True)
        checks = {check["id"]: check for check in row["checks"]}
        assert set(checks) == CHECK_IDS
        assert checks["min_sun_visible_pct"]["threshold"] == thresholds.min_sun_visible_pct
        assert checks["min_earth_visible_pct"]["threshold"] == thresholds.min_earth_visible_pct
        assert checks["max_earth_blackout_hours"]["threshold"] == thresholds.max_earth_blackout_hours
        assert checks["max_darkness_hours"]["threshold"] == thresholds.max_darkness_hours
        assert checks["min_sun_visible_pct"]["comparison"] == "at_least"
        assert checks["max_earth_blackout_hours"]["comparison"] == "at_most"


def test_satisfied_is_the_three_state_conjunction_of_the_checks():
    for row in _matrix()["rows"]:
        statuses = [check["status"] for check in row["checks"]]
        if "not_met" in statuses:
            assert row["satisfied"] is False
        elif "unknown" in statuses:
            assert row["satisfied"] is None
        else:
            assert row["satisfied"] is True


def test_row_checks_match_the_requirement_service_rules():
    """A blackout over the cap fails outright; a capped one can only be unknown."""
    for row in _matrix()["rows"]:
        for check in row["checks"]:
            assert check["value"] is None or row["summary"] is not None
            if check["id"] == "max_earth_blackout_hours":
                blackout = row["summary"]["longest_earth_blackout_hours"]
                assert check["value"] == blackout
                if blackout is not None and blackout > check["threshold"]:
                    assert check["status"] == "not_met"
                elif blackout is not None:
                    assert check["status"] in ("met", "unknown")


def test_terrain_rows_agree_with_the_phase3_endpoint():
    for row in _matrix()["rows"]:
        report = visibility_response(
            site_id=row["site_id"], window=row["window"]["key"])
        assert row["summary"]["sun_visible_pct"] == report["summary"]["sun_visible_pct"]
        assert row["summary"]["earth_visible_pct"] == report["summary"]["earth_visible_pct"]
        assert row["summary"]["longest_earth_blackout_hours"] == (
            report["summary"]["longest_earth_blackout_hours"])
        assert row["mask"]["max_range_km"] == report["mask"].get("max_range_km")


def test_terrain_basis_is_scientific_sourced_masks():
    for row in _matrix()["rows"]:
        assert row["basis"] == "terrain"
        assert row["mask"]["provenance"] == "scientific_sourced"
        assert row["mask"]["max_range_km"] >= 150.0


def test_geometric_baseline_matches_the_geometric_services():
    from app.services.geometric_earth import earth_visibility_response
    settings = get_settings()
    for row in _matrix()["rows"]:
        earth = earth_visibility_response(
            site_id=row["site_id"], window=row["window"]["key"])
        baseline = row["geometric_baseline"]
        assert baseline["basis"] == "geometric"
        earth_pct = earth["summary"]["visible_sample_pct"]
        assert baseline["earth"]["visible_sample_pct"] == earth_pct


def test_geometric_and_terrain_are_reported_side_by_side_not_merged():
    """Initial window: Earth is geometrically invisible everywhere; terrain may differ."""
    for row in _matrix()["rows"]:
        if row["window"]["key"] == "initial":
            assert row["geometric_baseline"]["earth"]["visible_sample_pct"] == 0.0
        assert "geometric_baseline" in row
        assert row["geometric_baseline"]["basis"] != row["basis"]


def test_site_context_carries_psr_proximity():
    repository = get_site_repository()
    for row in _matrix()["rows"]:
        site = repository.get(row["site_id"])
        assert row["context"]["psrs_within_10_km"] == site.psrs_within_10_km
        assert row["context"]["nearest_psr"]["psr_id"] == site.nearest_psr.psr_id


def test_matrix_notes_never_rank():
    notes = " ".join(_matrix()["notes"]).lower()
    assert "not a ranking" in notes
    assert "does not guarantee a successful communication link" in notes


def test_api_contract():
    response = client.get("/api/feasibility")
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema"] == "lunanav.feasibility_matrix.v1"
    assert payload["requirements_source"].endswith("-> requirements")
    assert set(payload["thresholds"]) == {
        "min_sun_visible_pct", "min_earth_visible_pct", "max_earth_blackout_hours",
        "max_darkness_hours"}
    assert len(payload["rows"]) == 6
    for row in payload["rows"]:
        assert row["satisfied"] in (True, False, None)
