"""One index of every dataset the backend loads.

Phase 2 Task 4 is about organisation, not acquisition: each dataset gets one
owner, one path, declared units and longitude convention, its sources, and
cross-dataset checks proving that a site is the same point in every file.

Everything here is derived by reading the files. A missing or malformed dataset
is reported as unavailable with a reason; nothing is filled in or guessed.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.core.settings import get_settings
from app.core.timeutil import parse_utc

SCHEMA = "lunanav.dataset_catalogue.v1"
ROOT = Path(__file__).resolve().parents[3]

LONGITUDE_CONVENTION = "selenographic east-positive, [-180, 180)"
UNITS = {
    "angle": "degrees",
    "height": "metres above the 1737.4 km reference sphere",
    "distance": "kilometres",
    "area": "square kilometres",
    "time": "UTC, ISO-8601 with Z",
}
COORD_TOLERANCE_DEG = 1e-6
ELEVATION_TOLERANCE_M = 0.05


# ---------------------------------------------------------------- helpers --


def _rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _read(path: Path) -> tuple[dict | None, str | None]:
    if not path.exists():
        return None, f"missing {_rel(path)}"
    try:
        return json.loads(path.read_text()), None
    except json.JSONDecodeError as exc:
        return None, f"{_rel(path)} is not valid JSON: {exc}"


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value)


def _count(payload: dict) -> int | None:
    for key in ("sites", "psrs", "craters", "samples", "series"):
        value = payload.get(key)
        if isinstance(value, (list, dict)):
            return len(value)
    return None


def site_record_problems(site: dict) -> list[str]:
    """Validate one catalogue site record (coordinates, elevation, source)."""
    site_id = site.get("id")
    if not site_id:
        return ["sites: entry without an id"]
    problems = []
    lat, lon = site.get("latitude_deg"), site.get("longitude_deg")
    if not (_finite(lat) and -90.0 <= lat <= 90.0):
        problems.append(f"sites: {site_id} latitude {lat!r} is not a valid latitude")
    if not (_finite(lon) and -180.0 <= lon < 180.0):
        problems.append(f"sites: {site_id} longitude {lon!r} is not in [-180, 180)")
    elevation = site.get("elevation_m")
    if elevation is not None and not _finite(elevation):
        problems.append(f"sites: {site_id} elevation_m {elevation!r} is not a finite number")
    if not str(site.get("source", "")).strip():
        problems.append(f"sites: {site_id} records no coordinate source")
    return problems


def series_site_problems(payload_site: dict, catalogue_site: dict) -> list[str]:
    """The series must describe the same point the catalogue does."""
    site_id = catalogue_site.get("id")
    problems = []
    lat, lon = payload_site.get("latitude_deg"), payload_site.get("longitude_deg")
    if not (_finite(lat) and abs(lat - catalogue_site["latitude_deg"]) <= COORD_TOLERANCE_DEG):
        problems.append(
            f"site_series: {site_id} latitude {lat!r} disagrees with the catalogue "
            f"{catalogue_site['latitude_deg']}")
    if not (_finite(lon) and -180.0 <= lon < 180.0):
        problems.append(
            f"site_series: {site_id} longitude {lon!r} is outside the declared [-180, 180) convention")
    elif abs(lon - catalogue_site["longitude_deg"]) > COORD_TOLERANCE_DEG:
        problems.append(
            f"site_series: {site_id} longitude {lon!r} disagrees with the catalogue "
            f"{catalogue_site['longitude_deg']}")
    elevation, recorded = payload_site.get("elevation_m"), catalogue_site.get("elevation_m")
    if recorded is not None and not (
        _finite(elevation) and abs(elevation - recorded) <= ELEVATION_TOLERANCE_M
    ):
        problems.append(
            f"site_series: {site_id} elevation {elevation!r} disagrees with the catalogue {recorded}")
    return problems


@dataclass
class Dataset:
    id: str
    label: str
    kind: str  # sites | observations | terrain | reference | cache
    path: str
    schema: str | None = None
    available: bool = True
    records: int | None = None
    unavailable_reason: str | None = None
    sources: list[dict] = field(default_factory=list)
    details: dict = field(default_factory=dict)
    units: dict = field(default_factory=dict)
    longitude_convention: str = LONGITUDE_CONVENTION

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "path": self.path,
            "schema": self.schema,
            "available": self.available,
            "records": self.records,
            "unavailable_reason": self.unavailable_reason,
            "units": self.units or dict(UNITS),
            "longitude_convention": self.longitude_convention,
            "sources": self.sources,
            "details": self.details,
        }


# --------------------------------------------------------------- datasets --


def _sites(settings, problems: list[str]) -> tuple[Dataset, dict[str, dict]]:
    path = Path(settings.datasets["sites"])
    raw, error = _read(path)
    dataset = Dataset("sites", "Landing-site catalogue (Phase 1 Task 1)", "sites", _rel(path))
    if error or raw is None:
        dataset.available = False
        dataset.unavailable_reason = error
        problems.append(str(error))
        return dataset, {}

    by_id: dict[str, dict] = {}
    for site in raw.get("sites", []):
        problems.extend(site_record_problems(site))
        if site.get("id"):
            by_id[site["id"]] = site
    candidates = list(settings.raw["mission"]["candidate_sites"])
    for site_id in candidates:
        if site_id not in by_id:
            problems.append(f"sites: mission candidate {site_id!r} is not in the catalogue")
        elif by_id[site_id].get("elevation_m") is None:
            problems.append(f"sites: mission candidate {site_id!r} has no recorded elevation")

    dataset.schema = raw.get("version")
    dataset.records = len(by_id)
    dataset.sources = [
        {"label": "Mazarico et al. 2011, Icarus 211, 1066-1081", "url": "https://doi.org/10.1016/j.icarus.2010.10.030"},
        {"label": "NASA PGDA LOLA 5 m/pix south-pole DEMs", "url": "https://pgda.gsfc.nasa.gov/products/78"},
    ]
    dataset.details = {
        "mission_candidates": candidates,
        "with_elevation": sum(1 for s in by_id.values() if s.get("elevation_m") is not None),
        "declared_frame": raw.get("coordinate_frame"),
    }
    return dataset, by_id


def _series(settings, sites_by_id: dict[str, dict], problems: list[str]) -> Dataset:
    index_path = Path(settings.datasets.get(
        "site_series_index", ROOT / "data" / "scientific" / "site_series" / "index.json"))
    index, error = _read(index_path)
    dataset = Dataset("site_series", "Hourly Sun/Earth series (Phase 2 Task 2)", "observations",
                      _rel(index_path))
    if error or index is None:
        dataset.available = False
        dataset.unavailable_reason = error
        problems.append(str(error))
        return dataset

    dataset.schema = index.get("schema")
    total = 0
    for entry in index.get("sites", []):
        site_id = entry.get("site_id")
        if site_id not in sites_by_id:
            problems.append(f"site_series: unknown site {site_id!r}")
        for window, name in entry.get("files", {}).items():
            payload, read_error = _read(index_path.parent / name)
            if read_error or payload is None:
                problems.append(f"site_series: {name}: {read_error}")
                continue
            site_block = payload.get("site", {})
            if site_id in sites_by_id:
                problems.extend(series_site_problems(site_block, sites_by_id[site_id]))
            records = payload.get("series", [])
            total += len(records)
            if not records:
                problems.append(f"site_series: {name} has no records")
                continue
            if payload.get("schema") != "lunanav.site_series.v1":
                problems.append(f"site_series: {name} schema {payload.get('schema')!r}")
            try:
                times = [parse_utc(r["timestamp_utc"]) for r in records]
            except Exception:  # noqa: BLE001 - reported, not raised, so other files still check
                problems.append(f"site_series: {name} has unreadable timestamps")
                continue
            if any(later <= earlier for earlier, later in zip(times, times[1:])):
                problems.append(f"site_series: {name} timestamps are not chronological")
            for record in records:
                for body in ("sun", "earth"):
                    sample = record.get(body, {})
                    if not (_finite(sample.get("azimuth_deg")) and _finite(sample.get("elevation_deg"))):
                        problems.append(f"site_series: {name} has a non-finite {body} value at "
                                        f"{record.get('timestamp_utc')}")
                        break
                else:
                    continue
                break

    if index.get("total_samples") != total:
        problems.append(
            f"site_series: index total_samples {index.get('total_samples')} but {total} on disk")
    dataset.records = total
    dataset.details = {
        "step": index.get("step"),
        "partial": index.get("partial"),
        "windows": index.get("windows"),
        "sites": [entry.get("site_id") for entry in index.get("sites", [])],
        "generated_utc": index.get("generated_utc"),
    }
    dataset.sources = [
        {"label": "NASA JPL Horizons API (observer tables)", "url": "https://ssd.jpl.nasa.gov/horizons/"},
        {"label": "LunaNav analytic cross-check (Meeus)", "url": None},
    ]
    return dataset


def _terrain(settings, sites_by_id: dict[str, dict], problems: list[str]) -> Dataset:
    path = Path(settings.datasets.get("site_terrain", ROOT / "data" / "reference" / "site_terrain.json"))
    payload, error = _read(path)
    dataset = Dataset("site_terrain", "LOLA terrain inventory (Phase 2 Task 3)", "terrain", _rel(path))
    if error or payload is None:
        dataset.available = False
        dataset.unavailable_reason = error
        problems.append(str(error))
        return dataset

    dataset.schema = payload.get("schema")
    sites = payload.get("sites", {})
    for site_id, entry in sites.items():
        catalogue_site = sites_by_id.get(site_id)
        if catalogue_site is None:
            problems.append(f"site_terrain: unknown site {site_id!r}")
        elif not (
            _finite(entry.get("latitude_deg")) and _finite(entry.get("longitude_deg"))
            and abs(entry["latitude_deg"] - catalogue_site["latitude_deg"]) <= COORD_TOLERANCE_DEG
            and abs(entry["longitude_deg"] - catalogue_site["longitude_deg"]) <= COORD_TOLERANCE_DEG
        ):
            problems.append(f"site_terrain: {site_id} coordinates disagree with the catalogue")
        dem = entry.get("dem", {})
        if dem.get("pixel_m") not in (None, 5.0):
            problems.append(f"site_terrain: {site_id} pixel size {dem.get('pixel_m')} m")
        if not (_finite(dem.get("bytes")) and dem["bytes"] > 0):
            problems.append(f"site_terrain: {site_id} DEM file size not recorded")
        if not (isinstance(dem.get("sha256"), str) and len(dem["sha256"]) == 64):
            problems.append(f"site_terrain: {site_id} DEM checksum not recorded")
        if "1737400" not in str(dem.get("crs_wkt", "")):
            problems.append(f"site_terrain: {site_id} DEM CRS is not the 1737.4 km sphere frame")
        terrain = entry.get("terrain", {})
        if not (_finite(terrain.get("max_obstruction_deg")) and 0.0 <= terrain["max_obstruction_deg"] < 90.0):
            problems.append(f"site_terrain: {site_id} obstruction angle is not physical")

    dataset.records = len(sites)
    dataset.details = {
        "sites": sorted(sites),
        "generated_utc": payload.get("generated_utc"),
        "limitations": payload.get("limitations", {}),
    }
    dataset.sources = payload.get("sources", [])
    return dataset


def _reference(dataset_id: str, label: str, path: Path, kind: str, problems: list[str]) -> Dataset:
    payload, error = _read(path)
    dataset = Dataset(dataset_id, label, kind, _rel(path))
    if error or payload is None:
        dataset.available = False
        dataset.unavailable_reason = error
        problems.append(str(error))
        return dataset
    dataset.schema = payload.get("schema") or payload.get("dataset")
    dataset.records = _count(payload)
    dataset.details = {"generated_utc": payload.get("generated_utc")}
    dataset.sources = [{"label": str(payload.get("source", "")), "url": None}]
    return dataset


def _optional_directory(dataset_id: str, label: str, path: Path, reason: str,
                        schema: str) -> Dataset:
    files = sorted(path.glob("*.json")) if path.exists() else []
    dataset = Dataset(dataset_id, label, "observations", _rel(path), schema=schema)
    if not files:
        dataset.available = False
        dataset.unavailable_reason = reason
        dataset.records = 0
        dataset.details = {"files": []}
        return dataset
    dataset.records = len(files)
    dataset.details = {"files": [f.name for f in files]}
    return dataset


def _cache(settings) -> Dataset:
    cache_dir = Path(settings.datasets["cache_dir"])
    dataset = Dataset("cache", "Astronomical and imagery response cache", "cache", _rel(cache_dir))
    horizons = sorted((cache_dir / "horizons").glob("*.json"))
    trek_files = [p for p in (cache_dir / "trek").rglob("*") if p.suffix in (".png", ".jpg")]
    dataset.records = len(horizons)
    dataset.details = {
        "horizons_months": [p.stem for p in horizons],
        "horizons_bytes": sum(p.stat().st_size for p in horizons),
        "trek_tiles": len(trek_files),
        "trek_bytes": sum(p.stat().st_size for p in trek_files),
        "policy": (
            "Horizons monthly sub-point tables are cached per month and reused, so a repeated "
            "scenario does not re-request the same days; Moon Trek tiles are cached per tile. "
            "Neither cache is committed, and a cached file is never extended with invented values."
        ),
    }
    return dataset


# -------------------------------------------------------------- catalogue --


def build_catalogue(*, use_cache: bool = False) -> dict:
    """Read every dataset, cross-check them and return the catalogue payload."""
    global _CACHED
    if use_cache and _CACHED is not None:
        return _CACHED

    settings = get_settings()
    problems: list[str] = []

    sites, sites_by_id = _sites(settings, problems)
    series = _series(settings, sites_by_id, problems)
    terrain = _terrain(settings, sites_by_id, problems)
    elevations = _reference("site_elevations", "LOLA 5 m/pix elevation sampling evidence",
                            Path(settings.datasets["site_elevations"]), "reference", problems)
    psrs = _reference("psr_catalogue", "LROC/LOLA PSR boundaries (> 5 km2)",
                      Path(settings.datasets["psr_catalogue"]), "reference", problems)
    craters = _reference("craters", "IAU Gazetteer crater centres",
                         Path(settings.datasets["craters"]), "reference", problems)
    ephemeris = _optional_directory(
        "ephemeris", "Tabulated Horizons ephemeris (Scientific Mode)",
        Path(settings.datasets["scientific_ephemeris_dir"]),
        "No tabulated ephemeris files; Scientific Mode uses the live Horizons provider instead.",
        "lunanav.ephemeris_table",
    )
    masks = _optional_directory(
        "horizon_masks", "LOLA horizon masks (Phase 2 Task 6)",
        Path(settings.datasets["scientific_horizon_dir"]),
        "No horizon masks yet (Phase 2 Task 6); Scientific Mode reports terrain unavailable.",
        "lunanav.horizon_mask",
    )
    cache = _cache(settings)

    declared = str(settings.raw["coordinates"]["longitude_convention"])
    if "east" not in declared.lower() or "180" not in declared:
        problems.append(f"config coordinates.longitude_convention {declared!r} is not east-positive [-180, 180)")
    if "east-positive" not in str(settings.raw["coordinates"]["longitude_convention"]).lower():
        problems.append("config longitude convention must state east-positive")

    payload = {
        "schema": SCHEMA,
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "conventions": {
            "longitude": LONGITUDE_CONVENTION,
            "units": dict(UNITS),
            "time": "UTC, ISO-8601 with Z; naive timestamps are rejected",
            "radius": "1737.4 km IAU mean sphere (no lunar geoid exists)",
        },
        "datasets": [d.as_dict() for d in
                     (sites, series, terrain, elevations, psrs, craters, ephemeris, masks, cache)],
        "problems": problems,
    }
    _CACHED = payload
    return payload


_CACHED: dict | None = None


def reset_cache() -> None:
    global _CACHED
    _CACHED = None
