"""Build two-tier LOLA horizon masks for the mission candidates (Phase 2, Task 6).

Tier 1 uses the 5 m/pixel PGDA site DEM out to the distance where it ends
(6.3-7.7 km) - the resolution the landing site needs. Tier 2 uses the 80 m/pixel
LDEM_80S_80MPP_ADJ wide polar DEM from there to 150 km, so the massifs and
crater walls 8-150 km away are included instead of being unknown.

The committed mask is the per-azimuth maximum of the two tiers: 360 points,
degrees, lunar curvature included, observer 2 m above the sampled ground.

Output: data/scientific/horizon_masks/<site-id>.json (~10 kB each).

Usage (from backend/, needs both cached DEMs and `pip install rasterio`):

    python scripts/build_site_horizon_masks.py
    python scripts/build_site_horizon_masks.py --verify-only   # offline check

The wide DEM is fetched once by `scripts/inspect_wide_terrain.py --download`.
Neither DEM is committed (data/cache/); the masks, the 5 m description and
data/reference/wide_dem.json are.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.errors import LunaNavError  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.core.timeutil import to_iso  # noqa: E402
from app.services.horizon import build_horizon_mask_from_dem  # noqa: E402
from app.services.site_data import MASK_SCHEMA  # noqa: E402
from app.services.terrain_inventory import (  # noqa: E402
    WIDE_DEM_FILE,
    WIDE_DEM_URL,
    WIDE_MAX_RANGE_M,
    WIDE_PIXEL_M,
    read_dem,
    site_xy_m,
)

ROOT = Path(__file__).resolve().parents[2]
TERRAIN = ROOT / "data" / "reference" / "site_terrain.json"
WIDE = ROOT / "data" / "reference" / "wide_dem.json"
NEAR_CACHE = ROOT / "data" / "cache" / "lola_5mpp"
WIDE_CACHE = ROOT / "data" / "cache" / "lola_wide"
DEFAULT_OUT = ROOT / "data" / "scientific" / "horizon_masks"

AZIMUTH_STEP_DEG = 1.0
OBSERVER_HEIGHT_M = 2.0
FAR_RANGE_M = WIDE_MAX_RANGE_M
# The terrain inventory measured the skyline at ground level (0 m eye). A 2 m
# observer sees near-field rims lower - by atan(2 m / distance) - so the near
# tier may be lower, never higher.
INVENTORY_MAX_DROP_DEG = 15.0

LIMITATIONS = [
    "Two tiers: 5 m/pixel to the site DEM edge (6.3-7.7 km), then 80 m/pixel to 150 km. "
    "The coarse far tier can miss a ridge narrower than ~80 m, so it is a lower bound beyond "
    "the near field, not an exact skyline.",
    "5 m/pixel horizontal resolution and ~0.3 m RMS height uncertainty (Barker et al. 2021). "
    "Rocks and lander-scale roughness are not resolved.",
    "Observer is 2 m above the sampled ground, matching the Sun/Earth track. A different lander "
    "height needs a rebuilt mask: near-field angles change by atan(delta_h / distance).",
    "Stereographic scale distortion (<0.2 % poleward of 85 S) is ignored; lunar curvature is "
    "included in both tiers.",
    "A clear skyline is not a landing certification and says nothing about thermal conditions, "
    "surface hazards or power.",
]


def _entry(terrain: dict, site_id: str) -> dict:
    try:
        return terrain["sites"][site_id]
    except KeyError as exc:
        raise SystemExit(f"{site_id!r} has no terrain reference entry") from exc


def _wide_entry(wide: dict, site_id: str) -> dict:
    try:
        return wide["sites"][site_id]
    except KeyError as exc:
        raise SystemExit(f"{site_id!r} is missing from data/reference/wide_dem.json") from exc


def build_mask(site_id: str, entry: dict, near_heights: np.ndarray,
               wide: dict, wide_heights: np.ndarray, out_dir: Path) -> dict:
    near = entry["dem"]
    near_bounds = near["bounds_m"]
    x_m, y_m = site_xy_m(entry["latitude_deg"], entry["longitude_deg"])
    near_radius_m = float(entry["coverage"]["radius_km"]) * 1000.0

    near_mask = build_horizon_mask_from_dem(
        near_heights, near_bounds["left"], near_bounds["top"], float(near["pixel_m"]), x_m, y_m,
        obs_height_m=OBSERVER_HEIGHT_M,
        azimuth_step_deg=AZIMUTH_STEP_DEG,
        max_range_m=near_radius_m,
        source=(f"LOLA 5 m/pix {near['file']} ray-march to {near_radius_m / 1000:.3f} km, "
                f"observer {OBSERVER_HEIGHT_M:.0f} m, lunar curvature included"),
    )
    wide_dem = wide["dem"]
    wide_bounds = wide_dem["bounds_m"]
    offset = float(wide["height"]["offset_m"])
    far_mask = build_horizon_mask_from_dem(
        wide_heights + offset if offset else wide_heights,
        wide_bounds["left"], wide_bounds["top"], float(wide_dem["pixel_m"]), x_m, y_m,
        obs_height_m=OBSERVER_HEIGHT_M,
        azimuth_step_deg=AZIMUTH_STEP_DEG,
        min_range_m=near_radius_m,
        max_range_m=FAR_RANGE_M,
        source=(f"LOLA 80 m/pix {wide_dem['file']} ray-march {near_radius_m / 1000:.3f}-"
                f"{FAR_RANGE_M / 1000:.0f} km, observer {OBSERVER_HEIGHT_M:.0f} m, "
                "lunar curvature included"),
    )
    if not np.allclose(near_mask.azimuth_deg, far_mask.azimuth_deg):
        raise SystemExit("the two tiers used different azimuth grids")

    elevation = np.maximum(near_mask.elevation_deg, far_mask.elevation_deg)
    top = int(np.argmax(elevation))
    document = {
        "schema": MASK_SCHEMA,
        "site_id": site_id,
        "name": entry.get("name"),
        "latitude_deg": entry["latitude_deg"],
        "longitude_deg": entry["longitude_deg"],
        "elevation_m": entry["site_pixel"]["elevation_m"],
        "observer_height_m": OBSERVER_HEIGHT_M,
        "source": ("two-tier LOLA ray-march: 5 m/pix site DEM to its edge, then 80 m/pix "
                   f"LDEM_80S to {FAR_RANGE_M / 1000:.0f} km"),
        "generated_utc": to_iso(datetime.now(timezone.utc)),
        "generator": "backend/scripts/build_site_horizon_masks.py",
        "dem": {
            "file": near["file"],
            "sha256": near["sha256"],
            "pixel_m": near["pixel_m"],
            "bounds_m": near_bounds,
        },
        "wide_dem": {
            "file": wide_dem["file"],
            "sha256": wide_dem["sha256"],
            "pixel_m": wide_dem["pixel_m"],
            "bounds_m": wide_bounds,
            "offset_m": offset,
        },
        "max_range_m": FAR_RANGE_M,
        "azimuth_step_deg": AZIMUTH_STEP_DEG,
        "tiers": {
            "near": {
                "dem": near["file"],
                "pixel_m": near["pixel_m"],
                "min_range_m": 0.0,
                "max_range_m": round(near_radius_m, 3),
                "max_obstruction_deg": round(float(near_mask.elevation_deg.max()), 4),
                "max_obstruction_azimuth_deg": round(
                    float(near_mask.azimuth_deg[int(np.argmax(near_mask.elevation_deg))]), 1),
            },
            "far": {
                "dem": wide_dem["file"],
                "pixel_m": wide_dem["pixel_m"],
                "min_range_m": round(near_radius_m, 3),
                "max_range_m": FAR_RANGE_M,
                "max_obstruction_deg": round(float(far_mask.elevation_deg.max()), 4),
                "max_obstruction_azimuth_deg": round(
                    float(far_mask.azimuth_deg[int(np.argmax(far_mask.elevation_deg))]), 1),
            },
        },
        "inventory": {
            "max_obstruction_deg": entry["terrain"]["max_obstruction_deg"],
            "max_obstruction_azimuth_deg": entry["terrain"]["max_obstruction_azimuth_deg"],
            "observer_height_m": 0.0,
        },
        "wide_site_difference_m": _wide_entry(wide, site_id)["difference_m"],
        "summary": {
            "max_obstruction_deg": round(float(elevation.max()), 4),
            "max_obstruction_azimuth_deg": round(float(near_mask.azimuth_deg[top]), 1),
            "min_obstruction_deg": round(float(elevation.min()), 4),
            "mean_obstruction_deg": round(float(elevation.mean()), 4),
        },
        "azimuth_deg": [float(value) for value in near_mask.azimuth_deg],
        "elevation_deg": [round(float(value), 4) for value in elevation],
        "limitations": LIMITATIONS,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{site_id}.json").write_text(json.dumps(document, indent=1) + "\n")
    return document


def _load_references() -> tuple[dict, dict]:
    terrain = json.loads(TERRAIN.read_text())
    if not WIDE.exists():
        raise SystemExit(
            f"missing {WIDE.name}; run `python scripts/inspect_wide_terrain.py --download` first"
        )
    return terrain, json.loads(WIDE.read_text())


def build(site_ids: list[str] | None = None, out_dir: Path = DEFAULT_OUT) -> list[dict]:
    settings = get_settings()
    terrain, wide = _load_references()
    wanted = site_ids or list(settings.raw["mission"]["candidate_sites"])
    wide_path = WIDE_CACHE / WIDE_DEM_FILE
    if not wide_path.exists():
        raise SystemExit(
            f"missing {wide_path}; run `python scripts/inspect_wide_terrain.py --download` "
            f"to fetch {WIDE_DEM_URL}"
        )
    _, wide_heights = read_dem(wide_path)
    documents = []
    for site_id in wanted:
        entry = _entry(terrain, site_id)
        near_path = NEAR_CACHE / entry["dem"]["file"]
        if not near_path.exists():
            raise SystemExit(
                f"missing {near_path}; fetch the DEMs first with "
                "`python scripts/inspect_site_terrain.py --download`"
            )
        info, near_heights = read_dem(near_path)
        if info["sha256"] != entry["dem"]["sha256"]:
            raise SystemExit(
                f"{near_path.name} checksum {info['sha256']} does not match the terrain reference "
                f"{entry['dem']['sha256']} - refusing to build a mask from a different file"
            )
        document = build_mask(site_id, entry, near_heights, wide, wide_heights, out_dir)
        print(f"{site_id}: {len(document['azimuth_deg'])} azimuths, "
              f"max obstruction {document['summary']['max_obstruction_deg']} deg at "
              f"{document['summary']['max_obstruction_azimuth_deg']} deg, "
              f"range {document['max_range_m'] / 1000:.0f} km "
              f"(near {document['tiers']['near']['max_obstruction_deg']} deg, "
              f"far {document['tiers']['far']['max_obstruction_deg']} deg)")
        documents.append(document)
    return documents


def verify(out_dir: Path = DEFAULT_OUT) -> int:
    """Check the committed masks against both references. Reads files only."""
    terrain, wide = _load_references()
    candidates = list(get_settings().raw["mission"]["candidate_sites"])
    problems: list[str] = []
    files = sorted(out_dir.glob("*.json")) if out_dir.exists() else []
    if {path.stem for path in files} != set(candidates):
        problems.append(
            f"{out_dir.name} holds {sorted(path.stem for path in files)}, "
            f"candidates are {sorted(candidates)}"
        )
    print(f"{'site':22s} {'points':>6s} {'range':>7s} {'near':>7s} {'far':>7s} {'max':>7s}  checks")
    for site_id in candidates:
        path = out_dir / f"{site_id}.json"
        issues: list[str] = []
        if not path.exists():
            problems.append(f"{site_id}: missing mask")
            print(f"{site_id:22s} {'-':>6s} {'-':>7s} {'-':>7s} {'-':>7s} {'-':>7s}  FAILED: missing")
            continue
        document = json.loads(path.read_text())
        entry = _entry(terrain, site_id)
        azimuth = np.asarray(document.get("azimuth_deg") or [], float)
        elevation = np.asarray(document.get("elevation_deg") or [], float)
        if document.get("schema") != MASK_SCHEMA:
            issues.append(f"schema {document.get('schema')!r}")
        if document.get("site_id") != site_id:
            issues.append(f"site_id {document.get('site_id')!r}")
        if azimuth.size != elevation.size or azimuth.size != int(360 / AZIMUTH_STEP_DEG):
            issues.append(f"{azimuth.size} azimuth points")
        if not np.all(np.isfinite(elevation)):
            issues.append("non-finite elevation")
        if np.any(np.diff(azimuth) <= 0) or azimuth[0] != 0.0 or azimuth[-1] >= 360.0:
            issues.append("azimuth grid is not 0..360")
        for key, tol in (("latitude_deg", 1e-6), ("longitude_deg", 1e-6)):
            if abs(float(document.get(key, 1e9)) - float(entry[key])) > tol:
                issues.append(f"{key} disagrees with the terrain reference")
        if abs(float(document.get("elevation_m", 1e9)) - float(entry["site_pixel"]["elevation_m"])) > 0.05:
            issues.append("site elevation disagrees with the terrain reference")
        near = document.get("dem") or {}
        if near.get("file") != entry["dem"]["file"] or near.get("sha256") != entry["dem"]["sha256"]:
            issues.append("near DEM file/checksum disagrees with the terrain reference")
        far = document.get("wide_dem") or {}
        if far.get("file") != wide["dem"]["file"] or far.get("sha256") != wide["dem"]["sha256"]:
            issues.append("wide DEM file/checksum disagrees with wide_dem.json")
        if far.get("pixel_m") != wide["dem"]["pixel_m"]:
            issues.append("wide DEM pixel size disagrees with wide_dem.json")
        if abs(float(document.get("max_range_m", -1)) - FAR_RANGE_M) > 1e-6:
            issues.append(f"max_range_m {document.get('max_range_m')} != {FAR_RANGE_M:.0f}")
        tiers = document.get("tiers") or {}
        near_radius = float(entry["coverage"]["radius_km"]) * 1000.0
        if abs(float((tiers.get("near") or {}).get("max_range_m", -1)) - near_radius) > 1e-6:
            issues.append("near tier range disagrees with the terrain reference")
        if abs(float((tiers.get("far") or {}).get("min_range_m", -1)) - near_radius) > 1e-6:
            issues.append("far tier does not start at the near tier's edge")
        if float((tiers.get("far") or {}).get("max_range_m", -1)) != FAR_RANGE_M:
            issues.append("far tier range is not the wide DEM range")
        inventory = float(entry["terrain"]["max_obstruction_deg"])
        recorded = (document.get("inventory") or {}).get("max_obstruction_deg")
        near_max = float((tiers.get("near") or {}).get("max_obstruction_deg", np.nan))
        far_max = float((tiers.get("far") or {}).get("max_obstruction_deg", np.nan))
        if recorded != inventory:
            issues.append(f"inventory record {recorded!r} != {inventory}")
        if not np.isfinite(near_max) or not (inventory - INVENTORY_MAX_DROP_DEG <= near_max <= inventory + 1e-6):
            issues.append(f"near tier {near_max} deg vs ground-level inventory {inventory} deg")
        if not np.isfinite(far_max):
            issues.append("far tier maximum is not finite")
        measured = float(np.max(elevation)) if elevation.size else None
        if measured is not None:
            if measured < max(near_max, far_max) - 1e-6:
                issues.append("combined mask is below one of its tiers")
            if not -90.0 < measured < 90.0:
                issues.append(f"combined maximum {measured} deg is not physical")
            if document.get("summary", {}).get("max_obstruction_deg") != round(measured, 4):
                issues.append("recorded summary does not match the elevation array")
        if not document.get("limitations"):
            issues.append("no limitations recorded")
        problems.extend(f"{site_id}: {issue}" for issue in issues)
        print(f"{site_id:22s} {azimuth.size:6d} {FAR_RANGE_M / 1000:6.0f}k {near_max:7.2f} "
              f"{far_max:7.2f} {measured if measured is None else round(measured, 2):7.2f}  "
              f"{'ok' if not issues else 'FAILED: ' + '; '.join(issues)}")
    print("all horizon masks verified" if not problems else f"{len(problems)} problem(s) found")
    for problem in problems:
        print(f"  FAILED: {problem}", file=sys.stderr)
    return 0 if not problems else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build two-tier LOLA horizon masks for the mission candidates.")
    ap.add_argument("--site", action="append", help="site id (repeatable; default: candidates)")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--verify-only", action="store_true",
                    help="check the committed masks against both references (offline)")
    args = ap.parse_args(argv)
    if args.verify_only:
        return verify(args.out_dir)
    try:
        documents = build(args.site, args.out_dir)
    except LunaNavError as exc:
        print(f"FAILED: {exc.message}", file=sys.stderr)
        return 1
    print(f"wrote {len(documents)} mask(s) to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
