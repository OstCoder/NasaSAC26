import numpy as np
import pytest

from app.models.schemas import ProvenanceLevel
from app.providers.base import HorizonMask
from app.services import intervals as iv
from app.services.horizon import HorizonCalculator, build_horizon_mask_from_dem, disk_fraction_above


def mask_with_wall(wall_el=3.0):
    az = np.arange(0.0, 360.0, 10.0)
    el = np.where((az >= 80) & (az <= 100), wall_el, 0.5)
    return HorizonMask(az, el, source="test", provenance=ProvenanceLevel.synthetic)


class TestHorizonObstruction:
    def test_above_geometric_but_below_terrain_is_blocked(self):
        calc = HorizonCalculator()
        res = calc.evaluate(mask_with_wall(), np.array([90.0, 200.0]), np.array([1.5, 1.5]), 0.27)
        assert list(res.visible) == [False, True]
        assert res.clearance_deg[0] == pytest.approx(-1.5)

    def test_mask_interpolation_wraps_360(self):
        m = HorizonMask(np.array([0.0, 90.0, 180.0, 270.0]), np.array([1.0, 2.0, 3.0, 5.0]),
                        source="t", provenance=ProvenanceLevel.synthetic)
        assert m.elevation_at(315.0) == pytest.approx(3.0)  # halfway 5 -> 1
        assert m.elevation_at(-45.0) == pytest.approx(3.0)
        assert m.elevation_at(45.0) == pytest.approx(1.5)

    def test_invalid_mask_rejected(self):
        with pytest.raises(ValueError):
            HorizonMask(np.array([10.0, 5.0]), np.array([0.0, 0.0]), source="t",
                        provenance=ProvenanceLevel.synthetic)
        with pytest.raises(ValueError):
            HorizonMask(np.array([0.0, 360.0]), np.array([0.0, 0.0]), source="t",
                        provenance=ProvenanceLevel.synthetic)

    def test_disk_fraction(self):
        r = 0.2666
        assert disk_fraction_above(np.array([0.0]), r)[0] == pytest.approx(0.5)
        assert disk_fraction_above(np.array([r]), r)[0] == pytest.approx(1.0)
        assert disk_fraction_above(np.array([-2 * r]), r)[0] == pytest.approx(0.0)
        f = disk_fraction_above(np.linspace(-r, r, 11), r)
        assert np.all(np.diff(f) > 0)


class TestDemMask:
    def test_wall_produces_expected_angle(self):
        # 200 x 200 grid, 100 m pixels, observer at centre; 1 km-high wall 5 km to the north.
        n, px = 200, 100.0
        dem = np.zeros((n, n))
        x0, y0 = -n / 2 * px, n / 2 * px
        wall_row = int((y0 - 5000.0) / px)
        dem[wall_row, :] = 1000.0
        m = build_horizon_mask_from_dem(dem, x0, y0, px, 0.0, 0.0, obs_height_m=0.0,
                                        north_unit=(0.0, 1.0), max_range_m=9000, azimuth_step_deg=5,
                                        provenance=ProvenanceLevel.synthetic)
        expected = np.degrees(np.arctan2(1000.0 - 5000.0**2 / (2 * 1_737_400), 5000.0))
        assert m.elevation_at(0.0) == pytest.approx(expected, abs=0.6)
        assert m.elevation_at(180.0) < 0.0  # flat ground: curvature drop puts skyline below 0

    def test_curvature_lowers_flat_horizon(self):
        dem = np.zeros((50, 50))
        m = build_horizon_mask_from_dem(dem, -2500, 2500, 100, 0, 0, obs_height_m=10.0,
                                        north_unit=(0, 1), max_range_m=2400,
                                        provenance=ProvenanceLevel.synthetic)
        assert np.all(m.elevation_deg < 0)


class TestIntervals:
    def test_edges_are_interpolated(self):
        t = np.array([0.0, 100.0, 200.0, 300.0])
        c = np.array([-1.0, 1.0, 1.0, -3.0])
        assert iv.intervals_from_clearance(t, c) == [(50.0, 225.0)]

    def test_all_visible_and_none(self):
        t = np.arange(5.0)
        assert iv.intervals_from_clearance(t, np.ones(5)) == [(0.0, 4.0)]
        assert iv.intervals_from_clearance(t, -np.ones(5)) == []

    def test_algebra(self):
        a = [(0, 10), (20, 30)]
        b = [(5, 25)]
        assert iv.intersect(a, b) == [(5, 10), (20, 25)]
        assert iv.union(a, b) == [(0, 30)]
        assert iv.complement(a, (0, 40)) == [(10, 20), (30, 40)]
        assert iv.complement([], (0, 5)) == [(0, 5)]
        assert iv.total_seconds(a) == 20

    def test_longest_censored_flag(self):
        assert iv.longest([(0, 10), (12, 13)], (0, 100)) == (10, True)
        assert iv.longest([(5, 10), (50, 90)], (0, 100)) == (40, False)
        assert iv.longest([], (0, 1)) == (None, False)
