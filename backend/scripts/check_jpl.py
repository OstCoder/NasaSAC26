"""One-command check that this computer can reach NASA/JPL.

Usage (from backend/):  python scripts/check_jpl.py

1. Asks JPL Horizons for one hour of Moon geometry and verifies it parses.
2. Downloads one Moon Trek tile for each imagery layer.
3. Fetches the current month from Horizons through LunaNav's live provider,
   including the cross-check against the independent analytic model.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.errors import LunaNavError  # noqa: E402
from app.core.http import HttpError, get_bytes  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.models.schemas import Mode  # noqa: E402
from app.providers.horizons_format import build_query, parse_observer_csv  # noqa: E402
from app.providers.registry import get_bundle  # noqa: E402
from app.services.imagery import get_imagery  # noqa: E402

OK, FAIL = "  [ok]  ", "  [FAIL]"


def main() -> int:
    s = get_settings()
    failures = 0
    print("JPL Horizons:", s.jpl.horizons_api_url)
    try:
        res = get_bytes(build_query("2027-01-01 00:00", "2027-01-01 01:00", "1 h", s.jpl.horizons_api_url), 30)
        t = parse_observer_csv(res.body.decode("utf-8", "replace"))
        print(OK, f"HTTP {res.status}, {len(t['sun']['times_utc'])} rows, "
                  f"sub-Earth lon {t['earth']['sub_lon_deg'][0]:.3f}°, sub-solar lon {t['sun']['sub_lon_deg'][0]:.3f}°")
    except (HttpError, ValueError) as e:
        failures += 1
        print(FAIL, e)

    print("\nNASA/JPL Moon Trek:", s.jpl.trek_tiles_url)
    im = get_imagery()
    for layer in im.layers.values():
        try:
            tile = im.get_tile(layer, 0, 0, 0)
            print(OK if tile is not None else FAIL, f"{layer.id}: {'tile received' if tile is not None else 'no tile (404)'}")
            failures += tile is None
        except LunaNavError as e:
            failures += 1
            print(FAIL, f"{layer.id}: {e.message}")

    print("\nLunaNav live provider (fetch + cross-check, current month):")
    eph = get_bundle(Mode.jpl).ephemeris
    now = datetime.now(timezone.utc)
    when = min(max(now, s.simulation.supported_start), s.simulation.supported_end)
    try:
        sp = eph.sub_points("sun", [when])
        print(OK, f"sub-solar point {sp.sub_lat_deg[0]:.3f}°, {sp.sub_lon_deg[0]:.3f}° at {when:%Y-%m-%d %H:%M} UTC; "
                  f"cross-check max difference {eph.last_crosscheck_deg or '(from cache)'}")
    except LunaNavError as e:
        failures += 1
        print(FAIL, e.message)

    print("\nAll checks passed. Start the app and choose 'JPL live'." if not failures
          else f"\n{failures} check(s) failed. See docs/JPL_CONNECTION.md for fixes.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
