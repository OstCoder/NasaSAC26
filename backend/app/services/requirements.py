"""Check a scenario against the Phase 1 mission requirements.

The thresholds come from ``config/lunanav.config.json -> requirements`` and are
measured with the same metric registry the planner and the API already show, so
the verdict and the number on screen cannot disagree.

This is a constraint check, not a recommendation: it says whether a scenario
meets the stated targets. It does not rank sites or dates.
"""

from __future__ import annotations

from app.core.settings import RequirementThresholds, Settings, get_settings
from app.models.schemas import (
    RequirementCheck,
    RequirementEvaluation,
    RequirementStatus,
    ScenarioResult,
)
from app.services.sites import get_site_repository

REQUIREMENTS_SOURCE = "config/lunanav.config.json -> requirements"

# (check id, label, metric id, unit, RequirementThresholds attribute, comparison)
CHECKS: tuple[tuple[str, str, str, str, str, str], ...] = (
    ("min_sun_visible_pct", "Minimum sunlight availability",
     "sun_visible_pct", "%", "min_sun_visible_pct", "at_least"),
    ("min_earth_visible_pct", "Minimum Earth visibility",
     "earth_visible_pct", "%", "min_earth_visible_pct", "at_least"),
    ("max_earth_blackout_hours", "Maximum Earth communication blackout",
     "longest_earth_blackout_hours", "h", "max_earth_blackout_hours", "at_most"),
)


def _fmt(value: float, unit: str) -> str:
    return f"{value:.1f}%" if unit == "%" else f"{value:.1f} {unit}"


def status_at_least(value: float | None, threshold: float, censored: bool) -> RequirementStatus:
    """At least ``threshold``. A censored total is a lower bound, so it can still pass."""
    if value is None:
        return RequirementStatus.unknown
    if value >= threshold:
        return RequirementStatus.met
    # The true value may be larger than the window-limited lower bound.
    return RequirementStatus.unknown if censored else RequirementStatus.not_met


def status_at_most(value: float | None, threshold: float, censored: bool) -> RequirementStatus:
    """At most ``threshold``. A censored interval is a lower bound, so passing cannot be confirmed."""
    if value is None:
        return RequirementStatus.unknown
    if value > threshold:
        return RequirementStatus.not_met
    return RequirementStatus.unknown if censored else RequirementStatus.met


def _detail(label: str, unit: str, value: float | None, threshold: float,
            comparison: str, censored: bool) -> str:
    word = "at least" if comparison == "at_least" else "at most"
    if value is None:
        return f"{label}: no measurement in this window, so the requirement cannot be decided."
    text = f"{label}: {_fmt(value, unit)} measured against a target of {word} {_fmt(threshold, unit)}."
    if censored:
        text += (" The value is limited by the analysis window: the true total can only be larger."
                 if comparison == "at_least" else
                 " The value is limited by the analysis window: the true interval can only be longer.")
    return text


class RequirementService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.sites = get_site_repository()

    def evaluate(self, result: ScenarioResult,
                 thresholds: RequirementThresholds | None = None) -> RequirementEvaluation:
        req = thresholds or self.settings.requirements
        metrics = {m.id: m for m in result.metrics}

        checks: list[RequirementCheck] = []
        statuses: list[RequirementStatus] = []
        for check_id, label, metric_id, unit, attr, comparison in CHECKS:
            m = metrics.get(metric_id)
            value = m.value if m is not None else None
            censored = bool(m.censored) if m is not None else False
            threshold = float(getattr(req, attr))
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

        nearest_psr = None
        if result.location.site_id:
            nearest_psr = self.sites.get(result.location.site_id).nearest_psr

        notes = []
        if req.basis:
            notes.append(req.basis)
        notes.append(
            f"Measured from modelled Sun and Earth visibility over {result.duration_hours:g} h "
            "from the scenario landing time. Sunlight is not available power and Earth "
            "visibility is not a working communications link."
        )
        if result.provenance.overall.value != "scientific_sourced":
            notes.append(
                "Inputs are "
                f"{result.provenance.overall.value.replace('_', ' ')}: this verdict describes the "
                "model, not verified mission conditions."
            )
        if req.psr_proximity == "preferred" and nearest_psr is not None:
            notes.append(
                f"PSR proximity is recorded as a preference, not a threshold: the nearest mapped PSR "
                f"({nearest_psr.label}) is {nearest_psr.distance_km:.1f} km away. Only PSRs larger than "
                "~5 km2 are in the mapped catalogue."
            )
        notes.append("This is a requirement check, not a site recommendation or ranking.")

        return RequirementEvaluation(
            location=result.location,
            landing_utc=result.landing_utc,
            duration_hours=result.duration_hours,
            requirements_source=REQUIREMENTS_SOURCE,
            checks=checks,
            satisfied=satisfied,
            nearest_psr=nearest_psr,
            psr_preference=req.psr_proximity,
            notes=notes,
        )
