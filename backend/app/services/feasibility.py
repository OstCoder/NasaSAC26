"""One matrix: every Phase 1 candidate against both mission windows.

Phase 4 requirement: a feasibility table that composes what the committed
data already says - it computes no new physics:

- Terrain-adjusted visibility and metrics come from
  :func:`app.services.phase3.visibility_response` (committed Horizons series,
  committed LOLA horizon masks).
- The requirement checks reuse ``app.services.requirements``' threshold table,
  status rules and detail strings, so a verdict here cannot disagree with
  ``POST /api/requirements`` for the same numbers.
- The geometric (flat-horizon) baselines reuse Task 1/Task 2's single ``> 0``
  rule implementation, so the matrix cannot contradict ``/api/geometric-sun``
  or ``/api/geometric-earth`` either.
- Site context (PSR proximity) comes from the Phase 1 site catalogue.

The result is descriptive: it reports whether each candidate/window pair
meets the stated targets and how each number was measured. It does not rank
sites or windows.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from app.core.settings import Settings, get_settings
from app.models.schemas import RequirementCheck, RequirementStatus
from app.services.geometric import geometric_visibility, SUN_ANGULAR_RADIUS_DEG
from app.services.geometric_earth import geometric_earth_visibility
from app.services.phase3 import visibility_response
from app.services.requirements import (
    CHECKS,
    REQUIREMENTS_SOURCE,
    _detail,
    status_at_least,
    status_at_most,
)
from app.services.site_data import load_series
from app.services.sites import get_site_repository

SCHEMA = "lunanav.feasibility_matrix.v1"
NOTES = (
    "A verdict is not a ranking: it says whether the stated Phase 1 targets are met "
    "for that candidate and window, not which site to choose.",
    "Terrain-adjusted values use the committed LOLA horizon masks; geometric values "
    "use the flat 0 deg horizon. The two are reported side by side and never merged.",
    "A censored longest-blackout cannot pass: the window caps it, so 'at most' checks "
    "that only clear the threshold because of the cap are reported as unknown.",
    "Geometric Earth visibility does not guarantee a successful communication link; "
    "antenna pointing, link budget and ground-station scheduling are out of scope here.",
)


def _metric_value(metrics: list[dict], metric_id: str) -> tuple[float | None, bool]:
    for metric in metrics:
        if metric["id"] == metric_id:
            return metric["value"], bool(metric.get("censored", False))
    return None, False


def _visible_pct(visible: np.ndarray) -> float:
    return round(100.0 * float(np.count_nonzero(visible)) / visible.size, 4)


def _geometric_baseline(
    sun_elevations: np.ndarray, earth_elevations: np.ndarray
) -> dict:
    sun = geometric_visibility(sun_elevations, SUN_ANGULAR_RADIUS_DEG)
    earth = geometric_earth_visibility(earth_elevations)
    return {
        "basis": "geometric",
        "horizon_rule": "center_above_geometric",
        "sun": {
            "visible_sample_pct": _visible_pct(sun.visible),
            "grazing_samples": int(np.count_nonzero(sun.grazing)),
        },
        "earth": {
            "visible_sample_pct": _visible_pct(earth.visible),
            "grazing_samples": int(np.count_nonzero(earth.grazing)),
        },
        "notes": [
            "Geometric Earth visibility does not guarantee a successful "
            "communication link.",
        ],
    }


def _checks_from_metrics(metrics: list[dict], thresholds) -> tuple[list[RequirementCheck], bool | None]:
    checks: list[RequirementCheck] = []
    statuses: list[RequirementStatus] = []
    for check_id, label, metric_id, unit, attr, comparison in CHECKS:
        value, censored = _metric_value(metrics, metric_id)
        threshold = float(getattr(thresholds, attr))
        status = (status_at_least if comparison == "at_least" else status_at_most)(
            value, threshold, censored
        )
        statuses.append(status)
        checks.append(RequirementCheck(
            id=check_id, label=label, unit=unit, comparison=comparison,  # type: ignore[arg-type]
            threshold=threshold, value=value, status=status,
            detail=_detail(label, unit, value, threshold, comparison, censored),
        ))
    if any(s is RequirementStatus.not_met for s in statuses):
        satisfied: bool | None = False
    elif any(s is RequirementStatus.unknown for s in statuses):
        satisfied = None
    else:
        satisfied = True
    return checks, satisfied


def feasibility_matrix(settings: Settings | None = None) -> dict:
    """Every candidate x both windows against the Phase 1 requirements."""
    settings = settings or get_settings()
    thresholds = settings.requirements
    rows: list[dict[str, Any]] = []
    for site in get_site_repository().candidates():
        for window in ("initial", "alternative"):
            try:
                report = visibility_response(site_id=site.id, window=window, settings=settings)
                metrics = report["metrics"]
                checks, satisfied = _checks_from_metrics(metrics, thresholds)
                table = load_series(site.id, window, settings)
                geometric = _geometric_baseline(
                    np.array([r["sun"]["elevation_deg"] for r in table.records], float),
                    np.array([r["earth"]["elevation_deg"] for r in table.records], float),
                )
                rows.append({
                    "site_id": site.id,
                    "name": site.name,
                    "latitude_deg": site.latitude_deg,
                    "longitude_deg": site.longitude_deg,
                    "window": {
                        "key": window,
                        "label": report["window"]["label"],
                        "start_utc": report["window"]["start_utc"],
                        "stop_utc": report["window"]["stop_utc"],
                        "samples": report["window"]["samples"],
                    },
                    "basis": "terrain",
                    "mask": {
                        "provenance": report["provenance"]["terrain_provenance"],
                        "source": report["provenance"]["terrain"],
                        "max_range_km": report["mask"].get("max_range_km"),
                    },
                    "summary": {
                        "sun_visible_pct": report["summary"]["sun_visible_pct"],
                        "earth_visible_pct": report["summary"]["earth_visible_pct"],
                        "both_visible_pct": report["summary"]["both_visible_pct"],
                        "longest_sun_blackout_hours": report["summary"]["longest_sun_blackout_hours"],
                        "longest_earth_blackout_hours": report["summary"]["longest_earth_blackout_hours"],
                        "longest_no_simultaneous_hours": report["summary"]["longest_no_simultaneous_hours"],
                    },
                    "checks": [check.model_dump() for check in checks],
                    "satisfied": satisfied,
                    "geometric_baseline": geometric,
                    "context": {
                        "nearest_psr": site.nearest_psr.model_dump() if site.nearest_psr else None,
                        "psrs_within_10_km": site.psrs_within_10_km,
                    },
                })
            except Exception as exc:  # noqa: BLE001 - one failed cell must not blank the matrix
                rows.append({
                    "site_id": site.id,
                    "window": {"key": window},
                    "available": False,
                    "reason": str(getattr(exc, "message", exc)),
                    "checks": [],
                    "satisfied": None,
                })
    return {
        "schema": SCHEMA,
        "requirements_source": REQUIREMENTS_SOURCE,
        "thresholds": {
            "min_sun_visible_pct": thresholds.min_sun_visible_pct,
            "min_earth_visible_pct": thresholds.min_earth_visible_pct,
            "max_earth_blackout_hours": thresholds.max_earth_blackout_hours,
            "max_darkness_hours": thresholds.max_darkness_hours,
        },
        "rows": rows,
        "notes": NOTES,
    }
