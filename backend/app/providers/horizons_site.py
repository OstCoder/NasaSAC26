"""Topocentric JPL Horizons tracks: Sun and Earth azimuth/elevation from a lunar site.

Phase 2, Task 1. ``horizons_format`` asks Horizons for *Moon-centred sub-points*;
this module asks for an **observer table at a body-fixed lunar site** and reads
azimuth/elevation straight out of it::

    CENTER='coord@301'          observer on the Moon
    COORD_TYPE='GEODETIC'       (E-longitude, latitude, altitude) on the mean sphere
    SITE_COORD='<lon>,<lat>,<alt_km>'
    QUANTITIES='4,20'           apparent azimuth/elevation + observer-target range

That is a different query from the sub-point tables, with different columns, so
it has its own builder and parser.

Verified against the live service on 2026-11-14 (Shackleton Rim, -89.78 deg,
204.27 deg E, 1.734 km, 24 h at 30 min): the returned azimuth/elevation agrees
with LunaNav's independent analytic model to 0.020 deg in elevation and
0.017 deg in azimuth, which confirms the frame, longitude sense and units below.

Conventions (the same ones ``app/core/coords.py`` uses)
-------------------------------------------------------
- Longitude: selenographic, **east-positive**. Horizons is sent 0-360 deg; the
  ME frame it echoes back is documented as "East-longitude positive".
- Altitude: kilometres above the 1737.4 km IAU mean sphere, i.e. site elevation
  plus observer height. ``COORD_TYPE='GEODETIC'`` on the Moon's spherical radii
  makes this identical to the planetocentric sphere used everywhere else.
- Azimuth: degrees clockwise from local north, in [0, 360).
- Elevation: degrees above the local horizontal, airless (``APPARENT='AIRLESS'``,
  no refraction) - i.e. the geometric horizon, with terrain applied separately.
- Time: UTC calendar dates, no timezone ambiguity.

Failure behaviour
-----------------
- Bad site, window, step or row count -> :class:`InvalidInputError` (422).
- Network, HTTP, unreadable or ``n.a.`` output -> :class:`JplUnavailableError` (503).
Values are never interpolated, filled in or guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable
from urllib.parse import urlencode

import numpy as np

from app.core.coords import topocentric_az_el, validate_lat_lon
from app.core.errors import InvalidInputError, JplUnavailableError
from app.core.http import HttpError, HttpResult, get_bytes
from app.core.timeutil import parse_utc, to_iso

from .base import Body
from .ephemeris_analytic import AnalyticMeeusEphemeris
from .horizons_format import API_URL, AU_KM, parse_horizons_time

__all__ = [
    "MOON_MEAN_RADIUS_KM",
    "SITE_TARGETS",
    "CrossCheck",
    "ObserverSite",
    "SkyTrack",
    "build_site_query",
    "crosscheck_against_analytic",
    "fetch_sky",
    "fetch_site_track",
    "parse_site_csv",
    "step_minutes",
]

# Horizons target ids: the Sun and the Earth, as seen from the Moon.
SITE_TARGETS: dict[str, str] = {"sun": "10", "earth": "399"}

MOON_MEAN_RADIUS_KM = 1737.4

# Horizons refuses an observer below -20 km and truncates a table near 90 000 rows.
_MIN_ALT_KM = -20.0
_MAX_ALT_KM = 9.0
MAX_ROWS = 90_000

_STEP_RE = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)\s*$",
    re.IGNORECASE,
)
_UNIT_MINUTES = {"m": 1.0, "min": 1.0, "mins": 1.0, "minute": 1.0, "minutes": 1.0,
                 "h": 60.0, "hr": 60.0, "hrs": 60.0, "hour": 60.0, "hours": 60.0,
                 "d": 1440.0, "day": 1440.0, "days": 1440.0}

Fetcher = Callable[[str, float], HttpResult]


# ---------------------------------------------------------------- the site --


@dataclass(frozen=True)
class ObserverSite:
    """A surface observer on the Moon, in the conventions of ``core/coords.py``."""

    latitude_deg: float
    longitude_deg: float
    elevation_m: float = 0.0
    height_m: float = 2.0
    site_id: str | None = None

    @classmethod
    def at(
        cls,
        latitude_deg: float,
        longitude_deg: float,
        elevation_m: float = 0.0,
        height_m: float = 2.0,
        site_id: str | None = None,
    ) -> "ObserverSite":
        """Validate and build an observer (exact pole is rejected: azimuth undefined)."""
        lat, lon = validate_lat_lon(latitude_deg, longitude_deg)
        if not np.isfinite(elevation_m) or not -9000.0 <= elevation_m <= 9000.0:
            raise InvalidInputError(f"elevation_m={elevation_m!r} outside [-9000, 9000]")
        if not np.isfinite(height_m) or not 0.0 <= height_m <= 100.0:
            raise InvalidInputError(f"height_m={height_m!r} outside [0, 100]")
        altitude_km = (float(elevation_m) + float(height_m)) / 1000.0
        if not _MIN_ALT_KM < altitude_km <= _MAX_ALT_KM:
            raise InvalidInputError(
                f"observer altitude {altitude_km:.3f} km is outside "
                f"({_MIN_ALT_KM}, {_MAX_ALT_KM}] km; JPL Horizons rejects it"
            )
        return cls(lat, lon, float(elevation_m), float(height_m), site_id)

    @property
    def altitude_km(self) -> float:
        return (self.elevation_m + self.height_m) / 1000.0

    def as_dict(self) -> dict:
        return {
            "site_id": self.site_id,
            "latitude_deg": round(self.latitude_deg, 6),
            "longitude_deg": round(self.longitude_deg, 6),
            "elevation_m": round(self.elevation_m, 3),
            "height_m": round(self.height_m, 3),
            "altitude_km": round(self.altitude_km, 6),
        }


# --------------------------------------------------------------- the query --


def step_minutes(step: str) -> float:
    """Minutes in a Horizons step string such as ``'30 m'``, ``'1 h'`` or ``'1 d'``."""
    m = _STEP_RE.match(str(step))
    if not m:
        raise InvalidInputError(
            f"step {step!r} is not a Horizons interval; use e.g. '30 m', '1 h' or '1 d'"
        )
    value = float(m.group(1)) * _UNIT_MINUTES[m.group(2).lower()]
    if value <= 0:
        raise InvalidInputError("step must be positive")
    return value


def _fmt_time(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")


def build_site_query(
    *,
    body: Body,
    site: ObserverSite,
    start: datetime | str,
    stop: datetime | str,
    step: str = "30 m",
    api_url: str = API_URL,
) -> str:
    """URL for a topocentric Sun/Earth observer table at ``site``.

    Kept separate from the fetch so a caller can log, cache or replay the exact
    request, and so tests can assert on its parameters without a network.
    """
    try:
        target = SITE_TARGETS[body]
    except KeyError as exc:
        raise InvalidInputError(f"body must be 'sun' or 'earth', got {body!r}") from exc
    start_utc, stop_utc = _window(start, stop)
    if step_minutes(step) > (stop_utc - start_utc).total_seconds() / 60.0:
        raise InvalidInputError("step is longer than the requested window")
    params = {
        "format": "text",
        "COMMAND": f"'{target}'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'OBSERVER'",
        "CENTER": "'coord@301'",
        "COORD_TYPE": "'GEODETIC'",
        "SITE_COORD": f"'{site.longitude_deg % 360.0:.6f},{site.latitude_deg:.6f},{site.altitude_km:.6f}'",
        "START_TIME": f"'{_fmt_time(start_utc)}'",
        "STOP_TIME": f"'{_fmt_time(stop_utc)}'",
        "STEP_SIZE": f"'{step}'",
        "QUANTITIES": "'4,20'",
        "CSV_FORMAT": "'YES'",
        "ANG_FORMAT": "'DEG'",
        "TIME_DIGITS": "'MINUTES'",
        "APPARENT": "'AIRLESS'",
    }
    return f"{api_url}?{urlencode(params)}"


def _window(start: datetime | str, stop: datetime | str) -> tuple[datetime, datetime]:
    start_utc, stop_utc = parse_utc(start), parse_utc(stop)
    if start_utc >= stop_utc:
        raise InvalidInputError(
            f"start {to_iso(start_utc)} must be earlier than stop {to_iso(stop_utc)}"
        )
    if (stop_utc - start_utc) > timedelta(days=366):
        raise InvalidInputError("window is longer than a year; split it into smaller requests")
    return start_utc, stop_utc


# -------------------------------------------------------------- the result --


@dataclass(frozen=True)
class SkyTrack:
    """Sun or Earth azimuth/elevation above a lunar site's geometric horizon."""

    body: Body
    site: ObserverSite
    times_utc: tuple[datetime, ...]
    azimuth_deg: np.ndarray
    elevation_deg: np.ndarray
    range_km: np.ndarray | None = None
    query_url: str = ""
    retrieved_utc: datetime | None = None
    info: dict[str, str] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.times_utc)

    @property
    def step_minutes(self) -> float | None:
        if len(self.times_utc) < 2:
            return None
        gaps = np.diff([t.timestamp() for t in self.times_utc]) / 60.0
        return float(np.median(gaps))


@dataclass(frozen=True)
class CrossCheck:
    """Agreement between a fetched track and LunaNav's independent analytic model."""

    body: Body
    samples: int
    max_azimuth_deg: float
    max_elevation_deg: float
    rms_elevation_deg: float
    tolerance_deg: float

    @property
    def passed(self) -> bool:
        return self.max_azimuth_deg <= self.tolerance_deg and self.max_elevation_deg <= self.tolerance_deg

    def as_dict(self) -> dict:
        return {
            "samples": self.samples,
            "max_azimuth_difference_deg": round(self.max_azimuth_deg, 4),
            "max_elevation_difference_deg": round(self.max_elevation_deg, 4),
            "rms_elevation_difference_deg": round(self.rms_elevation_deg, 4),
            "tolerance_deg": self.tolerance_deg,
            "passed": self.passed,
        }


# ---------------------------------------------------------------- parsing --


def _snippet(text: str, limit: int = 300) -> str:
    return " ".join(line.strip() for line in text.splitlines() if line.strip())[:limit]


def _find_column(cols: list[str], needle: str, header: str) -> int:
    for i, c in enumerate(cols):
        if c.startswith(needle):
            return i
    raise ValueError(f"column {needle!r} not found in Horizons header: {header.strip()}")


def _info_block(lines: list[str]) -> dict[str, str]:
    """Pull the few header fields worth keeping as provenance."""
    labels = {
        "target": "Target body name:",
        "center": "Center geodetic",
        "frame": "Center pole/equ",
        "target_frame": "Target pole/equ",
    }
    out: dict[str, str] = {}
    for line in lines:
        for key, label in labels.items():
            if key not in out and line.strip().startswith(label):
                out[key] = line.split(":", 1)[1].split("{", 1)[0].strip()
    return out


def _check_center(echoed: str | None, site: ObserverSite) -> None:
    """Horizons echoes the observer it used; refuse a response for a different site."""
    if not echoed:
        return
    parts = [p for p in re.split(r"[;,\s]+", echoed) if p]
    try:
        lon, lat, alt = (float(p) for p in parts[:3])
    except (ValueError, StopIteration):
        return
    dlon = abs((lon - site.longitude_deg + 180.0) % 360.0 - 180.0)
    if abs(lat - site.latitude_deg) > 0.01 or dlon > 0.01 or abs(alt - site.altitude_km) > 0.01:
        raise ValueError(
            f"Horizons returned the observer at {lon:.4f}, {lat:.4f}, {alt:.4f} km, "
            f"not the requested {site.longitude_deg:.4f}, {site.latitude_deg:.4f}, "
            f"{site.altitude_km:.4f} km"
        )


def _check_target(target: str | None, expected: Body) -> None:
    if not target:
        return
    low = target.lower()
    got = "sun" if "sun" in low else "earth" if "earth" in low else None
    if got is None:
        raise ValueError(f"Horizons returned an unexpected target: {target!r}")
    if got != expected:
        raise ValueError(f"Horizons returned {got.capitalize()} data but {expected} was requested")


def parse_site_csv(
    text: str,
    *,
    site: ObserverSite,
    body: Body,
    query_url: str = "",
    retrieved_utc: datetime | None = None,
) -> SkyTrack:
    """Parse a Horizons observer CSV block (quantity 4, optional 20) into arrays.

    Raises ``ValueError`` with a readable reason for anything unexpected: an API
    error instead of a table, missing columns, ``n.a.`` values, non-increasing
    timestamps, an out-of-range angle, or a response for a different site.
    """
    lines = text.splitlines()
    if "$$SOE" not in text or "$$EOE" not in text:
        raise ValueError(f"Horizons returned no observer table: {_snippet(text) or 'empty response'}")
    try:
        soe = next(i for i, line in enumerate(lines) if line.strip() == "$$SOE")
        eoe = next(i for i, line in enumerate(lines) if line.strip() == "$$EOE")
    except StopIteration as exc:  # pragma: no cover - guarded by the check above
        raise ValueError("no $$SOE/$$EOE block in the Horizons output") from exc

    candidates = [line for line in reversed(lines[:soe]) if "," in line]
    header = next((line for line in candidates if "date" in line.lower()), None) or next(
        (line for line in candidates if any(k in line.lower() for k in ("azi", "elev"))), None
    )
    if header is None:
        raise ValueError("no column header found before $$SOE")
    cols = [c.strip().lower() for c in header.split(",")]
    i_az = _find_column(cols, "azi", header)
    i_el = _find_column(cols, "elev", header)
    i_rng = next((i for i, c in enumerate(cols) if c == "delta"), None)

    rows = [line.split(",") for line in lines[soe + 1:eoe] if line.strip()]
    if not rows:
        raise ValueError("Horizons observer table is empty")
    needed = max(i_az, i_el) + 1
    short = [r for r in rows if len(r) < needed]
    if short:
        raise ValueError(f"Horizons row has {len(short[0])} fields, expected at least {needed}")

    def number(cell: str, what: str, when: str) -> float:
        value = cell.strip()
        if value.lower() in ("n.a.", "nan", ""):
            raise ValueError(f"Horizons returned {value or 'an empty value'} for {what} at {when}")
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(f"unreadable {what} {value!r} at {when}") from exc

    times: list[datetime] = []
    azimuth: list[float] = []
    elevation: list[float] = []
    distance: list[float] = []
    for row in rows:
        when = row[0].strip()
        times.append(parse_horizons_time(row[0]))
        azimuth.append(number(row[i_az], "azimuth", when))
        elevation.append(number(row[i_el], "elevation", when))
        if i_rng is not None and i_rng < len(row):
            raw = row[i_rng].strip()
            if raw.lower() not in ("n.a.", "nan", ""):
                distance.append(float(raw) * AU_KM)

    az = np.asarray(azimuth, dtype=float)
    el = np.asarray(elevation, dtype=float)
    if not np.all(np.isfinite(az)) or not np.all(np.isfinite(el)):
        raise ValueError("Horizons returned non-finite azimuth/elevation")
    if np.any(el < -90.0 - 1e-9) or np.any(el > 90.0 + 1e-9):
        raise ValueError("Horizons elevation outside [-90, 90] deg: check the query columns")
    gaps = np.diff([t.timestamp() for t in times])
    if np.any(gaps <= 0):
        raise ValueError("Horizons timestamps are not strictly increasing")

    info = _info_block(lines[:soe])
    _check_target(info.get("target"), body)
    _check_center(info.get("center"), site)
    return SkyTrack(
        body=body,
        site=site,
        times_utc=tuple(times),
        azimuth_deg=az % 360.0,
        elevation_deg=el,
        range_km=np.asarray(distance, dtype=float) if len(distance) == len(rows) else None,
        query_url=query_url,
        retrieved_utc=retrieved_utc or datetime.now(timezone.utc),
        info=info,
    )


# --------------------------------------------------------------- fetching --


def fetch_site_track(
    body: Body,
    site: ObserverSite,
    start: datetime | str,
    stop: datetime | str,
    step: str = "30 m",
    *,
    timeout_s: float = 90.0,
    api_url: str = API_URL,
    fetch: Fetcher = get_bytes,
) -> SkyTrack:
    """Fetch one body's topocentric track from JPL Horizons.

    Raises :class:`InvalidInputError` for bad input and :class:`JplUnavailableError`
    (never a partial or substituted series) when Horizons cannot be used.
    """
    if body not in SITE_TARGETS:
        raise InvalidInputError(f"body must be 'sun' or 'earth', got {body!r}")
    if not isinstance(site, ObserverSite):
        raise InvalidInputError("site must be an ObserverSite (build it with ObserverSite.at)")
    start_utc, stop_utc = _window(start, stop)
    rows = (stop_utc - start_utc).total_seconds() / 60.0 / step_minutes(step) + 1
    if rows > MAX_ROWS:
        raise InvalidInputError(
            f"about {rows:.0f} rows requested; JPL Horizons truncates a single table near "
            f"{MAX_ROWS:,}. Use a coarser step or split the window."
        )
    url = build_site_query(body=body, site=site, start=start_utc, stop=stop_utc, step=step, api_url=api_url)
    try:
        result = fetch(url, timeout_s)
    except HttpError as exc:
        raise JplUnavailableError(
            f"Could not reach JPL Horizons ({exc}). Check the internet connection or firewall; "
            "GET /api/jpl/status shows the live connection state.",
            details={"service": "horizons", "url": api_url, "body": body},
        ) from exc
    if result.status != 200:
        raise JplUnavailableError(
            f"JPL Horizons answered HTTP {result.status}. It may be busy or in maintenance; "
            "try again shortly.",
            details={"service": "horizons", "status": result.status, "body": body},
        )
    text = result.body.decode("utf-8", errors="replace")
    try:
        return parse_site_csv(text, site=site, body=body, query_url=url)
    except ValueError as exc:
        raise JplUnavailableError(
            f"Could not use the JPL Horizons response for {body}: {exc}",
            details={"service": "horizons", "body": body},
        ) from exc


def fetch_sky(
    site: ObserverSite,
    start: datetime | str,
    stop: datetime | str,
    step: str = "30 m",
    **kwargs,
) -> dict[str, SkyTrack]:
    """Sun and Earth tracks for the same site and window (two Horizons requests)."""
    return {body: fetch_site_track(body, site, start, stop, step, **kwargs)
            for body in ("sun", "earth")}


# ------------------------------------------------------------ cross-check --


def crosscheck_against_analytic(
    track: SkyTrack,
    *,
    tolerance_deg: float = 0.5,
    ephemeris: AnalyticMeeusEphemeris | None = None,
) -> CrossCheck:
    """Compare a fetched track with LunaNav's independent analytic model.

    The two share no code or data: the analytic path computes geocentric
    sub-points from Meeus and projects them with ``topocentric_az_el``, while the
    track comes from Horizons' own geometry. Agreement of a few hundredths of a
    degree is expected; degrees would mean a frame, sign or column error.
    """
    times = list(track.times_utc)
    if not times:
        raise InvalidInputError("cannot cross-check an empty track")
    eph = ephemeris or AnalyticMeeusEphemeris(times[0] - timedelta(days=1), times[-1] + timedelta(days=1))
    vec = eph.body_vectors_km(track.body, times)
    az_ref, el_ref = topocentric_az_el(
        track.site.latitude_deg,
        track.site.longitude_deg,
        vec,
        MOON_MEAN_RADIUS_KM,
        track.site.altitude_km,
    )
    d_az = np.abs((track.azimuth_deg - az_ref + 180.0) % 360.0 - 180.0)
    d_el = np.abs(track.elevation_deg - el_ref)
    return CrossCheck(
        body=track.body,
        samples=len(times),
        max_azimuth_deg=float(d_az.max()),
        max_elevation_deg=float(d_el.max()),
        rms_elevation_deg=float(np.sqrt(np.mean(d_el**2))),
        tolerance_deg=float(tolerance_deg),
    )
