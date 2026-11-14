"""Permanently shadowed region (PSR) catalogue.

Reads ``data/reference/psrs.json`` (built by ``scripts/build_psr_catalogue.py``
from the LROC south-pole PSR boundary shapefile, which itself traces LOLA
permanent-shadow masks from Mazarico et al. 2011). Distances are computed in
the south polar stereographic plane of that product, which is also the
frontend map frame, so the same numbers drive the API, the map overlay and
the tests.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.core.errors import InvalidInputError
from app.core.settings import get_settings


@dataclass(frozen=True)
class Psr:
    psr_id: str
    area_km2: float
    perimeter_km: float
    centroid_latitude_deg: float
    centroid_longitude_deg: float
    near_crater: str
    rings: tuple[tuple[tuple[float, float], ...], ...]

    @property
    def label(self) -> str:
        crater = self.near_crater or "unnamed"
        return f"PSR near {crater} ({self.psr_id})"


def _point_segment_distance(px, py, ax, ay, bx, by) -> np.ndarray:
    """Distance from point (px, py) to segments [A, B]; arrays broadcast."""
    abx, aby = bx - ax, by - ay
    denom = abx * abx + aby * aby
    # coincident endpoints: fall back to point distance
    denom = np.where(denom == 0, np.finfo(float).tiny, denom)
    t = np.clip(((px - ax) * abx + (py - ay) * aby) / denom, 0.0, 1.0)
    cx, cy = ax + t * abx, ay + t * aby
    return np.hypot(px - cx, py - cy)


def _point_ring_distance(qx: float, qy: float, ring) -> float:
    """Min distance (km) from a query point to a closed ring in the plane."""
    p = np.asarray(ring, dtype=float)
    if np.array_equal(p[0], p[-1]):
        p = p[:-1]
    nxt = np.roll(p, -1, axis=0)
    return float(np.min(_point_segment_distance(qx, qy, p[:, 0], p[:, 1], nxt[:, 0], nxt[:, 1])))


def _point_in_ring(qx: float, qy: float, ring) -> bool:
    """Ray-casting containment test for a planar ring."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > qy) != (yj > qy):
            x_cross = (xj - xi) * (qy - yi) / (yj - yi) + xi
            if qx < x_cross:
                inside = not inside
        j = i
    return inside


class PsrCatalogue:
    def __init__(self, path: Path):
        raw = json.loads(Path(path).read_text())
        self.meta = {k: v for k, v in raw.items() if k != "psrs"}
        self._psrs: tuple[Psr, ...] = tuple(
            Psr(
                psr_id=p["psr_id"],
                area_km2=float(p["area_km2"]),
                perimeter_km=float(p.get("perimeter_km", 0.0)),
                centroid_latitude_deg=float(p["centroid_latitude_deg"]),
                centroid_longitude_deg=float(p["centroid_longitude_deg"]),
                near_crater=p.get("near_crater") or "",
                rings=tuple(tuple((float(x), float(y)) for x, y in ring) for ring in p["rings"]),
            )
            for p in raw["psrs"]
        )

    def __len__(self) -> int:
        return len(self._psrs)

    def all(self) -> list[Psr]:
        return list(self._psrs)

    def distance_to(self, psr: Psr, lat_deg: float, lon_deg: float) -> float:
        """Point-to-PSR distance in km (0 if the point lies inside the PSR)."""
        from app.core.coords import polar_stereographic_xy

        qx, qy = polar_stereographic_xy(lat_deg, lon_deg)
        for ring in psr.rings:
            if _point_in_ring(qx, qy, ring):
                return 0.0
        return min(_point_ring_distance(qx, qy, ring) for ring in psr.rings)

    def nearest(self, lat_deg: float, lon_deg: float, min_area_km2: float = 0.0) -> tuple[Psr, float]:
        if not math.isfinite(lat_deg) or not math.isfinite(lon_deg):
            raise InvalidInputError("PSR query coordinates must be finite")
        best, best_d = None, math.inf
        for psr in self._psrs:
            if psr.area_km2 < min_area_km2:
                continue
            d = self.distance_to(psr, lat_deg, lon_deg)
            if d < best_d:
                best, best_d = psr, d
        if best is None:
            raise InvalidInputError(f"No PSR with area >= {min_area_km2} km2 in the catalogue")
        return best, best_d

    def within_km(self, lat_deg: float, lon_deg: float, radius_km: float) -> list[tuple[Psr, float]]:
        from app.core.coords import polar_stereographic_xy

        qx, qy = polar_stereographic_xy(lat_deg, lon_deg)
        out: list[tuple[Psr, float]] = []
        for psr in self._psrs:
            # cheap centroid pre-filter using great-circle radius + PSR extent bound
            cg = _great_circle_km(lat_deg, lon_deg, psr.centroid_latitude_deg, psr.centroid_longitude_deg)
            extent = math.sqrt(psr.area_km2 / math.pi)
            if cg - extent > radius_km:
                continue
            d = self.distance_to(psr, lat_deg, lon_deg)
            if d <= radius_km:
                out.append((psr, d))
        out.sort(key=lambda t: t[1])
        return out


def _great_circle_km(lat1, lon1, lat2, lon2) -> float:
    from app.core.coords import great_circle_km

    return great_circle_km(lat1, lon1, lat2, lon2)


@lru_cache(maxsize=1)
def get_psr_catalogue() -> PsrCatalogue:
    return PsrCatalogue(get_settings().datasets["psr_catalogue"])
