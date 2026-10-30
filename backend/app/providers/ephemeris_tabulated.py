"""Tabulated ephemeris from JPL Horizons (Scientific Mode).

Expected files (produced by ``scripts/fetch_horizons.py``)::

    data/scientific/ephemeris/sun.json
    data/scientific/ephemeris/earth.json

Each file::

    {
      "body": "sun" | "earth",
      "source": "JPL Horizons API ...",
      "frame_note": "Horizons IAU Moon body-fixed (verify ME vs PA)",
      "generated_utc": "...",
      "times_utc": ["2027-01-01T00:00:00Z", ...],
      "sub_lat_deg": [...], "sub_lon_deg": [...], "distance_km": [...]
    }

Interpolation: linear on unit vectors (renormalised) and distance between
samples. With a 10-60 min table step the interpolation error is far below the
analytic model's error. Requests outside the table raise
OutOfSupportedRangeError; missing files raise DataUnavailableError.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np

from app.core.coords import unit_vector
from app.core.settings import rel
from app.core.errors import DataUnavailableError, OutOfSupportedRangeError
from app.core.timeutil import parse_utc, to_iso
from app.models.schemas import EffectsIncluded, ProvenanceLevel

from .base import Body, EphemerisProvider, SubPointTable, make_info


class HorizonsTableEphemeris(EphemerisProvider):
    id = "horizons_table"

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self._tables: dict[str, dict] = {}
        self._error: str | None = None
        try:
            for body in ("sun", "earth"):
                self._tables[body] = self._load(body)
        except DataUnavailableError as exc:
            self._error = exc.message

    def _load(self, body: str) -> dict:
        path = self.directory / f"{body}.json"
        if not path.exists():
            raise DataUnavailableError(
                f"Horizons table for {body} not found at {rel(path)}. "
                "Run backend/scripts/fetch_horizons.py to generate it.",
                details={"missing_file": rel(path)},
            )
        raw = json.loads(path.read_text())
        times = [parse_utc(t) for t in raw["times_utc"]]
        epoch = np.array([t.timestamp() for t in times])
        if len(epoch) < 2 or np.any(np.diff(epoch) <= 0):
            raise DataUnavailableError(f"{path} must contain >=2 strictly increasing timestamps")
        vec = unit_vector(np.asarray(raw["sub_lat_deg"], float), np.asarray(raw["sub_lon_deg"], float))
        return {
            "epoch": epoch,
            "vec": vec,
            "dist": np.asarray(raw["distance_km"], float),
            "start": times[0],
            "end": times[-1],
            "source": raw.get("source", "JPL Horizons"),
        }

    @property
    def available(self) -> bool:
        return self._error is None

    def supported_range(self):
        if not self.available:
            raise DataUnavailableError(self._error)
        start = max(t["start"] for t in self._tables.values())
        end = min(t["end"] for t in self._tables.values())
        return start, end

    def info(self):
        start = end = None
        if self.available:
            start, end = self.supported_range()
        return make_info(
            id=self.id,
            kind="ephemeris",
            name="JPL Horizons tabulated sub-solar / sub-Earth points",
            provenance=ProvenanceLevel.scientific_sourced,
            source="NASA JPL Horizons System (https://ssd.jpl.nasa.gov/horizons/)",
            description=(
                "Sub-observer (quantity 14) and sub-solar (quantity 15) points on the Moon "
                "with ranges, tabulated by Horizons and interpolated linearly."
            ),
            effects=EffectsIncluded(
                optical_libration=True,
                physical_libration=True,
                observer_parallax=True,
                light_time_correction=True,
                notes=["Inherits Horizons' lunar body-fixed model; confirm ME vs PA frame for your use."],
            ),
            available=self.available,
            unavailable_reason=self._error,
            supported_start_utc=start,
            supported_end_utc=end,
        )

    def sub_points(self, body: Body, times: list[datetime]) -> SubPointTable:
        if not self.available:
            raise DataUnavailableError(self._error)
        tab = self._tables[body]
        if times[0] < tab["start"] or times[-1] > tab["end"]:
            raise OutOfSupportedRangeError(
                f"Requested times exceed the Horizons table for {body} "
                f"({to_iso(tab['start'])} to {to_iso(tab['end'])}).",
                details={"supported_start_utc": to_iso(tab["start"]), "supported_end_utc": to_iso(tab["end"])},
            )
        t = np.array([x.timestamp() for x in times])
        v = np.stack([np.interp(t, tab["epoch"], tab["vec"][:, k]) for k in range(3)], axis=-1)
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        lat = np.degrees(np.arcsin(np.clip(v[:, 2], -1, 1)))
        lon = np.degrees(np.arctan2(v[:, 1], v[:, 0]))
        return SubPointTable(lat, lon, np.interp(t, tab["epoch"], tab["dist"]))
