"""The adaptation guide's metric example must keep working."""

from app.services import metrics
from app.services.metrics import MetricDef, register


def test_registered_metric_flows_through_scenario_and_comparison(client):
    m = register(MetricDef(
        id="sun_visible_first_72h_hours", label="Sunlight in first 72 h", unit="h", category="sun",
        description="Sun-visible time during the first 72 h after landing.", availability_direction=1,
        fn=lambda c: (sum(min(e, c.window[0] + 72 * 3600) - s
                          for s, e in c.spans["sun_visible"] if s < c.window[0] + 72 * 3600) / 3600, False),
    ))
    try:
        body = {"location": {"site_id": "malapert-massif"}, "landing_utc": "2027-01-15T12:00:00Z",
                "duration_hours": 120}
        r = client.post("/api/scenario", json=body).json()
        v = next(x for x in r["metrics"] if x["id"] == m.id)
        assert 0 <= v["value"] <= 72
        c = client.post("/api/compare", json={"a": body, "b": body}).json()
        assert any(d["id"] == m.id for d in c["deltas"])
    finally:
        metrics.REGISTRY.pop(m.id)


def test_feature_flags_exposed(client):
    flags = client.get("/api/config").json()["features"]
    assert flags["experimental_power_model"] is False
