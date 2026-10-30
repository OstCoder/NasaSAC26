"""Compare the analytic (Meeus) ephemeris with Horizons tables.

Usage (from backend/): python scripts/validate_ephemeris.py
Prints the max/RMS angular difference between sub-points. Expect a few
hundredths of a degree for the Sun and up to ~0.1 deg for Earth (physical
libration + truncation). Differences of degrees indicate a frame or sign issue.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.settings import get_settings  # noqa: E402
from app.core.timeutil import time_grid  # noqa: E402
from app.providers.ephemeris_analytic import AnalyticMeeusEphemeris  # noqa: E402
from app.providers.ephemeris_tabulated import HorizonsTableEphemeris  # noqa: E402


def main():
    s = get_settings()
    tab = HorizonsTableEphemeris(s.datasets["scientific_ephemeris_dir"])
    if not tab.available:
        print("Horizons tables unavailable:", tab.info().unavailable_reason)
        return 1
    start, end = tab.supported_range()
    ana = AnalyticMeeusEphemeris(start, end)
    times = time_grid(start, (end - start).total_seconds() / 3600.0, 60)
    for body in ("sun", "earth"):
        a = ana.body_vectors_km(body, times)
        b = tab.body_vectors_km(body, times)
        cos = np.sum(a * b, 1) / np.linalg.norm(a, axis=1) / np.linalg.norm(b, axis=1)
        ang = np.degrees(np.arccos(np.clip(cos, -1, 1)))
        print(f"{body:5s}: max {ang.max():.4f} deg, rms {np.sqrt(np.mean(ang**2)):.4f} deg "
              f"over {len(times)} samples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
