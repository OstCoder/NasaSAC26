"""Phase 3: terrain-adjusted Sun/Earth visibility from the committed Phase 2 data.

This is the calculation the Phase 2 work exists for, and it runs with no network
access: the hourly Sun/Earth track comes from the Task 2 series, the skyline from
the Task 6 two-tier LOLA masks (lunar curvature included, 2 m observer), and the
visibility rule from ``config.visibility`` (the body's centre above the skyline).

The numbers are geometry:

- ``sun`` is whether the Sun's centre is above the terrain at its azimuth, plus
  the fraction of the solar disk that clears the skyline;
- ``earth`` is direct line of sight past the terrain, not a communications link;
- ``both`` is the intersection of the two, which is the useful lighting-and-Earth
  window but still not a power or downlink guarantee.

Visibility edges are interpolated between hourly samples, so the interval ends
are finer than one hour; the samples themselves are not new measurements.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from app.core.settings import Settings, get_settings
from app.core.timeutil import time_grid, to_iso
from app.models.schemas import ProvenanceLevel
from app.services import intervals as iv
from app.services.horizon import HorizonCalculator
from app.services.metrics import MetricContext, evaluate_all
from app.services.site_data import load_mask, load_series, mask_payload, mask_summary

SCHEMA = "lunanav.phase3_visibility.v1"
BODIES = ("sun", "earth")
NOTES = [
    "Visibility here is geometry: the body's centre above the LOLA skyline at its azimuth. "
    "The Sun's partial disk is reported separately; Earth's 0.95 degree disk is not.",
    "Sun above terrain is a precondition for solar power, not a power estimate. Earth above "
    "terrain is direct line of sight, not a communications link budget.",
    "The stored series is hourly. Interval edges are linearly interpolated from clearance, "
    "so their timing is finer than the sampling but is not a new measurement.",
    "The mask uses a 2 m observer, 5 m pixels to each site DEM edge and 80 m pixels to 150 km; "
    "terrain beyond 150 km cannot rise above the skyline at these sites.",
]


def _spans(spans, window) -> list[dict]:
    return [
        {
            "start_utc": to_iso(datetime.fromtimestamp(start, tz=timezone.utc)),
            "end_utc": to_iso(datetime.fromtimestamp(end, tz=timezone.utc)),
            "duration_hours": round((end - start) / 3600.0, 4),
        }
        for start, end in spans
    ]


def _metric(metrics: list[dict], metric_id: str):
    for metric in metrics:
        if metric["id"] == metric_id:
            return metric["value"]
    raise KeyError(metric_id)


def _next_start(spans, after: float) -> str | None:
    """First interval edge strictly after ``after``, or None if there is none."""
    for start, _ in sorted(spans):
        if start > after + 1.0:
            return to_iso(datetime.fromtimestamp(start, tz=timezone.utc))
    return None


def visibility_response(
    *, site_id: str, window: str = "initial", settings: Settings | None = None
) -> dict:
    """One site's terrain-adjusted visibility for one mission window."""
    settings = settings or get_settings()
    table = load_series(site_id, window, settings)
    mask = load_mask(site_id, settings)
    payload = mask_payload(site_id, settings)
    horizon = HorizonCalculator()

    sun_az = np.array([record["sun"]["azimuth_deg"] for record in table.records], float)
    sun_el = np.array([record["sun"]["elevation_deg"] for record in table.records], float)
    earth_az = np.array([record["earth"]["azimuth_deg"] for record in table.records], float)
    earth_el = np.array([record["earth"]["elevation_deg"] for record in table.records], float)

    sun = horizon.evaluate(mask, sun_az, sun_el, settings.sun_angular_radius_deg)
    earth = horizon.evaluate(mask, earth_az, earth_el, settings.earth_angular_radius_deg)
    rules = settings.raw.get("visibility") or {}
    if rules.get("sun_visibility_rule") != "center_above_terrain":
        raise ValueError(
            f"unsupported sun_visibility_rule {rules.get('sun_visibility_rule')!r}")
    if rules.get("earth_visibility_rule") != "center_above_terrain":
        raise ValueError(
            f"unsupported earth_visibility_rule {rules.get('earth_visibility_rule')!r}")

    t = np.array([when.timestamp() for when in table.times], float)
    span = (float(t[0]), float(t[-1]))
    sun_spans = iv.intervals_from_clearance(t, sun.clearance_deg)
    earth_spans = iv.intervals_from_clearance(t, earth.clearance_deg)
    both_spans = iv.intersect(sun_spans, earth_spans)
    sun_only_spans = iv.intersect(sun_spans, iv.complement(earth_spans, span))
    earth_only_spans = iv.intersect(earth_spans, iv.complement(sun_spans, span))
    spans = {
        "sun_visible": sun_spans,
        "earth_visible": earth_spans,
        "both_visible": both_spans,
        "sun_only": sun_only_spans,
        "earth_only": earth_only_spans,
        "sun_blocked": iv.complement(sun_spans, span),
        "earth_blocked": iv.complement(earth_spans, span),
        "neither_visible": iv.complement(iv.union(sun_spans, earth_spans), span),
        "not_both": iv.complement(both_spans, span),
    }
    metrics = [
        metric.model_dump()
        for metric in evaluate_all(
            MetricContext(span, t, spans, sun_el, earth_el, sun.clearance_deg, earth.clearance_deg)
        )
    ]

    records = []
    for index, when in enumerate(table.times):
        record = {"timestamp_utc": to_iso(when)}
        for body, result, az, el in (("sun", sun, sun_az, sun_el), ("earth", earth, earth_az, earth_el)):
            record[body] = {
                "azimuth_deg": round(float(az[index]), 6),
                "elevation_deg": round(float(el[index]), 6),
                "skyline_deg": round(float(result.terrain_horizon_deg[index]), 4),
                "clearance_deg": round(float(result.clearance_deg[index]), 4),
                "visible": bool(result.visible[index]),
            }
            if body == "sun":
                record[body]["disk_fraction"] = round(float(result.disk_fraction[index]), 4)
        records.append(record)

    site_block = table.payload.get("site") or {}
    window_block = table.payload.get("window") or {}
    return {
        "schema": SCHEMA,
        "site": {
            "site_id": site_id,
            "name": site_block.get("name"),
            "latitude_deg": site_block.get("latitude_deg"),
            "longitude_deg": site_block.get("longitude_deg"),
            "elevation_m": site_block.get("elevation_m"),
            "height_m": site_block.get("height_m"),
        },
        "window": {
            "key": table.window,
            "label": window_block.get("label"),
            "start_utc": to_iso(table.start),
            "stop_utc": to_iso(table.stop),
            "step": table.step,
            "samples": len(table),
        },
        "rule": {
            "sun": rules.get("sun_visibility_rule"),
            "earth": rules.get("earth_visibility_rule"),
            "sun_angular_radius_deg": settings.sun_angular_radius_deg,
            "earth_angular_radius_deg": settings.earth_angular_radius_deg,
        },
        "mask": {
            **(mask_summary(payload) if payload else {}),
            "provenance": mask.provenance.value,
            "tiers": (payload or {}).get("tiers"),
            "wide_dem": (payload or {}).get("wide_dem"),
        },
        "summary": {
            "sun_visible_pct": _metric(metrics, "sun_visible_pct"),
            "sun_visible_hours": _metric(metrics, "sun_visible_hours"),
            "longest_sun_blackout_hours": _metric(metrics, "longest_sun_blackout_hours"),
            "earth_visible_pct": _metric(metrics, "earth_visible_pct"),
            "earth_visible_hours": _metric(metrics, "earth_visible_hours"),
            "longest_earth_blackout_hours": _metric(metrics, "longest_earth_blackout_hours"),
            "both_visible_pct": _metric(metrics, "both_visible_pct"),
            "both_visible_hours": _metric(metrics, "both_visible_hours"),
            "longest_no_simultaneous_hours": _metric(metrics, "longest_no_simultaneous_hours"),
            "sun_only_hours": round(iv.total_seconds(sun_only_spans) / 3600.0, 4),
            "earth_only_hours": round(iv.total_seconds(earth_only_spans) / 3600.0, 4),
            "sun_blocked_hours": _metric(metrics, "sun_blocked_hours"),
            "longest_sun_visible_hours": _metric(metrics, "longest_sun_visible_hours"),
            "longest_earth_visible_hours": _metric(metrics, "longest_earth_visible_hours"),
        },
        "intervals": {key: _spans(value, span) for key, value in spans.items() if key != "not_both"},
        "transitions": {
            "basis": (
                "First visibility or obstruction edge strictly after the window start, "
                "interpolated between the stored hourly samples (not a new measurement)."
            ),
            "next_sunset_utc": _next_start(spans["sun_blocked"], span[0]),
            "next_sunrise_utc": _next_start(sun_spans, span[0]),
            "next_earthset_utc": _next_start(spans["earth_blocked"], span[0]),
            "next_earthrise_utc": _next_start(earth_spans, span[0]),
        },
        "metrics": metrics,
        "provenance": {
            "ephemeris": (table.payload.get("source") or "NASA JPL Horizons"),
            "terrain": mask.source,
            "terrain_provenance": mask.provenance.value,
            "time": "UTC, ISO-8601 with Z; airless geometry",
            "sampling": "1 h stored series; interval edges interpolated from clearance",
            "visibility": "Body centre above the terrain skyline (config.visibility rules)",
            "expected_terrain_provenance": ProvenanceLevel.scientific_sourced.value,
        },
        "checks": {
            "records_match_track": len(records) == len(table),
            "skyline_matches_mask": bool(np.allclose(
                [r["sun"]["skyline_deg"] for r in records],
                mask.elevation_at(sun_az).round(4), atol=1e-4)),
            "mask_reaches_150_km": bool(payload and float(payload.get("max_range_m", 0)) >= 150_000),
            "all_values_finite": bool(
                np.isfinite(sun.clearance_deg).all() and np.isfinite(earth.clearance_deg).all()),
        },
        "notes": NOTES,
        "series": records,
    }


def all_windows_summary(settings: Settings | None = None) -> dict:
    """Every candidate and both mission windows, for the readiness UI."""
    settings = settings or get_settings()
    sites = []
    for site_id in settings.raw["mission"]["candidate_sites"]:
        windows = {}
        for window in ("initial", "alternative"):
            try:
                report = visibility_response(site_id=site_id, window=window, settings=settings)
            except Exception as exc:  # noqa: BLE001 - reported per window, others still load
                windows[window] = {"available": False, "reason": str(getattr(exc, "message", exc))}
                continue
            windows[window] = {
                "available": True,
                "summary": report["summary"],
                "samples": report["window"]["samples"],
                "mask_max_range_km": (report["mask"] or {}).get("max_range_km"),
            }
        sites.append({"site_id": site_id, "windows": windows})
    return {
        "schema": "lunanav.phase3_windows.v1",
        "step": "1 h",
        "sites": sites,
        "notes": [
            "Both windows are stored hourly; these percentages use the committed Task 2 series "
            "and Task 6 masks, with no live request.",
            "A percentage is not a mission verdict and does not rank the sites.",
        ],
    }
