"""Download Sun/Earth sub-points on the Moon from JPL Horizons for Scientific Mode.

Usage (from backend/, needs internet):
    python scripts/fetch_horizons.py --start 2027-01-01 --stop 2027-03-01 --step "30 m"

Writes data/scientific/ephemeris/{sun,earth}.json. Horizons limits a single
request to ~90k rows; keep (stop - start) / step below that, or run several
windows and merge.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.providers.horizons_format import build_query, parse_observer_csv  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "scientific" / "ephemeris"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--stop", required=True)
    ap.add_argument("--step", default="30 m")
    ap.add_argument("--lon-sign", type=int, default=1, choices=[1, -1])
    ap.add_argument("--save-raw", action="store_true")
    a = ap.parse_args()

    url = build_query(a.start, a.stop, a.step)
    print("GET", url)
    with urllib.request.urlopen(url, timeout=120) as r:
        text = r.read().decode()
    if a.save_raw:
        (OUT / "horizons_raw.txt").write_text(text)
    tables = parse_observer_csv(text, lon_sign=a.lon_sign)
    OUT.mkdir(parents=True, exist_ok=True)
    for body, table in tables.items():
        (OUT / f"{body}.json").write_text(json.dumps(table))
        print(f"wrote {OUT / (body + '.json')} ({len(table['times_utc'])} rows)")
    print("Next: python scripts/validate_ephemeris.py  to compare with the analytic model.")


if __name__ == "__main__":
    main()
