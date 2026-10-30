"""Live JPL Horizons ephemeris (JPL and Scientific modes).

On demand, fetches one calendar month of Sun/Earth sub-points on the Moon from
the Horizons API (no key required), caches it under
``data/cache/horizons/YYYY-MM.json``, and serves interpolated values.

Every download is cross-checked against the independent analytic model. If the
two disagree by more than ``horizons_crosscheck_tolerance_deg`` the data is
REJECTED (not used, not cached) with an explanation, because a disagreement of
degrees means a frame, sign or parsing problem, not a real ephemeris effect.
If a sign flip of longitude would fix it, the error says so.

Network or Horizons failures raise JplUnavailableError (HTTP 503 at the API).
Nothing falls back to the analytic model silently.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import numpy as np

from app.core.coords import unit_vector
from app.core.errors import JplUnavailableError, OutOfSupportedRangeError
from app.core.http import HttpError, HttpResult, get_bytes
from app.core.settings import JplSettings, rel
from app.core.timeutil import to_iso
from app.models.schemas import EffectsIncluded, ProvenanceLevel

from .base import Body, EphemerisProvider, SubPointTable, make_info
from .ephemeris_analytic import AnalyticMeeusEphemeris
from .ephemeris_tabulated import interpolate_table, table_from_json
from .horizons_format import build_query, parse_observer_csv

Fetcher = Callable[[str, float], HttpResult]
PAD = timedelta(hours=1)


def _month_start(dt: datetime) -> datetime:
    return datetime(dt.year, dt.month, 1, tzinfo=timezone.utc)


def _next_month(dt: datetime) -> datetime:
    return datetime(dt.year + (dt.month == 12), dt.month % 12 + 1, 1, tzinfo=timezone.utc)


def _max_angle_deg(a: np.ndarray, b: np.ndarray) -> float:
    cos = np.sum(a * b, axis=1)
    return float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))).max())


class HorizonsLiveEphemeris(EphemerisProvider):
    id = "horizons_live"

    def __init__(
        self,
        jpl: JplSettings,
        cache_dir: Path,
        supported_start: datetime,
        supported_end: datetime,
        fetch: Fetcher = get_bytes,
    ):
        self.jpl = jpl
        self.cache_dir = Path(cache_dir) / "horizons"
        self._start, self._end = supported_start, supported_end
        self._fetch = fetch
        self._months: dict[str, dict[str, dict]] = {}
        self._lock = threading.Lock()
        self._crosscheck = AnalyticMeeusEphemeris(supported_start - PAD * 800, supported_end + PAD * 800)
        self.last_error: str | None = None
        self.last_crosscheck_deg: dict[str, float] = {}

    # --------------------------------------------------------------- info --
    def info(self):
        cached = sorted(p.stem for p in self.cache_dir.glob("*.json")) if self.cache_dir.exists() else []
        return make_info(
            id=self.id,
            kind="ephemeris",
            name="JPL Horizons (live)",
            provenance=ProvenanceLevel.scientific_sourced,
            source=f"NASA JPL Horizons API ({self.jpl.horizons_api_url})",
            description=(
                "Sub-Earth and sub-solar points on the Moon fetched on demand from JPL Horizons "
                "(target 301, geocentre, quantities 14/15/19/20), cached by month and cross-checked "
                "against an independent analytic model before use. Requires internet access."
                + (f" Cached months: {', '.join(cached)}." if cached else "")
            ),
            effects=EffectsIncluded(
                optical_libration=True,
                physical_libration=True,
                observer_parallax=True,
                light_time_correction=True,
                notes=["Inherits Horizons' lunar body-fixed model; confirm ME vs PA frame for your use."],
            ),
            available=True,
            unavailable_reason=self.last_error,
            supported_start_utc=self._start,
            supported_end_utc=self._end,
        )

    def supported_range(self):
        return self._start, self._end

    # ------------------------------------------------------------- months --
    def _months_for(self, start: datetime, end: datetime) -> list[datetime]:
        out, m = [], _month_start(start - PAD)
        while m <= end + PAD:
            out.append(m)
            m = _next_month(m)
        return out

    def _cache_path(self, month: datetime) -> Path:
        return self.cache_dir / f"{month:%Y-%m}.json"

    def _load_month(self, month: datetime) -> dict[str, dict]:
        key = f"{month:%Y-%m}"
        if key in self._months:
            return self._months[key]
        path = self._cache_path(month)
        if path.exists():
            raw = json.loads(path.read_text())
        else:
            raw = self._download(month)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(raw))
        tabs = {body: table_from_json(raw[body]) for body in ("sun", "earth")}
        self._months[key] = tabs
        return tabs

    def _download(self, month: datetime) -> dict:
        start = month - PAD
        stop = _next_month(month) + PAD
        url = build_query(start.strftime("%Y-%m-%d %H:%M"), stop.strftime("%Y-%m-%d %H:%M"),
                          self.jpl.horizons_step, self.jpl.horizons_api_url)
        try:
            res = self._fetch(url, self.jpl.horizons_timeout_s)
        except HttpError as e:
            raise JplUnavailableError(
                f"Could not reach JPL Horizons ({e}). Check your internet connection or firewall; "
                "GET /api/jpl/status shows the live connection state.",
                details={"service": "horizons", "url": self.jpl.horizons_api_url},
            ) from e
        if res.status != 200:
            raise JplUnavailableError(
                f"JPL Horizons answered HTTP {res.status}. It may be busy or down; try again shortly.",
                details={"service": "horizons", "status": res.status},
            )
        text = res.body.decode("utf-8", errors="replace")
        try:
            tables = parse_observer_csv(text, lon_sign=self.jpl.horizons_lon_sign)
        except (ValueError, IndexError, StopIteration) as e:
            raise JplUnavailableError(f"Could not read the Horizons response: {e}",
                                      details={"service": "horizons"}) from e
        self._crosscheck_tables(tables)
        tables["fetched_utc"] = to_iso(datetime.now(timezone.utc))
        tables["query_url"] = url
        tables["crosscheck_max_deg"] = dict(self.last_crosscheck_deg)
        return tables

    def _crosscheck_tables(self, tables: dict) -> None:
        """Reject data that disagrees with the independent analytic model."""
        tol = self.jpl.horizons_crosscheck_tolerance_deg
        report = {}
        for body in ("sun", "earth"):
            t = tables[body]
            times = [datetime.fromisoformat(x.replace("Z", "+00:00")) for x in t["times_utc"]]
            ref = self._crosscheck.sub_points(body, times)
            a = unit_vector(ref.sub_lat_deg, ref.sub_lon_deg)
            lat, lon = np.asarray(t["sub_lat_deg"]), np.asarray(t["sub_lon_deg"])
            err = _max_angle_deg(a, unit_vector(lat, lon))
            report[body] = round(err, 4)
            if err > tol:
                flipped = _max_angle_deg(a, unit_vector(lat, -lon))
                hint = (" Flipping the longitude sign would match: set jpl.horizons_lon_sign to "
                        f"{-self.jpl.horizons_lon_sign} in config/lunanav.config.json."
                        if flipped <= tol else " Check the Horizons query and column layout.")
                raise JplUnavailableError(
                    f"Horizons {body} positions disagree with the independent cross-check by "
                    f"{err:.2f}° (tolerance {tol}°), so they were not used.{hint}",
                    details={"service": "horizons", "body": body, "max_difference_deg": round(err, 3)},
                )
        self.last_crosscheck_deg = report

    # ---------------------------------------------------------- interface --
    def sub_points(self, body: Body, times: list[datetime]) -> SubPointTable:
        if times[0] < self._start or times[-1] > self._end:
            raise OutOfSupportedRangeError(
                f"Requested {to_iso(times[0])} to {to_iso(times[-1])} is outside the supported window "
                f"{to_iso(self._start)} to {to_iso(self._end)}.",
                details={"supported_start_utc": to_iso(self._start), "supported_end_utc": to_iso(self._end)},
            )
        with self._lock:
            try:
                months = [self._load_month(m) for m in self._months_for(times[0], times[-1])]
                self.last_error = None
            except JplUnavailableError as e:
                self.last_error = e.message
                raise
        merged = {
            "epoch": np.concatenate([m[body]["epoch"] for m in months]),
            "vec": np.concatenate([m[body]["vec"] for m in months]),
            "dist": np.concatenate([m[body]["dist"] for m in months]),
        }
        order = np.argsort(merged["epoch"], kind="stable")
        epoch = merged["epoch"][order]
        keep = np.concatenate([[True], np.diff(epoch) > 0])
        tab = {k: v[order][keep] for k, v in merged.items()}
        return interpolate_table(tab, times)

    def cache_summary(self) -> dict:
        files = sorted(self.cache_dir.glob("*.json")) if self.cache_dir.exists() else []
        return {"directory": rel(self.cache_dir), "months": [p.stem for p in files]}
