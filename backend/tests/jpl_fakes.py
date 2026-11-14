"""Fake JPL services for tests. Values come from the analytic model, so they are
structurally identical to Horizons output but are NOT real Horizons data."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from app.core.coords import topocentric_az_el
from app.core.http import HttpError, HttpResult
from app.core.timeutil import time_grid
from app.providers.ephemeris_analytic import AnalyticMeeusEphemeris

AU = 149_597_870.7
_EPH = AnalyticMeeusEphemeris(datetime(2025, 1, 1, tzinfo=timezone.utc), datetime(2032, 1, 1, tzinfo=timezone.utc))
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def horizons_text(start: datetime, stop: datetime, step_min: float = 30, lon_sign: int = 1) -> str:
    times = time_grid(start, (stop - start).total_seconds() / 3600, step_min)
    e = _EPH.sub_points("earth", times)
    s = _EPH.sub_points("sun", times)
    rows = []
    for i, t in enumerate(times):
        rows.append(
            f" {t.year}-{MON[t.month-1]}-{t.day:02d} {t.hour:02d}:{t.minute:02d}, , ,"
            f" {(lon_sign * e.sub_lon_deg[i]) % 360:.6f}, {e.sub_lat_deg[i]:.6f},"
            f" {(lon_sign * s.sub_lon_deg[i]) % 360:.6f}, {s.sub_lat_deg[i]:.6f},"
            f" {s.distance_km[i] / AU:.10f}, 0.1, {e.distance_km[i] / AU:.12f}, 0.2,"
        )
    return "\n".join([
        "*******************************************************************************",
        " Ephemeris / API_USER  (FAKE, generated for tests)",
        " Date__(UT)__HR:MN, , , ObsSub-LON, ObsSub-LAT, SunSub-LON, SunSub-LAT, r, rdot, delta, deldot,",
        "$$SOE", *rows, "$$EOE", ""])


class FakeHorizons:
    """Callable with the HTTP fetcher signature. Records calls."""

    def __init__(self, lon_sign: int = 1, fail: str | None = None):
        self.lon_sign = lon_sign
        self.fail = fail
        self.calls: list[str] = []

    def __call__(self, url: str, timeout: float) -> HttpResult:
        self.calls.append(url)
        if self.fail == "network":
            raise HttpError("URLError: [Errno 111] Connection refused")
        if self.fail == "http500":
            return HttpResult(500, b"Internal error")
        if self.fail == "api_error":
            return HttpResult(200, b"API ERROR: Cannot interpret date")
        q = parse_qs(urlparse(url).query)
        parse = lambda v: datetime.strptime(v[0].strip("'"), "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)  # noqa: E731
        start, stop = parse(q["START_TIME"]), parse(q["STOP_TIME"])
        return HttpResult(200, horizons_text(start, stop, 30, self.lon_sign).encode())


def _encoded_tile(z: int, row: int, col: int) -> bytes:
    """Test tile whose pixels encode their own position: R = longitude, G = latitude below 80°S."""
    import io

    import numpy as np
    from PIL import Image

    deg = 180 / 2 ** z / 256
    py, px = np.mgrid[0:256, 0:256]
    lat = 90 - (row * 256 + py + 0.5) * deg
    lon = -180 + (col * 256 + px + 0.5) * deg
    r = (lon + 180) / 360 * 255
    g = np.clip((-lat - 80) * 25, 0, 255)
    img = np.dstack([r, g, np.full_like(r, 128)]).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, "PNG")
    return buf.getvalue()


class FakeTrek:
    def __init__(self, fail: str | None = None, missing_cols: set[int] | None = None):
        self.fail = fail
        self.missing_cols = missing_cols or set()
        self.calls: list[str] = []

    def __call__(self, url: str, timeout: float) -> HttpResult:
        self.calls.append(url)
        if self.fail == "network":
            raise HttpError("URLError: timed out")
        parts = url.rsplit("/", 3)
        z, row = int(parts[1]), int(parts[2])
        col, ext = parts[3].split(".")
        if ext != "png":
            return HttpResult(404, b"")
        if int(col) in self.missing_cols:
            return HttpResult(404, b"")
        return HttpResult(200, _encoded_tile(z, row, int(col)), "image/png")


# ------------------------------------- JPL Horizons topocentric observer table --

SITE_HEADER = (
    " Date__(UT)__HR:MN, , ,Azi_(a-app), Elev_(a-app),             delta,     deldot,"
)


def _step_minutes(step: str) -> float:
    value, unit = step.split()
    return float(value) * {"m": 1.0, "h": 60.0, "d": 1440.0}[unit.lower()]


def horizons_site_text(times, body: str, az_deg, el_deg, range_km, center, na_row=None) -> str:
    """Render an OBSERVER table with QUANTITIES='4,20' in Horizons' CSV layout."""
    target = "Sun (10)" if body == "sun" else "Earth (399)"
    rows = []
    for i, t in enumerate(times):
        az = "        n.a." if na_row is not None and i == na_row else f"{az_deg[i]:12.6f}"
        rows.append(
            f" {t:%Y-%b-%d %H:%M},*,i,{az},{el_deg[i]:12.6f},"
            f" {range_km[i] / AU:.11f}, -1.0000000,"
        )
    return "\n".join([
        " API VERSION: 1.3",
        " API SOURCE: NASA/JPL Horizons API",
        "",
        "*******************************************************************************",
        " Ephemeris / API_USER  (FAKE, generated for tests)",
        f" Target body name: {target}",
        " Center-site name: (user defined site below)",
        f" Center geodetic : {center[0]}, {center[1]}, {center[2]}"
        "           {E-lon(deg),Lat(deg),Alt(km)}",
        " Center pole/equ : MEAN_ME (high precision)        {East-longitude positive}",
        SITE_HEADER,
        "$$SOE", *rows, "$$EOE", "",
    ])


class FakeHorizonsSite:
    """Fake topocentric Horizons: analytic geometry, real layout, recorded calls."""

    def __init__(self, fail: str | None = None, na_row: int | None = None):
        self.fail = fail
        self.na_row = na_row
        self.calls: list[str] = []

    def __call__(self, url: str, timeout: float) -> HttpResult:
        self.calls.append(url)
        if self.fail == "network":
            raise HttpError("URLError: [Errno 111] Connection refused")
        if self.fail == "http500":
            return HttpResult(500, b"Internal error")
        if self.fail == "api_error":
            return HttpResult(200, b"API ERROR: one or more query parameter was not recognized")
        q = parse_qs(urlparse(url).query)
        lon, lat, alt = (float(v) for v in q["SITE_COORD"][0].strip("'").split(","))
        body = "sun" if "10" in q["COMMAND"][0] else "earth"
        start = datetime.strptime(q["START_TIME"][0].strip("'"), "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        stop = datetime.strptime(q["STOP_TIME"][0].strip("'"), "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        times = time_grid(start, (stop - start).total_seconds() / 3600.0, _step_minutes(q["STEP_SIZE"][0].strip("'")))
        vec = _EPH.body_vectors_km(body, times)
        az, el = topocentric_az_el(lat, ((lon + 180.0) % 360.0) - 180.0, vec, 1737.4, alt)
        text = horizons_site_text(times, body, az, el, _EPH.sub_points(body, times).distance_km,
                                  (lon, lat, alt), na_row=self.na_row)
        return HttpResult(200, text.encode())
