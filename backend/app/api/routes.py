"""HTTP routes. Thin: validate -> call a service -> return a schema."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.core.settings import get_settings
from app.models.schemas import (
    ComparisonResult,
    CompareRequest,
    HorizonMaskOut,
    LocationInput,
    Mode,
    ProviderInfo,
    RescheduleRequest,
    RescheduleResult,
    ScenarioInput,
    ScenarioResult,
    Site,
    Snapshot,
    SnapshotRequest,
)
from app.providers.registry import get_bundle
from app.services.comparison import ScenarioComparisonService, ScenarioService
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
    return get_site_repository().all()


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
