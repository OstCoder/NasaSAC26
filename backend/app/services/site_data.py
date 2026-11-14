"""Phase 2 Task 6: the data-access layer Phase 3 calculations read from.

Phase 3 needs two things per candidate site and mission window: the Sun/Earth
direction as a function of UTC, and the terrain skyline those directions are
judged against. Both already exist on disk (Task 2 series, Task 3/6 masks), but
until now only scripts read them. This module is the one Python and HTTP entry
point, so a calculation module never has to know a file path or a JSON key.

Guarantees
----------
- One record shape everywhere: the files, this module and ``GET /api/series``
  all use ``{site_id, timestamp_utc, sun:{azimuth_deg,elevation_deg,range_km},
  earth:{...}}``. A record with missing or extra fields raises instead of being
  quietly reshaped.
- Resampling is interpolation, never extrapolation: a request outside the
  stored window raises ``OutOfSupportedRangeError``. Azimuth is interpolated
  circularly (359 -> 1 does not go the long way round).
- Terrain is never applied here. ``apply_mask`` returns the skyline and the
  clearance so a caller can decide what "visible" means; the visibility service
  keeps owning that rule.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from app.core.errors import (
    DataUnavailableError,
    InvalidInputError,
    OutOfSupportedRangeError,
    UnknownSiteError,
)
from app.core.settings import Settings, get_settings
from app.core.timeutil import parse_utc, time_grid, to_iso
from app.models.schemas import ProvenanceLevel
from app.providers.base import HorizonMask
from app.providers.horizons_site import step_minutes as parse_step
from app.services.site_series import BODIES, SCHEMA as SERIES_SCHEMA, series_checks
from app.services.sites import get_site_repository

ACCESS_SCHEMA = "lunanav.series_access.v1"
MASK_SCHEMA = "lunanav.horizon_mask.v1"
READINESS_SCHEMA = "lunanav.phase3_readiness.v1"

RECORD_FIELDS = ("site_id", "timestamp_utc", "sun", "earth")
BODY_FIELDS = ("azimuth_deg", "elevation_deg")
OPTIONAL_BODY_FIELDS = ("range_km",)
FIELDS = (
    "site_id",
    "timestamp_utc",
    "sun.azimuth_deg",
    "sun.elevation_deg",
    "sun.range_km",
    "earth.azimuth_deg",
    "earth.elevation_deg",
    "earth.range_km",
)


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value)


def _index(settings: Settings) -> dict:
    path = Path(settings.datasets["site_series_index"])
    if not path.exists():
        raise DataUnavailableError(f"The Task 2 series index is missing: {path.name}")
    return json.loads(path.read_text())


def _mask_dir(settings: Settings) -> Path:
    return Path(settings.datasets["scientific_horizon_dir"])


# ----------------------------------------------------------------- records --


def check_record(record: dict, site_id: str | None = None) -> None:
    """Refuse a record that is not the one documented shape.

    Called for every record read from disk, so a schema drift shows up at the
    boundary instead of as a ``KeyError`` inside a visibility calculation.
    """
    if not isinstance(record, dict):
        raise DataUnavailableError("series record is not a JSON object")
    missing = [key for key in RECORD_FIELDS if key not in record]
    extra = [key for key in record if key not in RECORD_FIELDS]
    if missing or extra:
        raise DataUnavailableError(
            f"series record fields {sorted(record)} are not {list(RECORD_FIELDS)}"
        )
    if site_id is not None and record["site_id"] != site_id:
        raise DataUnavailableError(
            f"series record describes site {record['site_id']!r}, not {site_id!r}"
        )
    parse_utc(record["timestamp_utc"])
    for body in BODIES:
        block = record[body]
        if not isinstance(block, dict):
            raise DataUnavailableError(f"series record {body} is not an object")
        bad = [key for key in block if key not in BODY_FIELDS + OPTIONAL_BODY_FIELDS]
        if bad:
            raise DataUnavailableError(f"series record {body} has unexpected fields {sorted(bad)}")
        for field in BODY_FIELDS:
            if not _finite(block.get(field)):
                raise DataUnavailableError(
                    f"series record {body}.{field} is {block.get(field)!r} at "
                    f"{record['timestamp_utc']}"
                )
        if block.get("range_km") is not None and not _finite(block["range_km"]):
            raise DataUnavailableError(
                f"series record {body}.range_km is {block['range_km']!r} at {record['timestamp_utc']}"
            )


@dataclass(frozen=True)
class BodySamples:
    azimuth_deg: np.ndarray
    elevation_deg: np.ndarray
    range_km: np.ndarray | None

    def __len__(self) -> int:
        return int(self.azimuth_deg.size)


@dataclass(frozen=True)
class SeriesTable:
    """One site's stored track for one mission window, validated and as arrays."""

    site_id: str
    window: str
    start: datetime
    stop: datetime
    step: str
    times: tuple[datetime, ...]
    sun: BodySamples
    earth: BodySamples
    records: tuple[dict, ...]
    payload: dict

    @property
    def step_minutes(self) -> float:
        return parse_step(self.step)

    def __len__(self) -> int:
        return len(self.times)


def load_series(site_id: str, window: str = "initial",
                settings: Settings | None = None) -> SeriesTable:
    """The committed Sun/Earth track for a site and mission window.

    Raises ``UnknownSiteError`` for an unknown site, ``InvalidInputError`` for an
    unknown window, ``DataUnavailableError`` if the file is missing or malformed.
    """
    settings = settings or get_settings()
    get_site_repository().get(site_id)  # raises UnknownSiteError
    index = _index(settings)
    entry = next((e for e in index.get("sites", []) if e.get("site_id") == site_id), None)
    if entry is None:
        raise DataUnavailableError(f"No Task 2 series is indexed for site {site_id!r}")
    windows = index.get("windows") or {}
    if window not in windows:
        raise InvalidInputError(
            f"window must be one of {sorted(windows)}, got {window!r}"
        )
    name = (entry.get("files") or {}).get(window)
    if not name:
        raise DataUnavailableError(
            f"Site {site_id!r} has no {window!r} series; files present: "
            f"{sorted((entry.get('files') or {}))}"
        )
    path = Path(settings.datasets["site_series_index"]).parent / name
    if not path.exists():
        raise DataUnavailableError(f"Task 2 series file is missing: {name}")
    payload = json.loads(path.read_text())
    if payload.get("schema") != SERIES_SCHEMA:
        raise DataUnavailableError(f"{name}: schema {payload.get('schema')!r}, expected {SERIES_SCHEMA}")
    block = payload.get("site") or {}
    if block.get("site_id") != site_id:
        raise DataUnavailableError(f"{name} describes site {block.get('site_id')!r}")

    records = payload.get("series") or []
    if not records:
        raise DataUnavailableError(f"{name} has no records")
    for record in records:
        check_record(record, site_id)
    times = tuple(parse_utc(record["timestamp_utc"]) for record in records)
    if any(later <= earlier for earlier, later in zip(times, times[1:])):
        raise DataUnavailableError(f"{name} timestamps are not strictly increasing")

    def body(key: str) -> BodySamples:
        az = np.array([record[key]["azimuth_deg"] for record in records], float)
        el = np.array([record[key]["elevation_deg"] for record in records], float)
        ranges = [record[key].get("range_km") for record in records]
        rng = np.array(ranges, float) if all(value is not None for value in ranges) else None
        return BodySamples(az, el, rng)

    window_block = payload.get("window") or {}
    return SeriesTable(
        site_id=site_id,
        window=window,
        start=parse_utc(window_block.get("start_utc", records[0]["timestamp_utc"])),
        stop=parse_utc(window_block.get("stop_utc", records[-1]["timestamp_utc"])),
        step=str((payload.get("request") or {}).get("step", "1 h")),
        times=times,
        sun=body("sun"),
        earth=body("earth"),
        records=tuple(records),
        payload=payload,
    )


def interpolate_circular(hours: np.ndarray, angles_deg: np.ndarray, query_hours: np.ndarray) -> np.ndarray:
    """Circular linear interpolation: 350 deg -> 10 deg passes through 0, not 180."""
    unwrapped = np.degrees(np.unwrap(np.radians(np.asarray(angles_deg, float))))
    return np.mod(np.interp(query_hours, hours, unwrapped), 360.0)


def sample_records(table: SeriesTable, start: str | datetime, stop: str | datetime,
                   step_minutes: float) -> tuple[list[dict], dict]:
    """Interpolate the stored track onto an arbitrary grid inside its window.

    Values are never extrapolated: a start/stop outside the stored window raises
    with the supported range in ``details``. Odds are rounded to the file's own
    precision (6 dp for angles, 3 dp for kilometres).
    """
    start_utc, stop_utc = parse_utc(start), parse_utc(stop)
    if start_utc >= stop_utc:
        raise InvalidInputError("start must be earlier than stop")
    if not (_finite(step_minutes) and step_minutes > 0):
        raise InvalidInputError(f"step_minutes must be positive, got {step_minutes!r}")
    if step_minutes < 1.0:
        raise InvalidInputError("step_minutes finer than 1 minute is not supported")
    if start_utc < table.start or stop_utc > table.stop:
        raise OutOfSupportedRangeError(
            f"Requested {to_iso(start_utc)}..{to_iso(stop_utc)} is outside the stored "
            f"{table.site_id} {table.window} window {to_iso(table.start)}..{to_iso(table.stop)}.",
            details={"site_id": table.site_id, "window": table.window,
                     "supported_start_utc": to_iso(table.start),
                     "supported_stop_utc": to_iso(table.stop)},
        )
    hours = (stop_utc - start_utc).total_seconds() / 3600.0
    times = [when for when in time_grid(start_utc, hours, step_minutes) if when <= stop_utc]
    if not times:
        raise InvalidInputError("the requested grid has no samples")

    base = [when.timestamp() / 3600.0 for when in table.times]
    query = np.array([when.timestamp() / 3600.0 for when in times])
    stored = {when.timestamp() for when in table.times}

    arrays: dict[str, dict[str, np.ndarray | None]] = {}
    for body, samples in (("sun", table.sun), ("earth", table.earth)):
        arrays[body] = {
            "azimuth_deg": interpolate_circular(base, samples.azimuth_deg, query),
            "elevation_deg": np.interp(query, base, samples.elevation_deg),
            "range_km": (np.interp(query, base, samples.range_km)
                         if samples.range_km is not None else None),
        }

    records = []
    for index, when in enumerate(times):
        record = {"site_id": table.site_id, "timestamp_utc": to_iso(when)}
        for body in BODIES:
            values = arrays[body]
            record[body] = {
                "azimuth_deg": round(float(values["azimuth_deg"][index]), 6),
                "elevation_deg": round(float(values["elevation_deg"][index]), 6),
            }
            if values["range_km"] is not None:
                record[body]["range_km"] = round(float(values["range_km"][index]), 3)
        records.append(record)
    meta = {
        "start_utc": to_iso(start_utc),
        "stop_utc": to_iso(stop_utc),
        "step_minutes": float(step_minutes),
        "samples": len(records),
        "interpolated": any(when.timestamp() not in stored for when in times),
    }
    return records, meta


# ------------------------------------------------------------------ terrain --


def mask_path(site_id: str, settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return _mask_dir(settings) / f"{site_id}.json"


def mask_payload(site_id: str, settings: Settings | None = None) -> dict | None:
    """The committed mask document, or ``None`` when there is no mask for the site."""
    path = mask_path(site_id, settings)
    if not path.exists():
        return None
    raw = json.loads(path.read_text())
    if raw.get("schema") != MASK_SCHEMA:
        raise DataUnavailableError(f"{path.name}: schema {raw.get('schema')!r}, expected {MASK_SCHEMA}")
    if raw.get("site_id") != site_id:
        raise DataUnavailableError(f"{path.name} describes site {raw.get('site_id')!r}")
    azimuth = np.asarray(raw.get("azimuth_deg") or [], float)
    elevation = np.asarray(raw.get("elevation_deg") or [], float)
    if azimuth.size != elevation.size or azimuth.size < 2:
        raise DataUnavailableError(f"{path.name}: azimuth/elevation arrays do not match")
    if not np.all(np.isfinite(elevation)) or np.any(np.diff(azimuth) <= 0) \
            or azimuth[0] < 0 or azimuth[-1] >= 360:
        raise DataUnavailableError(f"{path.name}: mask grid is not finite, sorted and inside [0, 360)")
    return raw


def mask_summary(payload: dict) -> dict:
    """The small mask description returned with a series (never the whole skyline)."""
    return {
        "site_id": payload.get("site_id"),
        "source": payload.get("source"),
        "azimuth_step_deg": payload.get("azimuth_step_deg"),
        "max_range_km": round(float(payload.get("max_range_m", 0.0)) / 1000.0, 3),
        "max_obstruction_deg": (payload.get("summary") or {}).get("max_obstruction_deg"),
        "max_obstruction_azimuth_deg": (payload.get("summary") or {}).get("max_obstruction_azimuth_deg"),
        "observer_height_m": payload.get("observer_height_m"),
        "dem": (payload.get("dem") or {}).get("file"),
        "available": True,
    }


def load_mask(site_id: str, settings: Settings | None = None) -> HorizonMask:
    """The terrain skyline as a ``HorizonMask`` the visibility code can consume."""
    payload = mask_payload(site_id, settings)
    if payload is None:
        raise DataUnavailableError(
            f"No LOLA horizon mask for {site_id!r}; run scripts/build_site_horizon_masks.py.",
            details={"site_id": site_id, "directory": str(_mask_dir(settings or get_settings()))},
        )
    return HorizonMask(
        np.asarray(payload["azimuth_deg"], float),
        np.asarray(payload["elevation_deg"], float),
        source=str(payload.get("source", "LOLA horizon mask")),
        provenance=ProvenanceLevel.scientific_sourced,
        metadata={key: value for key, value in payload.items()
                  if key not in ("azimuth_deg", "elevation_deg")},
    )


def apply_mask(records: list[dict], mask: HorizonMask) -> dict[str, dict[str, np.ndarray]]:
    """Skyline and clearance per body — the input Phase 3's visibility rules use.

    ``clearance_deg = elevation_deg - skyline(azimuth)``. Whether a positive
    clearance means "visible" stays the caller's policy decision.
    """
    out: dict[str, dict[str, np.ndarray]] = {}
    for body in BODIES:
        az = np.array([record[body]["azimuth_deg"] for record in records], float)
        el = np.array([record[body]["elevation_deg"] for record in records], float)
        skyline = mask.elevation_at(az)
        out[body] = {
            "azimuth_deg": az,
            "elevation_deg": el,
            "skyline_deg": skyline,
            "clearance_deg": el - skyline,
            "above_skyline": el > skyline,
        }
    return out


# -------------------------------------------------------------------- api ----


def _window_for_range(index: dict, start: str, stop: str) -> str:
    """The mission window that fully contains a requested range."""
    start_utc, stop_utc = parse_utc(start), parse_utc(stop)
    for key, window in (index.get("windows") or {}).items():
        if parse_utc(window["start_utc"]) <= start_utc and stop_utc <= parse_utc(window["stop_utc"]):
            return key
    spans = ", ".join(f"{w['start_utc']}..{w['stop_utc']}" for w in (index.get("windows") or {}).values())
    raise OutOfSupportedRangeError(
        f"{start}..{stop} is not inside a stored mission window ({spans}).",
        details={"supported_windows": list((index.get("windows") or {}).keys())},
    )


def series_response(*, site_id: str, window: str | None = None, start: str | None = None,
                    stop: str | None = None, step_minutes: float = 60.0,
                    settings: Settings | None = None) -> dict:
    """The payload behind ``GET /api/series`` (records in the file's own shape).

    ``window`` may be omitted: a start/stop range selects the mission window that
    contains it, and a bare request returns the first (initial) window.
    """
    settings = settings or get_settings()
    index = _index(settings)
    if window is None:
        keys = list((index.get("windows") or {}).keys())
        if start is not None and stop is not None:
            window = _window_for_range(index, start, stop)
        elif keys:
            window = keys[0]
        else:
            raise DataUnavailableError("the Task 2 series index lists no mission windows")
    table = load_series(site_id, window, settings)
    if (start is None) != (stop is None):
        raise InvalidInputError("give both start and stop, or neither")
    if start is None:
        records = list(table.records)
        request = {
            "start_utc": to_iso(table.start),
            "stop_utc": to_iso(table.stop),
            "step_minutes": table.step_minutes,
            "native_step": table.step,
            "interpolated": False,
            "samples": len(records),
        }
    else:
        records, meta = sample_records(table, start, stop, step_minutes)
        request = {**meta, "native_step": table.step}

    payload = mask_payload(site_id, settings)
    site_block = table.payload.get("site") or {}
    window_block = table.payload.get("window") or {}
    return {
        "schema": ACCESS_SCHEMA,
        "records_schema": SERIES_SCHEMA,
        "site": {
            "site_id": site_id,
            "name": site_block.get("name"),
            "latitude_deg": site_block.get("latitude_deg"),
            "longitude_deg": site_block.get("longitude_deg"),
            "elevation_m": site_block.get("elevation_m"),
            "height_m": site_block.get("height_m"),
            "altitude_km": site_block.get("altitude_km"),
        },
        "window": {
            "key": table.window,
            "label": window_block.get("label"),
            "start_utc": to_iso(table.start),
            "stop_utc": to_iso(table.stop),
        },
        "request": request,
        "mask": mask_summary(payload) if payload else None,
        "provenance": {
            "ephemeris": (table.payload.get("source") or "NASA JPL Horizons"),
            "terrain": (payload or {}).get("source") or "no LOLA horizon mask for this site",
            "time": "UTC, ISO-8601 with Z; positions are apparent and airless",
            "interpolation": "linear on elevation and range, circular on azimuth; no extrapolation",
            "visibility": (
                "Clearance is computed by apply_mask / HorizonCalculator; this payload is "
                "geometry only and never says a body is visible."
            ),
        },
        "fields": list(FIELDS),
        "checks": series_checks(records),
        "series": records,
    }


def build_readiness(settings: Settings | None = None) -> dict:
    """Per-candidate Phase 3 readiness: both windows present and a LOLA skyline."""
    settings = settings or get_settings()
    index = _index(settings)
    repo = get_site_repository()
    sites, missing = [], []
    for site_id in settings.raw["mission"]["candidate_sites"]:
        site = repo.get(site_id)
        entry = next((e for e in index.get("sites", []) if e.get("site_id") == site_id), {})
        problems: list[str] = []
        windows: dict[str, dict] = {}
        for key in ("initial", "alternative"):
            try:
                table = load_series(site_id, key, settings)
            except (DataUnavailableError, UnknownSiteError) as exc:
                problems.append(str(getattr(exc, "message", exc)))
                continue
            windows[key] = {
                "start_utc": to_iso(table.start),
                "stop_utc": to_iso(table.stop),
                "records": len(table),
                "step": table.step,
            }
        if not entry:
            problems.append("no Task 2 series entry")
        payload = mask_payload(site_id, settings)
        if payload is None:
            problems.append(
                "no LOLA horizon mask: terrain obstruction unavailable (run "
                "scripts/build_site_horizon_masks.py)"
            )
        sites.append({
            "site_id": site_id,
            "name": site.name,
            "latitude_deg": site.latitude_deg,
            "longitude_deg": site.longitude_deg,
            "elevation_m": site.elevation_m,
            "windows": windows,
            "mask": mask_summary(payload) if payload else None,
            "ready": not problems,
            "problems": problems,
        })
        if problems:
            missing.append(site_id)
    return {
        "schema": READINESS_SCHEMA,
        "generated_utc": to_iso(datetime.now(timezone.utc)),
        "sites": sites,
        "summary": {
            "sites": len(sites),
            "ready": len(sites) - len(missing),
            "with_mask": sum(1 for site in sites if site["mask"] is not None),
            "missing": missing,
        },
        "notes": [
            "Ready means both mission windows are stored and a LOLA skyline exists.",
            "A ready site still needs terrain applied by the visibility rule before any "
            "Sun/Earth visibility is reported.",
        ],
    }
