"""Build JPL Horizons API queries and parse their CSV observer tables.

We ask Horizons for the Moon (target 301) as seen from the geocentre
(500@399) with quantities:
    14  sub-observer point on the Moon   -> sub-Earth lon/lat
    15  sub-solar point on the Moon      -> sub-solar lon/lat
    19  heliocentric range r of the Moon (AU)  -> Sun-Moon distance
    20  observer range delta (AU)              -> Earth-Moon distance

Longitude sense: Horizons reports lunar longitudes east-positive. If that ever
differs for your query, pass ``lon_sign=-1``; scripts/validate_ephemeris.py
compares against the analytic model and will reveal a sign error immediately
(errors of many degrees instead of hundredths).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urlencode

AU_KM = 149_597_870.7
API_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"


def build_query(start: str, stop: str, step: str = "30 m", api_url: str = API_URL) -> str:
    params = {
        "format": "text",
        "COMMAND": "'301'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'OBSERVER'",
        "CENTER": "'500@399'",
        "START_TIME": f"'{start}'",
        "STOP_TIME": f"'{stop}'",
        "STEP_SIZE": f"'{step}'",
        "QUANTITIES": "'14,15,19,20'",
        "CSV_FORMAT": "'YES'",
        "ANG_FORMAT": "'DEG'",
        "TIME_DIGITS": "'MINUTES'",
    }
    return f"{api_url}?{urlencode(params)}"


_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def _parse_time(s: str) -> datetime:
    m = re.match(r"\s*(\d{4})-([A-Za-z]{3})-(\d{2})\s+(\d{2}):(\d{2})(?::(\d{2}))?", s)
    if not m:
        raise ValueError(f"Unrecognised Horizons timestamp {s!r}")
    y, mon, d, hh, mm, ss = m.groups()
    return datetime(int(y), _MONTHS[mon], int(d), int(hh), int(mm), int(ss or 0), tzinfo=timezone.utc)


def parse_observer_csv(text: str, lon_sign: int = 1) -> dict[str, dict]:
    """Return {'sun': table, 'earth': table} in LunaNav's tabulated-ephemeris format."""
    lines = text.splitlines()
    if "$$SOE" not in text:
        # Horizons reports problems as plain text (e.g. "API ERROR", "No ephemeris for target").
        snippet = " ".join(l.strip() for l in lines if l.strip())[:300]
        raise ValueError(f"Horizons returned no ephemeris table: {snippet or 'empty response'}")
    try:
        soe = next(i for i, l in enumerate(lines) if l.strip() == "$$SOE")
        eoe = next(i for i, l in enumerate(lines) if l.strip() == "$$EOE")
    except StopIteration as exc:
        raise ValueError("No $$SOE/$$EOE block found in Horizons output") from exc
    header = next(l for l in reversed(lines[:soe]) if "Date" in l and "," in l)
    cols = [c.strip().lower() for c in header.split(",")]

    def find(*needles) -> int:
        for i, c in enumerate(cols):
            if all(n in c for n in needles):
                return i
        raise ValueError(f"Column with {needles} not found in header: {header}")

    i_obs_lon, i_obs_lat = find("obs", "lon"), find("obs", "lat")
    # Column names differ between Horizons versions: "SunSub-LON" (new) vs "Solar-lon" (old).
    try:
        i_sun_lon, i_sun_lat = find("sun", "lon"), find("sun", "lat")
    except ValueError:
        i_sun_lon, i_sun_lat = find("sol", "lon"), find("sol", "lat")
    i_r = next(i for i, c in enumerate(cols) if c == "r")
    i_delta = next(i for i, c in enumerate(cols) if c == "delta")

    rows = [l.split(",") for l in lines[soe + 1:eoe] if l.strip()]
    if not rows:
        raise ValueError("Horizons table is empty")
    for r in rows:
        for i in (i_obs_lon, i_obs_lat, i_sun_lon, i_sun_lat, i_r, i_delta):
            if r[i].strip().lower() in ("n.a.", "", "nan"):
                raise ValueError(f"Horizons returned 'n.a.' values at {r[0].strip()}")
    times = [_parse_time(r[0]).strftime("%Y-%m-%dT%H:%M:%SZ") for r in rows]

    def lon(v):
        x = lon_sign * float(v)
        return ((x + 180.0) % 360.0) - 180.0

    common = {"source": "JPL Horizons API (target 301, center 500@399, quantities 14,15,19,20)",
              "frame_note": "Horizons lunar body-fixed model; verify ME vs PA for your application",
              "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "times_utc": times}
    earth = {**common, "body": "earth",
             "sub_lat_deg": [float(r[i_obs_lat]) for r in rows],
             "sub_lon_deg": [lon(r[i_obs_lon]) for r in rows],
             "distance_km": [float(r[i_delta]) * AU_KM for r in rows]}
    sun = {**common, "body": "sun",
           "sub_lat_deg": [float(r[i_sun_lat]) for r in rows],
           "sub_lon_deg": [lon(r[i_sun_lon]) for r in rows],
           "distance_km": [float(r[i_r]) * AU_KM for r in rows]}
    return {"sun": sun, "earth": earth}
