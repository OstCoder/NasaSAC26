"""Geometric Sun visibility.

The rule is the one the task specifies, exactly:

    Sun visible      <=> Sun elevation > 0 degrees
    Sun not visible  <=> Sun elevation <= 0 degrees

Terrain is deliberately NOT applied here - that is Task 3, and the
terrain-adjusted answer already lives in ``services/phase3.py``. This module is
the geometric baseline the later tasks are compared against.

Near the horizon the point-source rule is fragile: a sample at +0.01 deg is
"visible" and one at -0.01 deg is not, although the Sun's disk straddles the
horizon in both cases. Such samples are flagged ``grazing`` (within the Sun's
apparent radius) and their ``disk_fraction`` is reported, but the visibility
boolean still follows the task's centre-above-0 rule. Folding the disk into the
boolean here would stop it being a geometric point-source calculation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

from app.core.settings import Settings, get_settings
from app.core.timeutil import to_iso
from app.services import intervals as iv
from app.services.horizon import disk_fraction_above
from app.services.site_data import load_series

SCHEMA = "lunanav.geometric_sun_visibility.v1"
SUN_ANGULAR_RADIUS_DEG = 0.2666


@dataclass(frozen=True)
class GeometricVisibility:
    """Point-source visibility, with grazing samples flagged for inspection."""

    visible: np.ndarray
    grazing: np.ndarray
    disk_fraction: np.ndarray


def geometric_visibility(
    elevation_deg: np.ndarray | list[float],
    angular_radius_deg: float = SUN_ANGULAR_RADIUS_DEG,
) -> GeometricVisibility:
    """The Task 1 rule: visible exactly when elevation is strictly above 0 deg.

    ``angular_radius_deg`` only labels grazing samples and computes the disk
    fraction; it never changes ``visible``. ``-0.0`` is not visible, and ``0.0``
    is not visible, because the rule is ``> 0``.
    """
    elevation = np.asarray(elevation_deg, float)
    if elevation.ndim != 1:
        raise ValueError(f"elevation must be one-dimensional, got shape {elevation.shape}")
    if not np.all(np.isfinite(elevation)):
        raise ValueError("elevation contains non-finite values")
    if not (isinstance(angular_radius_deg, (int, float)) and 0.0 <= angular_radius_deg < 90.0):
        raise ValueError(f"angular_radius_deg must be in [0, 90), got {angular_radius_deg!r}")
    return GeometricVisibility(
        visible=elevation > 0.0,
        grazing=np.abs(elevation) <= float(angular_radius_deg),
        disk_fraction=disk_fraction_above(elevation, float(angular_radius_deg)),
    )


def _spans(spans) -> list[dict]:
    return [
        {
            "start_utc": to_iso(datetime.fromtimestamp(start, tz=timezone.utc)),
            "end_utc": to_iso(datetime.fromtimestamp(end, tz=timezone.utc)),
            "duration_hours": round((end - start) / 3600.0, 4),
        }
        for start, end in spans
    ]


def sun_visibility_response(
    *, site_id: str, window: str = "initial", settings: Settings | None = None
) -> dict:
    """Geometric Sun visibility for every timestamp of one mission window."""
    settings = settings or get_settings()
    table = load_series(site_id, window, settings)
    result = geometric_visibility(table.sun.elevation_deg, settings.sun_angular_radius_deg)

    times = np.array([when.timestamp() for when in table.times], float)
    spans = iv.intervals_from_clearance(times, table.sun.elevation_deg)

    records = []
    for index, when in enumerate(table.times):
        sun = table.records[index]["sun"]
        records.append({
            "timestamp_utc": to_iso(when),
            # Azimuth and elevation are copied from the Task 2 record unchanged.
            "azimuth_deg": sun["azimuth_deg"],
            "elevation_deg": sun["elevation_deg"],
            "visible": bool(result.visible[index]),
            "grazing": bool(result.grazing[index]),
            "disk_fraction": round(float(result.disk_fraction[index]), 6),
        })

    visible_samples = int(result.visible.sum())
    grazing = int(result.grazing.sum())
    visible_index = np.nonzero(result.visible)[0]
    summary = {
        "samples": len(records),
        "visible_samples": visible_samples,
        "visible_sample_pct": round(100.0 * visible_samples / len(records), 4),
        "visible_hours": round(iv.total_seconds(spans) / 3600.0, 4),
        "first_visible_utc": records[int(visible_index[0])]["timestamp_utc"] if visible_samples else None,
        "last_visible_utc": records[int(visible_index[-1])]["timestamp_utc"] if visible_samples else None,
        "grazing_samples": grazing,
        "grazing_band_deg": round(float(settings.sun_angular_radius_deg), 4),
    }

    return {
        "schema": SCHEMA,
        "site": {
            "site_id": site_id,
            "name": (table.payload.get("site") or {}).get("name"),
            "latitude_deg": (table.payload.get("site") or {}).get("latitude_deg"),
            "longitude_deg": (table.payload.get("site") or {}).get("longitude_deg"),
            "elevation_m": (table.payload.get("site") or {}).get("elevation_m"),
            "height_m": (table.payload.get("site") or {}).get("height_m"),
        },
        "window": {
            "key": table.window,
            "label": (table.payload.get("window") or {}).get("label"),
            "start_utc": to_iso(table.start),
            "stop_utc": to_iso(table.stop),
            "step": table.step,
        },
        "rule": {
            "name": "point_source_elevation_above_zero",
            "expression": "sun.elevation_deg > 0",
            "terrain_applied": False,
            "angular_diameter_in_rule": False,
            "grazing_band_deg": round(float(settings.sun_angular_radius_deg), 4),
        },
        "summary": summary,
        "intervals": _spans(spans),
        "checks": {
            "every_timestamp_has_a_result": len(records) == len(table),
            "booleans_follow_elevation_gt_zero": bool(
                np.array_equal(result.visible, np.asarray(table.sun.elevation_deg) > 0.0)),
            "angles_preserved_from_task2": bool(
                all(record["azimuth_deg"] == table.records[index]["sun"]["azimuth_deg"]
                    and record["elevation_deg"] == table.records[index]["sun"]["elevation_deg"]
                    for index, record in enumerate(records))),
            "grazing_samples_flagged": grazing == int(np.sum(
                np.abs(np.asarray(table.sun.elevation_deg)) <= settings.sun_angular_radius_deg)),
        },
        "provenance": {
            "ephemeris": table.payload.get("source") or "NASA JPL Horizons",
            "series": "Hourly Sun track (data/scientific/site_series)",
            "terrain": "none - geometric horizon only",
            "time": "UTC, ISO-8601 with Z; airless, no refraction",
            "rule": "Sun centre strictly above 0 deg; terrain and the solar disk are not applied",
        },
        "notes": [
            "This is the geometric baseline: a positive elevation is not a terrain clearance. "
            "Terrain-adjusted visibility is GET /api/phase3.",
            "Samples within the solar radius of the horizon are flagged grazing; their disk "
            "fraction is reported for context but does not change the point-source boolean.",
            "An elevation of exactly 0 deg is not visible, per the task's '> 0' rule.",
        ],
        "series": records,
    }
