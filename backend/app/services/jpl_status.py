"""Live reachability check for the NASA/JPL services LunaNav uses."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from app.core.http import HttpError
from app.core.settings import get_settings
from app.core.timeutil import to_iso
from app.models.schemas import Mode
from app.providers.horizons_format import build_query, parse_observer_csv
from app.providers.registry import get_bundle

from .imagery import get_imagery

_CACHE: dict = {"at": 0.0, "value": None}
TTL_S = 30.0


def _service(name: str, url: str, check) -> dict:
    t0 = time.perf_counter()
    try:
        ok, message = check()
    except HttpError as e:
        ok, message = False, f"Not reachable: {e}"
    except Exception as e:  # noqa: BLE001 - status must never crash
        ok, message = False, f"Unexpected response: {e}"
    return {"service": name, "url": url, "reachable": ok, "message": message,
            "latency_ms": round((time.perf_counter() - t0) * 1000)}


def jpl_status(force: bool = False) -> dict:
    now = time.time()
    if not force and _CACHE["value"] and now - _CACHE["at"] < TTL_S:
        return _CACHE["value"]
    s = get_settings()
    eph = get_bundle(Mode.jpl).ephemeris
    fetch = getattr(eph, "_fetch")

    def horizons():
        url = build_query("2027-01-01 00:00", "2027-01-01 01:00", "1 h", s.jpl.horizons_api_url)
        res = fetch(url, min(s.jpl.horizons_timeout_s, 20))
        if res.status != 200:
            return False, f"HTTP {res.status}"
        parse_observer_csv(res.body.decode("utf-8", "replace"))
        return True, "Horizons answered with a valid ephemeris table."

    def trek():
        res = get_imagery().probe()
        return (res.status == 200, "Moon Trek served a tile." if res.status == 200 else f"HTTP {res.status}")

    value = {
        "checked_utc": to_iso(datetime.now(timezone.utc)),
        "horizons": _service("JPL Horizons", s.jpl.horizons_api_url, horizons),
        "trek": _service("NASA/JPL Moon Trek", s.jpl.trek_tiles_url, trek),
        "horizons_cache": eph.cache_summary() if hasattr(eph, "cache_summary") else None,
    }
    _CACHE.update(at=now, value=value)
    return value
