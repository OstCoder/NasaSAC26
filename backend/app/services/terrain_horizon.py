"""Phase 3 Task 3: terrain horizon obstructions.

Phase 3's visibility calculation already applies a LOLA skyline, but it returns
one array of angles. This module makes the *obstruction* itself the object of
study, the way the Phase 3 task list describes it: the surface elevation, the
observer height, the per-azimuth horizon profile, curvature, and an explicit
comparison of Sun and Earth elevation against that profile.

What it does
------------
- Loads the committed two-tier LOLA mask for a site (5 m/pixel near, 80 m/pixel
  to 150 km, 1 degree azimuth step, curvature already applied when the mask was
  built) and exposes the full 360-point profile, its coverage, and its
  uncertainty instead of only a maximum angle.
- Compares both bodies against the skyline at their own azimuths: samples above
  and below, clearance extremes, the skyline range over the sampled azimuths,
  and how many samples where the flat-horizon rule ``elevation > 0`` would have
  said "visible" the terrain actually blocks.
- Delegates the adjusted visibility, intervals and metrics to
  ``services/phase3.py::visibility_response``. There is exactly one visibility
  calculation in the project; this module must never disagree with it, and the
  tests assert that the delegated payload is copied verbatim.
- Marks any point without a committed mask (custom coordinates, or a site whose
  mask was never built) as ``basis: "geometric"`` / ``geometric_only: true``
  with a flat 0 degree horizon. It never fabricates a profile and never presents
  a flat horizon as terrain-verified.

What it does not claim
----------------------
The angles are airless geometry from a 2 m eye height at the stored UTC
samples. Sun above terrain is a precondition for solar power, not a power
estimate; Earth above terrain is line of sight, not a link budget. A pixel
smooths terrain finer than its size, so the far tier is a lower bound on
distant ridges.
"""

from __future__ import annotations

import numpy as np

from app.core.errors import InvalidInputError
from app.core.settings import Settings, get_settings
from app.models.schemas import ProvenanceLevel
from app.providers.base import HorizonMask
from app.services.phase3 import visibility_response
from app.services.site_data import load_series, load_mask, mask_payload
from app.services.sites import get_site_repository

SCHEMA = "lunanav.terrain_horizon.v1"
BODIES = ("sun", "earth")

#: The mask builder's constants, repeated here so the response can state them.
CURVATURE_RADIUS_M = 1_737_400.0
OBSERVER_HEIGHT_M = 2.0
OBSERVER_HEIGHT_UNCERTAINTY_M = 0.3
AZIMUTH_STEP_DEG = 1.0
NEAR_PIXEL_M = 5.0
FAR_PIXEL_M = 80.0
MAX_RANGE_KM = 150.0

WINDOWS = ("initial", "alternative")


def flat_profile(step_deg: float = AZIMUTH_STEP_DEG) -> HorizonMask:
    """A 0 degree horizon at every azimuth: geometry without terrain."""
    azimuth = np.arange(0.0, 360.0, step_deg, dtype=float)
    return HorizonMask(
        azimuth,
        np.zeros_like(azimuth),
        source="flat geometric horizon (no terrain data)",
        provenance=ProvenanceLevel.geometric_only,
        metadata={"terrain": "none", "azimuth_step_deg": step_deg},
    )


def _pct(part: int, total: int) -> float:
    return round(100.0 * part / total, 4) if total else 0.0


def _comparison(report: dict, mask: HorizonMask) -> dict:
    """Sun and Earth elevation against the skyline, at each body's azimuth."""
    out: dict[str, dict | None] = {}
    for body in BODIES:
        elevation = np.array(
            [record[body]["elevation_deg"] for record in report["series"]], float)
        azimuth = np.array([record[body]["azimuth_deg"] for record in report["series"]], float)
        skyline = np.asarray(mask.elevation_at(azimuth), float)
        clearance = elevation - skyline
        above = clearance > 0
        visible = np.array([record[body]["visible"] for record in report["series"]], bool)
        out[body] = {
            "samples": int(elevation.size),
            "above_skyline": int(above.sum()),
            "below_skyline": int((~above).sum()),
            "above_skyline_pct": _pct(int(above.sum()), int(elevation.size)),
            "max_clearance_deg": round(float(clearance.max()), 4),
            "min_clearance_deg": round(float(clearance.min()), 4),
            "skyline_min_deg": round(float(skyline.min()), 4),
            "skyline_max_deg": round(float(skyline.max()), 4),
            "elevation_max_deg": round(float(elevation.max()), 4),
            "elevation_min_deg": round(float(elevation.min()), 4),
            # The comparison the task list asks for, in one number: samples where
            # the flat-horizon rule would have said visible and terrain does not.
            "flat_horizon_visible": int((elevation > 0).sum()),
            "blocked_by_terrain": int(((elevation > 0) & (~above)).sum()),
            "visible_added_by_terrain": int(((elevation <= 0) & above).sum()),
            "agrees_with_visibility": bool(np.array_equal(above, visible)),
            "rule": "elevation_deg > skyline_deg at the body's own azimuth",
        }
    return out


def _coverage(payload: dict) -> dict:
    tiers = payload.get("tiers") or {}
    near = tiers.get("near") or {}
    far = tiers.get("far") or {}
    return {
        "near": {
            "pixel_m": near.get("pixel_m", near.get("pixel_size_m")),
            "max_range_m": near.get("max_range_m"),
            "dem": near.get("dem"),
        },
        "far": {
            "pixel_m": far.get("pixel_m", far.get("pixel_size_m")),
            "max_range_m": far.get("max_range_m"),
            "dem": far.get("dem"),
        },
        "max_sampled_range_km": round(float(payload.get("max_range_m", 0.0)) / 1000.0, 3),
        "azimuth_step_deg": float(payload.get("azimuth_step_deg", AZIMUTH_STEP_DEG)),
        "curvature_applied": True,
        "curvature_radius_m": CURVATURE_RADIUS_M,
        "curvature_model": "drop = s^2 / (2R) applied when the mask was built, R = 1 737 400 m",
        "beyond_range_note": (
            "Past 150 km lunar curvature puts even the highest lunar terrain below the "
            "tangent plane for these sites (~194 km for a 10.8 km peak), so terrain "
            "beyond the mask cannot rise above this skyline."
        ),
    }


def _uncertainty(payload: dict) -> dict:
    coverage = _coverage(payload)
    return {
        "observer_height_m": float(payload.get("observer_height_m", OBSERVER_HEIGHT_M)),
        "observer_height_uncertainty_m": OBSERVER_HEIGHT_UNCERTAINTY_M,
        "near_pixel_m": float(coverage["near"]["pixel_m"] or NEAR_PIXEL_M),
        "far_pixel_m": float(coverage["far"]["pixel_m"] or FAR_PIXEL_M),
        "azimuth_step_deg": float(payload.get("azimuth_step_deg", AZIMUTH_STEP_DEG)),
        "max_range_km": float(coverage["max_sampled_range_km"]),
        "unmodelled": [
            "Terrain finer than one pixel (5 m near, 80 m far) is smoothed out, so a "
            "narrow distant ridge is a lower bound on the obstruction.",
            "Obstructions narrower than the 1 degree azimuth step are sampled, not resolved.",
            "A different observer height (mast, lander deck) changes the skyline; the "
            "mask must be rebuilt rather than offset.",
        ],
    }


def _limits(site_id: str) -> list[str]:
    return [
        f"Terrain profile for {site_id}: 5 m/pixel to the site DEM edge, 80 m/pixel to "
        "150 km, 360 azimuths at 1 degree, 2 m observer, curvature applied.",
        "Terrain beyond 150 km cannot obstruct these sites; the far tier is a lower "
        "bound on distant ridges. Obstructions narrower than 1 degree are sampled, not "
        "resolved.",
        "Sun above the skyline is a precondition for solar power, not a power estimate.",
        "Earth above the skyline is direct line of sight, not a communications link "
        "budget, and Earth's 0.95 degree disk is treated as a point.",
        "Geometry only: airless, no scattering, at the stored hourly UTC samples. Not a "
        "landing recommendation.",
    ]


def _geometric_only_response(
    *, latitude_deg: float | None, longitude_deg: float | None, window: str,
    settings: Settings, site: dict | None = None, reason: str | None = None,
) -> dict:
    """A point with no committed LOLA skyline: flat horizon, flagged, no numbers faked."""
    if (latitude_deg is None) != (longitude_deg is None):
        raise InvalidInputError(
            "Give both latitude_deg and longitude_deg for a geometric-only point.")
    if latitude_deg is not None and not -90.0 <= latitude_deg <= 90.0:
        raise InvalidInputError(f"latitude_deg must be inside [-90, 90], got {latitude_deg}")
    if longitude_deg is not None and not -360.0 <= longitude_deg <= 360.0:
        raise InvalidInputError(f"longitude_deg must be inside [-360, 360], got {longitude_deg}")
    if window not in WINDOWS:
        raise InvalidInputError(f"unknown window {window!r}; expected one of {list(WINDOWS)}")

    flat = flat_profile()
    site_block = dict(site or {})
    site_block.setdefault("site_id", None)
    site_block.setdefault("latitude_deg", latitude_deg)
    site_block.setdefault("longitude_deg", longitude_deg)
    return {
        "schema": SCHEMA,
        "site": {
            "site_id": site_block.get("site_id"),
            "name": site_block.get("name"),
            "latitude_deg": site_block.get("latitude_deg"),
            "longitude_deg": site_block.get("longitude_deg"),
            "elevation_m": site_block.get("elevation_m"),
        },
        "window": {"key": window},
        "terrain": {
            "available": False,
            "basis": "geometric",
            "geometric_only": True,
            "source": flat.source,
            "provenance": flat.provenance.value,
            "observer_height_m": OBSERVER_HEIGHT_M,
            "azimuth_step_deg": AZIMUTH_STEP_DEG,
            "surface_elevation_m": site_block.get("elevation_m"),
            "profile": {
                "azimuth_deg": [round(float(value), 6) for value in flat.azimuth_deg],
                "elevation_deg": [round(float(value), 6) for value in flat.elevation_deg],
            },
            "summary": {
                "max_obstruction_deg": 0.0,
                "min_obstruction_deg": 0.0,
                "mean_obstruction_deg": 0.0,
                "max_obstruction_azimuth_deg": None,
            },
            "coverage": {
                "near": {"pixel_m": None, "max_range_m": None, "dem": None},
                "far": {"pixel_m": None, "max_range_m": None, "dem": None},
                "max_sampled_range_km": None,
                "azimuth_step_deg": AZIMUTH_STEP_DEG,
                "curvature_applied": False,
                "curvature_radius_m": CURVATURE_RADIUS_M,
                "curvature_model": "not applied: no terrain is loaded for this point",
                "beyond_range_note": "No mask exists, so no range limit is claimed.",
            },
            "uncertainty": {
                "observer_height_m": OBSERVER_HEIGHT_M,
                "observer_height_uncertainty_m": None,
                "near_pixel_m": None,
                "far_pixel_m": None,
                "azimuth_step_deg": AZIMUTH_STEP_DEG,
                "max_range_km": None,
                "unmodelled": [
                    "Everything: there is no terrain profile for this point, so the "
                    "horizon is a flat 0 degree assumption.",
                ],
            },
            "limits": [
                "No LOLA horizon mask covers this point, so every visibility answer for "
                "it is a flat-horizon geometric estimate. Real terrain can only make the "
                "result stricter, never looser.",
                "Not terrain-verified. Do not present this as a terrain-adjusted result.",
            ],
        },
        "visibility": {
            "available": False,
            "basis": "geometric",
            "geometric_only": True,
            "window": {"key": window},
            "reason": reason or (
                "No committed Sun/Earth series exists for this point. Add the point as a "
                "candidate site and build its Phase 2 series and LOLA mask, or use "
                "/api/sky/now for a single instant."),
            "summary": None,
            "intervals": None,
            "metrics": None,
            "series_endpoint": None,
        },
        "comparison": {"sun": None, "earth": None},
        "checks": {
            "terrain_profile_available": False,
            "geometric_only_flagged": True,
            "profile_has_360_points": len(flat.azimuth_deg) == 360,
            "all_profile_angles_finite": True,
            "terrain_changes_the_answer": False,
        },
        "provenance": {
            "ephemeris": None,
            "terrain": flat.source,
            "terrain_provenance": ProvenanceLevel.geometric_only.value,
            "time": "UTC, ISO-8601 with Z; airless geometry",
            "sampling": "flat 0 degree horizon at 1 degree azimuth steps",
            "visibility": "Body centre above a flat horizon (geometric only)",
            "expected_terrain_provenance": ProvenanceLevel.scientific_sourced.value,
        },
        "notes": [
            "This point has no terrain model in the repository. The profile is flat by "
            "construction, not because the Moon is flat.",
            "Marked geometric-only so a client cannot mistake it for a terrain-verified "
            "site.",
        ],
    }


def terrain_horizon_response(
    *, site_id: str | None = None, latitude_deg: float | None = None,
    longitude_deg: float | None = None, window: str = "initial",
    settings: Settings | None = None,
) -> dict:
    """One site's terrain horizon and terrain-adjusted visibility.

    Pass either ``site_id`` or ``latitude_deg`` + ``longitude_deg``. A site with a
    committed mask gets the full profile and delegated adjusted visibility; any
    other point is returned geometric-only, flagged, with a flat horizon.
    """
    settings = settings or get_settings()
    if site_id is not None and (latitude_deg is not None or longitude_deg is not None):
        raise InvalidInputError("Pass either site_id or latitude_deg/longitude_deg, not both.")
    if site_id is None:
        return _geometric_only_response(
            latitude_deg=latitude_deg, longitude_deg=longitude_deg, window=window,
            settings=settings)
    if window not in WINDOWS:
        raise InvalidInputError(f"unknown window {window!r}; expected one of {list(WINDOWS)}")

    site = get_site_repository().get(site_id)  # raises UnknownSiteError
    payload = mask_payload(site_id, settings)
    if payload is None:
        # No skyline for this site: report it as geometric-only rather than
        # inventing a profile. Coordinates come from the site record.
        block = {
            "site_id": getattr(site, "id", site_id),
            "name": getattr(site, "name", None),
            "latitude_deg": getattr(site, "latitude_deg", None),
            "longitude_deg": getattr(site, "longitude_deg", None),
            "elevation_m": getattr(site, "elevation_m", None),
        }
        return _geometric_only_response(
            latitude_deg=block["latitude_deg"], longitude_deg=block["longitude_deg"],
            window=window, settings=settings, site=block,
            reason=(f"No LOLA horizon mask is committed for {site_id!r}; its visibility "
                    "is geometric only. Run scripts/build_site_horizon_masks.py."))

    mask = load_mask(site_id, settings)
    report = visibility_response(site_id=site_id, window=window, settings=settings)
    comparison = _comparison(report, mask)
    uncertainty = _uncertainty(payload)
    coverage = _coverage(payload)

    terrain_changed = any(
        block["blocked_by_terrain"] or block["visible_added_by_terrain"]
        for block in comparison.values())
    return {
        "schema": SCHEMA,
        "site": dict(report["site"]),
        "window": dict(report["window"]),
        "rule": dict(report["rule"]),
        "terrain": {
            "available": True,
            "basis": "terrain",
            "geometric_only": False,
            "source": mask.source,
            "provenance": mask.provenance.value,
            "observer_height_m": float(payload.get("observer_height_m", OBSERVER_HEIGHT_M)),
            "azimuth_step_deg": float(payload.get("azimuth_step_deg", AZIMUTH_STEP_DEG)),
            "surface_elevation_m": report["site"].get("elevation_m"),
            "profile": {
                "azimuth_deg": [round(float(value), 6) for value in payload["azimuth_deg"]],
                "elevation_deg": [round(float(value), 6) for value in payload["elevation_deg"]],
            },
            "summary": dict(payload.get("summary") or {}),
            "coverage": coverage,
            "uncertainty": uncertainty,
            "limits": _limits(site_id),
        },
        "comparison": comparison,
        "visibility": {
            "available": True,
            "basis": "terrain",
            "geometric_only": False,
            "window": dict(report["window"]),
            "rule": dict(report["rule"]),
            "summary": report["summary"],
            "intervals": report["intervals"],
            "metrics": report["metrics"],
            "mask": dict(report["mask"]),
            # One calculation, one place: this is the same payload as /api/phase3.
            "series_endpoint": f"/api/phase3?site_id={site_id}&window={window}",
        },
        "checks": {
            "terrain_profile_available": True,
            "geometric_only_flagged": False,
            "profile_has_360_points": len(payload["azimuth_deg"]) == 360,
            "profile_matches_mask": bool(np.allclose(
                payload["elevation_deg"], mask.elevation_deg, atol=1e-9)),
            "skyline_matches_mask": report["checks"]["skyline_matches_mask"],
            "observer_height_agrees_with_series": float(
                payload.get("observer_height_m", OBSERVER_HEIGHT_M)
            ) == OBSERVER_HEIGHT_M,
            "all_profile_angles_finite": bool(np.isfinite(
                np.asarray(payload["elevation_deg"], float)).all()),
            "comparison_agrees_with_visibility": all(
                block["agrees_with_visibility"] for block in comparison.values()),
            "terrain_changes_the_answer": bool(terrain_changed),
            "mask_reaches_150_km": coverage["max_sampled_range_km"] >= MAX_RANGE_KM,
        },
        "provenance": {
            "ephemeris": report["provenance"]["ephemeris"],
            "terrain": mask.source,
            "terrain_provenance": mask.provenance.value,
            "time": report["provenance"]["time"],
            "sampling": ("360 azimuths at 1 degree; Phase 2 hourly series for the body "
                         "positions; interval edges interpolated from clearance"),
            "visibility": report["provenance"]["visibility"],
            "observer_height_m": float(payload.get("observer_height_m", OBSERVER_HEIGHT_M)),
            "curvature": coverage["curvature_model"],
            "expected_terrain_provenance": ProvenanceLevel.scientific_sourced.value,
        },
        "notes": [
            "Terrain horizon profile: committed two-tier LOLA mask, 1 degree azimuth step, "
            "2 m observer, curvature applied when the mask was built.",
            "The adjusted visibility, intervals and metrics are delegated to "
            "/api/phase3 unchanged; only the profile, coverage and comparison blocks are new.",
            "blocked_by_terrain counts samples where the flat-horizon rule elevation > 0 "
            "would have said visible and the skyline does not. It is geometry, not a "
            "mission verdict.",
            *report["notes"],
        ],
    }
