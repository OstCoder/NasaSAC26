"""HTTP routes. Thin: validate -> call a service -> return a schema."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

import json

from fastapi import APIRouter, Query, Response

from app.core.settings import get_settings
from app.models.schemas import (
    ComparisonResult,
    CompareRequest,
    Crater,
    HorizonMaskOut,
    LocationInput,
    Mode,
    ProviderInfo,
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
from app.services.imagery import get_imagery
from app.services.jpl_status import jpl_status
from app.services.sites import get_site_repository

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/config")
def config():
    """Public configuration: supported range, feature flags, providers per mode."""
    return get_settings().public_dict()


@router.get("/providers", response_model=list[ProviderInfo])
def providers(mode: Mode = Mode.demo):
    b = get_bundle(mode)
    return [b.ephemeris.info(), b.terrain.info()]


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
