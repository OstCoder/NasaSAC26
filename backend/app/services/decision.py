"""Decision support: requirements, power survival and a transparent rank.

This module is intentionally a composition layer. It does not invent a second
visibility or power model:

- Sun/Earth metrics come from :class:`~app.services.comparison.ScenarioService`;
- the three mission checks and maximum darkness come from
  :func:`app.services.requirements.RequirementService`;
- battery survival comes from :func:`app.services.engineering.engineering_response`
  with the caller's power demand substituted for the configured load.

Ranking is deliberately narrow. Only candidates whose every selected check is
met are ranked. A failure or an undecidable check is never treated as a high
score. The score is a weighted comparison of measured metrics after min/max
normalisation on the eligible set; it is not a universal NASA suitability score.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from types import SimpleNamespace
from typing import Any

from app.core.settings import Settings, get_settings
from app.models.schemas import (
    DecisionBattery,
    DecisionPower,
    DecisionRecommendation,
    DecisionRequest,
    DecisionResult,
    DecisionSite,
    DecisionThresholdsInput,
    DecisionWeights,
    LocationInput,
    PsrProximity,
    RequirementCheck,
    RequirementStatus,
    ScenarioInput,
)
from app.services.comparison import ScenarioService
from app.services.engineering import engineering_response, window_for_landing
from app.services.psr import get_psr_catalogue
from app.services.requirements import RequirementService
from app.services.sites import get_site_repository

SCHEMA = "lunanav.mission_decision.v1"

METRIC_IDS = (
    "sun_visible_pct",
    "earth_visible_pct",
    "both_visible_pct",
    "longest_sun_blackout_hours",
    "longest_earth_blackout_hours",
    "longest_no_simultaneous_hours",
)


def _fmt(value: float | None, unit: str) -> str:
    if value is None:
        return "no measurement"
    return f"{value:.1f}%" if unit == "%" else f"{value:.1f} {unit}"


def _power_check(power: DecisionPower, demand_w: float) -> RequirementCheck:
    if not power.available or power.battery is None:
        return RequirementCheck(
            id="power_system_survives",
            label="Battery reserve throughout mission",
            unit="Wh",
            comparison="at_most",
            threshold=0.0,
            value=None,
            status=RequirementStatus.unknown,
            detail=(
                f"Power demand is {demand_w:g} W, but {power.reason or 'the engineering model is unavailable'} "
                "Undecided is not a pass."
            ),
        )
    battery = power.battery
    met = battery.reserve_respected and not battery.depleted
    status = RequirementStatus.met if met else RequirementStatus.not_met
    detail = (
        f"Modelled {demand_w:g} W load; minimum battery {battery.min_soc_pct:.1f}% "
        f"(reserve {battery.reserve_pct:.0f}%), {battery.unserved_wh:.1f} Wh unserved. "
        f"{battery.verdict}"
    )
    return RequirementCheck(
        id="power_system_survives",
        label="Battery reserve throughout mission",
        unit="Wh",
        comparison="at_most",
        threshold=0.0,
        value=battery.unserved_wh,
        status=status,
        detail=detail,
    )


def _overall(checks: list[RequirementCheck]) -> tuple[bool | None, str]:
    required = [check for check in checks if check.required]
    if any(check.status is RequirementStatus.not_met for check in required):
        return False, "fail"
    if any(check.status is RequirementStatus.unknown for check in required):
        return None, "unknown"
    return True, "pass"


def _normalise(rows: list[dict[str, Any]], field: str, higher_is_better: bool) -> dict[str, float]:
    """Min/max normalise one measured field over the eligible rows only."""
    values = [(row["site_id"], row["_raw"][field]) for row in rows]
    usable = [(site_id, value) for site_id, value in values if value is not None]
    if not usable:
        return {site_id: 0.0 for site_id, _ in values}
    low = min(value for _, value in usable)
    high = max(value for _, value in usable)
    if abs(high - low) < 1e-12:
        return {site_id: 1.0 for site_id, _ in values}
    out: dict[str, float] = {}
    for site_id, value in values:
        if value is None:
            out[site_id] = 0.0
        else:
            fraction = (value - low) / (high - low)
            out[site_id] = round(fraction if higher_is_better else 1.0 - fraction, 6)
    return out


def _score_eligible(rows: list[dict[str, Any]], weights: DecisionWeights) -> None:
    """Assign score, components and rank to rows that already passed every check."""
    eligible = [row for row in rows if row["satisfied"] is True]
    if not eligible:
        return

    sunlight = _normalise(eligible, "sun_visible_pct", True)
    earth = _normalise(eligible, "earth_visible_pct", True)
    communication = _normalise(eligible, "longest_earth_blackout_hours", False)
    science = _normalise(eligible, "psr_distance_km", False)
    raw_weights = {
        "sunlight": weights.sunlight,
        "earth_visibility": weights.earth_visibility,
        "communication": weights.communication,
        "science": weights.science,
    }
    total_weight = sum(raw_weights.values())

    for row in eligible:
        site_id = row["site_id"]
        components = {
            "sunlight": sunlight[site_id],
            "earth_visibility": earth[site_id],
            "communication": communication[site_id],
            "science": science[site_id],
        }
        score = 100.0 * sum(raw_weights[key] * components[key] for key in raw_weights) / total_weight
        row["score"] = round(score, 1)
        row["score_components"] = components

    eligible.sort(key=lambda row: (-row["score"], row["_order"]))
    for index, row in enumerate(eligible, start=1):
        row["rank"] = index


def _reasons(row: dict[str, Any], checks: list[RequirementCheck], rank: int | None,
             eligible_count: int) -> tuple[list[str], list[str]]:
    reasons: list[str] = []
    risks: list[str] = []
    failed = [check for check in checks if check.required and check.status is RequirementStatus.not_met]
    unknown = [check for check in checks if check.required and check.status is RequirementStatus.unknown]
    advisory = [check for check in checks if not check.required]

    if row["satisfied"] is True:
        reasons.append("Meets every selected mission constraint in this window.")
    elif row["satisfied"] is False:
        reasons.append("Does not meet all selected mission constraints, so it is not eligible for ranking.")
        reasons.extend(f"Fails {check.label}: {check.detail}" for check in failed)
    else:
        reasons.append("At least one constraint cannot be decided from this window; undecided is not a pass.")
        reasons.extend(f"Undecided {check.label}: {check.detail}" for check in unknown)

    sun = row["_raw"]["sun_visible_pct"]
    earth = row["_raw"]["earth_visible_pct"]
    dark = row["_raw"]["longest_sun_blackout_hours"]
    blackout = row["_raw"]["longest_earth_blackout_hours"]
    reasons.append(
        f"Sun above the skyline {_fmt(sun, '%')}; Earth above the skyline {_fmt(earth, '%')}; "
        f"longest darkness {_fmt(dark, 'h')}; longest Earth blackout {_fmt(blackout, 'h')}."
    )

    if row["rank"] is not None:
        if eligible_count == 1:
            reasons.append("Only eligible candidate under the selected constraints; rank 1 of 1.")
        elif rank == 1:
            reasons.append(
                f"Rank 1 of {eligible_count} eligible candidates under the selected weights. "
                "This is a comparison of measured values, not a landing-safety verdict."
            )
        else:
            reasons.append(f"Rank {rank} of {eligible_count} eligible candidates under the selected weights.")

    if failed:
        risks.extend(check.detail for check in failed)
    if unknown:
        risks.extend(check.detail for check in unknown)
    for check in advisory:
        risks.append(
            f"Advisory {check.label}: {check.detail} This check does not gate the ranking."
        )
    if blackout is not None and blackout >= 12:
        risks.append(
            f"The {blackout:.1f} h Earth blackout is a geometric outage, not a guaranteed loss of "
            "communications; the link budget and station schedule are separate questions."
        )
    if row["_raw"]["psr_distance_km"] is None:
        risks.append("No mapped PSR proximity is recorded for this site.")

    return reasons, risks


def decide(req: DecisionRequest, settings: Settings | None = None) -> DecisionResult:
    settings = settings or get_settings()
    repository = get_site_repository()
    scenarios = ScenarioService(settings)
    requirements = RequirementService(settings)

    base = settings.requirements
    thresholds_input = req.thresholds or DecisionThresholdsInput()
    overrides = thresholds_input.model_dump(exclude_none=True)
    demand_w = float(overrides.pop("power_demand_w", base.power_demand_w))
    thresholds = replace(base, **overrides)

    site_ids = req.site_ids or list(settings.raw["mission"]["candidate_sites"])
    sites: list[Any] = [repository.get(site_id) for site_id in site_ids]
    if req.custom_location is not None:
        loc = repository.resolve(req.custom_location)
        catalogue = get_psr_catalogue()
        psr, distance = catalogue.nearest(loc.latitude_deg, loc.longitude_deg)
        sites.append(SimpleNamespace(
            id="custom",
            name=loc.name,
            latitude_deg=loc.latitude_deg,
            longitude_deg=loc.longitude_deg,
            nearest_psr=PsrProximity(
                psr_id=psr.psr_id,
                label=psr.label,
                distance_km=round(distance, 3),
                area_km2=psr.area_km2,
                centroid_latitude_deg=psr.centroid_latitude_deg,
                centroid_longitude_deg=psr.centroid_longitude_deg,
            ),
            psrs_within_10_km=len(catalogue.within_km(loc.latitude_deg, loc.longitude_deg, 10.0)),
        ))
    window = window_for_landing(req.landing_utc, settings)

    rows: list[dict[str, Any]] = []
    for order, site in enumerate(sites):
        scenario = ScenarioInput(
            location=LocationInput(site_id=site.id) if site.id != "custom" else LocationInput(
                latitude_deg=site.latitude_deg, longitude_deg=site.longitude_deg, label=site.name),
            landing_utc=req.landing_utc,
            duration_hours=req.duration_hours,
            mode=req.mode,
            label=site.name,
        )
        result = scenarios.run(scenario)
        evaluation = requirements.evaluate(result, thresholds)
        checks = list(evaluation.checks)

        if site.id == "custom":
            power = DecisionPower(
                available=False,
                reason="The power model needs a catalogue site with a committed hourly series.",
            )
        elif window is None:
            power = DecisionPower(
                available=False,
                reason=(
                    "The power model uses the committed hourly series for the two mission windows "
                    "(1 Dec and 11 Dec 2026 UTC). This landing time is outside those windows, so "
                    "battery survival is undecided rather than assumed."
                ),
            )
        else:
            report = engineering_response(
                site_id=site.id, window=window, settings=settings, load_w=demand_w,
                panel_design=req.panel_design, panel_tilt_deg=req.panel_tilt_deg,
                panel_azimuth_deg=req.panel_azimuth_deg,
            )
            budget = report["power"]["budget"]
            battery = budget["battery"]
            design = report["power"]["design"]
            power = DecisionPower(
                available=True,
                window=window,  # type: ignore[arg-type]
                load_w=budget["load_w"],
                load_wh=budget["load_wh"],
                array_energy_wh=budget["array_energy_wh"],
                net_wh=budget["net_wh"],
                battery=DecisionBattery(**battery),
                panel_design=design["selected"],
                panel_tilt_deg=design["tilt_deg"],
                panel_azimuth_deg=design["azimuth_deg"],
            )
        checks.append(_power_check(power, demand_w))
        optional = set(req.optional_checks)
        for check in checks:
            check.required = check.id not in optional
        satisfied, status = _overall(checks)

        metrics = {metric_id: None for metric_id in METRIC_IDS}
        for metric in result.metrics:
            if metric.id in metrics:
                metrics[metric.id] = metric.value

        psr_distance = site.nearest_psr.distance_km if site.nearest_psr else None
        row = {
            "site_id": site.id,
            "name": site.name,
            "latitude_deg": site.latitude_deg,
            "longitude_deg": site.longitude_deg,
            "status": status,
            "satisfied": satisfied,
            "checks": checks,
            "metrics": metrics,
            "rank": None,
            "score": None,
            "score_components": {},
            "power": power,
            "nearest_psr": site.nearest_psr,
            "psrs_within_10_km": site.psrs_within_10_km,
            "reasons": [],
            "risks": [],
            "provenance": result.provenance.overall.value,
            "_raw": {**metrics, "psr_distance_km": psr_distance},
            "_order": order,
        }
        rows.append(row)

    _score_eligible(rows, req.weights)
    eligible_count = sum(1 for row in rows if row["rank"] is not None)
    for row in rows:
        row["reasons"], row["risks"] = _reasons(row, row["checks"], row["rank"], eligible_count)
        row.pop("_raw", None)
        row.pop("_order", None)

    if req.weights.science > 0:
        for row in rows:
            psr = row["nearest_psr"]
            if psr is None:
                row["risks"].append(
                    "Science priority requested, but this site has no mapped PSR proximity; "
                    "the science score is treated as the least favourable value."
                )
            else:
                row["reasons"].append(
                    f"Science priority includes the {psr.distance_km:.1f} km straight-line distance "
                    f"to {psr.label}; this is proximity, not water-ice or rover-access evidence."
                )

    ranked = sorted((row for row in rows if row["rank"] is not None), key=lambda row: row["rank"])
    if ranked:
        top = ranked[0]
        summary = (
            f"{top['name']} ranks first of {len(ranked)} eligible candidate(s) at "
            f"{top['score']:.1f}/100 under the selected weights. It meets every selected constraint; "
            "the rank compares measured conditions and is not a landing-safety or NASA approval."
        )
        recommendation = DecisionRecommendation(
            status="ranked",
            top_site_id=top["site_id"],
            top_site_name=top["name"],
            ranked_site_ids=[row["site_id"] for row in ranked],
            summary=summary,
        )
    else:
        recommendation = DecisionRecommendation(
            status="no_eligible_site",
            ranked_site_ids=[],
            summary=(
                "No candidate meets every selected constraint in this window, so LunaNav does not "
                "recommend one. Review the failing or undecided checks rather than choosing the "
                "highest raw measurement."
            ),
        )

    mode = req.mode.value if req.mode is not None else settings.default_mode
    notes = [
        "Only candidates that pass every required check are ranked. FAIL and UNDECIDED are never "
        "treated as favorable, and missing measurements receive no score. Advisory checks are shown "
        "for context but do not gate the ranking.",
        "Scores are a weighted comparison of normalised measured metrics, not a universal NASA "
        "landing-site suitability score. Change the weights to express a different mission priority.",
        "Sunlight is a precondition for solar power, not a power guarantee; Earth visibility is a "
        "precondition for a link, not a working communications link.",
        "The power check uses the mission engineering model, the caller's average power demand "
        "and the selected panel design. Panel, battery, load and loss assumptions are engineering "
        "estimates, not measured hardware. The sensitivity cases are deterministic one-at-a-time "
        "bounds, not measured uncertainty.",
        "The engineering model only covers the two committed mission windows; other landing times "
        "return UNDECIDED for battery survival.",
        "PSR proximity is straight-line distance to a mapped region, not proof of water ice or rover "
        "accessibility.",
        "A passing verdict does not mean a site is safe, approved, or flight-ready. Landing hazards, "
        "radiation, thermal limits and other mission risks are out of scope.",
    ]
    notes.insert(
        0,
        f"Data basis: {str(result.provenance.overall.value).replace('_', ' ')}. "
        "The ranking describes the model, not verified mission conditions.",
    )

    return DecisionResult(
        schema_id=SCHEMA,
        landing_utc=req.landing_utc,
        duration_hours=req.duration_hours,
        mode=mode,
        thresholds={
            "min_sun_visible_pct": thresholds.min_sun_visible_pct,
            "min_earth_visible_pct": thresholds.min_earth_visible_pct,
            "max_earth_blackout_hours": thresholds.max_earth_blackout_hours,
            "max_darkness_hours": thresholds.max_darkness_hours,
            "power_demand_w": demand_w,
        },
        weights=req.weights.model_dump(),
        recommendation=recommendation,
        sites=[DecisionSite(**row) for row in rows],
        notes=notes,
    )
