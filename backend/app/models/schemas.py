"""Typed API contracts (Pydantic v2).

These schemas are the single source of truth for the HTTP API; the frontend
mirrors them in ``frontend/src/types/api.ts``. They do not depend on any
frontend component, so a new client (CLI, notebook, 3D viewer) can reuse them.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class Mode(str, Enum):
    demo = "demo"
    scientific = "scientific"


class ProvenanceLevel(str, Enum):
    """How much a value can be trusted, from weakest to strongest."""

    synthetic = "synthetic"  # invented, representative only
    geometric_only = "geometric_only"  # real geometry, no terrain applied
    analytic_approximate = "analytic_approximate"  # real physics, truncated model
    scientific_sourced = "scientific_sourced"  # sourced dataset (Horizons, SPICE, LOLA)


PROVENANCE_RANK = {
    ProvenanceLevel.synthetic: 0,
    ProvenanceLevel.geometric_only: 1,
    ProvenanceLevel.analytic_approximate: 2,
    ProvenanceLevel.scientific_sourced: 3,
}


class EffectsIncluded(BaseModel):
    """Which physical effects a provider or calculation accounts for."""

    terrain_topography: bool = False
    optical_libration: bool = False
    physical_libration: bool = False
    observer_parallax: bool = False
    light_time_correction: bool = False
    finite_solar_disk: bool = False
    lunar_curvature_in_horizon: bool = False
    notes: list[str] = Field(default_factory=list)


class ProviderInfo(BaseModel):
    id: str
    kind: Literal["ephemeris", "terrain"]
    name: str
    provenance: ProvenanceLevel
    source: str
    description: str
    effects: EffectsIncluded
    available: bool
    unavailable_reason: Optional[str] = None
    supported_start_utc: Optional[datetime] = None
    supported_end_utc: Optional[datetime] = None


class Provenance(BaseModel):
    """Attached to every computed result so the UI can label it honestly."""

    mode: Mode
    overall: ProvenanceLevel
    label: str
    ephemeris: ProviderInfo
    terrain: ProviderInfo
    terrain_mask_source: str
    effects: EffectsIncluded
    caveats: list[str]


# ---------------------------------------------------------------- sites ----


class Site(BaseModel):
    id: str
    name: str
    latitude_deg: float
    longitude_deg: float
    region: str = "South Polar Region"
    description: str = ""
    coordinate_note: str = ""
    tags: list[str] = Field(default_factory=list)
    source: str = ""


class LocationInput(BaseModel):
    """Either a known ``site_id`` or explicit coordinates (custom site)."""

    site_id: Optional[str] = None
    latitude_deg: Optional[float] = None
    longitude_deg: Optional[float] = None
    label: Optional[str] = None
    height_m: float = Field(2.0, ge=0, le=100, description="Observer height above local terrain")

    @model_validator(mode="after")
    def _one_of(self):
        has_coords = self.latitude_deg is not None and self.longitude_deg is not None
        if not self.site_id and not has_coords:
            raise ValueError("Provide site_id or both latitude_deg and longitude_deg")
        return self


class ResolvedLocation(BaseModel):
    site_id: Optional[str]
    name: str
    latitude_deg: float
    longitude_deg: float
    is_custom: bool
    height_m: float


# ------------------------------------------------------------- scenario ----


class ScenarioInput(BaseModel):
    location: LocationInput
    landing_utc: datetime
    duration_hours: float = Field(..., gt=0)
    step_minutes: Optional[float] = Field(None, gt=0)
    mode: Optional[Mode] = None
    label: Optional[str] = None

    @field_validator("landing_utc")
    @classmethod
    def _aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("landing_utc must include a timezone (use Z for UTC)")
        return v


class Interval(BaseModel):
    start_utc: datetime
    end_utc: datetime
    duration_hours: float
    clipped_start: bool = Field(description="Interval was already in progress at window start")
    clipped_end: bool = Field(description="Interval continues past window end")


class IntervalSet(BaseModel):
    sun_visible: list[Interval]
    earth_visible: list[Interval]
    both_visible: list[Interval]
    sun_blocked: list[Interval]
    earth_blocked: list[Interval]
    neither_visible: list[Interval]


class TimeSeries(BaseModel):
    """Column-oriented samples. All arrays share the ``times_utc`` index."""

    times_utc: list[datetime]
    sun_azimuth_deg: list[float]
    sun_elevation_deg: list[float]
    sun_terrain_horizon_deg: list[float]
    sun_disk_fraction: list[float]
    sun_visible: list[bool]
    earth_azimuth_deg: list[float]
    earth_elevation_deg: list[float]
    earth_terrain_horizon_deg: list[float]
    earth_visible: list[bool]


class MetricValue(BaseModel):
    id: str
    label: str
    value: Optional[float]
    unit: str
    description: str
    category: Literal["sun", "earth", "combined", "geometry"]
    censored: bool = Field(
        False, description="True if the value is limited by the analysis window (true value may be larger)"
    )


class HorizonMaskOut(BaseModel):
    azimuth_deg: list[float]
    elevation_deg: list[float]
    source: str
    provenance: ProvenanceLevel


class ScenarioResult(BaseModel):
    label: Optional[str]
    location: ResolvedLocation
    landing_utc: datetime
    end_utc: datetime
    duration_hours: float
    step_minutes: float
    series: TimeSeries
    intervals: IntervalSet
    metrics: list[MetricValue]
    horizon_mask: HorizonMaskOut
    provenance: Provenance


class SnapshotRequest(BaseModel):
    location: LocationInput
    time_utc: datetime
    mode: Optional[Mode] = None
    lookahead_hours: Optional[float] = Field(None, gt=0)


class BodyState(BaseModel):
    azimuth_deg: float
    elevation_deg: float
    terrain_horizon_deg: float
    clearance_deg: float = Field(description="Elevation minus terrain horizon at that azimuth")
    visible: bool
    disk_fraction: Optional[float] = None
    next_transition_utc: Optional[datetime] = None
    hours_until_transition: Optional[float] = None
    transition_kind: Optional[Literal["set", "rise"]] = None
    transition_beyond_lookahead: bool = False


class Snapshot(BaseModel):
    location: ResolvedLocation
    time_utc: datetime
    sun: BodyState
    earth: BodyState
    lookahead_hours: float
    provenance: Provenance


# ----------------------------------------------------------- comparison ----


class MetricDelta(BaseModel):
    id: str
    label: str
    unit: str
    category: str
    a: Optional[float]
    b: Optional[float]
    delta: Optional[float]
    percent_change: Optional[float]
    either_censored: bool
    availability_direction: int = Field(
        0, description="+1: larger means more availability; -1: larger means longer outage; 0: neutral"
    )
    statement: str


class CompareRequest(BaseModel):
    a: ScenarioInput
    b: ScenarioInput


class ComparisonResult(BaseModel):
    a: ScenarioResult
    b: ScenarioResult
    deltas: list[MetricDelta]
    tradeoffs: list[str]
    comparable: bool
    comparability_notes: list[str]


class RescheduleRequest(BaseModel):
    location: LocationInput
    original_landing_utc: datetime
    proposed_landing_utc: datetime
    duration_hours: float = Field(..., gt=0)
    step_minutes: Optional[float] = Field(None, gt=0)
    mode: Optional[Mode] = None


class RescheduleResult(BaseModel):
    shift_hours: float
    comparison: ComparisonResult
    headline_changes: list[MetricDelta]


class ApiError(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)
