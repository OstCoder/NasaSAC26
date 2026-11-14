"""Task 1 site-selection deliverables: catalogue integrity, LOLA elevation
consistency, PSR catalogue geometry, API surface, and elevation propagation
into the visibility geometry.

The data files this test guards:
  data/demo/sites.json               - the selected coordinates + recorded measurements
  data/reference/site_elevations.json- LOLA 5 m/pix PGDA DEM sampling evidence
  data/reference/psrs.json           - LROC south-pole PSR boundaries (>5 km2)
"""

import json
import math
from pathlib import Path

import numpy as np
import pytest

from app.core.coords import great_circle_km, polar_stereographic_xy, unit_vector
from app.services.psr import PsrCatalogue, _point_in_ring, _point_ring_distance
from app.services.sites import get_site_repository

ROOT = Path(__file__).resolve().parents[2]
SITES_JSON = ROOT / "data" / "demo" / "sites.json"
PSRS_JSON = ROOT / "data" / "reference" / "psrs.json"
EVIDENCE_JSON = ROOT / "data" / "reference" / "site_elevations.json"

CANDIDATES = ("shackleton-rim", "connecting-ridge", "de-gerlache-rim")


@pytest.fixture(scope="module")
def repo():
    return get_site_repository()


@pytest.fixture(scope="module")
def raw_sites():
    return {s["id"]: s for s in json.loads(SITES_JSON.read_text())["sites"]}


@pytest.fixture(scope="module")
def evidence():
    return json.loads(EVIDENCE_JSON.read_text())


@pytest.fixture(scope="module")
def catalogue():
    return PsrCatalogue(PSRS_JSON)


# ------------------------------------------------------------- coordinates --

class TestSiteCatalogue:
    def test_all_three_candidates_present(self, raw_sites):
        assert set(CANDIDATES) <= set(raw_sites)

    def test_coordinates_match_published_points(self, raw_sites):
        # Mazarico et al. 2011 LOLA points 4 / 1 / 11 (see docs/SITES.md).
        assert raw_sites["shackleton-rim"]["latitude_deg"] == pytest.approx(-89.78)
        assert raw_sites["shackleton-rim"]["longitude_deg"] == pytest.approx(-155.73)  # 204.27E
        assert raw_sites["connecting-ridge"]["latitude_deg"] == pytest.approx(-89.45)
        assert raw_sites["connecting-ridge"]["longitude_deg"] == pytest.approx(-137.31)  # 222.69E
        assert raw_sites["de-gerlache-rim"]["latitude_deg"] == pytest.approx(-88.67)
        assert raw_sites["de-gerlache-rim"]["longitude_deg"] == pytest.approx(-68.10)  # 291.90E

    def test_candidates_inside_south_polar_band(self, repo):
        for s in repo.candidates():
            assert -90.0 < s.latitude_deg <= -85.0, s.id
            assert -180.0 <= s.longitude_deg < 180.0

    def test_every_candidate_has_provenance(self, repo):
        for s in repo.candidates():
            assert s.source, s.id
            assert s.nasa_site_id and s.nasa_site_id.startswith("NASA 2020 site"), s.id
            assert len(s.sources) >= 3, s.id
            assert all(ref.label for ref in s.sources), s.id

    def test_distances_between_candidates_are_reasonable(self, repo):
        a, b, c = (repo.get(i) for i in CANDIDATES)
        # Shackleton rim <-> connecting ridge crest: neighbouring, ~11 km
        assert great_circle_km(a.latitude_deg, a.longitude_deg,
                               b.latitude_deg, b.longitude_deg) < 15.0
        # de Gerlache rim is on the far side of the pole, ~41 km from the ridge
        d_bc = great_circle_km(b.latitude_deg, b.longitude_deg,
                               c.latitude_deg, c.longitude_deg)
        assert 30.0 < d_bc < 50.0


# ---------------------------------------------------------------- elevation --

class TestElevations:
    def test_candidates_have_recorded_elevation_and_slope(self, repo):
        for s in repo.candidates():
            assert s.elevation_m is not None, s.id
            assert s.slope_deg is not None, s.id
            assert s.elevation_note, s.id
            # all three are high-standing rim/crest sites
            assert 500.0 <= s.elevation_m <= 4000.0, s.id
            assert 0.0 <= s.slope_deg <= 30.0, s.id

    def test_recorded_elevation_matches_lola_evidence(self, repo, evidence):
        for s in repo.candidates():
            truth = evidence["samples"][s.id]["products"]["surf"]["median"]
            assert s.elevation_m == pytest.approx(truth, abs=0.01), s.id

    def test_evidence_dem_is_centered_on_the_published_point(self, evidence):
        # The PGDA DEM for each Mazarico site is centred on the site point;
        # if the projection convention were wrong this offset would blow up.
        for sid in CANDIDATES:
            off = evidence["samples"][sid]["dem_center_offset_km"]
            assert math.hypot(*off) < 2.5, (sid, off)

    def test_repository_rejects_wrong_recorded_elevation(self, tmp_path, monkeypatch, write_json):
        import app.services.sites as sites_mod

        raw = json.loads(SITES_JSON.read_text())
        raw["sites"][0]["elevation_m"] = raw["sites"][0]["elevation_m"] + 100.0
        path = tmp_path / "sites.json"
        path.write_text(json.dumps(raw))
        with pytest.raises(ValueError, match="disagrees with LOLA"):
            sites_mod.SiteRepository(path)

    def test_site_elevation_enters_the_geometry(self, client, landing):
        """Earth parallax depends on the observer radius, so a +1.5 km site
        elevation must shift the Earth elevation (the Sun barely moves at ~1 AU)."""
        base = {"landing_utc": landing.isoformat(), "duration_hours": 24, "step_minutes": 60}
        r0 = client.post("/api/scenario", json={**base, "location": {"latitude_deg": -89.0, "longitude_deg": 0.0}}).json()
        r1 = client.post("/api/scenario", json={**base, "location": {"latitude_deg": -89.0, "longitude_deg": 0.0, "elevation_m": 1500.0}}).json()
        d_sun = np.max(np.abs(np.array(r1["series"]["sun_elevation_deg"]) - np.array(r0["series"]["sun_elevation_deg"])))
        d_earth = np.max(np.abs(np.array(r1["series"]["earth_elevation_deg"]) - np.array(r0["series"]["earth_elevation_deg"])))
        assert d_sun < d_earth / 100.0
        assert 1e-5 < d_earth < 1e-2  # ~0.0005 deg from the parallax change

    def test_catalogue_site_carries_elevation_through_scenarios(self, client, repo, landing):
        s = repo.get("connecting-ridge")
        body = client.post("/api/scenario", json={
            "location": {"site_id": "connecting-ridge"},
            "landing_utc": landing.isoformat(), "duration_hours": 48,
        }).json()
        assert body["location"]["elevation_m"] == pytest.approx(s.elevation_m)


# ---------------------------------------------------------------- PSR data --

class TestPsrGeometry:
    def test_catalogue_loaded(self, catalogue):
        assert len(catalogue) >= 600
        assert catalogue.meta["projection"]["sphere_radius_km"] == 1737.4

    def test_haversine_known_values(self):
        # pole to pole: half circumference
        assert great_circle_km(90, 0, -90, 0) == pytest.approx(math.pi * 1737.4, rel=1e-9)
        # quarter circumference along a meridian
        assert great_circle_km(0, 0, 90, 0) == pytest.approx(math.pi * 1737.4 / 2, rel=1e-9)
        # 1 m apart at the equator
        d = great_circle_km(0, 0, 0, 1 / (1737.4 * 1000) * (180 / math.pi))
        assert d == pytest.approx(0.001, rel=1e-3)

    def test_projection_round_trip_and_orientation(self):
        x, y = polar_stereographic_xy(-89.0, 0.0)
        assert x == pytest.approx(0.0, abs=1e-9) and y > 0  # 0 meridian up
        x, y = polar_stereographic_xy(-89.0, 90.0)
        assert x > 0 and y == pytest.approx(0.0, abs=1e-9)  # 90E right
        rho = math.hypot(x, y)
        lat = -90 + 2 * math.degrees(math.atan(rho / (2 * 1737.4)))
        assert lat == pytest.approx(-89.0, abs=1e-9)

    def test_point_ring_distance_synthetic_square(self):
        ring = [(0, 0), (10, 0), (10, 10), (0, 10)]
        assert _point_ring_distance(5, 20, ring) == pytest.approx(10.0)   # above edge
        assert _point_ring_distance(-4, 5, ring) == pytest.approx(4.0)    # left edge
        assert _point_ring_distance(5, 5, ring) == pytest.approx(5.0)     # inside -> boundary distance
        assert _point_ring_distance(13, 13, ring) == pytest.approx(math.sqrt(18))  # corner

    def test_point_in_ring(self):
        square = [(0, 0), (10, 0), (10, 10), (0, 10)]
        assert _point_in_ring(5, 5, square)
        assert not _point_in_ring(15, 5, square)
        assert not _point_in_ring(-1, -1, square)

    def test_nearest_psr_values_for_candidates(self, repo):
        prox = {s.id: s.nearest_psr for s in repo.candidates()}
        # Shackleton rim looks straight down onto the mapped Shackleton floor PSR
        assert prox["shackleton-rim"].label.startswith("PSR near Shackleton")
        assert 0.5 <= prox["shackleton-rim"].distance_km <= 8.0
        # ridge and de Gerlache rim sites: mapped (>5 km2) PSRs are kilometres away;
        # sub-km PSRs are below the product threshold (published values in sources)
        for sid in ("connecting-ridge", "de-gerlache-rim"):
            assert 2.0 <= prox[sid].distance_km <= 25.0, (sid, prox[sid])
        # only the Shackleton-rim site has a mapped PSR within 10 km
        assert repo.get("shackleton-rim").psrs_within_10_km >= 1
        for s in repo.candidates():
            assert s.nearest_psr.area_km2 >= 4.9  # product threshold (>5 km2)

    def test_within_km_consistency(self, catalogue, repo):
        s = repo.get("shackleton-rim")
        near = catalogue.within_km(s.latitude_deg, s.longitude_deg, 10.0)
        assert near, "expected at least one PSR within 10 km of the Shackleton rim"
        assert near[0][1] == pytest.approx(s.nearest_psr.distance_km, abs=0.01)
        assert all(d <= 10.0 for _, d in near)
        assert near == sorted(near, key=lambda t: t[1])

    def test_distance_to_centroid_matches_haversine(self, catalogue):
        p = catalogue.all()[0]
        from app.core.coords import great_circle_km as gc

        assert gc(p.centroid_latitude_deg, p.centroid_longitude_deg,
                  p.centroid_latitude_deg, p.centroid_longitude_deg) == pytest.approx(0.0)


# ----------------------------------------------------------------- the API --

class TestSiteApi:
    def test_sites_endpoint_includes_task1_fields(self, client):
        sites = {s["id"]: s for s in client.get("/api/sites").json()}
        for sid in CANDIDATES:
            s = sites[sid]
            assert s["elevation_m"] is not None
            assert s["nearest_psr"]["psr_id"].startswith("SP_")
            assert s["nearest_psr"]["distance_km"] > 0
            assert isinstance(s["psrs_within_10_km"], int)
            assert len(s["sources"]) >= 3
            assert s["sources"][0]["label"]

    def test_single_site_endpoint(self, client):
        s = client.get("/api/sites/connecting-ridge").json()
        assert s["nasa_site_id"] == "NASA 2020 site 001"
        assert s["elevation_m"] == pytest.approx(1955.23, abs=0.01)

    def test_unknown_site_still_404(self, client):
        assert client.get("/api/sites/nope").status_code == 404

    def test_psrs_endpoint(self, client):
        r = client.get("/api/psrs", params={"min_area_km2": 1.0, "max_latitude_deg": -80})
        assert r.status_code == 200
        data = r.json()
        assert len(data) > 300
        p = data[0]
        assert p["psr_id"].startswith("SP_")
        ring = p["rings"][0]
        assert all(len(pt) == 2 for pt in ring) and len(ring) >= 3
        # projected km: near-pole PSRs must be inside ~350 km of the pole
        assert all(abs(pt[0]) <= 350 and abs(pt[1]) <= 350 for pt in ring[:50])

    def test_psrs_near_site_filter(self, client):
        r = client.get("/api/psrs", params={"near_site_id": "shackleton-rim", "radius_km": 15})
        data = r.json()
        assert 1 <= len(data) <= 20
        assert any(p["near_crater"] == "Shackleton" for p in data)

    def test_scenarios_still_work_for_each_candidate(self, client, landing):
        for sid in CANDIDATES:
            r = client.post("/api/scenario", json={
                "location": {"site_id": sid},
                "landing_utc": landing.isoformat(), "duration_hours": 72,
            })
            assert r.status_code == 200, (sid, r.text)
            body = r.json()
            assert body["location"]["site_id"] == sid
            assert body["provenance"]["overall"] == "synthetic"  # demo mode
            ids = {m["id"] for m in body["metrics"]}
            assert "sun_visible_hours" in ids

    def test_config_mission_candidates_updated(self, client):
        cfg = client.get("/api/config").json()
        assert cfg["mission"]["candidate_sites"] == list(CANDIDATES)


# ------------------------------------------------- coordinate-frame sanity --

class TestConventions:
    def test_unit_vector_still_consistent_with_great_circle(self):
        v1, v2 = unit_vector(45, 30), unit_vector(45, 30.01)
        cosang = float(np.dot(v1, v2))
        assert great_circle_km(45, 30, 45, 30.01) == pytest.approx(math.acos(cosang) * 1737.4, rel=1e-6)
