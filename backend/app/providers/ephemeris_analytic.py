"""Low-precision analytic lunar ephemeris (Meeus, *Astronomical Algorithms*, 2nd ed.).

What it computes
----------------
- Geocentric Moon position: Ch. 47 mean elements with the leading periodic
  terms of Tables 47.A/47.B (truncated series).
- Sun position: Ch. 25 low-accuracy solar coordinates.
- Selenographic sub-Earth and sub-solar points: Ch. 53 *optical* libration
  formulas, with the inclination of the lunar equator I = 1.54242 deg.

What it omits (documented, not hidden)
--------------------------------------
- Physical libration (~0.02-0.04 deg), nutation (cancels to first order),
  light-time and aberration, Earth-Moon barycentre subtleties.
- Truncation error of the series: typically < ~0.05 deg in Moon longitude.

Net accuracy of Sun/Earth elevation seen from the surface is of order
0.05-0.1 deg. That is good enough to explore *trends* (when the Sun skims the
horizon, how Earth bobs with libration) but it is NOT a mission-grade source,
so results are labelled ``analytic_approximate`` and Scientific Mode does not
use this provider unless the config explicitly allows it.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np

from app.core.errors import OutOfSupportedRangeError
from app.core.timeutil import julian_centuries_tt, to_iso
from app.models.schemas import EffectsIncluded, ProvenanceLevel

from .base import Body, EphemerisProvider, SubPointTable, make_info

AU_KM = 149_597_870.7
INCLINATION_LUNAR_EQUATOR_DEG = 1.54242

# Meeus Table 47.A: D, M, M', F, Σl (1e-6 deg), Σr (1e-3 km)
_LR_TERMS = np.array(
    [
        (0, 0, 1, 0, 6288774, -20905355),
        (2, 0, -1, 0, 1274027, -3699111),
        (2, 0, 0, 0, 658314, -2955968),
        (0, 0, 2, 0, 213618, -569925),
        (0, 1, 0, 0, -185116, 48888),
        (0, 0, 0, 2, -114332, -3149),
        (2, 0, -2, 0, 58793, 246158),
        (2, -1, -1, 0, 57066, -152138),
        (2, 0, 1, 0, 53322, -170733),
        (2, -1, 0, 0, 45758, -204586),
        (0, 1, -1, 0, -40923, -129620),
        (1, 0, 0, 0, -34720, 108743),
        (0, 1, 1, 0, -30383, 104755),
        (2, 0, 0, -2, 15327, 10321),
        (0, 0, 1, 2, -12528, 0),
        (0, 0, 1, -2, 10980, 79661),
        (4, 0, -1, 0, 10675, -34782),
        (0, 0, 3, 0, 10034, -23210),
        (4, 0, -2, 0, 8548, -21636),
        (2, 1, -1, 0, -7888, 24208),
        (2, 1, 0, 0, -6766, 30824),
        (1, 0, -1, 0, -5163, -8379),
        (1, 1, 0, 0, 4987, -16675),
        (2, -1, 1, 0, 4036, -12831),
        (2, 0, 2, 0, 3994, -10445),
        (4, 0, 0, 0, 3861, -11650),
        (2, 0, -3, 0, 3665, 14403),
        (0, 1, -2, 0, -2689, -7003),
        (2, 0, -1, 2, -2602, 0),
        (2, -1, -2, 0, 2390, 10056),
        (1, 0, 1, 0, -2348, 6322),
        (2, -2, 0, 0, 2236, -9884),
    ],
    dtype=float,
)

# Meeus Table 47.B: D, M, M', F, Σb (1e-6 deg)
_B_TERMS = np.array(
    [
        (0, 0, 0, 1, 5128122),
        (0, 0, 1, 1, 280602),
        (0, 0, 1, -1, 277693),
        (2, 0, 0, -1, 173237),
        (2, 0, -1, 1, 55413),
        (2, 0, -1, -1, 46271),
        (2, 0, 0, 1, 32573),
        (0, 0, 2, 1, 17198),
        (2, 0, 1, -1, 9266),
        (0, 0, 2, -1, 8822),
        (2, -1, 0, -1, 8216),
        (2, 0, -2, -1, 4324),
        (2, 0, 1, 1, 4200),
        (2, 1, 0, -1, -3359),
        (2, -1, -1, 1, 2463),
        (2, -1, 0, 1, 2211),
        (2, -1, -1, -1, 2065),
        (0, 1, -1, -1, -1870),
        (4, 0, -1, -1, 1828),
        (0, 1, 0, 1, -1794),
    ],
    dtype=float,
)


def _norm(deg):
    return np.mod(deg, 360.0)


def moon_geocentric(T: np.ndarray) -> dict[str, np.ndarray]:
    """Geocentric ecliptic longitude/latitude (deg, mean equinox of date) and distance (km)."""
    Lp = _norm(218.3164477 + 481267.88123421 * T - 0.0015786 * T**2)
    D = _norm(297.8501921 + 445267.1114034 * T - 0.0018819 * T**2)
    M = _norm(357.5291092 + 35999.0502909 * T - 0.0001536 * T**2)
    Mp = _norm(134.9633964 + 477198.8675055 * T + 0.0087414 * T**2)
    F = _norm(93.2720950 + 483202.0175233 * T - 0.0036539 * T**2)
    A1 = _norm(119.75 + 131.849 * T)
    A2 = _norm(53.09 + 479264.290 * T)
    A3 = _norm(313.45 + 481266.484 * T)
    E = 1.0 - 0.002516 * T - 0.0000074 * T**2

    rad = np.radians
    args = np.stack([D, M, Mp, F], axis=-1)  # (N, 4)

    lr_arg = rad(args @ _LR_TERMS[:, :4].T)  # (N, K)
    e_fac = E[:, None] ** np.abs(_LR_TERMS[:, 1])[None, :]
    sum_l = np.sum(_LR_TERMS[:, 4] * e_fac * np.sin(lr_arg), axis=1)
    sum_r = np.sum(_LR_TERMS[:, 5] * e_fac * np.cos(lr_arg), axis=1)

    b_arg = rad(args @ _B_TERMS[:, :4].T)
    e_fac_b = E[:, None] ** np.abs(_B_TERMS[:, 1])[None, :]
    sum_b = np.sum(_B_TERMS[:, 4] * e_fac_b * np.sin(b_arg), axis=1)

    sum_l += 3958 * np.sin(rad(A1)) + 1962 * np.sin(rad(Lp - F)) + 318 * np.sin(rad(A2))
    sum_b += (
        -2235 * np.sin(rad(Lp))
        + 382 * np.sin(rad(A3))
        + 175 * np.sin(rad(A1 - F))
        + 175 * np.sin(rad(A1 + F))
        + 127 * np.sin(rad(Lp - Mp))
        - 115 * np.sin(rad(Lp + Mp))
    )

    return {
        "lon": _norm(Lp + sum_l / 1e6),
        "lat": sum_b / 1e6,
        "dist_km": 385000.56 + sum_r / 1000.0,
        "F": F,
        "Omega": _norm(125.0445479 - 1934.1362891 * T + 0.0020754 * T**2),
    }


def sun_geocentric(T: np.ndarray) -> dict[str, np.ndarray]:
    """Geocentric ecliptic longitude (deg) and distance (km) of the Sun (Meeus Ch. 25)."""
    L0 = _norm(280.46646 + 36000.76983 * T + 0.0003032 * T**2)
    M = _norm(357.52911 + 35999.05029 * T - 0.0001537 * T**2)
    e = 0.016708634 - 0.000042037 * T - 0.0000001267 * T**2
    Mr = np.radians(M)
    C = (
        (1.914602 - 0.004817 * T - 0.000014 * T**2) * np.sin(Mr)
        + (0.019993 - 0.000101 * T) * np.sin(2 * Mr)
        + 0.000289 * np.sin(3 * Mr)
    )
    nu = np.radians(M + C)
    R_au = 1.000001018 * (1 - e**2) / (1 + e * np.cos(nu))
    return {"lon": _norm(L0 + C), "dist_km": R_au * AU_KM}


def optical_libration(lon_deg, lat_deg, Omega_deg, F_deg):
    """Meeus eq. 53.1: selenographic (lon, lat) of the point facing the given direction.

    Inputs are the ecliptic longitude/latitude of the vector *toward the Moon*
    from the body of interest (Earth, or the Sun via heliocentric coordinates).
    Returns the sub-body selenographic longitude (east-positive) and latitude.
    """
    I = np.radians(INCLINATION_LUNAR_EQUATOR_DEG)
    W = np.radians(lon_deg - Omega_deg)
    b = np.radians(lat_deg)
    A = np.degrees(
        np.arctan2(np.sin(W) * np.cos(b) * np.cos(I) - np.sin(b) * np.sin(I), np.cos(W) * np.cos(b))
    )
    l_sub = ((A - F_deg + 180.0) % 360.0) - 180.0
    b_sub = np.degrees(np.arcsin(-np.sin(W) * np.cos(b) * np.sin(I) - np.sin(b) * np.cos(I)))
    return l_sub, b_sub


class AnalyticMeeusEphemeris(EphemerisProvider):
    id = "analytic_meeus"

    def __init__(self, supported_start: datetime, supported_end: datetime):
        self._start = supported_start
        self._end = supported_end

    def info(self):
        return make_info(
            id=self.id,
            kind="ephemeris",
            name="Analytic lunar ephemeris (Meeus, truncated series)",
            provenance=ProvenanceLevel.analytic_approximate,
            source="J. Meeus, Astronomical Algorithms, 2nd ed., Ch. 25, 47, 53",
            description=(
                "Closed-form Sun/Moon positions and optical libration. Real physics, "
                "approximate (~0.05-0.1 deg). Suitable for demonstrations and trend "
                "exploration, not for mission certification."
            ),
            effects=EffectsIncluded(
                optical_libration=True,
                physical_libration=False,
                observer_parallax=True,
                light_time_correction=False,
                notes=[
                    "Physical libration omitted (~0.02-0.04 deg).",
                    "Light-time and aberration omitted.",
                    "Fixed UTC->TT offset of 69.184 s.",
                ],
            ),
            available=True,
            supported_start_utc=self._start,
            supported_end_utc=self._end,
        )

    def supported_range(self):
        return self._start, self._end

    def _check(self, times):
        if times[0] < self._start or times[-1] > self._end:
            raise OutOfSupportedRangeError(
                f"Requested {to_iso(times[0])} to {to_iso(times[-1])} is outside the "
                f"supported window {to_iso(self._start)} to {to_iso(self._end)}.",
                details={"supported_start_utc": to_iso(self._start), "supported_end_utc": to_iso(self._end)},
            )

    def sub_points(self, body: Body, times: list[datetime]) -> SubPointTable:
        self._check(times)
        T = julian_centuries_tt(times)
        moon = moon_geocentric(T)
        if body == "earth":
            l, b = optical_libration(moon["lon"], moon["lat"], moon["Omega"], moon["F"])
            return SubPointTable(b, l, moon["dist_km"])
        if body == "sun":
            sun = sun_geocentric(T)
            ratio = moon["dist_km"] / sun["dist_km"]
            lam_h = sun["lon"] + 180.0 + np.degrees(
                ratio * np.cos(np.radians(moon["lat"])) * np.sin(np.radians(sun["lon"] - moon["lon"]))
            )
            beta_h = ratio * moon["lat"]
            l0, b0 = optical_libration(lam_h, beta_h, moon["Omega"], moon["F"])
            # Moon->Sun distance: Sun vector minus Moon vector (ecliptic, km)
            def vec(lon, lat, r):
                lo, la = np.radians(lon), np.radians(lat)
                return np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], -1) * r[:, None]

            d = np.linalg.norm(
                vec(sun["lon"], np.zeros_like(T), sun["dist_km"]) - vec(moon["lon"], moon["lat"], moon["dist_km"]),
                axis=1,
            )
            return SubPointTable(b0, l0, d)
        raise ValueError(f"Unknown body {body!r}")
