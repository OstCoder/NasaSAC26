from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from app.core.coords import topocentric_az_el, unit_vector, validate_lat_lon
from app.core.errors import InvalidInputError
from app.core.timeutil import parse_utc, time_grid, to_iso

R = 1737.4


class TestCoordinateValidation:
    def test_valid_and_longitude_wrap(self):
        assert validate_lat_lon(-89.45, 222.69) == pytest.approx((-89.45, -137.31))
        assert validate_lat_lon(-85, -180)[1] == -180
        assert validate_lat_lon(-85, 180)[1] == -180

    @pytest.mark.parametrize("lat,lon", [(-91, 0), (90.5, 0), (0, 400), (float("nan"), 0), (0, float("inf"))])
    def test_rejects_out_of_range(self, lat, lon):
        with pytest.raises(InvalidInputError):
            validate_lat_lon(lat, lon)

    def test_rejects_exact_pole(self):
        with pytest.raises(InvalidInputError, match="pole"):
            validate_lat_lon(-90, 0)
        validate_lat_lon(-89.999, 0)  # just off the pole is fine


class TestTopocentric:
    def test_zenith(self):
        lat, lon = -88.0, 40.0
        body = unit_vector(lat, lon) * 1.5e8
        _, el = topocentric_az_el(lat, lon, body[None, :], R)
        assert el[0] == pytest.approx(90.0, abs=1e-6)

    def test_north_is_toward_equator_near_south_pole(self):
        # Distant body on the equator at the site's meridian lies due north.
        lat, lon = -85.0, 10.0
        body = unit_vector(0.0, lon) * 1.5e8
        az, el = topocentric_az_el(lat, lon, body[None, :], R)
        assert az[0] == pytest.approx(0.0, abs=1e-6) or az[0] == pytest.approx(360.0, abs=1e-6)
        assert el[0] == pytest.approx(-85.0 + 90.0, abs=0.01)

    def test_east_azimuth(self):
        lat, lon = -85.0, 0.0
        body = unit_vector(-85.0, 0.01) * 1.5e8  # slightly east, far away
        body = unit_vector(0.0, 90.0) * 1.5e8   # direction of +y = east at lon 0
        az, _ = topocentric_az_el(lat, lon, body[None, :], R)
        assert az[0] == pytest.approx(90.0, abs=1e-6)

    def test_earth_parallax_is_included(self):
        lat, lon = -89.0, 0.0
        far = unit_vector(0.0, 0.0) * 1e12
        near = unit_vector(0.0, 0.0) * 384_400
        _, e_far = topocentric_az_el(lat, lon, far[None, :], R)
        _, e_near = topocentric_az_el(lat, lon, near[None, :], R)
        # Parallax lowers a near body by ~R/D rad ≈ 0.26 deg
        assert e_far[0] - e_near[0] == pytest.approx(np.degrees(R / 384_400), abs=0.01)


class TestTime:
    def test_parse_z_and_offset(self):
        a = parse_utc("2027-01-15T12:00:00Z")
        b = parse_utc("2027-01-15T07:00:00-05:00")
        assert a == b and a.tzinfo == timezone.utc

    def test_naive_rejected(self):
        with pytest.raises(InvalidInputError, match="timezone"):
            parse_utc("2027-01-15T12:00:00")

    def test_garbage_rejected(self):
        with pytest.raises(InvalidInputError):
            parse_utc("next tuesday")

    def test_grid_inclusive(self):
        start = datetime(2027, 1, 1, tzinfo=timezone.utc)
        g = time_grid(start, 2, 30)
        assert len(g) == 5 and g[-1] == start + timedelta(hours=2)
        assert to_iso(g[1]) == "2027-01-01T00:30:00Z"
