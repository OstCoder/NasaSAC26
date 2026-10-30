"""Provider interfaces.

Scientific inputs enter LunaNav only through these two interfaces. Swapping a
data source (analytic -> JPL Horizons -> SPICE; synthetic horizon -> LOLA
horizon masks) means writing one class and registering it in
``app/providers/registry.py``. Nothing in the services or API layer changes.

Contract: when a provider cannot answer from real data it raises
:class:`app.core.errors.DataUnavailableError`. It never invents values.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional

import numpy as np

from app.core.coords import unit_vector
from app.models.schemas import EffectsIncluded, ProviderInfo, ProvenanceLevel

Body = Literal["sun", "earth"]


@dataclass(frozen=True)
class SubPointTable:
    """Sub-body point on the Moon (where the body is at zenith) + distance."""

    sub_lat_deg: np.ndarray
    sub_lon_deg: np.ndarray
    distance_km: np.ndarray

    def vectors_km(self) -> np.ndarray:
        return unit_vector(self.sub_lat_deg, self.sub_lon_deg) * self.distance_km[:, None]


class EphemerisProvider(ABC):
    """Positions of the Sun and Earth in the Moon body-fixed (ME) frame."""

    id: str

    @abstractmethod
    def info(self) -> ProviderInfo: ...

    @abstractmethod
    def supported_range(self) -> tuple[datetime, datetime]:
        """UTC range for which this provider can answer."""

    @abstractmethod
    def sub_points(self, body: Body, times: list[datetime]) -> SubPointTable:
        """Sub-body points for ``times``. Raises DataUnavailableError / OutOfSupportedRangeError."""

    def body_vectors_km(self, body: Body, times: list[datetime]) -> np.ndarray:
        return self.sub_points(body, times).vectors_km()


@dataclass(frozen=True)
class HorizonMask:
    """Terrain horizon: elevation angle of the skyline as a function of azimuth.

    Azimuth in degrees clockwise from local north, sorted, within [0, 360).
    Elevation in degrees relative to the local geometric (spherical) horizon,
    i.e. it already includes lunar curvature if the builder applied it.
    """

    azimuth_deg: np.ndarray
    elevation_deg: np.ndarray
    source: str
    provenance: ProvenanceLevel
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        az = np.asarray(self.azimuth_deg, dtype=float)
        el = np.asarray(self.elevation_deg, dtype=float)
        if az.shape != el.shape or az.ndim != 1 or az.size < 2:
            raise ValueError("HorizonMask needs matching 1-D azimuth/elevation arrays (>=2 samples)")
        if np.any(np.diff(az) <= 0) or az[0] < 0 or az[-1] >= 360:
            raise ValueError("HorizonMask azimuths must be strictly increasing within [0, 360)")
        if not np.all(np.isfinite(el)):
            raise ValueError("HorizonMask elevations must be finite")
        object.__setattr__(self, "azimuth_deg", az)
        object.__setattr__(self, "elevation_deg", el)

    def elevation_at(self, azimuth_deg) -> np.ndarray:
        """Circular linear interpolation of the skyline elevation."""
        az = np.asarray(azimuth_deg, dtype=float) % 360.0
        xp = np.concatenate([self.azimuth_deg, [self.azimuth_deg[0] + 360.0]])
        fp = np.concatenate([self.elevation_deg, [self.elevation_deg[0]]])
        # handle wrap below the first sample
        az = np.where(az < xp[0], az + 360.0, az)
        return np.interp(az, xp, fp)


class LunarTerrainProvider(ABC):
    """Supplies terrain horizon masks (and, later, elevations) for a location."""

    id: str

    @abstractmethod
    def info(self) -> ProviderInfo: ...

    @abstractmethod
    def horizon_mask(
        self, lat_deg: float, lon_deg: float, site_id: Optional[str] = None
    ) -> HorizonMask:
        """Return the horizon mask or raise DataUnavailableError."""

    def surface_elevation_m(self, lat_deg: float, lon_deg: float) -> float:  # pragma: no cover
        """Extension point for DEM-backed providers (slope/hazard constraints, 3D view)."""
        from app.core.errors import DataUnavailableError

        raise DataUnavailableError(f"{self.id} does not provide surface elevations")


def flat_mask(source: str, provenance: ProvenanceLevel, step_deg: float = 1.0) -> HorizonMask:
    az = np.arange(0.0, 360.0, step_deg)
    return HorizonMask(az, np.zeros_like(az), source=source, provenance=provenance)


def make_info(**kwargs) -> ProviderInfo:
    kwargs.setdefault("effects", EffectsIncluded())
    return ProviderInfo(**kwargs)
