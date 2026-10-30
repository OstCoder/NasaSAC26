"""ScenarioService and ScenarioComparisonService.

Comparison output is descriptive: it states measured differences and the
trade-offs they imply between metrics. It never recommends a site or date,
because the inputs (especially in Demo Mode) cannot support that.
"""

from __future__ import annotations

from app.core.settings import Settings, get_settings
from app.models.schemas import (
    ComparisonResult,
    LocationInput,
    MetricDelta,
    Mode,
    ProvenanceLevel,
    RescheduleResult,
    ScenarioInput,
    ScenarioResult,
    Snapshot,
)
from app.providers.registry import get_bundle

from .metrics import REGISTRY
from .sites import get_site_repository
from .visibility import VisibilityCalculator

HEADLINE_METRICS = [
    "sun_visible_hours",
    "earth_visible_hours",
    "both_visible_hours",
    "longest_sun_blackout_hours",
    "longest_earth_blackout_hours",
    "longest_no_simultaneous_hours",
]

TRADEOFF_METRICS = {
    "sun_visible_hours": "Sun-visible time",
    "earth_visible_hours": "Earth-visible time",
    "both_visible_hours": "simultaneous Sun+Earth time",
    "longest_sun_blackout_hours": "maximum Sun blackout",
    "longest_earth_blackout_hours": "maximum Earth blackout",
}


def _names(a: ScenarioResult, b: ScenarioResult) -> tuple[str, str]:
    if (a.label, b.label) == ("Original", "Proposed"):
        return "the original date", "the proposed date"
    return "Scenario A", "Scenario B"

# Changes smaller than this are reported as "about the same".
ABS_EPS = {"h": 0.25, "%": 0.5, "deg": 0.05}


class ScenarioService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.sites = get_site_repository()

    def calculator(self, mode: Mode | None) -> VisibilityCalculator:
        return VisibilityCalculator(get_bundle(mode or Mode(self.settings.default_mode)), self.settings)

    def run(self, s: ScenarioInput) -> ScenarioResult:
        loc = self.sites.resolve(s.location)
        return self.calculator(s.mode).scenario(loc, s.landing_utc, s.duration_hours, s.step_minutes, s.label)

    def snapshot(self, location: LocationInput, when, mode: Mode | None, lookahead: float | None) -> Snapshot:
        loc = self.sites.resolve(location)
        return self.calculator(mode).snapshot(loc, when, lookahead)


def _fmt(v: float, unit: str) -> str:
    return f"{v:.1f} {unit}" if unit != "%" else f"{v:.1f} percentage points"


class ScenarioComparisonService:
    def __init__(self, scenarios: ScenarioService | None = None):
        self.scenarios = scenarios or ScenarioService()

    def compare(self, a_in: ScenarioInput, b_in: ScenarioInput) -> ComparisonResult:
        a = self.scenarios.run(a_in)
        b = self.scenarios.run(b_in)
        return self.compare_results(a, b)

    @staticmethod
    def compare_results(a: ScenarioResult, b: ScenarioResult) -> ComparisonResult:
        am = {m.id: m for m in a.metrics}
        bm = {m.id: m for m in b.metrics}
        deltas: list[MetricDelta] = []
        for mid, ma in am.items():
            mb = bm.get(mid)
            if mb is None:
                continue
            delta = pct = None
            if ma.value is not None and mb.value is not None:
                delta = round(mb.value - ma.value, 4)
                if abs(ma.value) > 1e-9 and ma.unit != "%":
                    pct = round(100.0 * delta / abs(ma.value), 2)
            deltas.append(
                MetricDelta(
                    id=mid, label=ma.label, unit=ma.unit, category=ma.category,
                    a=ma.value, b=mb.value, delta=delta, percent_change=pct,
                    either_censored=ma.censored or mb.censored,
                    availability_direction=REGISTRY[mid].availability_direction if mid in REGISTRY else 0,
                    statement=ScenarioComparisonService._statement(ma.label, ma.unit, delta,
                                                                   ma.censored or mb.censored, _names(a, b)),
                )
            )
        notes = ScenarioComparisonService._comparability(a, b)
        return ComparisonResult(
            a=a, b=b, deltas=deltas,
            tradeoffs=ScenarioComparisonService._tradeoffs(deltas, a, b),
            comparable=not any(n.startswith("Not directly comparable") for n in notes),
            comparability_notes=notes,
        )

    @staticmethod
    def _statement(label: str, unit: str, delta, censored: bool,
                   names: tuple[str, str] = ("Scenario A", "Scenario B")) -> str:
        if delta is None:
            return (f"{label}: no value for at least one scenario (the body was not visible at landing, "
                    "or the event falls outside the window).")
        tail = " (at least one value is limited by the window length)" if censored else ""
        if abs(delta) < ABS_EPS.get(unit, 1e-6):
            return f"{label}: about the same in both scenarios{tail}."
        direction = "higher" if delta > 0 else "lower"
        return f"{label}: {names[1][0].upper() + names[1][1:]} is {_fmt(abs(delta), unit)} {direction} than {names[0]}{tail}."

    @staticmethod
    def _tradeoffs(deltas: list[MetricDelta], a: ScenarioResult, b: ScenarioResult) -> list[str]:
        gains, losses = [], []
        by_id = {d.id: d for d in deltas}
        for mid, phrase in TRADEOFF_METRICS.items():
            d = by_id.get(mid)
            if d is None or d.delta is None or abs(d.delta) < ABS_EPS["h"]:
                continue
            direction = REGISTRY[mid].availability_direction
            signed = f"{'+' if d.delta > 0 else '−'}{abs(d.delta):.1f} h"
            text = f"{'more' if d.delta > 0 else 'less'} {phrase} ({signed})"
            if mid.startswith("longest"):
                text = f"{'a longer' if d.delta > 0 else 'a shorter'} {phrase} ({signed})"
            (gains if d.delta * direction > 0 else losses).append(text)
        out = []
        na, nb = _names(a, b)
        lead = f"Relative to {na}, {nb} has"
        if gains and losses:
            out.append(f"{lead} {', '.join(gains)}, but {', '.join(losses)}.")
        elif gains:
            out.append(f"{lead} {', '.join(gains)}, with no offsetting losses on the tracked visibility measures.")
        elif losses:
            out.append(f"{lead} {', '.join(losses)}, with no offsetting gains on the tracked visibility measures.")
        else:
            out.append("The tracked visibility measures are about the same in both scenarios.")
        weakest = min((a.provenance.overall, b.provenance.overall),
                      key=lambda p: ["synthetic", "geometric_only", "analytic_approximate",
                                     "scientific_sourced"].index(p.value))
        if weakest != ProvenanceLevel.scientific_sourced:
            out.append("These differences come from non-validated inputs "
                       f"({weakest.value.replace('_', ' ')}) and describe the model, not verified mission conditions.")
        out.append("Visibility is a precondition for, not a guarantee of, solar power and direct-to-Earth "
                   "communications.")
        return out

    @staticmethod
    def _comparability(a: ScenarioResult, b: ScenarioResult) -> list[str]:
        notes = []
        if a.provenance.mode != b.provenance.mode:
            notes.append("Not directly comparable: scenarios were computed in different modes.")
        if a.provenance.overall != b.provenance.overall:
            notes.append(f"Data quality differs: A is {a.provenance.overall.value}, "
                         f"B is {b.provenance.overall.value}.")
        if abs(a.duration_hours - b.duration_hours) > 1e-6:
            notes.append("Mission durations differ: compare percentages rather than hour totals.")
        if abs(a.step_minutes - b.step_minutes) > 1e-6:
            notes.append(f"Sampling steps differ ({a.step_minutes:g} vs {b.step_minutes:g} min).")
        cens = [m.label for m in a.metrics + b.metrics if m.censored]
        if cens:
            notes.append("Some values touch the window edge and are lower bounds: "
                         + ", ".join(sorted(set(cens))) + ".")
        return notes

    def reschedule(self, location: LocationInput, original, proposed, duration_hours: float,
                   step_minutes: float | None, mode: Mode | None) -> RescheduleResult:
        a = ScenarioInput(location=location, landing_utc=original, duration_hours=duration_hours,
                          step_minutes=step_minutes, mode=mode, label="Original")
        b = ScenarioInput(location=location, landing_utc=proposed, duration_hours=duration_hours,
                          step_minutes=step_minutes, mode=mode, label="Proposed")
        cmp = self.compare(a, b)
        by_id = {d.id: d for d in cmp.deltas}
        return RescheduleResult(
            shift_hours=round((proposed - original).total_seconds() / 3600.0, 3),
            comparison=cmp,
            headline_changes=[by_id[i] for i in HEADLINE_METRICS if i in by_id],
        )
