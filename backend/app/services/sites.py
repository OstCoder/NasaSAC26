"""Landing-site catalogue and location resolution.

Predefined sites are a convenience, not a requirement: every analysis accepts
arbitrary coordinates through :class:`LocationInput`.

Each catalogue site is enriched at load time with its nearest mapped PSR (from
the LROC/LOLA PSR boundary catalogue) and a consistency check of the recorded
LOLA elevation against the sampling evidence file.

The catalogue is where Task 1's site table lands. The mission block names the
three candidates and their order, and the catalogue declares the same ids in
``mission_candidates``; this repository refuses to load if the two disagree or
if it cannot supply them, so the mission and the coordinates cannot drift apart
silently.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.core.coords import validate_lat_lon
from app.core.errors import UnknownSiteError
from app.core.settings import get_settings
from app.models.schemas import LocationInput, PsrProximity, ResolvedLocation, Site
from app.services.psr import get_psr_catalogue

# Tolerance when cross-checking the elevation recorded in sites.json against
# the PGDA-DEM sampling evidence (data/reference/site_elevations.json).
ELEVATION_CHECK_TOLERANCE_M = 0.05


class SiteRepository:
    def __init__(self, path: Path, candidate_ids: list[str] | None = None):
        raw = json.loads(Path(path).read_text())
        self.meta = {k: v for k, v in raw.items() if k != "sites"}
        self._sites = {s["id"]: Site(**s) for s in raw["sites"]}
        self._enrich_with_psr()
        self._check_elevations()
        if candidate_ids is None:
            candidate_ids = list(get_settings().raw["mission"]["candidate_sites"])
        self._candidates = self._resolve_candidates(candidate_ids)

    def _resolve_candidates(self, ids: list[str]) -> list[Site]:
        declared = list(self.meta.get("mission_candidates", []))
        if declared and declared != list(ids):
            raise ValueError(
                f"config mission.candidate_sites {list(ids)} disagrees with the catalogue's "
                f"mission_candidates {declared}"
            )
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

    # ------------------------------------------------------------- helpers --
    def _enrich_with_psr(self) -> None:
        catalogue = get_psr_catalogue()
        for site in self._sites.values():
            psr, dist = catalogue.nearest(site.latitude_deg, site.longitude_deg)
            site.nearest_psr = PsrProximity(
                psr_id=psr.psr_id,
                label=psr.label,
                distance_km=round(dist, 3),
                area_km2=psr.area_km2,
                centroid_latitude_deg=psr.centroid_latitude_deg,
                centroid_longitude_deg=psr.centroid_longitude_deg,
            )
            site.psrs_within_10_km = len(catalogue.within_km(site.latitude_deg, site.longitude_deg, 10.0))

    def _check_elevations(self) -> None:
        """Fail fast if a recorded elevation disagrees with the sampling evidence."""
        evidence_path = get_settings().datasets.get("site_elevations")
        if evidence_path is None or not Path(evidence_path).exists():
            return
        samples = json.loads(Path(evidence_path).read_text()).get("samples", {})
        for site in self._sites.values():
            sample = samples.get(site.id)
            if site.elevation_m is None or sample is None:
                continue
            truth = sample["products"]["surf"]["median"]
            if abs(site.elevation_m - truth) > ELEVATION_CHECK_TOLERANCE_M:
                raise ValueError(
                    f"site '{site.id}' elevation_m={site.elevation_m} disagrees with LOLA "
                    f"sampling evidence {truth} m in {Path(evidence_path).name}"
                )

    # --------------------------------------------------------------- api ----
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
                is_custom=False, height_m=loc.height_m, elevation_m=s.elevation_m,
            )
        lat, lon = validate_lat_lon(loc.latitude_deg, loc.longitude_deg)
        return ResolvedLocation(
            site_id=None,
            name=loc.label or f"Custom ({lat:.3f}°, {lon:.3f}°)",
            latitude_deg=lat, longitude_deg=lon, is_custom=True, height_m=loc.height_m,
            elevation_m=loc.elevation_m,
        )


@lru_cache(maxsize=1)
def get_site_repository() -> SiteRepository:
    return SiteRepository(get_settings().datasets["sites"])
