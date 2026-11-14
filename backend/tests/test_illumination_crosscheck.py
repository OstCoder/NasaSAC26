"""Phase 3 Task 10: the committed NASA illumination cross-check.

The check itself needs the 189 MB LOLA wide DEM and rasterio, so it is run by
``scripts/check_psr_illumination.py`` and committed as a small document. CI
validates that document offline: the sources are recorded, every sampled PSR is
shadowed by the terrain model, and the check is not vacuous.
"""

import json
from pathlib import Path

REFERENCE = Path(__file__).resolve().parents[2] / "data" / "reference" / "illumination_crosscheck.json"
SCHEMA = "lunanav.illumination_crosscheck.v1"


def load() -> dict:
    return json.loads(REFERENCE.read_text())


def test_reference_records_its_sources_and_method():
    doc = load()
    assert doc["schema"] == SCHEMA
    assert doc["generator"] == "backend/scripts/check_psr_illumination.py"
    assert "NASA/GSFC" in doc["sources"]["psr_catalogue"]["provider"]
    assert "Mazarico" in doc["sources"]["psr_catalogue"]["derived_from"]
    assert "LOLA" in doc["sources"]["terrain"]["label"]
    assert doc["sources"]["terrain"]["sha256"]
    assert doc["method"]["sample_step_days"] == 1
    assert doc["method"]["span_days"] == 365
    assert doc["summary"]["psrs_checked"] >= 6


def test_every_sampled_psr_is_shadowed_by_the_terrain_model():
    doc = load()
    for row in doc["psrs"]:
        assert row["shadowed"] is True, row
        assert row["sunlit_samples"] == 0, row
        assert row["max_clearance_deg"] <= 0.0, row
        # The skyline is what produces the shadow, not a flat horizon or a coincidence.
        assert row["max_skyline_deg"] > row["max_sun_elevation_deg"] - 1e-9, row
        assert row["area_km2"] >= doc["method"]["min_area_km2"]
        assert 30.0 <= row["max_range_km"] <= 150.0


def test_summary_agrees_with_the_rows():
    doc = load()
    rows = doc["psrs"]
    summary = doc["summary"]

    assert summary["status"] == "pass"
    assert summary["sunlit_samples"] == 0
    assert summary["psrs_shadowed"] == len(rows)
    assert summary["worst_margin_deg"] == max(row["max_clearance_deg"] for row in rows)


def test_selection_accounting_is_complete():
    """Every eligible PSR is either checked or counted as skipped - none vanish."""
    summary = load()["summary"]

    assert summary["psrs_checked"] + summary["psrs_outside_dem"] \
        + summary["psrs_insufficient_range"] + summary["psrs_no_height"] \
        == summary["psrs_eligible"]
    assert summary["full_range_rows"] + summary["edge_limited_rows"] == summary["psrs_checked"]
    assert summary["psrs_eligible"] >= summary["psrs_checked"] >= 6


def test_the_check_is_not_vacuous():
    doc = load()
    skylines = [row["max_skyline_deg"] for row in doc["psrs"]]
    # A flat horizon (0 deg) would make the agreement meaningless.
    assert min(skylines) > 0.5
    assert max(skylines) < 90.0
    assert all(row["max_sun_elevation_deg"] > 0.0 for row in doc["psrs"])


def test_dem_checksum_matches_the_committed_wide_dem_record():
    doc = load()
    wide = json.loads((REFERENCE.parent / "wide_dem.json").read_text())
    assert doc["sources"]["terrain"]["sha256"] == wide["dem"]["sha256"]
    assert doc["sources"]["terrain"]["file"] == wide["dem"]["file"]
