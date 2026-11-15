"""Validate the NASA-derived datasets end to end.

Task 2 produced 1,014 hourly Sun/Earth records from JPL Horizons; Task 3 produced
three LOLA DEM descriptions. This module answers, from the committed files
alone, whether those numbers can be used: are the coordinates on the Moon, was
the observer a point on the lunar surface, do the angles and distances mean what
the schema says, is the sampling continuous and in UTC, and do the values
reproduce an independently fetched Horizons table?

Three independent sources are compared, never merged:

1. the committed series (Horizons observer tables, ``lunanav.site_series.v1``);
2. LunaNav's own analytic model (Meeus), which shares no code or data with
   Horizons and computes topocentric az/el from the same site coordinates;
3. ``data/reference/horizons_reference.json``, a separate Horizons fetch at a
   coarser step that the hourly series must reproduce row for row.

Agreement between (1) and (2) is what makes a frame, sign or column error
visible; agreement between (1) and (3) is what makes a copy or interpolation
error visible. Neither proves the published Horizons values themselves are
correct - see the ``limitations`` block in the report.

Nothing here repairs data. A check that cannot be run is a failure with a
reason, and a missing file is reported, never skipped.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np

from app.core.coords import MOON_MEAN_RADIUS_KM, topocentric_az_el, validate_lat_lon
from app.core.settings import Settings, get_settings
from app.core.timeutil import parse_utc, to_iso
from app.providers.ephemeris_analytic import AnalyticMeeusEphemeris
from app.providers.horizons_site import ObserverSite, fetch_site_track, fetch_sky
from app.services.site_series import BODIES, expected_samples, mission_windows
from app.services.sites import get_site_repository
from app.services.terrain_inventory import site_xy_m

SCHEMA = "lunanav.nasa_validation.v1"
REFERENCE_SCHEMA = "lunanav.horizons_reference.v1"
GENERATOR = "backend/scripts/validate_nasa_data.py"

# Tolerances. Each is chosen so the check fails on a *class* of error, not on
# noise: the observed analytic agreement is a few hundredths of a degree.
ANALYTIC_TOLERANCE_DEG = 0.15      # Horizons vs Meeus (observed max ~0.033)
REFERENCE_TOLERANCE_DEG = 0.002    # same request, different step -> identical rows
LIVE_TOLERANCE_DEG = 0.002         # re-fetch of the committed window
# The analytic model's Moon-Sun/Moon-Earth distance is good to ~1e-4 relative,
# while a value stored in AU or miles is off by a factor of ~1.5e8 or 1.6.
RANGE_TOLERANCE_RELATIVE = 1e-3
REFERENCE_RANGE_TOLERANCE_KM = 1.0
LIVE_RANGE_TOLERANCE_KM = 1.0
STEP_TOLERANCE_DEG = 0.05          # hourly change may exceed the model's by this much
COORD_TOLERANCE_DEG = 1e-6
ELEVATION_TOLERANCE_M = 0.05
# A lunar-surface observer is 1737.4 km + altitude from the Moon's centre.
# Earth's surface would need an altitude of ~4640 km; the Moon's centre is -1737 km.
OBSERVER_ALTITUDE_KM = (-20.0, 9.0)
# Sees the Sun and Earth from poleward of 85 S: both stay near the horizon.
MAX_HORIZON_ELEVATION_DEG = 15.0
SUN_RANGE_KM = (1.46e8, 1.53e8)
EARTH_RANGE_KM = (3.5e5, 4.1e5)
TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

OBSERVER_QUERY_FIELDS = {
    "CENTER": "coord@301",
    "COORD_TYPE": "GEODETIC",
    "QUANTITIES": "4,20",
    "APPARENT": "AIRLESS",
    "EPHEM_TYPE": "OBSERVER",
    "CSV_FORMAT": "YES",
    "ANG_FORMAT": "DEG",
}

TASK5_ITEMS = [
    ("site_coordinates", "Confirm that all three site coordinates are valid."),
    ("observer_on_moon", "Verify the Horizons observer location is on the Moon."),
    ("sun_earth_positions", "Check Sun and Earth position results."),
    ("horizons_reference", "Compare selected results against Horizons reference output."),
    ("units", "Verify azimuth and elevation units."),
    ("utc_time", "Confirm UTC date and time handling."),
    ("continuity", "Check data continuity across the mission interval."),
    ("same_site_different_dates", "Test the same site on different dates."),
    ("different_sites_same_time", "Test different sites at the same date and time."),
    ("assumptions_documented", "Document any assumptions or known limitations."),
]

ASSUMPTIONS = [
    "Longitude is selenographic east-positive in [-180, 180); Horizons receives the same meridian as 0-360 deg.",
    "Heights are metres above the 1737.4 km IAU mean sphere; the Moon has no geoid.",
    "The observer is the site point plus a 2 m antenna/eye height above the LOLA surface sample.",
    "Elevation is apparent, airless and terrain-free: the geometric horizon, with no atmospheric refraction.",
    "UTC is used everywhere; UTC -> TT for the analytic model uses the fixed 69.184 s offset valid for 2026-2030.",
    "Hourly sampling is adequate to validate the data, not to time sunrise/Earthrise; the visibility step refines edges.",
    "Horizons applies light-time and aberration to the apparent position; the analytic model omits them.",
]

LIMITATIONS = [
    {"item": "Two methods, one authority",
     "impact": "LunaNav verifies that the committed values reproduce Horizons and agree with an independent model. It cannot prove Horizons' own ephemeris is correct; Horizons remains the reference."},
    {"item": "Analytic model accuracy",
     "impact": "Meeus' truncated series omits physical libration, light-time and aberration. Agreement of a few hundredths of a degree is expected; a sub-arcsecond disagreement is not claimed."},
    {"item": "Geometric, not terrain-obstructed, visibility",
     "impact": "Every elevation here is above the local flat horizon. A Sun or Earth at +0.5 deg can still be hidden by the 6-13 deg LOLA skylines in data/reference/site_terrain.json; the terrain-adjusted result applies them."},
    {"item": "Time resolution of the verification",
     "impact": "The series is hourly and the reference fetch is 12-hourly. A value at an un-sampled minute is not validated by either; the visibility step interpolates and must say so."},
    {"item": "Observer height",
     "impact": "A 2 m observer is assumed for all three sites. A real lander's camera, antenna or solar panel sits at a different height, which changes the geometric horizon by ~0.0005 deg per km and the terrain horizon much more."},
    {"item": "Site elevation provenance",
     "impact": "Elevations are a 125 m-window median of a 5 m/pixel LOLA DEM, not a surveyed datum. The 0.3 m RMS height uncertainty is small next to the 5 m pixel, but the point itself is a study coordinate, not a certified landing pad."},
    {"item": "Frame assumptions",
     "impact": "Moon Mean Earth / Polar Axis, planetocentric, with the 1.54242 deg lunar-equator inclination in the analytic model. PA vs ME differences (~0.5 km at the surface) and any future IAU frame change are below the stated tolerances but not zero."},
    {"item": "No atmosphere, no refraction",
     "impact": "Physically correct for the Moon, but it means these elevations are not comparable with Earth-based observing conventions."},
    {"item": "No power or link-budget meaning",
     "impact": "Sun elevation is illumination geometry, never electrical power; Earth elevation is line-of-sight geometry, never a communication link or data rate."},
    {"item": "Coverage of the validation",
     "impact": "Only the three mission candidates and the two mission windows are validated. Custom coordinates and other dates reuse the same code but are not covered by this report."},
]


# ------------------------------------------------------------------ helpers --


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value)


def _round(value, digits: int = 6):
    return None if value is None else round(float(value), digits)


def _signed_circ(a, b) -> np.ndarray:
    """Signed angular difference a - b in [-180, 180)."""
    return (np.asarray(a, float) - np.asarray(b, float) + 180.0) % 360.0 - 180.0


def _abs_circ(a, b) -> np.ndarray:
    return np.abs(_signed_circ(a, b))


def _read_json(path: Path) -> tuple[dict | None, str | None]:
    if not path.exists():
        return None, f"missing {path.name}"
    try:
        return json.loads(path.read_text()), None
    except json.JSONDecodeError as exc:
        return None, f"{path.name} is not valid JSON: {exc}"


def _query_params(url: str) -> dict[str, str]:
    return {k: v[0].strip("'") for k, v in parse_qs(urlparse(url).query).items()}


@dataclass
class Check:
    id: str
    title: str
    task5_item: str
    detail: str = ""
    metrics: dict = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "task5_item": self.task5_item,
            "passed": not self.problems,
            "detail": self.detail,
            "metrics": self.metrics,
            "problems": list(self.problems),
        }


@dataclass
class Track:
    """One body's track for one site and window, with its analytic counterpart."""

    site_id: str
    window: str
    body: str
    payload: dict
    times: list[datetime]
    az: np.ndarray
    el: np.ndarray
    range_km: np.ndarray
    az_ref: np.ndarray
    el_ref: np.ndarray
    range_ref: np.ndarray


# ------------------------------------------------------------------ context --


@dataclass
class Context:
    settings: Settings
    repo: object
    payloads: dict[tuple[str, str], dict]
    tracks: dict[tuple[str, str, str], Track]
    index: dict
    windows: dict[str, object]
    reference: dict | None
    reference_error: str | None
    terrain: dict | None
    terrain_error: str | None

    @property
    def candidates(self) -> list[str]:
        return list(self.settings.raw["mission"]["candidate_sites"])


def _context(settings: Settings) -> Context:
    repo = get_site_repository()
    index_path = Path(settings.datasets["site_series_index"])
    index, index_error = _read_json(index_path)
    if index is None or index_error:
        raise FileNotFoundError(index_error or str(index_path))
    if index.get("schema") != "lunanav.site_series_index.v1":
        raise ValueError(f"{index_path.name}: unexpected schema {index.get('schema')!r}")

    payloads: dict[tuple[str, str], dict] = {}
    tracks: dict[tuple[str, str, str], Track] = {}
    for entry in index.get("sites", []):
        site_id = entry.get("site_id")
        for window_key, name in entry.get("files", {}).items():
            payload, error = _read_json(index_path.parent / name)
            if payload is None or error:
                raise FileNotFoundError(error or name)
            records = payload.get("series") or []
            payloads[(site_id, window_key)] = payload
            if not records:
                continue
            times = [parse_utc(record["timestamp_utc"]) for record in records]
            site = payload["site"]
            lat, lon = float(site["latitude_deg"]), float(site["longitude_deg"])
            altitude_km = float(site["altitude_km"])
            ephemeris = AnalyticMeeusEphemeris(
                times[0] - timedelta(days=1), times[-1] + timedelta(days=1)
            )
            for body in BODIES:
                az = np.array([float(r[body]["azimuth_deg"]) for r in records])
                el = np.array([float(r[body]["elevation_deg"]) for r in records])
                rng = np.array(
                    [float(r[body].get("range_km", np.nan)) if r[body].get("range_km") is not None
                     else np.nan for r in records]
                )
                vectors = ephemeris.body_vectors_km(body, times)
                az_ref, el_ref = topocentric_az_el(
                    lat, lon, vectors, MOON_MEAN_RADIUS_KM, altitude_km
                )
                tracks[(site_id, window_key, body)] = Track(
                    site_id=site_id, window=window_key, body=body, payload=payload,
                    times=times, az=az, el=el, range_km=rng,
                    az_ref=az_ref, el_ref=el_ref,
                    range_ref=np.linalg.norm(vectors, axis=1),
                )

    root = Path(__file__).resolve().parents[3]
    reference, reference_error = _read_json(
        settings.datasets.get("horizons_reference", root / "data" / "reference" / "horizons_reference.json")
    )
    terrain, terrain_error = _read_json(
        settings.datasets.get("site_terrain", root / "data" / "reference" / "site_terrain.json")
    )
    return Context(
        settings=settings,
        repo=repo,
        payloads=payloads,
        tracks=tracks,
        index=index,
        windows={w.key: w for w in mission_windows(settings)},
        reference=reference,
        reference_error=reference_error,
        terrain=terrain,
        terrain_error=terrain_error,
    )


# ------------------------------------------------------------------- checks --


def check_site_coordinates(ctx: Context) -> Check:
    check = Check("site_coordinates", "Site coordinates are valid and agree across files",
                  TASK5_ITEMS[0][1])
    sites: dict[str, dict] = {}
    terrain_sites = (ctx.terrain or {}).get("sites", {})
    if not terrain_sites:
        check.problems.append(f"terrain reference unavailable: {ctx.terrain_error}")
    for site_id in ctx.candidates:
        site = ctx.repo.get(site_id)
        try:
            lat, lon = validate_lat_lon(site.latitude_deg, site.longitude_deg)
        except Exception as exc:  # noqa: BLE001 - reported as a failed check
            check.problems.append(f"{site_id}: {exc}")
            continue
        if site.elevation_m is None or not _finite(site.elevation_m):
            check.problems.append(f"{site_id}: no finite recorded elevation")
            continue
        radius_km = MOON_MEAN_RADIUS_KM + site.elevation_m / 1000.0
        if not MOON_MEAN_RADIUS_KM - 20.0 < radius_km <= MOON_MEAN_RADIUS_KM + 20.0:
            check.problems.append(f"{site_id}: surface radius {radius_km:.1f} km is not on the Moon")
        if not str(getattr(site, "source", "") or "").strip():
            check.problems.append(f"{site_id}: no coordinate source recorded")

        terrain = terrain_sites.get(site_id)
        entry = {
            "latitude_deg": lat, "longitude_deg": lon,
            "elevation_m": round(site.elevation_m, 3),
            "surface_radius_km": round(radius_km, 3),
        }
        if terrain is None:
            check.problems.append(f"{site_id}: no terrain entry to confirm the coordinate against")
        else:
            dem = terrain.get("dem") or {}
            bounds = dem.get("bounds_m") or {}
            x_m, y_m = site_xy_m(lat, lon)
            inside = bool(bounds) and (
                bounds["left"] <= x_m <= bounds["right"]
                and bounds["bottom"] <= y_m <= bounds["top"]
            )
            coverage = terrain.get("coverage") or {}
            entry.update({
                "pgda_site": terrain.get("pgda_site"),
                "inside_dem": inside,
                "dem_radius_km": coverage.get("radius_km"),
                "terrain_site_inside": coverage.get("site_inside"),
            })
            if not inside:
                check.problems.append(
                    f"{site_id}: projected point ({x_m:.0f}, {y_m:.0f}) m is outside the "
                    f"{terrain.get('pgda_site')} DEM footprint"
                )
            if coverage.get("site_inside") is not True:
                check.problems.append(f"{site_id}: terrain coverage does not record the site as inside")
            for field_name, tol in (("latitude_deg", COORD_TOLERANCE_DEG),
                                    ("longitude_deg", COORD_TOLERANCE_DEG)):
                if abs(float(terrain.get(field_name, 1e9)) - float(entry[field_name])) > tol:
                    check.problems.append(
                        f"{site_id}: terrain {field_name} {terrain.get(field_name)} disagrees "
                        f"with the site catalogue {entry[field_name]}"
                    )
            for window_key in ("initial", "alternative"):
                payload = ctx.payloads.get((site_id, window_key))
                if payload is None:
                    check.problems.append(f"{site_id}: no {window_key} series to cross-check")
                    continue
                block = payload.get("site") or {}
                for field_name in ("latitude_deg", "longitude_deg"):
                    got = block.get(field_name)
                    if not _finite(got) or abs(float(got) - float(entry[field_name])) > COORD_TOLERANCE_DEG:
                        check.problems.append(
                            f"{site_id} {window_key}: series {field_name} {got!r} disagrees with "
                            f"the catalogue {entry[field_name]}"
                        )
                got_elevation = block.get("elevation_m")
                if not _finite(got_elevation) or abs(got_elevation - site.elevation_m) > ELEVATION_TOLERANCE_M:
                    check.problems.append(
                        f"{site_id} {window_key}: series elevation {got_elevation!r} disagrees "
                        f"with the catalogue {site.elevation_m}"
                    )
        sites[site_id] = entry
    check.metrics = {"sites": sites, "candidates": len(ctx.candidates)}
    check.detail = (f"{len(sites)} candidates validated: finite coordinates, a recorded source, "
                    "inside their PGDA DEM footprint, and the same point in the Task 2 series.")
    return check


def check_observer_on_moon(ctx: Context) -> Check:
    check = Check("observer_on_moon", "Horizons was asked for a lunar-surface observer",
                  TASK5_ITEMS[1][1])
    sites: dict[str, dict] = {}
    for (site_id, window_key), payload in sorted(ctx.payloads.items()):
        block = payload.get("site") or {}
        queries = (payload.get("request") or {}).get("queries") or {}
        latitude, longitude = block.get("latitude_deg"), block.get("longitude_deg")
        altitude_km = block.get("altitude_km")
        if not (_finite(latitude) and _finite(longitude) and _finite(altitude_km)):
            check.problems.append(f"{site_id} {window_key}: site block lacks lat/lon/altitude")
            continue
        if not OBSERVER_ALTITUDE_KM[0] < altitude_km <= OBSERVER_ALTITUDE_KM[1]:
            check.problems.append(
                f"{site_id} {window_key}: observer altitude {altitude_km} km is not a lunar "
                f"surface height (allowed {OBSERVER_ALTITUDE_KM})"
            )
        radius_km = MOON_MEAN_RADIUS_KM + float(altitude_km)
        expected = f"{float(longitude) % 360.0:.6f},{float(latitude):.6f},{float(altitude_km):.6f}"
        for body, url in queries.items():
            params = _query_params(url)
            for key, value in OBSERVER_QUERY_FIELDS.items():
                if params.get(key) != value:
                    check.problems.append(
                        f"{site_id} {window_key} {body}: query {key}={params.get(key)!r}, expected {value!r}"
                    )
            target = params.get("COMMAND")
            if target not in ("10", "399"):
                check.problems.append(f"{site_id} {window_key} {body}: COMMAND={target!r}")
            site_coord = params.get("SITE_COORD", "")
            try:
                got = (float(site_coord.split(",")[0]) % 360.0,
                       float(site_coord.split(",")[1]),
                       float(site_coord.split(",")[2]))
            except (ValueError, IndexError):
                check.problems.append(f"{site_id} {window_key} {body}: SITE_COORD={site_coord!r}")
                continue
            want = (float(longitude) % 360.0, float(latitude), float(altitude_km))
            if (abs(got[0] - want[0]) > 1e-5 or abs(got[1] - want[1]) > 1e-5
                    or abs(got[2] - want[2]) > 1e-5):
                check.problems.append(
                    f"{site_id} {window_key} {body}: SITE_COORD {site_coord!r} != {expected!r}"
                )
        sites.setdefault(site_id, {
            "latitude_deg": latitude, "longitude_deg": longitude,
            "elevation_m": block.get("elevation_m"),
            "altitude_km": altitude_km,
            "observer_radius_km": round(radius_km, 3),
            "query_count": len(queries),
        })

    # The live reference fetch echoes back the observer Horizons actually used.
    echoed: dict[str, str] = {}
    for request in (ctx.reference or {}).get("requests", []):
        header = request.get("header") or {}
        center = str(header.get("center", "")).strip()
        site_id = request.get("site_id")
        if not center:
            check.problems.append(f"{site_id}: reference request carries no echoed observer")
            continue
        echoed.setdefault(site_id, center)
        block = (ctx.payloads.get((site_id, "initial")) or {}).get("site") or {}
        try:
            lon, lat, alt = [float(part) for part in re.split(r"[;,\s]+", center) if part][:3]
        except ValueError:
            check.problems.append(f"{site_id}: unreadable echoed observer {center!r}")
            continue
        want_lon = float(block.get("longitude_deg", 0.0)) % 360.0
        if (abs(lon - want_lon) > 0.02 or abs(lat - float(block.get("latitude_deg", 0.0))) > 0.02
                or abs(alt - float(block.get("altitude_km", 0.0))) > 0.02):
            check.problems.append(
                f"{site_id}: Horizons echoed observer {center!r}, not the requested site"
            )
        target = str(header.get("target", ""))
        if not any(word in target.lower() for word in ("sun", "earth")):
            check.problems.append(f"{site_id}: echoed target {target!r} is not Sun or Earth")
    if not echoed and ctx.reference is None:
        check.problems.append(f"no Horizons reference output to confirm the echoed observer: "
                              f"{ctx.reference_error}")
    for site_id, value in echoed.items():
        if site_id in sites:
            sites[site_id]["horizons_echo"] = value
    check.metrics = {"sites": sites,
                     "earth_centre_altitude_km": -MOON_MEAN_RADIUS_KM,
                     "queries_checked": sum(len((p.get("request") or {}).get("queries") or {})
                                            for p in ctx.payloads.values())}
    check.detail = ("Every query uses CENTER='coord@301' (the Moon, body 301), "
                    "COORD_TYPE='GEODETIC', an altitude of a few km above the mean sphere, and "
                    "the recorded site coordinate; the reference fetch echoes that same observer.")
    return check


def check_sun_earth_positions(ctx: Context) -> Check:
    check = Check("sun_earth_positions", "Sun and Earth positions agree with an independent model",
                  TASK5_ITEMS[2][1])
    worst: dict[str, dict] = {}
    for body in BODIES:
        d_az, d_el, d_range_km, d_range_rel = [], [], [], []
        for track in ctx.tracks.values():
            if track.body != body:
                continue
            d_az.append(_abs_circ(track.az, track.az_ref))
            d_el.append(np.abs(track.el - track.el_ref))
            d_range_km.append(np.abs(track.range_km - track.range_ref))
            with np.errstate(divide="ignore", invalid="ignore"):
                d_range_rel.append(np.abs(track.range_km - track.range_ref) / track.range_ref)
        if not d_az:
            check.problems.append(f"{body}: no tracks to check")
            continue
        az = np.concatenate(d_az)
        el = np.concatenate(d_el)
        rng = np.concatenate(d_range_km)
        rel = np.concatenate(d_range_rel)
        finite = np.isfinite(rng)
        entry = {
            "samples": int(az.size),
            "max_azimuth_difference_deg": _round(az.max(), 4),
            "max_elevation_difference_deg": _round(el.max(), 4),
            "rms_elevation_difference_deg": _round(float(np.sqrt(np.mean(el ** 2))), 4),
            "max_range_difference_km": _round(rng[finite].max(), 1) if finite.any() else None,
            "max_range_difference_ppm": _round(rel[finite].max() * 1e6, 1) if finite.any() else None,
            "tolerance_deg": ANALYTIC_TOLERANCE_DEG,
            "range_tolerance_relative": RANGE_TOLERANCE_RELATIVE,
        }
        worst[body] = entry
        if az.max() > ANALYTIC_TOLERANCE_DEG:
            check.problems.append(f"{body}: azimuth differs by up to {az.max():.3f} deg")
        if el.max() > ANALYTIC_TOLERANCE_DEG:
            check.problems.append(f"{body}: elevation differs by up to {el.max():.3f} deg")
        if finite.any() and rel[finite].max() > RANGE_TOLERANCE_RELATIVE:
            check.problems.append(
                f"{body}: range differs by {rel[finite].max() * 1e6:.0f} ppm, more than "
                f"{RANGE_TOLERANCE_RELATIVE * 1e6:.0f} ppm"
            )
        if not finite.any():
            check.problems.append(f"{body}: no range_km values to check")

    # Geometry sanity independent of the comparison: both bodies near the horizon.
    elevations = np.concatenate([t.el for t in ctx.tracks.values()])
    if elevations.size and np.nanmax(np.abs(elevations)) > MAX_HORIZON_ELEVATION_DEG:
        check.problems.append(
            f"an elevation reaches {np.nanmax(np.abs(elevations)):.2f} deg; at >85 S the Sun and "
            f"Earth should stay within {MAX_HORIZON_ELEVATION_DEG} deg of the horizon"
        )
    check.metrics = {"bodies": worst,
                     "elevation_range_deg": [_round(np.nanmin(elevations), 4),
                                             _round(np.nanmax(elevations), 4)]}
    check.detail = ("All records recomputed with LunaNav's Meeus model from the same site "
                    "coordinates; Horizons (light-time, physical libration) and the analytic "
                    "model (neither) share no code.")
    return check


def check_horizons_reference(ctx: Context) -> Check:
    check = Check("horizons_reference", "Committed values reproduce an independent Horizons fetch",
                  TASK5_ITEMS[3][1])
    reference = ctx.reference
    if reference is None:
        check.problems.append(f"Horizons reference unavailable: {ctx.reference_error}")
        check.detail = "No committed Horizons reference output to compare against; run --live."
        return check
    if reference.get("schema") != REFERENCE_SCHEMA:
        check.problems.append(f"reference schema {reference.get('schema')!r}, expected {REFERENCE_SCHEMA!r}")
    rows = 0
    d_az, d_el, d_range = [], [], []
    for request in reference.get("requests", []):
        site_id, body = request.get("site_id"), request.get("body")
        if body not in BODIES or site_id not in ctx.candidates:
            check.problems.append(f"reference request names {site_id!r}/{body!r}")
            continue
        params = _query_params(request.get("query_url", ""))
        if params.get("CENTER") != "coord@301" or params.get("QUANTITIES") != "4,20":
            check.problems.append(f"{site_id} {body}: reference query is not an observer table")
        for row in request.get("rows", []):
            rows += 1
            timestamp = row.get("timestamp_utc")
            window_key = next(
                (key for key, window in ctx.windows.items()
                 if window.start <= parse_utc(timestamp) <= window.end), None
            )
            payload = ctx.payloads.get((site_id, window_key)) if window_key else None
            if payload is None:
                check.problems.append(f"{site_id} {timestamp}: no hourly series for that instant")
                continue
            stored = next((r for r in payload["series"] if r["timestamp_utc"] == timestamp), None)
            if stored is None:
                check.problems.append(f"{site_id} {timestamp}: reference instant is not in the series")
                continue
            sample = stored.get(body) or {}
            if not (_finite(sample.get("azimuth_deg")) and _finite(sample.get("elevation_deg"))):
                check.problems.append(f"{site_id} {timestamp} {body}: stored value is missing")
                continue
            d_az.append(abs(float(_signed_circ(sample["azimuth_deg"], row["azimuth_deg"]))))
            d_el.append(abs(float(sample["elevation_deg"]) - float(row["elevation_deg"])))
            ref_range = row.get("range_km")
            got_range = sample.get("range_km")
            if ref_range is not None and got_range is not None:
                d_range.append(abs(float(got_range) - float(ref_range)))
    if rows == 0:
        check.problems.append("reference output has no rows")
    if d_az and max(d_az) > REFERENCE_TOLERANCE_DEG:
        check.problems.append(f"azimuth differs from Horizons by up to {max(d_az):.4f} deg")
    if d_el and max(d_el) > REFERENCE_TOLERANCE_DEG:
        check.problems.append(f"elevation differs from Horizons by up to {max(d_el):.4f} deg")
    if d_range and max(d_range) > REFERENCE_RANGE_TOLERANCE_KM:
        check.problems.append(f"range differs from Horizons by up to {max(d_range):.3f} km")
    check.metrics = {
        "rows": rows,
        "requests": len(reference.get("requests", [])),
        "max_azimuth_difference_deg": _round(max(d_az), 6) if d_az else None,
        "max_elevation_difference_deg": _round(max(d_el), 6) if d_el else None,
        "max_range_difference_km": _round(max(d_range), 3) if d_range else None,
        "reference_generated_utc": reference.get("generated_utc"),
        "reference_step": reference.get("step"),
        "tolerance_deg": REFERENCE_TOLERANCE_DEG,
    }
    check.detail = (f"{rows} selected rows from a {reference.get('step', '?')} Horizons fetch over "
                    "both mission windows, compared at the exact hourly timestamps in the series.")
    return check


def check_units(ctx: Context) -> Check:
    check = Check("units", "Angles are degrees and distances are kilometres", TASK5_ITEMS[4][1])
    def joined(values):
        return np.concatenate(values) if values else np.array([])

    az = joined([t.az for t in ctx.tracks.values()])
    el = joined([t.el for t in ctx.tracks.values()])
    az_ref = joined([t.az_ref for t in ctx.tracks.values()])
    sun_range = joined([t.range_km for t in ctx.tracks.values() if t.body == "sun"])
    earth_range = joined([t.range_km for t in ctx.tracks.values() if t.body == "earth"])
    if az.size == 0:
        check.problems.append("no values to check")
        return check
    if not (np.all(np.isfinite(az)) and np.all(np.isfinite(el))):
        check.problems.append("non-finite azimuth/elevation values present")
    if az.min() < 0.0 or az.max() >= 360.0:
        check.problems.append(f"azimuth outside [0, 360): {az.min():.3f}..{az.max():.3f}")
    if el.min() < -90.0 or el.max() > 90.0:
        check.problems.append(f"elevation outside [-90, 90]: {el.min():.3f}..{el.max():.3f}")
    degree_error = float(np.max(_abs_circ(az, az_ref)))
    radian_error = float(np.max(_abs_circ(np.degrees(az), az_ref)))
    if degree_error > radian_error:
        check.problems.append(
            f"stored angles behave like radians, not degrees ({degree_error:.3f} vs {radian_error:.3f})"
        )
    if degree_error > ANALYTIC_TOLERANCE_DEG:
        check.problems.append(f"angles in degrees disagree with the model by {degree_error:.3f}")
    for name, values, span in (("sun", sun_range, SUN_RANGE_KM), ("earth", earth_range, EARTH_RANGE_KM)):
        finite = values[np.isfinite(values)]
        if not finite.size:
            check.problems.append(f"{name}: no range_km values")
            continue
        median = float(np.median(finite))
        if not span[0] <= median <= span[1]:
            check.problems.append(
                f"{name}: median range {median:.3e} km is outside {span}; a value stored in AU "
                "or radians would land here"
            )
    check.metrics = {
        "samples": int(az.size),
        "azimuth_range_deg": [_round(az.min(), 3), _round(az.max(), 3)],
        "elevation_range_deg": [_round(el.min(), 3), _round(el.max(), 3)],
        "degree_hypothesis_max_error_deg": _round(degree_error, 4),
        "radian_hypothesis_max_error_deg": _round(radian_error, 4),
        "sun_range_km_median": _round(float(np.median(sun_range[np.isfinite(sun_range)])), 1),
        "earth_range_km_median": _round(float(np.median(earth_range[np.isfinite(earth_range)])), 1),
    }
    check.detail = ("Angles are degrees (the radian hypothesis is rejected by a wide margin) and "
                    "ranges are kilometres at the physical Sun and Moon-Earth distances.")
    return check


def check_utc_time(ctx: Context) -> Check:
    check = Check("utc_time", "Every timestamp is UTC, ISO-8601 and on the mission grid",
                  TASK5_ITEMS[5][1])
    firsts, lasts, steps = [], [], []
    for (site_id, window_key), payload in sorted(ctx.payloads.items()):
        window = ctx.windows.get(window_key)
        records = payload.get("series") or []
        if window is None:
            check.problems.append(f"{site_id} {window_key}: window is not in the mission config")
            continue
        recorded = payload.get("window") or {}
        if recorded.get("start_utc") != to_iso(window.start) or recorded.get("stop_utc") != to_iso(window.end):
            check.problems.append(
                f"{site_id} {window_key}: file window {recorded.get('start_utc')}.."
                f"{recorded.get('stop_utc')} != config {to_iso(window.start)}..{to_iso(window.end)}"
            )
        if len(records) != expected_samples(window, 60.0):
            check.problems.append(
                f"{site_id} {window_key}: {len(records)} samples, expected "
                f"{expected_samples(window, 60.0)}"
            )
        times = []
        for record in records:
            text = record.get("timestamp_utc")
            if not isinstance(text, str) or not TIME_RE.match(text):
                check.problems.append(f"{site_id} {window_key}: timestamp {text!r} is not ISO-8601 Z")
                continue
            when = parse_utc(text)
            if to_iso(when) != text:
                check.problems.append(f"{site_id} {window_key}: {text!r} does not round-trip to UTC")
            if when.utcoffset() != timedelta(0):
                check.problems.append(f"{site_id} {window_key}: {text!r} is not UTC")
            if not ctx.settings.simulation.supported_start <= when <= ctx.settings.simulation.supported_end:
                check.problems.append(f"{site_id} {window_key}: {text!r} is outside the supported range")
            times.append(when)
        if times:
            if times[0] != window.start:
                check.problems.append(f"{site_id} {window_key}: first sample is not the window start")
            if times[-1] != window.end:
                check.problems.append(f"{site_id} {window_key}: last sample is not the window stop")
            if len(set(times)) != len(times):
                check.problems.append(f"{site_id} {window_key}: duplicate timestamps")
            gaps = {round(float((b - a).total_seconds()), 3) for a, b in zip(times, times[1:])}
            if gaps and gaps != {3600.0}:
                check.problems.append(f"{site_id} {window_key}: sample spacing {sorted(gaps)} s")
            firsts.append(times[0])
            lasts.append(times[-1])
            steps.extend(sorted(gaps))
    if firsts:
        check.metrics = {
            "files": len(ctx.payloads),
            "samples": sum(len(p.get("series") or []) for p in ctx.payloads.values()),
            "first_utc": to_iso(min(firsts)),
            "last_utc": to_iso(max(lasts)),
            "step_s": steps[0] if len(set(steps)) == 1 else sorted(set(steps)),
            "windows_match_config": True,
        }
    check.detail = ("Timestamps are ISO-8601 with Z, round-trip through the UTC parser, sit exactly "
                    "on the configured landing date plus 7 days, and are one hour apart.")
    return check


def check_continuity(ctx: Context) -> Check:
    check = Check("continuity", "No gaps or jumps across either mission interval",
                  TASK5_ITEMS[6][1])
    max_az, max_el, max_ref = 0.0, 0.0, 0.0
    gaps: set[float] = set()
    for (site_id, window_key, body), track in sorted(ctx.tracks.items()):
        if len(track.times) < 2:
            check.problems.append(f"{site_id} {window_key} {body}: fewer than two samples")
            continue
        spacing = np.diff([t.timestamp() for t in track.times])
        gaps.update(round(float(value), 3) for value in spacing)
        if np.any(spacing <= 0):
            check.problems.append(f"{site_id} {window_key} {body}: timestamps are not increasing")
        if not np.all(np.isfinite(track.az)) or not np.all(np.isfinite(track.el)):
            check.problems.append(f"{site_id} {window_key} {body}: non-finite sample")
            continue
        step_az = float(np.max(_abs_circ(track.az[1:], track.az[:-1])))
        step_el = float(np.max(np.abs(track.el[1:] - track.el[:-1])))
        ref_step = max(
            float(np.max(_abs_circ(track.az_ref[1:], track.az_ref[:-1]))),
            float(np.max(np.abs(track.el_ref[1:] - track.el_ref[:-1]))),
        )
        max_az, max_el, max_ref = max(max_az, step_az), max(max_el, step_el), max(max_ref, ref_step)
        if step_az > ref_step + STEP_TOLERANCE_DEG or step_el > ref_step + STEP_TOLERANCE_DEG:
            check.problems.append(
                f"{site_id} {window_key} {body}: hourly change up to "
                f"{max(step_az, step_el):.3f} deg, model predicts at most {ref_step:.3f}"
            )
    if gaps != {3600.0}:
        check.problems.append(f"sample spacing is {sorted(gaps)} s, expected exactly 3600 s")
    check.metrics = {
        "samples": sum(len(t.times) for t in ctx.tracks.values()),
        "spacing_s": sorted(gaps),
        "max_azimuth_step_deg": _round(max_az, 4),
        "max_elevation_step_deg": _round(max_el, 4),
        "max_model_step_deg": _round(max_ref, 4),
        "tolerance_deg": STEP_TOLERANCE_DEG,
    }
    check.detail = ("Every hour is present with no duplicates, and the largest hour-to-hour change "
                    "is what the analytic geometry predicts (no swapped, repeated or interpolated rows).")
    return check


def check_same_site_different_dates(ctx: Context) -> Check:
    check = Check("same_site_different_dates", "Each site's two mission windows are distinct and consistent",
                  TASK5_ITEMS[7][1])
    sites: dict[str, dict] = {}
    fields = ("latitude_deg", "longitude_deg", "elevation_m", "height_m", "altitude_km")
    for site_id in ctx.candidates:
        initial = ctx.payloads.get((site_id, "initial"))
        alternative = ctx.payloads.get((site_id, "alternative"))
        if initial is None or alternative is None:
            check.problems.append(f"{site_id}: both mission windows must be present")
            continue
        a, b = initial.get("site") or {}, alternative.get("site") or {}
        for name in fields:
            if a.get(name) != b.get(name):
                check.problems.append(
                    f"{site_id}: observer {name} changed between windows ({a.get(name)!r} vs {b.get(name)!r})"
                )
        diffs = {}
        for body in BODIES:
            ta = ctx.tracks.get((site_id, "initial", body))
            tb = ctx.tracks.get((site_id, "alternative", body))
            if ta is None or tb is None:
                continue
            az = float(np.max(_abs_circ(ta.az, tb.az)))
            el = float(np.max(np.abs(ta.el - tb.el)))
            diffs[body] = {"max_azimuth_difference_deg": _round(az, 4),
                           "max_elevation_difference_deg": _round(el, 4)}
            if max(az, el) <= 0.05:
                check.problems.append(
                    f"{site_id} {body}: the two windows differ by at most {max(az, el):.4f} deg; "
                    "a copied file would look like this"
                )
        sites[site_id] = {
            "initial_start_utc": (initial.get("window") or {}).get("start_utc"),
            "alternative_start_utc": (alternative.get("window") or {}).get("start_utc"),
            "differences": diffs,
        }
    if len(ctx.windows) == 2:
        gap_days = (ctx.windows["alternative"].start - ctx.windows["initial"].start).days
        if gap_days <= 0:
            check.problems.append("the alternative window does not start after the initial one")
    else:
        gap_days = None
    check.metrics = {"sites": sites, "days_between_landings": gap_days}
    check.detail = ("The same observer point is used in both windows, the windows start ten days "
                    "apart, and the Sun/Earth geometry differs in each as the model predicts.")
    return check


def check_different_sites_same_time(ctx: Context) -> Check:
    check = Check("different_sites_same_time", "The three sites are three different observers",
                  TASK5_ITEMS[8][1])
    pairs = 0
    worst_az, worst_el = 0.0, 0.0
    sun_spread, earth_spread = 0.0, 0.0
    for window_key in ("initial", "alternative"):
        available = [s for s in ctx.candidates if (s, window_key, "sun") in ctx.tracks]
        for i, site_a in enumerate(available):
            for site_b in available[i + 1:]:
                ta = ctx.tracks[(site_a, window_key, "sun")]
                tb = ctx.tracks[(site_b, window_key, "sun")]
                index = {t: k for k, t in enumerate(tb.times)}
                common = [(k, index[t]) for k, t in enumerate(ta.times) if t in index]
                if not common:
                    check.problems.append(f"{site_a}/{site_b} {window_key}: no shared timestamps")
                    continue
                for body in BODIES:
                    xa, xb = ctx.tracks[(site_a, window_key, body)], ctx.tracks[(site_b, window_key, body)]
                    ia = [c[0] for c in common]
                    ib = [c[1] for c in common]
                    d_obs_az = _signed_circ(xa.az[ia], xb.az[ib])
                    d_ref_az = _signed_circ(xa.az_ref[ia], xb.az_ref[ib])
                    d_obs_el = xa.el[ia] - xb.el[ib]
                    d_ref_el = xa.el_ref[ia] - xb.el_ref[ib]
                    err_az = float(np.max(np.abs(_signed_circ(d_obs_az, d_ref_az))))
                    err_el = float(np.max(np.abs(d_obs_el - d_ref_el)))
                    worst_az, worst_el = max(worst_az, err_az), max(worst_el, err_el)
                    if body == "sun":
                        sun_spread = max(sun_spread, float(np.max(np.abs(d_obs_el))))
                    else:
                        earth_spread = max(earth_spread, float(np.max(np.abs(d_obs_el))))
                    pairs += 1
                    if err_az > ANALYTIC_TOLERANCE_DEG or err_el > ANALYTIC_TOLERANCE_DEG:
                        check.problems.append(
                            f"{site_a}/{site_b} {window_key} {body}: site-to-site difference "
                            f"disagrees with the model by {max(err_az, err_el):.3f} deg"
                        )
                if np.allclose(ta.az, tb.az) and np.allclose(ta.el, tb.el):
                    check.problems.append(
                        f"{site_a}/{site_b} {window_key}: identical Sun tracks for different coordinates"
                    )
    if sun_spread <= 0.05:
        check.problems.append(
            f"the Sun elevation spread across sites is only {sun_spread:.4f} deg; the observer "
            "coordinates do not look site-specific"
        )
    check.metrics = {
        "pairs": pairs,
        "max_difference_of_differences_azimuth_deg": _round(worst_az, 4),
        "max_difference_of_differences_elevation_deg": _round(worst_el, 4),
        "sun_elevation_spread_deg": _round(sun_spread, 4),
        "earth_elevation_spread_deg": _round(earth_spread, 4),
        "tolerance_deg": ANALYTIC_TOLERANCE_DEG,
    }
    check.detail = ("At identical timestamps the sites differ by the amount their separation, "
                    "latitude and elevation predict - the values were computed per observer, not shared.")
    return check


def check_assumptions_documented(ctx: Context) -> Check:
    check = Check("assumptions_documented", "Assumptions and limitations are written down and complete",
                  TASK5_ITEMS[9][1])
    docs = Path(__file__).resolve().parents[3] / "docs" / "VALIDATION.md"
    if not docs.exists():
        check.problems.append("docs/VALIDATION.md is missing")
    if len(LIMITATIONS) < 6:
        check.problems.append("fewer than six documented limitations")
    if len(ASSUMPTIONS) < 5:
        check.problems.append("fewer than five documented assumptions")
    ids = [item[0] for item in TASK5_ITEMS]
    if len(set(ids)) != len(ids):
        check.problems.append("duplicate Task 5 item ids")
    if ids[0] != "site_coordinates" or ids[-1] != "assumptions_documented":
        check.problems.append("Task 5 items are not in the order the task lists them")
    check.metrics = {
        "task5_items": len(TASK5_ITEMS),
        "limitations": len(LIMITATIONS),
        "assumptions": len(ASSUMPTIONS),
        "documentation": str(docs.relative_to(Path(__file__).resolve().parents[3]))
        if docs.exists() else None,
    }
    check.detail = ("All ten Task 5 items are mapped to a check, ten limitations and seven "
                    "assumptions are recorded here and in docs/VALIDATION.md.")
    return check


# ------------------------------------------------------------------- report --


def _carried_live(settings: Settings) -> dict | None:
    path = settings.datasets.get(
        "nasa_validation", Path(__file__).resolve().parents[3] / "data" / "reference" / "nasa_validation.json"
    )
    payload, _ = _read_json(Path(path))
    live = (payload or {}).get("live")
    if not live:
        return None
    return {**live, "carried_from_utc": (payload or {}).get("generated_utc"),
            "note": "Recorded by the last live run; re-run with --live to refresh."}


def build_report(*, settings: Settings | None = None, live: dict | None = None) -> dict:
    """Validate the committed NASA datasets and return the Task 5 report."""
    settings = settings or get_settings()
    ctx = _context(settings)
    checks = [
        check_site_coordinates(ctx),
        check_observer_on_moon(ctx),
        check_sun_earth_positions(ctx),
        check_horizons_reference(ctx),
        check_units(ctx),
        check_utc_time(ctx),
        check_continuity(ctx),
        check_same_site_different_dates(ctx),
        check_different_sites_same_time(ctx),
        check_assumptions_documented(ctx),
    ]
    if live is None:
        live = _carried_live(settings)
    failed = [check for check in checks if check.problems]
    return {
        "schema": SCHEMA,
        "generated_utc": to_iso(datetime.now(timezone.utc)),
        "generator": GENERATOR,
        "deliverable": "Validated astronomical datasets and documented limitations",
        "method": (
            "Re-read the committed Task 2 series and Task 3 terrain reference, recompute every "
            "azimuth/elevation with LunaNav's independent analytic model, compare the records "
            "with the committed Horizons reference fetch, and check coordinates, observer, units, "
            "UTC handling, continuity and cross-site geometry. Nothing is repaired or filled in."
        ),
        "sources": [
            {"label": "NASA JPL Horizons API (observer tables at coord@301)",
             "url": "https://ssd.jpl.nasa.gov/horizons/"},
            {"label": "NASA PGDA LOLA 5 m/pix site DEMs", "url": "https://pgda.gsfc.nasa.gov/products/78"},
            {"label": "LunaNav analytic ephemeris (Meeus, 2nd ed.)", "url": None},
        ],
        "summary": {
            "checks": len(checks),
            "passed": len(checks) - len(failed),
            "failed": len(failed),
            "status": "pass" if not failed else "fail",
            "records_checked": sum(len(p.get("series") or []) for p in ctx.payloads.values()),
            "sites": ctx.candidates,
        },
        "task5_items": [{"id": key, "item": text, "check": key} for key, text in TASK5_ITEMS],
        "checks": [check.as_dict() for check in checks],
        "sites": checks[0].metrics.get("sites", {}),
        "live": live,
        "assumptions": ASSUMPTIONS,
        "limitations": LIMITATIONS,
        "documents": ["docs/VALIDATION.md", "docs/DATASETS.md", "docs/JPL_CONNECTION.md",
                      "docs/METHODOLOGY.md", "docs/TERRAIN.md"],
    }


def problems(report: dict) -> list[str]:
    """Every failed check as one readable line (used by the script and tests)."""
    return [
        f"{check['id']}: {problem}"
        for check in report.get("checks", [])
        if not check["passed"]
        for problem in check["problems"]
    ]


# ---------------------------------------------------------------- live part --


def build_reference(*, settings: Settings | None = None, timeout_s: float = 90.0) -> dict:
    """Fetch the independent Horizons reference table (12 h step, both windows).

    Needs the network. Returns the document written to
    ``data/reference/horizons_reference.json``; raises ``LunaNavError`` on any
    unusable response rather than writing a partial table.
    """
    settings = settings or get_settings()
    repo = get_site_repository()
    windows = mission_windows(settings)
    start, stop = windows[0].start, windows[1].end
    spans = [(window.start, window.end) for window in windows]
    requests = []
    for site_id in settings.raw["mission"]["candidate_sites"]:
        site = repo.get(site_id)
        if site.elevation_m is None:
            raise ValueError(f"site {site_id!r} has no recorded elevation")
        observer = ObserverSite.at(site.latitude_deg, site.longitude_deg, site.elevation_m,
                                   2.0, site_id=site_id)
        for body in BODIES:
            track = fetch_site_track(body, observer, start, stop, "12 h", timeout_s=timeout_s)
            rows = []
            excluded = 0
            for index, when in enumerate(track.times_utc):
                if not any(low <= when <= high for low, high in spans):
                    excluded += 1  # the 8-10 Dec gap between the two mission windows
                    continue
                row = {"timestamp_utc": to_iso(when),
                       "azimuth_deg": round(float(track.azimuth_deg[index]), 6),
                       "elevation_deg": round(float(track.elevation_deg[index]), 6)}
                if track.range_km is not None:
                    row["range_km"] = round(float(track.range_km[index]), 3)
                rows.append(row)
            requests.append({
                "site_id": site_id,
                "body": body,
                "query_url": track.query_url,
                "header": dict(track.info),
                "rows": rows,
                "excluded_outside_windows": excluded,
            })
    return {
        "schema": REFERENCE_SCHEMA,
        "generated_utc": to_iso(datetime.now(timezone.utc)),
        "generator": GENERATOR,
        "source": ("NASA JPL Horizons API observer tables: CENTER='coord@301', "
                   "COORD_TYPE='GEODETIC', QUANTITIES='4,20', APPARENT='AIRLESS'"),
        "why": ("An independent re-sample of the same geometry at a coarser step. The hourly "
                "Task 2 series must reproduce these rows; differences mean a copy, interpolation "
                "or unit error rather than a different model."),
        "step": "12 h",
        "start_utc": to_iso(start),
        "stop_utc": to_iso(stop),
        "rows": sum(len(request["rows"]) for request in requests),
        "excluded_outside_windows": sum(request["excluded_outside_windows"] for request in requests),
        "requests": requests,
    }


def live_checks(reference: dict, previous: dict | None, *, timeout_s: float = 90.0,
                settings: Settings | None = None) -> dict:
    """Re-fetch a short window from Horizons and compare it with the committed series."""
    settings = settings or get_settings()
    repo = get_site_repository()
    windows = mission_windows(settings)
    initial = windows[0]
    reproduction: list[str] = []
    echo_lines: list[str] = []
    echo_problems: list[str] = []
    d_az, d_el, d_range = [], [], []
    for site_id in settings.raw["mission"]["candidate_sites"]:
        site = repo.get(site_id)
        observer = ObserverSite.at(site.latitude_deg, site.longitude_deg, site.elevation_m,
                                   2.0, site_id=site_id)
        stop = initial.start + timedelta(hours=2)
        tracks = fetch_sky(observer, initial.start, stop, "1 h", timeout_s=timeout_s)
        payload = json.loads(
            (Path(settings.datasets["site_series_index"]).parent
             / f"{site_id}-initial.json").read_text()
        )
        stored = {record["timestamp_utc"]: record for record in payload["series"]}
        for body, track in tracks.items():
            echo = track.info.get("center", "")
            if not echo:
                echo_problems.append(f"{site_id} {body}: Horizons did not echo the observer")
            else:
                try:
                    lon, lat, alt = [float(part) for part in re.split(r"[;,\s]+", echo) if part][:3]
                except ValueError:
                    echo_problems.append(f"{site_id} {body}: unreadable echoed observer {echo!r}")
                else:
                    if (abs(lon - observer.longitude_deg % 360.0) > 0.02
                            or abs(lat - observer.latitude_deg) > 0.02
                            or abs(alt - observer.altitude_km) > 0.02):
                        echo_problems.append(f"{site_id} {body}: echoed observer {echo!r}")
                    else:
                        echo_lines.append(f"{site_id} {body}: {echo}")
            for index, when in enumerate(track.times_utc):
                record = stored.get(to_iso(when))
                if record is None:
                    reproduction.append(f"{site_id} {body}: {to_iso(when)} is not in the series")
                    continue
                sample = record.get(body) or {}
                if sample.get("azimuth_deg") is None or sample.get("elevation_deg") is None:
                    reproduction.append(f"{site_id} {body}: {to_iso(when)} has no stored value")
                    continue
                d_az.append(abs(float(_signed_circ(sample["azimuth_deg"], track.azimuth_deg[index]))))
                d_el.append(abs(float(sample["elevation_deg"]) - float(track.elevation_deg[index])))
                if track.range_km is not None and sample.get("range_km") is not None:
                    d_range.append(abs(float(sample["range_km"]) - float(track.range_km[index])))

    if d_az and max(d_az) > LIVE_TOLERANCE_DEG:
        reproduction.append(f"azimuth moved by up to {max(d_az):.4f} deg since generation")
    if d_el and max(d_el) > LIVE_TOLERANCE_DEG:
        reproduction.append(f"elevation moved by up to {max(d_el):.4f} deg since generation")
    if d_range and max(d_range) > LIVE_RANGE_TOLERANCE_KM:
        reproduction.append(f"range moved by up to {max(d_range):.3f} km since generation")

    stable_problems: list[str] = []
    stable_metrics: dict = {"compared_rows": 0}
    if previous is None:
        stable_metrics["note"] = "no previous reference file; this run establishes it"
    else:
        old_rows = {(request.get("site_id"), request.get("body"), row.get("timestamp_utc")): row
                    for request in previous.get("requests", [])
                    for row in request.get("rows", [])}
        new_rows = {(request.get("site_id"), request.get("body"), row.get("timestamp_utc")): row
                    for request in reference.get("requests", [])
                    for row in request.get("rows", [])}
        missing = sorted(set(old_rows) - set(new_rows))
        if missing:
            stable_problems.append(f"{len(missing)} previously committed reference rows are gone")
        diffs = [
            (abs(float(_signed_circ(n["azimuth_deg"], old_rows[k]["azimuth_deg"]))),
             abs(float(n["elevation_deg"]) - float(old_rows[k]["elevation_deg"])))
            for k, n in new_rows.items() if k in old_rows
        ]
        stable_metrics["compared_rows"] = len(diffs)
        if diffs:
            stable_metrics["max_azimuth_change_deg"] = _round(max(d[0] for d in diffs), 9)
            stable_metrics["max_elevation_change_deg"] = _round(max(d[1] for d in diffs), 9)
            if max(max(d) for d in diffs) > 1e-6:
                stable_problems.append("Horizons returned different values for identical requests")

    return {
        "performed": True,
        "retrieved_utc": to_iso(datetime.now(timezone.utc)),
        "host": settings.jpl.horizons_api_url,
        "checks": [
            {
                "id": "reproduction",
                "passed": not reproduction,
                "detail": ("A fresh 1 h fetch at each site's initial window start reproduces the "
                           "committed records at the same timestamps."),
                "metrics": {
                    "samples": len(d_az),
                    "max_azimuth_difference_deg": _round(max(d_az), 9) if d_az else None,
                    "max_elevation_difference_deg": _round(max(d_el), 9) if d_el else None,
                    "max_range_difference_km": _round(max(d_range), 6) if d_range else None,
                    "tolerance_deg": LIVE_TOLERANCE_DEG,
                },
                "problems": reproduction,
            },
            {
                "id": "echoed_observer",
                "passed": not echo_problems,
                "detail": "Horizons echoed the observer it used for every live query.",
                "metrics": {"queries": len(echo_lines) + len(echo_problems), "echoes": echo_lines},
                "problems": echo_problems,
            },
            {
                "id": "reference_stable",
                "passed": not stable_problems,
                "detail": ("The re-fetched reference table matches the previously committed one "
                           "row for row." if previous is not None
                           else "First reference run; the table is now committed as evidence."),
                "metrics": stable_metrics,
                "problems": stable_problems,
            },
        ],
    }
