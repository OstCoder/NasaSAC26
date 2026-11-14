"""Phase 4 Task 6: the committed site-DEM previews behind GET /api/terrain-dem.

The endpoint copies committed evidence and validates it; these tests check the
copying and the validation, not the raster (the full 5 m/pix files are not
committed). The numbers themselves were pinned when the previews were
generated from the LOLA cache.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.errors import DataUnavailableError
from app.main import app
from app.core.settings import _resolve, get_settings
from app.services.site_dem import terrain_dem_response
from app.services.sites import get_site_repository

client = TestClient(app)

SITES = ("shackleton-rim", "connecting-ridge", "de-gerlache-rim")


def test_every_candidate_has_a_committed_preview():
    directory = _resolve(get_settings().raw["datasets"]["site_dem_dir"])
    for site_id in SITES:
        path = directory / f"{site_id}.json"
        assert path.exists(), path
        document = json.loads(path.read_text())
        assert document["schema"] == "lunanav.site_dem_preview.v1"
        assert document["source"]["sha256"], document["source"]["file"]


def test_response_copies_the_committed_grid():
    for site_id in SITES:
        report = terrain_dem_response(site_id=site_id)
        committed = json.loads(
            (_resolve(get_settings().raw["datasets"]["site_dem_dir"]) / f"{site_id}.json").read_text())
        assert report["schema"] == "lunanav.terrain_dem.v1"
        assert report["heights_m"] == committed["heights_m"]
        assert report["site_height_m"] == committed["site_height_m"]
        assert report["provenance"] == "scientific_sourced"


def test_grid_shape_cell_and_site_cell_are_sane():
    for site_id in SITES:
        report = terrain_dem_response(site_id=site_id)
        heights = report["heights_m"]
        assert len(heights) == 128 and len(heights[0]) == 128
        assert report["grid"]["cell_m"] == 125.0
        assert report["grid"]["extent_m"]["east_west"] == 16000.0
        # every value finite and in a plausible LOLA range
        flat = [value for row in heights for value in row]
        assert all(-9000 < value < 9000 for value in flat)


def test_site_height_agrees_with_the_sampled_elevation_evidence():
    """The pooled site cell must sit near the exactly-sampled site elevation."""
    evidence = json.loads(Path(get_settings().datasets["site_elevations"]).read_text())
    for site_id in SITES:
        report = terrain_dem_response(site_id=site_id)
        truth = evidence["samples"][site_id]["products"]["surf"]["median"]
        assert abs(report["site_height_m"] - truth) < 20.0


def test_unknown_site_is_404_and_missing_artifact_is_503(tmp_path, monkeypatch):
    settings = get_settings()
    with pytest.raises(Exception):
        terrain_dem_response(site_id="not-a-site")
    empty = tmp_path / "site_dems"
    empty.mkdir()
    monkeypatch.setitem(settings.raw["datasets"], "site_dem_dir", str(empty))
    with pytest.raises(DataUnavailableError) as excinfo:
        terrain_dem_response(site_id="shackleton-rim")
    assert excinfo.value.details["code"] == "DEM_UNAVAILABLE"


def test_tampered_schema_is_rejected(tmp_path, monkeypatch):
    settings = get_settings()
    directory = tmp_path / "site_dems"
    directory.mkdir()
    document = json.loads(
        (_resolve(settings.raw["datasets"]["site_dem_dir"]) / "shackleton-rim.json").read_text())
    document["schema"] = "lunanav.something_else.v1"
    (directory / "shackleton-rim.json").write_text(json.dumps(document))
    monkeypatch.setitem(settings.raw["datasets"], "site_dem_dir", str(directory))
    with pytest.raises(DataUnavailableError):
        terrain_dem_response(site_id="shackleton-rim")


def test_api_contract(client):
    for site_id in SITES:
        response = client.get(f"/api/terrain-dem?site_id={site_id}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["schema"] == "lunanav.terrain_dem.v1"
        assert payload["site"]["site_id"] == site_id
        assert payload["grid"]["size"] == 128
        assert "2D terrain horizon profile" in " ".join(payload["notes"])
    unknown = client.get("/api/terrain-dem?site_id=not-a-site")
    assert unknown.status_code == 404
