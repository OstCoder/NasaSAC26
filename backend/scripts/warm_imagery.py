"""Pre-download Moon Trek imagery and Horizons months so a demo works offline.

Usage (from backend/, needs internet):
    python scripts/warm_imagery.py                   # imagery + Jan-Mar 2027 ephemeris
    python scripts/warm_imagery.py --months 2027-01 2027-02
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.settings import get_settings  # noqa: E402
from app.models.schemas import Mode  # noqa: E402
from app.providers.registry import get_bundle  # noqa: E402
from app.services.imagery import get_imagery  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", nargs="*", default=["2027-01", "2027-02", "2027-03"])
    ap.add_argument("--size", type=int, default=get_settings().imagery["south_pole_size_px"])
    a = ap.parse_args()
    im = get_imagery()
    for layer in im.layers:
        t = time.time()
        _, meta = im.south_pole_png(layer, a.size, -80.0)
        print(f"south pole {layer}: zoom {meta['zoom']} ({time.time() - t:.0f} s)")
        t = time.time()
        im.global_jpeg(layer, 2)
        im.global_jpeg(layer, 3)
        print(f"global {layer}: ({time.time() - t:.0f} s)")
    t = time.time()
    im.relief_jpeg("height", 2)
    im.relief_jpeg("normal", 3)
    print(f"relief: ({time.time() - t:.0f} s)")
    eph = get_bundle(Mode.jpl).ephemeris
    for m in a.months:
        y, mo = map(int, m.split("-"))
        eph.sub_points("sun", [datetime(y, mo, 15, tzinfo=timezone.utc)])
        print(f"horizons {m}: cached (cross-check {eph.last_crosscheck_deg or 'from cache'})")


if __name__ == "__main__":
    main()
