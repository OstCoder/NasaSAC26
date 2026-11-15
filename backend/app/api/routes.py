"""HTTP routes. Thin: validate -> call a service -> return a schema."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

import json
import os
import subprocess

from fastapi import APIRouter, Query, Response

from app.core.errors import DataUnavailableError
from app.core.settings import REPO_ROOT, get_settings
from app.models.schemas import (
    ComparisonResult,
    CompareRequest,
    DecisionRequest,
    DecisionResult,
    Crater,
    HorizonMaskOut,
    LocationInput,
    Mode,
    ProviderInfo,
    PsrOut,
    RequirementEvaluation,
    RequirementRequest,
    RescheduleRequest,
    RescheduleResult,
    ScenarioInput,
    ScenarioResult,
    Site,
    SkyNow,
    Snapshot,
    SnapshotRequest,
    SubPoint,
)
from app.providers.registry import get_bundle
from app.services.comparison import ScenarioComparisonService, ScenarioService
from app.services.dataset_catalogue import build_catalogue
from app.services.nasa_validation import build_report as build_validation_report
from app.services.imagery import get_imagery
from app.services.jpl_status import jpl_status
from app.services.psr import get_psr_catalogue
from app.services.science import (
    nearest_psr_response,
    psr_catalogue_response,
    site_context_response,
)
from app.services.feasibility import feasibility_matrix
from app.services.geometric import sun_visibility_response
from app.services.geometric_earth import earth_visibility_response
from app.services.mission_report import mission_report
from app.services.report_export import mission_report_markdown
from app.services.decision import decide
from app.services.engineering import engineering_response
from app.services.phase3 import all_windows_summary, visibility_response
from app.services.site_data import build_readiness, series_response
from app.services.requirements import RequirementService
from app.services.sites import get_site_repository
from app.services.site_dem import terrain_dem_response
from app.services.terrain_horizon import terrain_horizon_response

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/ready")
def ready():
    """Readiness: the committed data files the API needs are present and loadable."""
    s = get_settings()
    checks = {
        "sites": Path(s.datasets["sites"]).is_file(),
        "craters": Path(s.datasets["craters"]).is_file(),
        "psr_catalogue": Path(s.datasets["psr_catalogue"]).is_file(),
        "site_series_index": Path(s.datasets["site_series_index"]).is_file(),
        "site_terrain": Path(s.datasets["site_terrain"]).is_file(),
        "horizons_reference": Path(s.datasets["horizons_reference"]).is_file(),
    }
    if not all(checks.values()):
        raise DataUnavailableError("One or more required data files are missing.")
    return {"status": "ready", "checks": checks}


@router.get("/version")
def version():
    """App name, version and supported mission window. Useful for verifying a deployment."""
    s = get_settings()
    sha = None
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL, text=True, cwd=str(REPO_ROOT),
            timeout=2,
        ).strip() or None
    except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
        sha = None
    return {
        "name": s.raw["app"]["name"],
        "version": s.raw["app"]["version"],
        "api_contract": "lunanav.v1",
        "supported_start_utc": s.raw["simulation"]["supported_start_utc"],
        "supported_end_utc": s.raw["simulation"]["supported_end_utc"],
        "default_mode": s.default_mode,
        "git_commit": sha,
    }


@router.get("/config")
def config():
    """Public configuration: supported range, feature flags, providers per mode."""
    return get_settings().public_dict()


@router.get("/providers", response_model=list[ProviderInfo])
def providers(mode: Mode = Mode.demo):
    b = get_bundle(mode)
    return [b.ephemeris.info(), b.terrain.info()]


@router.get("/datasets")
def datasets(force: bool = False):
    """Every dataset the backend loads: units, conventions, sources and checks.

    ``problems`` is empty when all cross-dataset checks pass. A dataset that is
    not available yet is listed with the reason instead of being omitted.
    ``force=true`` re-reads the files instead of using the in-process cache.
    """
    return build_catalogue(use_cache=not force)


@lru_cache(maxsize=1)
def _validation_report() -> dict:
    try:
        return build_validation_report()
    except (FileNotFoundError, ValueError) as exc:
        raise DataUnavailableError(
            f"The Phase 2 Task 5 validation report cannot be built: {exc}"
        ) from exc


@router.get("/validation")
def validation(force: bool = False):
    """Phase 2 Task 5: ten checks over the committed NASA datasets.

    Offline, derived from the files: coordinates, lunar observer, Sun/Earth
    positions against an independent model, the Horizons reference sample, units,
    UTC handling, continuity, and the cross-site/cross-date geometry. ``live``
    records the last live Horizons verification; ``force=true`` rebuilds the
    report instead of using the in-process cache.
    """
    if force:
        _validation_report.cache_clear()
    return _validation_report()


@router.get("/readiness")
def readiness():
    """Phase 2 Task 6: which candidates have both mission windows and a LOLA skyline.

    ``ready`` means the data a Phase 3 visibility calculation needs is present;
    it is not a landing recommendation and terrain still has to be applied.
    """
    return build_readiness()


@router.get("/series")
def site_series(
    site_id: str,
    window: Optional[str] = None,
    start: Optional[str] = None,
    stop: Optional[str] = None,
    step_minutes: float = 60.0,
):
    """The committed Sun/Earth track for one site and window, optionally resampled.

    Records keep the on-disk shape (``site_id``, ``timestamp_utc``, ``sun`` and
    ``earth`` with ``azimuth_deg``/``elevation_deg``/``range_km``) so a client
    reads the same fields as the JSON files. Omitting ``start``/``stop`` returns
    the stored hourly records; giving both interpolates onto that grid and
    refuses to extrapolate outside the window. Omitting ``window`` selects the
    window that contains the requested range (or the initial window).
    """
    return series_response(site_id=site_id, window=window, start=start, stop=stop,
                           step_minutes=step_minutes)


@router.get("/geometric-sun")
def geometric_sun(site_id: str, window: str = "initial"):
    """Phase 3 Task 1: geometric Sun visibility, point source, no terrain.

    The rule is exactly ``sun.elevation_deg > 0``. Every timestamp keeps its
    Task 2 azimuth and elevation, gains a boolean, a grazing flag (within the
    Sun's apparent radius) and the solar disk fraction for context. For a
    terrain-adjusted answer use ``/api/phase3``.
    """
    return sun_visibility_response(site_id=site_id, window=window)


@router.get("/geometric-earth")
def geometric_earth(site_id: str, window: str = "initial"):
    """Phase 3 Task 2: geometric Earth visibility, point source, no terrain.

    The rule is exactly ``earth.elevation_deg > 0``. Every timestamp keeps its
    Phase 2 azimuth and elevation, gains a boolean, a grazing flag (within
    Earth's apparent angular radius, 0.95 deg) and the Earth disk fraction for
    context. Geometric visibility is not a communication link. For a
    terrain-adjusted answer use ``/api/phase3``.
    """
    return earth_visibility_response(site_id=site_id, window=window)


@router.get("/feasibility")
def feasibility():
    """Phase 4: every candidate x both windows against the Phase 1 requirements.

    Composes the committed terrain-adjusted metrics, the shared requirement
    thresholds and Task 1/Task 2's geometric baselines into one matrix. It
    reports pass/fail/unknown per requirement; it does not rank sites.
    """
    return feasibility_matrix()


@router.get("/phase3")
def phase3(site_id: str, window: str = "initial"):
    """Phase 3: terrain-adjusted Sun/Earth visibility from the committed data.

    Offline: the hourly track is the Phase 2 Task 2 series, the skyline is the
    Phase 2 Task 6 two-tier LOLA mask. Records carry elevation, skyline,
    clearance and a boolean, plus intervals and summary metrics. Geometry only:
    Sun above terrain is not power, Earth above terrain is not a link budget.
    """
    return visibility_response(site_id=site_id, window=window)


@router.get("/phase3/windows")
def phase3_windows():
    """Every candidate and both mission windows, for the readiness view."""
    return all_windows_summary()


@router.get("/terrain-horizon")
def terrain_horizon(
    site_id: Optional[str] = Query(None),
    latitude_deg: Optional[float] = Query(None),
    longitude_deg: Optional[float] = Query(None),
    window: str = "initial",
):
    """Phase 3 Task 3: the terrain horizon profile, and visibility against it.

    The full 360-point LOLA skyline for a candidate site with its coverage and
    uncertainty, Sun and Earth elevation compared against it at their own
    azimuths, and the adjusted visibility delegated unchanged to
    ``/api/phase3``. A point with no committed mask comes back
    ``basis: "geometric"`` / ``geometric_only: true`` with a flat 0 degree
    horizon, never a fabricated profile. Geometry only: terrain does not prove
    power or a link budget.
    """
    return terrain_horizon_response(
        site_id=site_id, latitude_deg=latitude_deg, longitude_deg=longitude_deg,
        window=window)


@router.get("/terrain-dem")
def terrain_dem(site_id: str):
    """Phase 4 Task 6 (experimental): one candidate's pooled LOLA DEM grid.

    A committed 128x128 average-pooled height sample of the 5 m/pix PGDA site
    model, for the feature-flagged 3D terrain view. Display only - the 2D
    terrain horizon profile and its numbers stay the source of truth.
    """
    return terrain_dem_response(site_id=site_id)


@router.get("/mission-report")
def mission_report_route(site_id: str, window: str = "initial"):
    """Phase 3 Task 11: one result envelope per site and window, for Phase 4.

    Concatenates the terrain basis and coverage, adjusted visibility, intervals,
    metrics and the Phase 1 requirement checks into one deterministic document.
    Every number is copied from ``/api/terrain-horizon`` and ``/api/phase3``;
    there is no wall clock, so a re-run reproduces it. Geometry only.
    """
    return mission_report(site_id=site_id, window=window)


@router.post("/decision", response_model=DecisionResult)
def decision(req: DecisionRequest):
    """Phase 5 Tasks 6-11: evaluate, explain and rank mission candidates.

    The evaluator composes the scenario metrics, the shared requirement checks,
    maximum darkness and the Phase 5 power/battery model with the caller's
    average power demand. Only candidates that pass every selected check are
    ranked; FAIL and UNDECIDED stay visible and are never scored as favorable.
    """
    return decide(req)


@router.get("/engineering")
def engineering(site_id: str, window: str = "initial",
               load_w: Optional[float] = Query(None, ge=0, le=100_000),
               panel_design: Optional[str] = None,
               panel_tilt_deg: Optional[float] = Query(None, ge=0, le=90),
               panel_azimuth_deg: Optional[float] = Query(None, ge=0, lt=360)):
    """Phase 5 Tasks 1-2: solar-power and direct-to-Earth budgets.

    Both budgets use only committed numbers: the hourly Sun/Earth track and Earth
    range from the Phase 2 series, and the terrain-adjusted visibility flags from
    ``/api/phase3``. The power side reports a fixed horizontal array, a vertical
    azimuth-tracking array (the polar case), and optionally an arbitrary fixed
    tilt/azimuth design selected with ``panel_design=fixed``. The selected design
    drives the battery, trace and one-at-a-time sensitivity; the other designs
    remain visible for comparison. The link side reports a representative X-band
    free-space budget with C/N0, supported rate and margin. Assumptions live in
    ``config -> power / link``, are echoed in the response and are not measured
    hardware: engineering estimates, not flight budgets.
    """
    return engineering_response(
        site_id=site_id, window=window, load_w=load_w,
        panel_design=panel_design, panel_tilt_deg=panel_tilt_deg,
        panel_azimuth_deg=panel_azimuth_deg,
    )


@router.get("/mission-report.md", response_class=Response)
def mission_report_markdown_route(site_id: str, window: str = "initial"):
    """Phase 5 Task 3: the mission report as deterministic Markdown.

    Same numbers as ``/api/mission-report`` plus the Phase 5 engineering budgets,
    rendered as tables with assumptions, provenance and limitations. No wall
    clock, so the same committed inputs produce the same bytes.
    """
    body = mission_report_markdown(site_id=site_id, window=window)
    return Response(
        content=body,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="lunanav-{site_id}-{window}.md"',
        },
    )


@router.get("/sites", response_model=list[Site])
def sites():
    """Mission candidates first, in the order the mission declares them (Task 1's A/B/C)."""
    repo = get_site_repository()
    candidates = repo.candidates()
    candidate_ids = {s.id for s in candidates}
    return candidates + [s for s in repo.all() if s.id not in candidate_ids]


@router.get("/sites/{site_id}", response_model=Site)
def site(site_id: str):
    return get_site_repository().get(site_id)


@router.get("/psrs", response_model=list[PsrOut])
def psrs(
    min_area_km2: float = Query(1.0, ge=0),
    max_latitude_deg: float = Query(-80.0, le=0, gt=-90),
    near_site_id: Optional[str] = None,
    radius_km: float = Query(30.0, ge=0, le=200),
):
    """PSR polygons (LROC/LOLA, > 5 km2 by default product; min_area_km2 filters further).

    Rings are in the south polar stereographic km frame (x = rho*sin(lon),
    y = rho*cos(lon)); draw with Leaflet [y, x]. ``near_site_id`` + ``radius_km``
    restricts to PSRs within that distance of a catalogue site.
    """
    catalogue = get_psr_catalogue()
    if near_site_id is not None:
        loc = get_site_repository().resolve(LocationInput(site_id=near_site_id))
        close = catalogue.within_km(loc.latitude_deg, loc.longitude_deg, radius_km)
        selected = {p.psr_id: d for p, d in close}
    else:
        selected = None
    out = []
    for p in catalogue.all():
        if p.area_km2 < min_area_km2 or p.centroid_latitude_deg > max_latitude_deg:
            continue
        if selected is not None and p.psr_id not in selected:
            continue
        out.append(PsrOut(
            psr_id=p.psr_id, area_km2=p.area_km2, perimeter_km=p.perimeter_km,
            centroid_latitude_deg=p.centroid_latitude_deg,
            centroid_longitude_deg=p.centroid_longitude_deg,
            near_crater=p.near_crater,
            rings=[[list(pt) for pt in ring] for ring in p.rings],
        ))
    return out


@router.get("/science/psrs")
def science_psrs(
    min_area_km2: float = Query(5.0, ge=0),
    max_latitude_deg: float = Query(-80.0, le=0, gt=-90),
    near_site_id: Optional[str] = None,
    radius_km: float = Query(30.0, ge=0, le=200),
):
    """Phase 6: verified PSR polygons plus their source and geometry metadata.

    Same LROC/LOLA catalogue as ``GET /api/psrs``; the envelope keeps the
    dataset provenance next to the geometry so a client can show attribution
    without hardcoding it.
    """
    return psr_catalogue_response(
        min_area_km2=min_area_km2, max_latitude_deg=max_latitude_deg,
        near_site_id=near_site_id, radius_km=radius_km)


@router.get("/science/nearest-psr")
def science_nearest_psr(
    site_id: Optional[str] = None,
    latitude_deg: Optional[float] = Query(None, ge=-90, le=90),
    longitude_deg: Optional[float] = Query(None, ge=-360, le=360),
    radius_km: float = Query(10.0, ge=0, le=200),
    limit: int = Query(5, ge=1, le=50),
):
    """Phase 6: nearest mapped PSR and nearby PSRs for a site or coordinate.

    ``boundary_distance_km`` is the minimum point-to-polygon distance (zero
    inside). ``centroid_distance_km`` is the haversine value. Neither is a
    traverse distance, and neither proves water ice.
    """
    return nearest_psr_response(
        site_id=site_id, latitude_deg=latitude_deg, longitude_deg=longitude_deg,
        radius_km=radius_km, limit=limit)


@router.get("/science/site-context")
def science_site_context(site_id: str):
    """Phase 6: PSR, terrain and visibility context for one landing site.

    The water-ice field is explicitly withheld (``confirmed: null`` with status
    ``not_assessed``) because the committed data contains no ice detection.
    """
    return site_context_response(site_id=site_id)


@router.get("/terrain/mesh")
def terrain_mesh(site_id: str):
    """Phase 6 alias for the committed pooled site DEM used by the 3D view."""
    return terrain_dem_response(site_id=site_id)


@router.get("/horizon-mask", response_model=HorizonMaskOut)
def horizon_mask(
    site_id: Optional[str] = None,
    latitude_deg: Optional[float] = Query(None),
    longitude_deg: Optional[float] = Query(None),
    mode: Optional[Mode] = None,
):
    loc = get_site_repository().resolve(
        LocationInput(site_id=site_id, latitude_deg=latitude_deg, longitude_deg=longitude_deg)
    )
    calc = ScenarioService().calculator(mode)
    m = calc.mask_for(loc)
    return HorizonMaskOut(azimuth_deg=m.azimuth_deg.tolist(), elevation_deg=m.elevation_deg.tolist(),
                          source=m.source, provenance=m.provenance)


@router.post("/scenario", response_model=ScenarioResult)
def scenario(req: ScenarioInput):
    return ScenarioService().run(req)


@router.post("/requirements", response_model=RequirementEvaluation)
def requirements(req: RequirementRequest):
    """Check one scenario against mission requirements.

    Thresholds default to ``config/lunanav.config.json -> requirements`` (never
    hardcoded); optional ``thresholds`` override them for this check only. The
    response says which targets this scenario meets; it is not a site ranking or
    recommendation.
    """
    service = RequirementService()
    thresholds = service.settings.requirements
    overrides = req.thresholds.model_dump(exclude_none=True) if req.thresholds else {}
    if overrides:
        thresholds = replace(thresholds, **overrides)

    scenario = ScenarioInput(**req.model_dump(exclude={"thresholds"}))
    evaluation = service.evaluate(ScenarioService().run(scenario), thresholds)
    if overrides:
        evaluation.requirements_source = (
            "user-adjusted demonstration targets; defaults: "
            "config/lunanav.config.json -> requirements"
        )
        evaluation.notes.insert(
            0,
            "Thresholds were adjusted for this check only. They are demonstration "
            "targets, not NASA flight requirements.",
        )
    return evaluation


@router.post("/snapshot", response_model=Snapshot)
def snapshot(req: SnapshotRequest):
    return ScenarioService().snapshot(req.location, req.time_utc, req.mode, req.lookahead_hours)


@router.post("/compare", response_model=ComparisonResult)
def compare(req: CompareRequest):
    return ScenarioComparisonService().compare(req.a, req.b)


@router.post("/reschedule", response_model=RescheduleResult)
def reschedule(req: RescheduleRequest):
    return ScenarioComparisonService().reschedule(
        req.location, req.original_landing_utc, req.proposed_landing_utc,
        req.duration_hours, req.step_minutes, req.mode,
    )


@lru_cache
def _craters() -> list[dict]:
    return json.loads(Path(get_settings().datasets["craters"]).read_text())["craters"]


@router.get("/craters", response_model=list[Crater])
def craters():
    """Named lunar craters from the IAU Gazetteer of Planetary Nomenclature."""
    return _craters()


@router.get("/sky/now", response_model=SkyNow)
def sky_now(mode: Optional[Mode] = None):
    """Sub-solar and sub-Earth points at this moment, from the mode's ephemeris provider."""
    ephemeris = get_bundle(mode or Mode(get_settings().default_mode)).ephemeris
    now = datetime.now(timezone.utc).replace(microsecond=0)

    def point(body):
        sp = ephemeris.sub_points(body, [now])
        return SubPoint(latitude_deg=round(float(sp.sub_lat_deg[0]), 5),
                        longitude_deg=round(float(sp.sub_lon_deg[0]), 5),
                        distance_km=round(float(sp.distance_km[0]), 1))

    return SkyNow(time_utc=now, sun=point("sun"), earth=point("earth"), source=ephemeris.info().name)


# ------------------------------------------------------------ NASA/JPL ----


@router.get("/jpl/status")
def jpl_status_route(force: bool = False):
    """Reachability of JPL Horizons and Moon Trek from this server (cached 30 s)."""
    return jpl_status(force)


@router.get("/imagery/layers")
def imagery_layers():
    im = get_imagery()
    return [{"id": l.id, "label": l.label, "credit": l.credit, "source": f"{im.jpl.trek_tiles_url}/{l.path}"}
            for l in im.layers.values()]


def _image_response(data: bytes, meta: dict, media_type: str) -> Response:
    return Response(content=data, media_type=media_type, headers={
        "Cache-Control": "public, max-age=86400",
        "X-LunaNav-Imagery": json.dumps(meta),
        "Access-Control-Expose-Headers": "X-LunaNav-Imagery",
    })


@router.get("/imagery/south-pole")
def imagery_south_pole(layer: Optional[str] = None, size: int = 2048, max_lat: float = -80.0):
    """Moon Trek imagery reprojected to LunaNav's south polar stereographic map grid (PNG)."""
    im = get_imagery()
    data, meta = im.south_pole_png(layer or im.settings.imagery["default_layer"], size, max_lat)
    return _image_response(data, meta, "image/png")


@router.get("/imagery/global")
def imagery_global(layer: Optional[str] = None, zoom: int = 2):
    """Equirectangular global texture stitched from Moon Trek tiles (JPEG), for the 3D globe."""
    im = get_imagery()
    data, meta = im.global_jpeg(layer or "wac", zoom)
    return _image_response(data, meta, "image/jpeg")


@router.get("/imagery/relief")
def imagery_relief(kind: str = "height", zoom: int = 2):
    """LOLA-derived height or normal map (JPEG) that gives the 3D globe its real shape. Display only."""
    data, meta = get_imagery().relief_jpeg(kind, zoom)
    return _image_response(data, meta, "image/jpeg")


@router.get("/imagery/tile/{layer}/{z}/{row}/{col}")
def imagery_tile(layer: str, z: int, row: int, col: int):
    """One Moon Trek tile through the disk cache, for the whole-Moon 2D map. 404 where Trek has no data."""
    tile = get_imagery().tile_bytes(layer, z, row, col)
    if tile is None:
        return Response(status_code=404)
    data, media_type = tile
    return Response(content=data, media_type=media_type, headers={"Cache-Control": "public, max-age=86400"})
