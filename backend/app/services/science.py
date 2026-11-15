"""Phase 6 science context: PSR boundaries, proximity and explicit unknowns.

The PSR polygons already exist in ``data/reference/psrs.json`` and the Phase 1
site catalogue already carries a nearest-PSR summary.  This module exposes the
same verified catalogue through the Phase 6 science endpoints without adding a
second geometry implementation:

- polygon distance comes from :class:`app.services.psr.PsrCatalogue`, the same
  code that enriches ``GET /api/sites`` and drives the 2D map;
- centroid distances use the documented haversine formula on the 1737.4 km
  reference sphere;
- terrain availability comes from the committed LOLA horizon profile;
- water-ice status is always ``None`` ("not assessed"), because proximity to a
  PSR is not evidence of ice, concentration or accessibility.

The service deliberately reports both distance bases.  A boundary distance is
the useful map/proximity number; a centroid distance is the simple
haversine value and is easier to reproduce by hand.  Neither is a traverse
distance.
"""

from __future__ import annotations

from typing import Any

from app.core.coords import great_circle_km, validate_lat_lon
from app.core.errors import InvalidInputError
from app.core.settings import Settings, get_settings
from app.models.schemas import LocationInput
from app.services.phase3 import visibility_response
from app.services.psr import Psr, PsrCatalogue, get_psr_catalogue
from app.services.sites import get_site_repository
from app.services.terrain_horizon import terrain_horizon_response

SCIENCE_SCHEMA = "lunanav.science_context.v1"
PSR_SCHEMA = "lunanav.science_psr_catalogue.v1"
BOUNDARY_UNCERTAINTY_KM = 0.06
BOUNDARY_UNCERTAINTY_75_82_KM = 0.12
AREA_THRESHOLD_KM2 = 5.0
DEFAULT_RADIUS_KM = 10.0

PSR_LIMITS = [
    "The LROC product maps PSRs larger than 5 km². Smaller permanently shadowed "
    "patches are not represented, even where published site notes quote them.",
    "Boundary coordinates are a traced product, not a rover-scale map. The source "
    "product resolves 120 m at 75–82°S and 60 m poleward of 82°S; treat the "
    "reported uncertainty as a lower bound on positional error.",
    "Distance is a straight-line surface distance to the nearest polygon boundary "
    "or zero inside a polygon. It is not a traverse distance, slope, thermal "
    "route, or proof that a rover can reach the region.",
    "A PSR is a shadow classification. It does not establish water-ice presence, "
    "concentration, depth, accessibility, or resource value.",
]


def _uncertainty_km(latitude_deg: float) -> float:
    return BOUNDARY_UNCERTAINTY_KM if latitude_deg <= -82.0 else BOUNDARY_UNCERTAINTY_75_82_KM


def _psr_entry(psr: Psr, distance_km: float, latitude_deg: float, longitude_deg: float) -> dict[str, Any]:
    centroid_km = great_circle_km(
        latitude_deg, longitude_deg,
        psr.centroid_latitude_deg, psr.centroid_longitude_deg,
    )
    return {
        "psr_id": psr.psr_id,
        "label": psr.label,
        "near_crater": psr.near_crater or None,
        "area_km2": psr.area_km2,
        "perimeter_km": psr.perimeter_km,
        "boundary_distance_km": round(distance_km, 3),
        "centroid_distance_km": round(centroid_km, 3),
        "inside": distance_km == 0.0,
        "distance_uncertainty_km": _uncertainty_km(latitude_deg),
        "centroid_latitude_deg": psr.centroid_latitude_deg,
        "centroid_longitude_deg": psr.centroid_longitude_deg,
    }


def _location(
    *, site_id: str | None, latitude_deg: float | None, longitude_deg: float | None,
) -> tuple[str | None, str, float, float]:
    if site_id is not None and (latitude_deg is not None or longitude_deg is not None):
        raise InvalidInputError("Pass either site_id or latitude_deg/longitude_deg, not both.")
    if site_id is not None:
        site = get_site_repository().get(site_id)
        return site.id, site.name, site.latitude_deg, site.longitude_deg
    if latitude_deg is None or longitude_deg is None:
        raise InvalidInputError("Provide site_id or both latitude_deg and longitude_deg.")
    lat, lon = validate_lat_lon(latitude_deg, longitude_deg)
    return None, f"Custom ({lat:.4f}°, {lon:.4f}°)", lat, lon


def nearest_psr_response(
    *,
    site_id: str | None = None,
    latitude_deg: float | None = None,
    longitude_deg: float | None = None,
    radius_km: float = DEFAULT_RADIUS_KM,
    limit: int = 5,
    catalogue: PsrCatalogue | None = None,
) -> dict[str, Any]:
    """Nearest mapped PSR and the nearby mapped regions for one point."""
    if radius_km < 0:
        raise InvalidInputError("radius_km must be non-negative")
    if limit < 1:
        raise InvalidInputError("limit must be at least 1")
    catalogue = catalogue or get_psr_catalogue()
    resolved_id, name, lat, lon = _location(
        site_id=site_id, latitude_deg=latitude_deg, longitude_deg=longitude_deg)
    nearest, distance = catalogue.nearest(lat, lon)
    nearby = catalogue.within_km(lat, lon, radius_km)
    return {
        "schema": SCIENCE_SCHEMA,
        "query": {
            "site_id": resolved_id,
            "name": name,
            "latitude_deg": lat,
            "longitude_deg": lon,
            "radius_km": radius_km,
        },
        "nearest_psr": _psr_entry(nearest, distance, lat, lon),
        "nearby_psrs": [
            _psr_entry(psr, dist, lat, lon) for psr, dist in nearby[:limit]
        ],
        "nearby_count": len(nearby),
        "status": "inside" if distance == 0.0 else "mapped",
        "water_ice": {
            "confirmed": None,
            "status": "not_assessed",
            "evidence": [],
            "interpretation": (
                "A nearby PSR is a target for investigation, not a water-ice detection. "
                "No ice concentration, depth or accessibility is inferred."
            ),
        },
        "distance_basis": (
            "Minimum point-to-boundary distance in the LROC south-polar stereographic "
            "plane (1737.4 km sphere); zero when the point lies inside the polygon. "
            "Centroid distance uses the haversine formula."
        ),
        "source": {
            "product": "LROC NAC_POLE_PSR_SOUTH companion shapefile",
            "derived_from": "LOLA permanent-shadow masks (Mazarico et al. 2011)",
            "provider": "NASA/GSFC/Arizona State University LROC team",
            "page": "https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_POLE_PSR_SOUTH",
            "area_threshold_km2": AREA_THRESHOLD_KM2,
            "count": len(catalogue),
        },
        "limits": PSR_LIMITS,
        "notes": [
            "The nearest mapped PSR is not necessarily the nearest scientifically "
            "interesting target; the product excludes regions below 5 km².",
            "Distance from a landing site to a PSR boundary is geometry only.",
        ],
    }


def psr_catalogue_response(
    *,
    min_area_km2: float = AREA_THRESHOLD_KM2,
    max_latitude_deg: float = -80.0,
    near_site_id: str | None = None,
    radius_km: float = 30.0,
    catalogue: PsrCatalogue | None = None,
) -> dict[str, Any]:
    """Verified PSR catalogue plus its source metadata.

    The geometry is copied from the same objects used by ``GET /api/psrs``.
    Returning the metadata here keeps the science view from having to scrape
    source strings out of a polygon array.
    """
    catalogue = catalogue or get_psr_catalogue()
    if min_area_km2 < 0:
        raise InvalidInputError("min_area_km2 must be non-negative")
    if not (-90.0 < max_latitude_deg <= 0.0):
        raise InvalidInputError("max_latitude_deg must be greater than -90 and at most 0")
    selected: dict[str, float] | None = None
    if near_site_id:
        loc = get_site_repository().resolve(LocationInput(site_id=near_site_id))
        close = catalogue.within_km(loc.latitude_deg, loc.longitude_deg, radius_km)
        selected = {psr.psr_id: distance for psr, distance in close}

    psrs = []
    for psr in catalogue.all():
        if psr.area_km2 < min_area_km2 or psr.centroid_latitude_deg > max_latitude_deg:
            continue
        if selected is not None and psr.psr_id not in selected:
            continue
        entry = {
            "psr_id": psr.psr_id,
            "area_km2": psr.area_km2,
            "perimeter_km": psr.perimeter_km,
            "centroid_latitude_deg": psr.centroid_latitude_deg,
            "centroid_longitude_deg": psr.centroid_longitude_deg,
            "near_crater": psr.near_crater or None,
            "rings": [[[x, y] for x, y in ring] for ring in psr.rings],
        }
        if selected is not None:
            entry["boundary_distance_km"] = round(selected[psr.psr_id], 3)
        psrs.append(entry)

    return {
        "schema": PSR_SCHEMA,
        "count": len(psrs),
        "catalogue_count": len(catalogue),
        "area_threshold_km2": min_area_km2,
        "max_latitude_deg": max_latitude_deg,
        "projection": catalogue.meta.get("projection"),
        "source": catalogue.meta.get("source"),
        "psrs": psrs,
        "limits": PSR_LIMITS,
    }


def site_context_response(
    site_id: str | None = None,
    latitude_deg: float | None = None,
    longitude_deg: float | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Scientific context for a catalogue site or a custom point.

    The context intentionally reports water ice as unmeasured, never "absent".
    Terrain availability is copied from the committed horizon service; a point
    without a LOLA mask is labelled rather than filled with a synthetic mesh.
    """
    settings = settings or get_settings()
    resolved_id, name, lat, lon = _location(
        site_id=site_id, latitude_deg=latitude_deg, longitude_deg=longitude_deg)
    site = get_site_repository().get(resolved_id) if resolved_id else None
    catalogue = get_psr_catalogue()
    nearest, distance = catalogue.nearest(lat, lon)
    nearby = catalogue.within_km(lat, lon, DEFAULT_RADIUS_KM)

    horizon = terrain_horizon_response(
        site_id=resolved_id, latitude_deg=None if resolved_id else lat,
        longitude_deg=None if resolved_id else lon, window="initial", settings=settings,
    )
    windows: dict[str, Any] = {}
    for window in ("initial", "alternative"):
        if resolved_id is None:
            windows[window] = {
                "available": False,
                "reason": "Committed mission windows are only available for catalogue sites.",
            }
            continue
        try:
            report = visibility_response(site_id=resolved_id, window=window, settings=settings)
            windows[window] = {
                "available": True,
                "label": report["window"].get("label"),
                "start_utc": report["window"].get("start_utc"),
                "stop_utc": report["window"].get("stop_utc"),
                "sun_visible_pct": report["summary"].get("sun_visible_pct"),
                "earth_visible_pct": report["summary"].get("earth_visible_pct"),
                "longest_sun_blackout_hours": report["summary"].get("longest_sun_blackout_hours"),
                "longest_earth_blackout_hours": report["summary"].get("longest_earth_blackout_hours"),
            }
        except Exception as exc:  # noqa: BLE001 - the context reports missing windows, not a crash
            windows[window] = {
                "available": False,
                "reason": str(getattr(exc, "message", exc)),
            }

    terrain = horizon["terrain"]
    return {
        "schema": SCIENCE_SCHEMA,
        "site": {
            "site_id": resolved_id,
            "name": name,
            "latitude_deg": lat,
            "longitude_deg": lon,
            "elevation_m": site.elevation_m if site else None,
            "slope_deg": site.slope_deg if site else None,
            "region": site.region if site else "Custom point",
            "description": site.description if site else "A location you chose on the map.",
            "sources": [source.model_dump() for source in site.sources] if site else [],
        },
        "nearest_psr": _psr_entry(nearest, distance, lat, lon),
        "nearby_psrs": [
            _psr_entry(psr, dist, lat, lon)
            for psr, dist in nearby[:5]
        ],
        "nearby_count": len(nearby),
        "terrain": {
            "available": terrain["available"],
            "basis": terrain["basis"],
            "geometric_only": terrain["geometric_only"],
            "source": terrain["source"],
            "provenance": terrain["provenance"],
            "surface_elevation_m": terrain.get("surface_elevation_m"),
            "observer_height_m": terrain["observer_height_m"],
            "coverage": terrain["coverage"],
            "uncertainty": terrain["uncertainty"],
            "limits": terrain["limits"],
        },
        "visibility_windows": windows,
        "science": {
            "water_ice_confirmed": None,
            "water_ice_status": "not_assessed",
            "water_ice_evidence": [],
            "psr_interpretation": (
                "Water ice is likely to form in the cold, permanently shadowed regions "
                "near the poles. A mapped PSR is a strong sign of a cold trap, but LunaNav "
                "has no ice detection, concentration, depth, temperature or rover-access "
                "measurement."
            ),
            "temperature": None,
            "temperature_note": "Surface temperature is not in the committed datasets.",
        },
        "status": "calculated" if terrain["available"] else "partial",
        "provenance": {
            "psr": "LROC/LOLA south-polar PSR catalogue, >5 km²",
            "terrain": terrain["source"],
            "ephemeris": horizon["provenance"].get("ephemeris"),
            "visibility": horizon["provenance"].get("visibility"),
            "time": horizon["provenance"].get("time"),
        },
        "limits": [
            *PSR_LIMITS,
            "Terrain values are pooled/committed products; this context does not "
            "model trafficability, thermal survival, radiation, or landing hazards.",
            "No water-ice detection, concentration, or resource assessment is made.",
        ],
        "notes": [
            "The science panel separates measured geometry from interpretive text.",
            "Unknown water-ice status is not evidence of absence.",
        ],
    }
