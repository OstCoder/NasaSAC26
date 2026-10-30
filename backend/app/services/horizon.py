"""HorizonCalculator: geometric elevation -> terrain-adjusted visibility.

A body is "above the terrain horizon" when its apparent centre is higher than
the skyline elevation at the body's azimuth. Elevation > 0 alone is NOT used,
because near the poles crater rims and massifs routinely rise 1-5 deg above
the geometric horizon, which is comparable to the Sun's maximum elevation
(~1.6 deg) at the pole itself.

Also contains :func:`build_horizon_mask_from_dem`, the routine that turns a
gridded DEM (e.g. a LOLA polar stereographic product) into a horizon mask.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.providers.base import HorizonMask
from app.models.schemas import ProvenanceLevel


def disk_fraction_above(clearance_deg: np.ndarray, radius_deg: float) -> np.ndarray:
    """Fraction of a circular disk above a locally straight skyline.

    ``clearance_deg`` is centre elevation minus skyline elevation. Uses the
    circular-segment area formula; assumes the skyline is straight across the
    disk (a good approximation for the Sun's 0.53 deg diameter).
    """
    h = np.clip(np.asarray(clearance_deg, float) / radius_deg, -1.0, 1.0)
    return 0.5 + (h * np.sqrt(1.0 - h * h) + np.arcsin(h)) / np.pi


@dataclass(frozen=True)
class BodyVisibility:
    terrain_horizon_deg: np.ndarray
    clearance_deg: np.ndarray
    visible: np.ndarray
    disk_fraction: np.ndarray


class HorizonCalculator:
    """Applies a horizon mask to body directions."""

    def evaluate(
        self,
        mask: HorizonMask,
        azimuth_deg: np.ndarray,
        elevation_deg: np.ndarray,
        angular_radius_deg: float,
    ) -> BodyVisibility:
        skyline = mask.elevation_at(azimuth_deg)
        clearance = np.asarray(elevation_deg, float) - skyline
        return BodyVisibility(
            terrain_horizon_deg=skyline,
            clearance_deg=clearance,
            visible=clearance > 0.0,
            disk_fraction=disk_fraction_above(clearance, angular_radius_deg),
        )


def build_horizon_mask_from_dem(
    dem_m: np.ndarray,
    x0_m: float,
    y0_m: float,
    pixel_m: float,
    obs_x_m: float,
    obs_y_m: float,
    obs_height_m: float = 2.0,
    north_unit: tuple[float, float] | None = None,
    azimuth_step_deg: float = 1.0,
    max_range_m: float = 150_000.0,
    radius_m: float = 1_737_400.0,
    source: str = "DEM ray-march",
    provenance: ProvenanceLevel = ProvenanceLevel.scientific_sourced,
) -> HorizonMask:
    """Ray-march a gridded DEM to obtain the skyline elevation per azimuth.

    Grid convention: ``dem_m[row, col]`` with x = x0 + col*pixel and
    y = y0 - row*pixel (north-up raster, as in GeoTIFF). For a south polar
    stereographic grid, local north at the observer points radially away from
    the pole; pass ``north_unit`` explicitly or it is derived from the observer
    position (x, y) / |(x, y)|.

    Elevation angle to a terrain sample at horizontal distance s:
        atan((h_t - drop(s) - h_obs) / s),   drop(s) = s^2 / (2R)
    The curvature drop makes far terrain sink below the tangent plane.
    Stereographic scale distortion (<0.2 % poleward of 85 deg S) is ignored.
    """
    dem = np.asarray(dem_m, float)
    rows, cols = dem.shape

    def sample(x, y):
        c = (x - x0_m) / pixel_m
        r = (y0_m - y) / pixel_m
        valid = (c >= 0) & (c <= cols - 1) & (r >= 0) & (r <= rows - 1)
        c = np.clip(c, 0, cols - 1)
        r = np.clip(r, 0, rows - 1)
        c0 = np.floor(c).astype(int)
        r0 = np.floor(r).astype(int)
        c1 = np.minimum(c0 + 1, cols - 1)
        r1 = np.minimum(r0 + 1, rows - 1)
        fc, fr = c - c0, r - r0
        z = (
            dem[r0, c0] * (1 - fc) * (1 - fr)
            + dem[r0, c1] * fc * (1 - fr)
            + dem[r1, c0] * (1 - fc) * fr
            + dem[r1, c1] * fc * fr
        )
        return np.where(valid, z, np.nan)

    if north_unit is None:
        rho = np.hypot(obs_x_m, obs_y_m)
        if rho < pixel_m:
            raise ValueError("Observer is at the projection pole; pass north_unit explicitly")
        north = np.array([obs_x_m, obs_y_m]) / rho
    else:
        north = np.asarray(north_unit, float) / np.linalg.norm(north_unit)
    # East is north rotated 90 deg clockwise when viewed with up toward the viewer.
    east = np.array([north[1], -north[0]])

    h_obs = float(sample(np.array([obs_x_m]), np.array([obs_y_m]))[0]) + obs_height_m
    if not np.isfinite(h_obs):
        raise ValueError("Observer lies outside the DEM")

    azimuths = np.arange(0.0, 360.0, azimuth_step_deg)
    dists = np.arange(pixel_m, max_range_m, pixel_m * 0.5)
    out = np.empty_like(azimuths)
    for i, az in enumerate(np.radians(azimuths)):
        d = np.sin(az) * east + np.cos(az) * north
        xs = obs_x_m + dists * d[0]
        ys = obs_y_m + dists * d[1]
        z = sample(xs, ys)
        drop = dists**2 / (2.0 * radius_m)
        ang = np.degrees(np.arctan2(z - drop - h_obs, dists))
        out[i] = np.nanmax(ang) if np.any(np.isfinite(ang)) else 0.0
    return HorizonMask(azimuths, out, source=source, provenance=provenance,
                       metadata={"max_range_m": max_range_m, "pixel_m": pixel_m})
