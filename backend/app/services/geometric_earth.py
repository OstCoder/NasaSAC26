"""Phase 3 Task 2: geometric Earth visibility.

The rule is the one the task specifies, exactly:

    Earth visible      <=> Earth elevation > 0 degrees
    Earth not visible  <=> Earth elevation <= 0 degrees

Terrain is deliberately NOT applied here - that is Task 3, and the
terrain-adjusted answer lives in ``services/phase3.py``. This module is the
geometric baseline for Earth, the counterpart of ``services/geometric.py``
(Task 1) whose rule, response shape and guarantees it mirrors. The two
results are labelled differently on purpose: a geometric Earth elevation
above 0 deg is NOT a working communication link (no antenna pattern, link
budget, ground-station scheduling or relay is modelled - see the notes).

Near the horizon the point-source rule is fragile: Earth's disk straddles the
horizon for every sample within its apparent angular radius (0.95 deg from
the Moon - about four Sun radii, so the grazing band matters more here than
for the Sun). Such samples are flagged ``grazing`` and their ``disk_fraction``
is reported, but the visibility boolean still follows the task's
centre-above-0 rule. Folding the disk into the boolean would stop this being
a geometric point-source calculation.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from app.core.settings import Settings, get_settings
from app.core.timeutil import to_iso
from app.services import intervals as iv
from app.services.geometric import GeometricVisibility, _spans, geometric_visibility
from app.services.site_data import load_series

SCHEMA = "lunanav.geometric_earth_visibility.v1"
EARTH_ANGULAR_RADIUS_DEG = 0.95


def geometric_earth_visibility(
    elevation_deg: np.ndarray | list[float],
    angular_radius_deg: float = EARTH_ANGULAR_RADIUS_DEG,
) -> GeometricVisibility:
    """The Task 2 rule: visible exactly when Earth elevation is strictly above 0 deg.

    Same contract as :func:`app.services.geometric.geometric_visibility` - one
    implementation, reused, so the two bodies cannot disagree on the rule.
    ``angular_radius_deg`` only labels grazing samples and computes the disk
    fraction; it never changes ``visible``. ``0.0`` and ``-0.0`` are not visible.
    """
    return geometric_visibility(elevation_deg, angular_radius_deg)


def earth_visibility_response(
    *, site_id: str, window: str = "initial", settings: Settings | None = None
) -> dict:
    """Geometric Earth visibility for every timestamp of one mission window."""
    settings = settings or get_settings()
    table = load_series(site_id, window, settings)
    result = geometric_earth_visibility(table.earth.elevation_deg, settings.earth_angular_radius_deg)

    times = np.array([when.timestamp() for when in table.times], float)
    spans = iv.intervals_from_clearance(times, table.earth.elevation_deg)

    records = []
    for index, when in enumerate(table.times):
        earth = table.records[index]["earth"]
        records.append({
            "timestamp_utc": to_iso(when),
            # Azimuth and elevation are copied from the Phase 2 record unchanged.
            "azimuth_deg": earth["azimuth_deg"],
            "elevation_deg": earth["elevation_deg"],
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
        "grazing_band_deg": round(float(settings.earth_angular_radius_deg), 4),
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
            "expression": "earth.elevation_deg > 0",
            "terrain_applied": False,
            "angular_diameter_in_rule": False,
            "grazing_band_deg": round(float(settings.earth_angular_radius_deg), 4),
        },
        "summary": summary,
        "intervals": _spans(spans),
        "checks": {
            "every_timestamp_has_a_result": len(records) == len(table),
            "booleans_follow_elevation_gt_zero": bool(
                np.array_equal(result.visible, np.asarray(table.earth.elevation_deg) > 0.0)),
            "angles_preserved_from_phase2": bool(
                all(record["azimuth_deg"] == table.records[index]["earth"]["azimuth_deg"]
                    and record["elevation_deg"] == table.records[index]["earth"]["elevation_deg"]
                    for index, record in enumerate(records))),
            "grazing_samples_flagged": grazing == int(np.sum(
                np.abs(np.asarray(table.earth.elevation_deg)) <= settings.earth_angular_radius_deg)),
        },
        "provenance": {
            "ephemeris": table.payload.get("source") or "NASA JPL Horizons",
            "series": "Phase 2 Task 2 hourly Earth track (data/scientific/site_series)",
            "terrain": "none - geometric horizon only",
            "time": "UTC, ISO-8601 with Z; airless, no refraction",
            "rule": "Earth centre strictly above 0 deg; terrain and the Earth disk are not applied",
        },
        "notes": [
            "This is the geometric baseline: a positive elevation is not a terrain clearance. "
            "Terrain-adjusted visibility is GET /api/phase3.",
            "Geometric Earth visibility does NOT guarantee a successful communication link: "
            "antenna orientation, signal strength, ground-station availability and relay "
            "satellites are not modelled here.",
            "Samples within Earth's apparent angular radius of the horizon (0.95 deg from the "
            "Moon, about four Sun radii) are flagged grazing; their disk fraction is reported "
            "for context but does not change the point-source boolean.",
            "An elevation of exactly 0 deg is not visible, per the task's '> 0' rule.",
        ],
        "series": records,
    }
