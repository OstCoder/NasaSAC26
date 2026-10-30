"""Landing-site catalogue and location resolution.

Predefined sites are a convenience, not a requirement: every analysis accepts
arbitrary coordinates through :class:`LocationInput`.
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
    def __init__(self, path: Path):
        raw = json.loads(Path(path).read_text())
        self.meta = {k: v for k, v in raw.items() if k != "sites"}
        self._sites = {s["id"]: Site(**s) for s in raw["sites"]}

    def all(self) -> list[Site]:
        return list(self._sites.values())

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
