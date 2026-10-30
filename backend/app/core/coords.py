"""Lunar coordinate conventions and topocentric geometry.

Conventions (documented in docs/METHODOLOGY.md):

- Body-fixed frame: Moon Mean Earth / Polar Axis (ME). Selenographic
  latitude/longitude are planetocentric, longitude east-positive in [-180, 180).
- Reference sphere radius 1737.4 km (IAU mean radius). Observer height is
  measured above this sphere.
- Local horizon frame: East-North-Up (ENU). Azimuth is measured clockwise from
  local (lunar) north toward east, in [0, 360). Elevation is relative to the
  *geometric* (spherical) horizon; terrain is applied separately.

Near the south pole, "north" for any site points toward the equator along the
local meridian. At exactly -90 deg latitude north is undefined; we reject
latitudes within 1e-6 deg of either pole.
"""

from __future__ import annotations

import numpy as np

from .errors import InvalidInputError

POLE_EPS_DEG = 1e-6


def validate_lat_lon(lat_deg: float, lon_deg: float) -> tuple[float, float]:
    """Validate and normalise selenographic coordinates.

    Returns (lat, lon) with lon wrapped into [-180, 180).
    """
    for name, v in (("latitude", lat_deg), ("longitude", lon_deg)):
        if v is None or not np.isfinite(v):
            raise InvalidInputError(f"{name} must be a finite number")
    if not -90.0 <= lat_deg <= 90.0:
        raise InvalidInputError(f"latitude {lat_deg} outside [-90, 90]")
    if abs(abs(lat_deg) - 90.0) < POLE_EPS_DEG:
        raise InvalidInputError(
            "Exact pole: local azimuth is undefined. Offset the site slightly (e.g. -89.999)."
        )
    if not -360.0 <= lon_deg <= 360.0:
        raise InvalidInputError(f"longitude {lon_deg} outside [-360, 360]")
    lon = ((lon_deg + 180.0) % 360.0) - 180.0
    return float(lat_deg), float(lon)


def unit_vector(lat_deg, lon_deg) -> np.ndarray:
    """Body-fixed unit vector(s) for selenographic lat/lon. Shape (..., 3)."""
    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg)
    return np.stack(
        [np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)], axis=-1
    )


def enu_basis(lat_deg: float, lon_deg: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg)
    east = np.array([-np.sin(lon), np.cos(lon), 0.0])
    north = np.array([-np.sin(lat) * np.cos(lon), -np.sin(lat) * np.sin(lon), np.cos(lat)])
    up = np.array([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])
    return east, north, up


def topocentric_az_el(
    lat_deg: float,
    lon_deg: float,
    body_vectors_km: np.ndarray,
    radius_km: float,
    height_km: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Azimuth/elevation (deg) of bodies seen from a surface observer.

    ``body_vectors_km`` has shape (N, 3): Moon-centre -> body vectors in the
    body-fixed ME frame. Parallax from the observer's offset from the Moon's
    centre is included (relevant for Earth, ~0.26 deg; negligible for the Sun).
    """
    east, north, up = enu_basis(lat_deg, lon_deg)
    obs = up * (radius_km + height_km)
    rel = np.atleast_2d(body_vectors_km) - obs
    e = rel @ east
    n = rel @ north
    u = rel @ up
    el = np.degrees(np.arctan2(u, np.hypot(e, n)))
    az = np.degrees(np.arctan2(e, n)) % 360.0
    return az, el


def angular_distance_deg(lat1, lon1, lat2, lon2) -> float:
    a = unit_vector(lat1, lon1)
    b = unit_vector(lat2, lon2)
    return float(np.degrees(np.arccos(np.clip(np.dot(a, b), -1.0, 1.0))))
