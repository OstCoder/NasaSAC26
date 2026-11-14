"""Phase 3 Task 11 / Phase 4 Task 3: one result envelope per site and window.

Phase 3 produces a series, adjusted visibility, intervals, metrics and
requirement verdicts in four places. A chart, a report and a reviewer should not
have to join them by hand, so this module assembles one document:

``site`` -> ``window`` -> ``terrain`` -> ``sunlight`` / ``earth`` /
``simultaneous_visibility`` -> ``metrics`` -> ``requirements`` -> ``model``.

Two properties matter:
- **One source of truth.** Every number is read from
  ``terrain_horizon_response`` (which itself delegates visibility to
  ``phase3.visibility_response``) and the requirement verdicts from
  ``requirements.CHECKS`` — the same thresholds the API already serves. Nothing
  is recomputed here.
- **Reproducible.** There is no wall-clock field and no set iteration:
  ``mission_report_json`` sorts keys, so a re-run on the committed data produces
  the same bytes. A test asserts that.

The envelope is geometry, not a mission verdict: Sun above terrain is not power,
Earth above terrain is not a link budget, and ``unknown`` in a requirement check
is not a pass.
"""

from __future__ import annotations

import json

from app.core.errors import DataUnavailableError
from app.core.settings import Settings, get_settings
from app.models.schemas import RequirementStatus
from app.services.phase3 import visibility_response
from app.services.requirements import (
    CHECKS,
    REQUIREMENTS_SOURCE,
    status_at_least,
    status_at_most,
)
from app.services.terrain_horizon import terrain_horizon_response

SCHEMA = "lunanav.mission_report.v1"
VERSION = 1
UNIT_HINT = "angles in degrees, durations in hours, percentages in percent, distances in km"

NOTES = [
    "Every value is copied from /api/terrain-horizon and /api/phase3 on the committed data; "
    "this document adds structure, not new calculation.",
    "Sun above terrain is a precondition for solar power, not a power estimate; Earth above "
    "terrain is line of sight, not a communications link budget.",
    "A requirement check of 'unknown' is not a pass: the window-limited value cannot decide it.",
    "No wall-clock field is included, so re-running on the same committed inputs reproduces "
    "the same document byte for byte.",
]


def _requirements(metrics: list[dict], settings: Settings) -> dict:
    """The same three Phase 1 checks and thresholds /api/requirements uses."""
    req = settings.requirements
    by_id = {metric.get("id"): metric for metric in metrics}
    checks: list[dict] = []
    statuses: list[RequirementStatus] = []
    for check_id, label, metric_id, unit, attr, comparison in CHECKS:
        metric = by_id.get(metric_id) or {}
        value = metric.get("value")
        censored = bool(metric.get("censored"))
        threshold = float(getattr(req, attr))
        status = (status_at_least if comparison == "at_least" else status_at_most)(
            value, threshold, censored)
        statuses.append(status)
        checks.append({
            "id": check_id,
            "label": label,
            "unit": unit,
            "comparison": comparison,
            "threshold": threshold,
            "value": value,
            "status": status.value,
            "censored": censored,
        })
    if any(status is RequirementStatus.not_met for status in statuses):
        satisfied: bool | None = False
    elif any(status is RequirementStatus.unknown for status in statuses):
        satisfied = None
    else:
        satisfied = True
    return {
        "source": REQUIREMENTS_SOURCE,
        "satisfied": satisfied,
        "checks": checks,
        "note": "met / not_met / unknown per check; unknown is not a pass and this is not a ranking.",
    }


def mission_report(*, site_id: str, window: str = "initial",
                   settings: Settings | None = None) -> dict:
    """The Phase 3 result envelope for one site and mission window."""
    settings = settings or get_settings()
    horizon = terrain_horizon_response(site_id=site_id, window=window, settings=settings)
    if not horizon["visibility"]["available"]:
        raise DataUnavailableError(
            f"{site_id!r} has no committed series, so there is no mission report for it.",
            details={"site_id": site_id, "window": window,
                     "reason": horizon["visibility"].get("reason")},
        )
    report = visibility_response(site_id=site_id, window=window, settings=settings)
    summary = report["summary"]
    terrain = horizon["terrain"]
    comparison = horizon["comparison"]

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "site": {
            "site_id": horizon["site"]["site_id"],
            "name": horizon["site"]["name"],
            "latitude_deg": horizon["site"]["latitude_deg"],
            "longitude_deg": horizon["site"]["longitude_deg"],
            "elevation_m": horizon["site"]["elevation_m"],
            "height_m": horizon["site"].get("height_m"),
        },
        "window": {
            "key": report["window"]["key"],
            "label": report["window"]["label"],
            "start_utc": report["window"]["start_utc"],
            "stop_utc": report["window"]["stop_utc"],
            "step": report["window"]["step"],
            "samples": report["window"]["samples"],
        },
        "terrain": {
            "basis": terrain["basis"],
            "geometric_only": terrain["geometric_only"],
            "source": terrain["source"],
            "provenance": terrain["provenance"],
            "observer_height_m": terrain["observer_height_m"],
            "azimuth_step_deg": terrain["azimuth_step_deg"],
            "max_obstruction_deg": terrain["summary"].get("max_obstruction_deg"),
            "max_obstruction_azimuth_deg": terrain["summary"].get("max_obstruction_azimuth_deg"),
            "coverage": terrain["coverage"],
            "uncertainty": terrain["uncertainty"],
            "sun_above_skyline": (comparison["sun"] or {}).get("above_skyline"),
            "sun_blocked_by_terrain": (comparison["sun"] or {}).get("blocked_by_terrain"),
            "earth_above_skyline": (comparison["earth"] or {}).get("above_skyline"),
            "earth_blocked_by_terrain": (comparison["earth"] or {}).get("blocked_by_terrain"),
        },
        "sunlight": {
            "availability_percent": summary["sun_visible_pct"],
            "visible_hours": summary["sun_visible_hours"],
            "longest_darkness_hours": summary["longest_sun_blackout_hours"],
            "windows": report["intervals"]["sun_visible"],
        },
        "earth": {
            "visibility_percent": summary["earth_visible_pct"],
            "visible_hours": summary["earth_visible_hours"],
            "longest_blackout_hours": summary["longest_earth_blackout_hours"],
            "windows": report["intervals"]["earth_visible"],
        },
        "simultaneous_visibility": {
            "availability_percent": summary["both_visible_pct"],
            "visible_hours": summary["both_visible_hours"],
            "longest_gap_hours": summary["longest_no_simultaneous_hours"],
            "windows": report["intervals"]["both_visible"],
        },
        "metrics": report["metrics"],
        "requirements": _requirements(report["metrics"], settings),
        "model": {
            "visibility_type": "terrain-adjusted geometry",
            "status": "calculated",
            "rule": report["rule"],
            "ephemeris": report["provenance"]["ephemeris"],
            "terrain": report["provenance"]["terrain"],
            "terrain_provenance": report["provenance"]["terrain_provenance"],
            "time": report["provenance"]["time"],
            "sampling": report["provenance"]["sampling"],
            "expected_terrain_provenance": report["provenance"]["expected_terrain_provenance"],
            "units": UNIT_HINT,
        },
        "sources": {
            "series_endpoint": f"/api/phase3?site_id={site_id}&window={window}",
            "terrain_endpoint": f"/api/terrain-horizon?site_id={site_id}&window={window}",
        },
        "notes": NOTES,
    }


def mission_report_json(*, site_id: str, window: str = "initial",
                        settings: Settings | None = None, indent: int | None = 2) -> str:
    """The envelope as stable JSON: sorted keys, fixed separators, no wall clock."""
    return json.dumps(
        mission_report(site_id=site_id, window=window, settings=settings),
        sort_keys=True,
        indent=indent,
        separators=(",", ":") if indent is None else None,
    )
