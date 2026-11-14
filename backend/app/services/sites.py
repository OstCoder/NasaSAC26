"""Landing-site catalogue and location resolution.

Predefined sites are a convenience, not a requirement: every analysis accepts
arbitrary coordinates through :class:`LocationInput`.

The catalogue is also where Task 1's site table lands. The mission block names
the three candidates and their order; this repository refuses to load a
catalogue that cannot supply them, so the mission and the coordinates cannot
drift apart silently.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.core.coords import validate_lat_lon
from app.core.errors import UnknownSiteError
from app.core.settings import get_settings
from app.models.schemas import LocationInput, ResolvedLocation, Site


class SiteRepository:
    def __init__(self, path: Path, candidate_ids: list[str] | None = None):
        raw = json.loads(Path(path).read_text())
        self.meta = {k: v for k, v in raw.items() if k != "sites"}
        self._sites = {s["id"]: Site(**s) for s in raw["sites"]}
        if candidate_ids is None:
            candidate_ids = list(get_settings().raw["mission"]["candidate_sites"])
        self._candidates = self._resolve_candidates(candidate_ids)

    def _resolve_candidates(self, ids: list[str]) -> list[Site]:
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(f"mission.candidate_sites lists duplicates: {duplicates}")
        missing = [i for i in ids if i not in self._sites]
        if missing:
            raise ValueError(f"mission.candidate_sites references unknown site ids {missing}")
        unsourced = [i for i in ids if not self._sites[i].source.strip()]
        if unsourced:
            raise ValueError(f"mission candidate sites must record their coordinate source: {unsourced}")
        return [self._sites[i] for i in ids]

    def all(self) -> list[Site]:
        return list(self._sites.values())

    def candidates(self) -> list[Site]:
        """Mission candidates in the order the mission declares them (Task 1's table order)."""
        return list(self._candidates)

    def get(self, site_id: str) -> Site:
        try:
            return self._sites[site_id]
        except KeyError as exc:
            raise UnknownSiteError(f"Unknown site_id {site_id!r}") from exc

    def resolve(self, loc: LocationInput) -> ResolvedLocation:
        if loc.site_id:
            s = self.get(loc.site_id)
            lat, lon = validate_lat_lon(s.latitude_deg, s.longitude_deg)
            return ResolvedLocation(
                site_id=s.id, name=s.name, latitude_deg=lat, longitude_deg=lon,
                is_custom=False, height_m=loc.height_m,
            )
        lat, lon = validate_lat_lon(loc.latitude_deg, loc.longitude_deg)
        return ResolvedLocation(
            site_id=None,
            name=loc.label or f"Custom ({lat:.3f}°, {lon:.3f}°)",
            latitude_deg=lat, longitude_deg=lon, is_custom=True, height_m=loc.height_m,
        )


@lru_cache(maxsize=1)
def get_site_repository() -> SiteRepository:
    return SiteRepository(get_settings().datasets["sites"])
