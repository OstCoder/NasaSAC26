"""Moon Trek imagery: caching, reprojection accuracy, failure handling (fake Trek server)."""

import dataclasses
import io

import numpy as np
import pytest
from PIL import Image

from app.core.errors import InvalidInputError, JplUnavailableError
from app.core.settings import get_settings
from app.services.imagery import TrekImagery, rho_for_lat
from jpl_fakes import FakeTrek


@pytest.fixture
def make(tmp_path):
    def _make(fake):
        s = get_settings()
        s2 = dataclasses.replace(s, datasets={**s.datasets, "cache_dir": tmp_path})
        return TrekImagery(s2, fetch=fake)
    return _make


def pixel_for(lat, lon, size, max_lat):
    R = float(rho_for_lat(max_lat))
    rho = float(rho_for_lat(lat))
    x, y = rho * np.sin(np.radians(lon)), rho * np.cos(np.radians(lon))
    col = int((x + R) / (2 * R) * size)
    row = int((R - y) / (2 * R) * size)
    return row, col


def test_reprojection_places_pixels_at_correct_lat_lon(make):
    im = make(FakeTrek())
    png, meta = im.south_pole_png("lola_shade", 512, -80)
    img = np.asarray(Image.open(io.BytesIO(png)))
    assert img.shape == (512, 512, 4) and meta["zoom"] >= 1
    for lat, lon in [(-85.99, 2.9), (-84.6, 31.0), (-88.71, -68.8), (-82.0, 150.0), (-86.0, -120.0)]:
        r, c = pixel_for(lat, lon, 512, -80)
        R, G, _, A = img[r, c].astype(float)
        assert A == 255
        assert -80 - G / 25 == pytest.approx(lat, abs=0.15)
        dlon = ((R / 255 * 360 - 180) - lon + 180) % 360 - 180
        assert abs(dlon) < 3.0
    # corners lie outside the 80°S circle -> transparent
    assert img[0, 0, 3] == 0


def test_tiles_are_cached(make):
    fake = FakeTrek()
    im = make(fake)
    im.south_pole_png("lola_shade", 256, -84)
    n = len(fake.calls)
    im2 = make(FakeTrek(fail="network"))  # offline now
    png, _ = im2.south_pole_png("lola_shade", 256, -84)
    assert n > 0 and png.startswith(b"\x89PNG")


def test_extension_fallback_and_missing_tiles(make):
    fake = FakeTrek(missing_cols={0, 1})
    im = make(fake)
    png, _ = im.south_pole_png("wac", 256, -84)  # wac tries .jpg first (404), then .png
    assert any(u.endswith(".jpg") for u in fake.calls) and any(u.endswith(".png") for u in fake.calls)
    img = np.asarray(Image.open(io.BytesIO(png)))
    # Missing tiles (westernmost longitudes) stay transparent instead of being invented.
    r, c = pixel_for(-86.0, -175.0, 256, -84)
    assert img[r, c, 3] == 0


def test_network_failure_raises(make):
    with pytest.raises(JplUnavailableError, match="Moon Trek"):
        make(FakeTrek(fail="network")).south_pole_png("lola_shade", 256, -84)


def test_global_texture_and_validation(make):
    im = make(FakeTrek())
    jpg, meta = im.global_jpeg("lola_shade", 1)
    assert Image.open(io.BytesIO(jpg)).size == (1024, 512)
    with pytest.raises(InvalidInputError):
        im.layer("google_earth")
    with pytest.raises(InvalidInputError):
        im.south_pole_png("lola_shade", 100, -80)


def test_imagery_endpoint_reports_unreachable_trek(client):
    r = client.get("/api/imagery/south-pole?layer=lola_shade&size=256&max_lat=-88")
    assert r.status_code == 503 and r.json()["code"] == "JPL_UNAVAILABLE"
    st = client.get("/api/jpl/status?force=true").json()
    assert st["horizons"]["reachable"] is False and st["trek"]["reachable"] is False
    assert st["horizons"]["message"]


def test_layer_with_no_tiles_is_an_error_not_a_black_image(make, tmp_path):
    fake = FakeTrek(missing_cols=set(range(4096)))  # every tile 404s, as with a wrong layer path
    im = make(fake)
    with pytest.raises(JplUnavailableError, match="may be wrong or retired"):
        im.global_jpeg("lola_shade", 1)
    with pytest.raises(JplUnavailableError, match="LROC WAC"):
        im.south_pole_png("lola_shade", 256, -84)
    assert not list(tmp_path.rglob("*.jpg")) and not list(tmp_path.rglob("south_pole_*.png"))


def test_fixing_a_layer_path_ignores_old_missing_markers(make, tmp_path):
    im = make(FakeTrek(missing_cols=set(range(4096))))
    with pytest.raises(JplUnavailableError):
        im.global_jpeg("lola_shade", 0)
    im2 = make(FakeTrek())
    im2.layers["lola_shade"] = dataclasses.replace(im2.layers["lola_shade"], path="Moon/EQ/Corrected_Layer")
    jpg, _ = im2.global_jpeg("lola_shade", 0)
    assert np.asarray(Image.open(io.BytesIO(jpg))).mean() > 10
