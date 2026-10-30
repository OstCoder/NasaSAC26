"""NAIF SPICE ephemeris provider (integration point).

Status: implemented but NOT validated in the LunaNav repository, because the
kernels (~100+ MB) are not bundled. It becomes available automatically when
``spiceypy`` is installed and the kernels listed below exist. Until then it
reports itself unavailable; nothing is substituted.

Required kernels in ``data/scientific/spice/``:
    naif0012.tls                 leap seconds
    de440.bsp (or de440s.bsp)    planetary ephemeris
    pck00011.tpc                 planetary constants
    moon_pa_de440_200625.bpc     lunar orientation (PA)
    moon_de440_220930.tf         lunar frames (MOON_ME / MOON_PA)
Kernel names change over time; adjust KERNELS when NAIF publishes new ones.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np

from app.core.errors import DataUnavailableError
from app.core.settings import rel
from app.core.timeutil import to_iso
from app.models.schemas import EffectsIncluded, ProvenanceLevel

from .base import Body, EphemerisProvider, SubPointTable, make_info

KERNELS = [
    "naif0012.tls",
    "de440.bsp",
    "pck00011.tpc",
    "moon_pa_de440_200625.bpc",
    "moon_de440_220930.tf",
]


class SpiceEphemeris(EphemerisProvider):
    id = "spice"

    def __init__(self, kernel_dir: Path, start: datetime, end: datetime, frame: str = "MOON_ME"):
        self.kernel_dir = Path(kernel_dir)
        self.frame = frame
        self._start, self._end = start, end
        self._error = None
        try:
            import spiceypy  # noqa: F401
        except ImportError:
            self._error = "spiceypy is not installed (pip install spiceypy)."
            return
        missing = [k for k in KERNELS if not (self.kernel_dir / k).exists()]
        if missing:
            self._error = f"Missing SPICE kernels in {rel(self.kernel_dir)}: {', '.join(missing)}"
            return
        import spiceypy as sp

        for k in KERNELS:
            sp.furnsh(str(self.kernel_dir / k))

    def info(self):
        return make_info(
            id=self.id,
            kind="ephemeris",
            name=f"NAIF SPICE ({self.frame})",
            provenance=ProvenanceLevel.scientific_sourced,
            source="NASA NAIF SPICE toolkit with DE440 + lunar PA/ME kernels",
            description="Sun and Earth positions in the lunar body-fixed frame via spkpos (LT+S).",
            effects=EffectsIncluded(
                optical_libration=True,
                physical_libration=True,
                observer_parallax=True,
                light_time_correction=True,
            ),
            available=self._error is None,
            unavailable_reason=self._error,
            supported_start_utc=self._start,
            supported_end_utc=self._end,
        )

    def supported_range(self):
        return self._start, self._end

    def sub_points(self, body: Body, times: list[datetime]) -> SubPointTable:
        if self._error:
            raise DataUnavailableError(self._error)
        import spiceypy as sp

        target = {"sun": "SUN", "earth": "EARTH"}[body]
        vecs = []
        for t in times:
            et = sp.str2et(to_iso(t).replace("Z", " UTC"))
            pos, _lt = sp.spkpos(target, et, self.frame, "LT+S", "MOON")
            vecs.append(pos)
        v = np.asarray(vecs)
        r = np.linalg.norm(v, axis=1)
        lat = np.degrees(np.arcsin(v[:, 2] / r))
        lon = np.degrees(np.arctan2(v[:, 1], v[:, 0]))
        return SubPointTable(lat, lon, r)
