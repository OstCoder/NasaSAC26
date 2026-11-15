"""One index of every dataset the backend loads.

This catalogue is about organisation, not acquisition: each dataset gets one
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
MASK_SCHEMA = "lunanav.horizon_mask.v1"
MASK_AZIMUTHS = 360


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


def series_file_problems(payload: dict, site_id: str, window_key: str,
                         expected_window: dict) -> list[str]:
    """A series file must be the file index.json claims it is."""
    problems = []
    if payload.get("schema") != "lunanav.site_series.v1":
        problems.append(f"site_series: {site_id} {window_key} schema {payload.get('schema')!r}")
    if (payload.get("site") or {}).get("site_id") != site_id:
        problems.append(
            f"site_series: {site_id} {window_key} file describes site "
            f"{(payload.get('site') or {}).get('site_id')!r}")
    window = payload.get("window") or {}
    if expected_window and (window.get("start_utc") != expected_window.get("start_utc")
                            or window.get("stop_utc") != expected_window.get("stop_utc")):
        problems.append(
            f"site_series: {site_id} {window_key} window {window.get('start_utc')}.."
            f"{window.get('stop_utc')} does not match index.json "
            f"{expected_window.get('start_utc')}..{expected_window.get('stop_utc')}")
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
    dataset = Dataset("sites", "Landing-site catalogue", "sites", _rel(path))
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
    dataset = Dataset("site_series", "Hourly Sun/Earth series", "observations",
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
            problems.extend(series_file_problems(
                payload, site_id, window, (index.get("windows") or {}).get(window) or {}))
            records = payload.get("series", [])
            total += len(records)
            if not records:
                problems.append(f"site_series: {name} has no records")
                continue
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
    dataset = Dataset("site_terrain", "LOLA terrain inventory", "terrain", _rel(path))
    if error or payload is None:
        dataset.available = False
        dataset.unavailable_reason = error
        problems.append(str(error))
        return dataset

    dataset.schema = payload.get("schema")
    evidence_path = Path(settings.datasets["site_elevations"])
    evidence = json.loads(evidence_path.read_text()).get("samples", {}) if evidence_path.exists() else {}
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
        if dem.get("pixel_m") != 5.0:
            problems.append(f"site_terrain: {site_id} pixel size {dem.get('pixel_m')!r} m (expected 5.0)")
        center_px = (evidence.get(site_id) or {}).get("products", {}).get("surf", {}).get("center_px")
        site_pixel = (entry.get("site_pixel") or {}).get("elevation_m")
        if center_px is not None and not (
            _finite(site_pixel) and abs(site_pixel - center_px) <= ELEVATION_TOLERANCE_M
        ):
            problems.append(
                f"site_terrain: {site_id} DEM pixel elevation {site_pixel!r} disagrees with "
                f"the LOLA sampling evidence {center_px} m")
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
    source = payload.get("source")
    if isinstance(source, dict):
        source = source.get("label") or source.get("product") or source.get("provider")
    dataset.sources = [{"label": str(source), "url": payload.get("url")}] if source else []
    return dataset


def _horizons_reference(settings, sites_by_id: dict[str, dict], problems: list[str]) -> Dataset:
    """The independent Horizons sample the validation compares against."""
    path = Path(settings.datasets["horizons_reference"])
    payload, error = _read(path)
    dataset = Dataset("horizons_reference", "Independent Horizons reference sample",
                      "observations", _rel(path))
    if error or payload is None:
        dataset.available = False
        dataset.unavailable_reason = error
        problems.append(str(error))
        return dataset
    if payload.get("schema") != "lunanav.horizons_reference.v1":
        problems.append(f"horizons_reference: schema {payload.get('schema')!r}")
    rows = 0
    for request in payload.get("requests", []):
        site_id, body = request.get("site_id"), request.get("body")
        if site_id not in sites_by_id:
            problems.append(f"horizons_reference: unknown site {site_id!r}")
        if body not in ("sun", "earth"):
            problems.append(f"horizons_reference: {site_id} body {body!r}")
        for row in request.get("rows", []):
            rows += 1
            if not (_finite(row.get("azimuth_deg")) and _finite(row.get("elevation_deg"))):
                problems.append(
                    f"horizons_reference: {site_id} {row.get('timestamp_utc')} has a non-finite value")
    if payload.get("rows") != rows:
        problems.append(f"horizons_reference: {payload.get('rows')} rows claimed, {rows} on disk")
    dataset.schema = payload.get("schema")
    dataset.records = rows
    dataset.details = {
        "step": payload.get("step"),
        "requests": len(payload.get("requests", [])),
        "start_utc": payload.get("start_utc"),
        "stop_utc": payload.get("stop_utc"),
        "excluded_outside_windows": payload.get("excluded_outside_windows"),
        "generated_utc": payload.get("generated_utc"),
    }
    dataset.sources = [{"label": payload.get("source", "NASA JPL Horizons"),
                        "url": "https://ssd.jpl.nasa.gov/horizons/"}]
    return dataset


def _nasa_validation(settings, problems: list[str]) -> Dataset:
    """The validation report itself, indexed so its status is visible with the data."""
    path = Path(settings.datasets["nasa_validation"])
    payload, error = _read(path)
    dataset = Dataset("nasa_validation", "NASA data validation report", "reference", _rel(path))
    if error or payload is None:
        dataset.available = False
        dataset.unavailable_reason = error
        problems.append(str(error))
        return dataset
    if payload.get("schema") != "lunanav.nasa_validation.v1":
        problems.append(f"nasa_validation: schema {payload.get('schema')!r}")
    summary = payload.get("summary") or {}
    if summary.get("status") != "pass":
        problems.append(
            f"nasa_validation: status {summary.get('status')!r} with {summary.get('failed')} failed check(s)")
    dataset.schema = payload.get("schema")
    dataset.records = summary.get("checks")
    dataset.details = {
        "status": summary.get("status"),
        "passed": summary.get("passed"),
        "failed": summary.get("failed"),
        "records_checked": summary.get("records_checked"),
        "generated_utc": payload.get("generated_utc"),
        "live_check_utc": (payload.get("live") or {}).get("retrieved_utc"),
    }
    dataset.sources = payload.get("sources") or []
    return dataset


def _horizon_masks(settings, problems: list[str]) -> Dataset:
    """The committed masks, checked against both DEM references.

    A directory listing is not evidence: each file must be a 360-point mask for
    a mission candidate, reach the far tier, and carry the wide DEM checksum it
    was built from, so a stale or hand-edited mask is reported instead of served.
    """
    directory = Path(settings.datasets["scientific_horizon_dir"])
    wide_path = Path(settings.datasets["wide_terrain"])
    dataset = Dataset("horizon_masks", "LOLA two-tier horizon masks",
                      "terrain", _rel(directory), schema=MASK_SCHEMA)
    wide, wide_error = _read(wide_path)
    if wide_error or wide is None:
        problems.append(f"horizon_masks: {wide_error}")
    files = sorted(directory.glob("*.json")) if directory.exists() else []
    if not files:
        dataset.available = False
        dataset.records = 0
        dataset.unavailable_reason = (
            "No horizon masks are available, so terrain is reported as unavailable.")
        dataset.details = {"files": [], "wide_dem": {"available": False}}
        return dataset

    candidates = list(settings.raw["mission"]["candidate_sites"])
    sites: dict[str, dict] = {}
    for path in files:
        payload, error = _read(path)
        if error or payload is None:
            problems.append(f"horizon_masks: {path.name}: {error}")
            continue
        site_id = payload.get("site_id")
        if site_id not in candidates:
            problems.append(f"horizon_masks: {path.name} describes unknown site {site_id!r}")
        if payload.get("schema") != MASK_SCHEMA:
            problems.append(f"horizon_masks: {path.name} schema {payload.get('schema')!r}")
        azimuth = payload.get("azimuth_deg") or []
        elevation = payload.get("elevation_deg") or []
        measured = None
        if len(azimuth) != MASK_AZIMUTHS or len(elevation) != MASK_AZIMUTHS:
            problems.append(
                f"horizon_masks: {path.name} has {len(azimuth)} azimuths and {len(elevation)} "
                f"elevations (expected {MASK_AZIMUTHS})")
        elif not all(_finite(value) for value in elevation):
            problems.append(f"horizon_masks: {path.name} has a non-finite elevation")
        else:
            measured = round(max(elevation), 4)
            if not -90.0 < measured < 90.0:
                problems.append(f"horizon_masks: {path.name} maximum {measured} deg is not physical")
            if (payload.get("summary") or {}).get("max_obstruction_deg") != measured:
                problems.append(
                    f"horizon_masks: {path.name} summary disagrees with its elevation array")
        far_range = payload.get("max_range_m")
        if not (_finite(far_range) and far_range >= 100_000.0):
            problems.append(
                f"horizon_masks: {path.name} max_range_m {far_range!r} does not reach the far tier")
        tiers = payload.get("tiers") or {}
        for tier in ("near", "far"):
            if not isinstance(tiers.get(tier), dict):
                problems.append(f"horizon_masks: {path.name} records no {tier} tier")
        if wide:
            recorded = (payload.get("wide_dem") or {}).get("sha256")
            if recorded != wide["dem"]["sha256"]:
                problems.append(
                    f"horizon_masks: {path.name} was built from a different wide DEM than "
                    f"{_rel(wide_path)}")
            elif (payload.get("wide_dem") or {}).get("pixel_m") != wide["dem"]["pixel_m"]:
                problems.append(f"horizon_masks: {path.name} wide DEM pixel size disagrees")
        if not payload.get("limitations"):
            problems.append(f"horizon_masks: {path.name} records no limitations")
        sites[site_id] = {
            "max_obstruction_deg": measured,
            "max_obstruction_azimuth_deg": (payload.get("summary") or {}).get(
                "max_obstruction_azimuth_deg"),
            "max_range_km": round(float(far_range) / 1000.0, 3) if _finite(far_range) else None,
            "near_range_km": round(float((tiers.get("near") or {}).get("max_range_m", 0)) / 1000.0, 3),
            "far_pixel_m": (tiers.get("far") or {}).get("pixel_m"),
        }
    for candidate in candidates:
        if candidate not in sites:
            problems.append(f"horizon_masks: no mask for mission candidate {candidate!r}")

    dataset.records = len(files)
    dataset.details = {
        "files": [path.name for path in files],
        "sites": sites,
        "wide_dem": ({
            "available": True,
            "file": wide["dem"]["file"],
            "pixel_m": wide["dem"]["pixel_m"],
            "sha256": wide["dem"]["sha256"],
            "range_km": round(float(wide.get("far_range_m", 0)) / 1000.0, 3),
        } if wide else {"available": False, "reason": wide_error}),
    }
    dataset.sources = [
        {"label": "NASA PGDA LOLA 5 m/pix site DEMs", "url": "https://pgda.gsfc.nasa.gov/products/78"},
        {"label": "NASA PGDA LOLA 80 m/pix south polar DEM (Barker et al. 2023)",
         "url": "https://pgda.gsfc.nasa.gov/products/90"},
    ]
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
    dataset = Dataset("cache", "Astronomical and imagery response cache", "cache", _rel(cache_dir),
                      available=cache_dir.exists())
    if not cache_dir.exists():
        dataset.unavailable_reason = f"no cache directory at {_rel(cache_dir)} yet"
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
    reference = _horizons_reference(settings, sites_by_id, problems)
    validation = _nasa_validation(settings, problems)
    ephemeris = _optional_directory(
        "ephemeris", "Saved Horizons ephemeris",
        Path(settings.datasets["scientific_ephemeris_dir"]),
        "No saved ephemeris files; the live Horizons provider is used instead.",
        "lunanav.ephemeris_table",
    )
    masks = _horizon_masks(settings, problems)
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
                     (sites, series, terrain, elevations, psrs, craters, reference, validation,
                      ephemeris, masks, cache)],
        "problems": list(dict.fromkeys(problems)),
    }
    _CACHED = payload
    return payload


_CACHED: dict | None = None


def reset_cache() -> None:
    global _CACHED
    _CACHED = None
