"""Phase 2 Task 6 limit fix: the wide 80 m DEM that carries the masks to 150 km."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "data" / "reference" / "wide_dem.json"
SCRIPT = ROOT / "backend" / "scripts" / "inspect_wide_terrain.py"
TERRAIN = json.loads((ROOT / "data" / "reference" / "site_terrain.json").read_text())
CONFIG = json.loads((ROOT / "config" / "lunanav.config.json").read_text())
CANDIDATES = CONFIG["mission"]["candidate_sites"]


@pytest.fixture(scope="module")
def reference():
    return json.loads(REFERENCE.read_text())


def test_the_wide_dem_covers_the_far_tier(reference):
    assert reference["schema"] == "lunanav.wide_terrain.v1"
    dem = reference["dem"]
    assert dem["file"] == "LDEM_80S_80MPP_ADJ.TIF"
    assert dem["pixel_m"] == 80.0
    assert dem["sha256"] and len(dem["sha256"]) == 64
    assert reference["far_range_m"] == 150_000.0
    # 150 km from every candidate must lie inside the raster.
    radius_km = reference["far_range_m"] / 1000.0
    assert reference["source"]["coverage"]
    for site in reference["sites"].values():
        for value in site["xy_km"]:
            assert abs(value) + radius_km <= dem["extent_km"][0] / 2.0


def test_every_candidate_has_a_height_sample(reference):
    assert set(reference["sites"]) == set(CANDIDATES)
    for site_id, sample in reference["sites"].items():
        near = TERRAIN["sites"][site_id]["site_pixel"]["elevation_m"]
        assert sample["near_elevation_m"] == near
        assert sample["wide_elevation_m"] == pytest.approx(
            sample["near_elevation_m"] + sample["difference_m"], abs=1e-6)
        assert abs(sample["difference_m"]) < 250.0
    assert "1737.4" in reference["height"]["convention"]
    assert reference["limitations"]


def test_the_reference_verifies_offline_or_says_why_it_cannot(capsys):
    spec = importlib.util.spec_from_file_location("inspect_wide_terrain", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not (module.CACHE / module.FILE).exists():
        pytest.skip("wide LOLA DEM cache is not present")
    assert module.main(["--verify-only"]) == 0
    assert "verified" in capsys.readouterr().out
