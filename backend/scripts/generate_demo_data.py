"""Generate SYNTHETIC horizon profiles for the demo sites.

These skylines are invented (seeded random harmonics) so that the
terrain-obstruction logic has something non-trivial to work on in Demo Mode.
They are NOT derived from LOLA or any real topography. Replace them with real
masks via scripts/build_horizon_mask.py for Scientific Mode.

Usage (from backend/):  python scripts/generate_demo_data.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SITES = ROOT / "data" / "demo" / "sites.json"
OUT = ROOT / "data" / "demo" / "horizon_masks.json"

# (base elevation, roughness) in degrees — purely illustrative choices so that
# sites differ visibly in the demo. Ridge/peak sites get a low skyline.
STYLE = {
    "shackleton-rim": (0.3, 0.5),
    "connecting-ridge": (0.35, 0.45),
    "peak-near-shackleton": (0.25, 0.4),
    "de-gerlache-rim": (0.9, 0.9),
    "malapert-massif": (0.4, 0.6),
    "mons-mouton": (0.7, 0.8),
}


def profile(site_id: str, step: float = 1.0) -> tuple[list[float], list[float]]:
    seed = int(hashlib.sha256(site_id.encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    az = np.arange(0.0, 360.0, step)
    base, rough = STYLE.get(site_id, (0.8, 0.8))
    el = np.full_like(az, base)
    for k in range(1, 9):
        amp = rough * rng.uniform(0.3, 1.0) / k**0.8
        el += amp * np.sin(np.radians(k * az) + rng.uniform(0, 2 * np.pi))
    # one or two "massifs" on the skyline
    for _ in range(rng.integers(1, 3)):
        c, w, h = rng.uniform(0, 360), rng.uniform(10, 35), rng.uniform(1.0, 3.0) * rough + 0.5
        d = np.minimum(np.abs(az - c), 360 - np.abs(az - c))
        el += h * np.exp(-0.5 * (d / w) ** 2)
    el = np.clip(el, -1.2, 6.0)
    return az.round(3).tolist(), el.round(4).tolist()


def main():
    sites = json.loads(SITES.read_text())["sites"]
    out = {
        "dataset": "LunaNav SYNTHETIC horizon profiles",
        "synthetic": True,
        "disclaimer": "Invented skylines for UI and algorithm demonstration. Not real lunar topography.",
        "generator": "backend/scripts/generate_demo_data.py",
        "profiles": {},
    }
    for s in sites:
        az, el = profile(s["id"])
        out["profiles"][s["id"]] = {"azimuth_deg": az, "elevation_deg": el}
    OUT.write_text(json.dumps(out, indent=1))
    print(f"wrote {OUT} ({len(sites)} synthetic profiles)")


if __name__ == "__main__":
    main()
