"""Mid-project acceptance test: the terminal comparison CLI.

The CLI is the "readable terminal comparison table or report" deliverable. These
tests exercise its window resolution, its refusal to substitute data, the JSON
export and the table text, without writing into the repository.
"""

import json

import pytest

from app.core.settings import get_settings
from scripts.analyze_mission import (
    SCHEMA,
    build_document,
    main,
    render_report,
    resolve_window,
)

CANDIDATES = ["shackleton-rim", "connecting-ridge", "de-gerlache-rim"]


def test_resolves_both_mission_dates_at_seven_days():
    settings = get_settings()

    assert resolve_window(settings, "2026-12-01", 7).key == "initial"
    assert resolve_window(settings, "2026-12-01T00:00:00Z", 7).key == "initial"
    assert resolve_window(settings, "2026-12-11", 7).key == "alternative"


@pytest.mark.parametrize("start,days", [("2026-12-03", 7), ("2026-12-01", 6)])
def test_refuses_an_uncovered_window_instead_of_substituting(start, days):
    with pytest.raises(ValueError, match="No committed JPL Horizons series"):
        resolve_window(get_settings(), start, days)


def test_document_carries_every_candidate_and_requirement():
    settings = get_settings()
    document = build_document(settings, resolve_window(settings, "2026-12-01", 7), CANDIDATES)

    assert document["schema"] == SCHEMA
    assert [report["site"]["site_id"] for report in document["sites"]] == CANDIDATES
    for report in document["sites"]:
        assert report["schema"] == "lunanav.mission_report.v1"
        assert [check["id"] for check in report["requirements"]["checks"]] == [
            "min_sun_visible_pct", "min_earth_visible_pct", "max_earth_blackout_hours"]
        assert report["requirements"]["satisfied"] in {True, False, None}
        assert report["terrain"]["geometric_only"] is False
    assert len(document["delay"]) == len(CANDIDATES)
    assert all(row["available"] for row in document["delay"])


def test_document_is_reproducible():
    settings = get_settings()
    window = resolve_window(settings, "2026-12-11", 7)
    first = json.dumps(build_document(settings, window, CANDIDATES), sort_keys=True)
    second = json.dumps(build_document(settings, window, CANDIDATES), sort_keys=True)

    assert first == second


def test_report_is_readable_and_states_the_verdicts():
    settings = get_settings()
    document = build_document(settings, resolve_window(settings, "2026-12-01", 7), CANDIDATES)
    text = render_report(document)

    assert "Phase 3 mid-project comparison" in text
    for site in CANDIDATES:
        assert site in text
    assert "Minimum sunlight availability" in text  # failing requirement, explained
    assert "not met" in text
    assert "not a landing-safety" in text
    assert "Longest blackout" in text


def test_unknown_site_is_refused():
    settings = get_settings()
    window = resolve_window(settings, "2026-12-01", 7)

    with pytest.raises(Exception, match="atlantis|unknown|Unknown"):
        build_document(settings, window, ["atlantis"])


def test_empty_selection_is_refused():
    settings = get_settings()
    window = resolve_window(settings, "2026-12-01", 7)

    with pytest.raises(ValueError, match="no sites selected"):
        build_document(settings, window, [])


def test_delay_deltas_flag_window_limited_metrics():
    settings = get_settings()
    document = build_document(settings, resolve_window(settings, "2026-12-01", 7), CANDIDATES)

    assert any(row["censored_metrics"] for row in document["delay"])
    assert all("censored_metrics" in row for row in document["delay"])
    text = render_report(document)
    assert "* delta uses a window-limited" in text
    assert "*" in text.split("Delay effect", 1)[1]


def test_cli_reports_an_uncovered_date(capsys):
    assert main(["--start", "2026-12-03"]) == 2

    out = capsys.readouterr().out
    assert "No committed JPL Horizons series" in out
    assert "2026-12-01" in out and "2026-12-11" in out


def test_cli_reports_an_unknown_site(capsys):
    assert main(["--site", "atlantis"]) == 2
    assert "atlantis" in capsys.readouterr().out
