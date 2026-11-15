"""Phase 5 Tasks 1-3: power budget, link budget and the Markdown report."""

import json
import math
from datetime import datetime

import pytest

from app.core.errors import InvalidInputError
from app.services.engineering import (
    SCHEMA,
    engineering_response,
    link_budget,
    power_budget,
)
from app.services.phase3 import visibility_response

SITES = ("shackleton-rim", "connecting-ridge", "de-gerlache-rim")
WINDOWS = ("initial", "alternative")


def _find(field: str, key: str) -> tuple[str, str]:
    """First site/window whose summary field exceeds zero (deterministic order)."""
    for site in SITES:
        for window in WINDOWS:
            summary = visibility_response(site_id=site, window=window)["summary"]
            if summary[field] > 0:
                return site, window
    raise AssertionError(f"no site/window has {field} > 0 in the committed data")


def test_envelope_states_provenance_and_assumptions():
    doc = engineering_response(site_id="de-gerlache-rim")

    assert doc["schema"] == SCHEMA
    assert doc["site"]["site_id"] == "de-gerlache-rim"
    assert doc["window"]["samples"] == 169
    assert doc["provenance"]["assumptions"] == "config/lunanav.config.json -> power / link"
    assert doc["power"]["assumptions"]["panel_area_m2"] > 0
    assert doc["link"]["assumptions"]["frequency_ghz"] > 0
    assert doc["power"]["limits"] and doc["link"]["limits"]


def test_power_is_zero_when_terrain_blocks_all_sunlight():
    doc = engineering_response(site_id="shackleton-rim")
    power = doc["power"]

    assert power["window"]["sunlit_hours"] == 0
    for design in power["designs"]:
        assert design["energy_wh"] == 0
        assert design["peak_w"] == 0
    battery = power["budget"]["battery"]
    assert battery["depleted"] is True
    assert battery["unserved_wh"] > 0
    assert "No sunlight clears the skyline" in battery["verdict"]


def test_vertical_array_wins_at_polar_sun_elevations():
    site, window = _find("sun_visible_pct", "sun")
    power = engineering_response(site_id=site, window=window)["power"]
    horizontal, vertical = power["designs"]

    assert horizontal["id"] == "horizontal"
    assert vertical["id"] == "vertical_tracking"
    assert power["design"]["recommended"] == "vertical_tracking"
    assert vertical["energy_wh"] > horizontal["energy_wh"] * 2
    assert vertical["peak_w"] > horizontal["peak_w"]
    assert power["budget"]["array_energy_wh"] == vertical["energy_wh"]


def test_energy_and_battery_accounting_is_internally_consistent():
    site, window = _find("sun_visible_pct", "sun")
    power = engineering_response(site_id=site, window=window)["power"]
    budget = power["budget"]
    battery = budget["battery"]
    cfg = power["assumptions"]

    assert budget["load_wh"] == pytest.approx(
        cfg["load_w"] * power["window"]["hours"], rel=1e-6)
    assert budget["net_wh"] == pytest.approx(
        budget["array_energy_wh"] - budget["load_wh"], abs=1e-3)
    assert battery["usable_wh"] == pytest.approx(
        cfg["battery_capacity_wh"] * cfg["battery_max_depth_of_discharge"], abs=1e-6)
    # The depth-of-discharge floor is never spent, so the state of charge cannot
    # fall below it and no load is left unserved when the array beats the load.
    assert battery["min_soc_pct"] >= battery["reserve_pct"] - 1e-9
    assert battery["unserved_wh"] == 0
    assert battery["reserve_respected"] is True
    assert battery["initial_soc_pct"] == pytest.approx(
        cfg["initial_state_of_charge"] * 100, abs=1e-6)


def test_power_trace_is_aligned_and_accounts_for_the_same_energy():
    site, window = _find("sun_visible_pct", "sun")
    power = engineering_response(site_id=site, window=window)["power"]
    series = power["series"]
    n = len(series["times_utc"])

    assert n > 0
    assert len(series["times_utc"]) == n
    for key in ("solar_w", "load_w", "battery_wh", "battery_soc_pct",
                "sun_visible", "charging", "discharging", "unserved_wh"):
        assert len(series[key]) == n
    assert series["times_utc"][0].endswith("Z")
    assert series["battery_wh"][-1] == pytest.approx(
        power["budget"]["battery"]["final_soc_pct"] / 100
        * power["budget"]["battery"]["capacity_wh"], abs=1e-2)
    assert power["extremes"]["min_battery_wh"] == pytest.approx(
        min(series["battery_wh"]), abs=1e-2)
    assert series["battery_wh"][power["extremes"]["min_battery_index"]] == pytest.approx(
        power["extremes"]["min_battery_wh"], abs=1e-2)
    assert max(series["battery_wh"]) <= power["budget"]["battery"]["capacity_wh"] + 1e-6
    for solar, load, charging, discharging in zip(
            series["solar_w"], series["load_w"], series["charging"], series["discharging"]):
        assert charging is (solar > load)
        assert discharging is (solar < load)
    assert all(
        later >= earlier for earlier, later in zip(series["unserved_wh"], series["unserved_wh"][1:]))

    # Integrate the hourly solar series with the same left-step rule as the model.
    times = [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in series["times_utc"]]
    steps = [(times[i] - times[i - 1]).total_seconds() / 3600 for i in range(1, len(times))]
    energy = sum(series["solar_w"][i] * steps[i - 1] for i in range(1, len(times)))
    assert energy == pytest.approx(power["budget"]["array_energy_wh"], abs=0.1)


def test_panel_orientation_is_selectable_and_drives_the_battery():
    site, window = _find("sun_visible_pct", "sun")
    vertical = engineering_response(site_id=site, window=window)["power"]
    fixed = engineering_response(
        site_id=site, window=window, panel_design="fixed",
        panel_tilt_deg=45, panel_azimuth_deg=180,
    )["power"]

    assert fixed["design"]["selected"] == "fixed"
    assert fixed["design"]["tilt_deg"] == 45
    assert fixed["design"]["azimuth_deg"] == 180
    assert fixed["design"]["tracking"] is False
    assert [design["id"] for design in fixed["designs"]] == [
        "horizontal", "vertical_tracking", "fixed",
    ]
    selected = next(design for design in fixed["designs"] if design["id"] == "fixed")
    assert fixed["budget"]["array_energy_wh"] == pytest.approx(selected["energy_wh"], abs=1e-6)
    assert fixed["budget"]["array_energy_wh"] != pytest.approx(
        vertical["budget"]["array_energy_wh"], abs=1e-6)
    assert len(fixed["series"]["solar_w"]) == len(fixed["series"]["times_utc"])

    with pytest.raises(InvalidInputError):
        power_budget(site, window, panel_design="fixed", panel_tilt_deg=91)
    with pytest.raises(InvalidInputError):
        power_budget(site, window, panel_design="fixed", panel_azimuth_deg=360)
    with pytest.raises(InvalidInputError):
        power_budget(site, window, panel_design="sunflower")


def test_sensitivity_is_one_at_a_time_and_uses_the_selected_design():
    site, window = _find("sun_visible_pct", "sun")
    power = engineering_response(
        site_id=site, window=window, panel_design="vertical_tracking",
        load_w=40,
    )["power"]
    sensitivity = power["sensitivity"]
    cases = {case["id"]: case for case in sensitivity["cases"]}

    assert sensitivity["design"] == "vertical_tracking"
    assert set(cases) == {
        "base", "solar_low", "solar_high", "load_low", "load_high",
        "battery_low", "battery_high",
    }
    assert cases["solar_low"]["array_energy_wh"] < cases["base"]["array_energy_wh"]
    assert cases["solar_high"]["array_energy_wh"] > cases["base"]["array_energy_wh"]
    assert cases["load_high"]["min_soc_pct"] <= cases["base"]["min_soc_pct"]
    assert cases["load_low"]["min_soc_pct"] >= cases["base"]["min_soc_pct"]
    assert sensitivity["min_soc_range_pct"][0] <= cases["base"]["min_soc_pct"]
    assert sensitivity["min_soc_range_pct"][1] >= cases["base"]["min_soc_pct"]
    assert "not measured uncertainty" in " ".join(sensitivity["limits"])


def test_http_panel_orientation_contract(client):
    response = client.get("/api/engineering", params={
        "site_id": "de-gerlache-rim",
        "panel_design": "fixed",
        "panel_tilt_deg": 45,
        "panel_azimuth_deg": 180,
    })
    assert response.status_code == 200, response.text
    power = response.json()["power"]
    assert power["design"]["selected"] == "fixed"
    assert power["budget"]["array_energy_wh"] > 0
    assert len(power["sensitivity"]["cases"]) == 7

    assert client.get("/api/engineering", params={
        "site_id": "de-gerlache-rim", "panel_design": "fixed", "panel_tilt_deg": 91,
    }).status_code == 422


def test_link_budget_matches_a_hand_calculation():
    site, window = _find("earth_visible_pct", "earth")
    link = engineering_response(site_id=site, window=window)["link"]
    assumptions = link["assumptions"]
    best = link["best_case"]

    wavelength = 299_792_458.0 / (assumptions["frequency_ghz"] * 1e9)
    fspl = 20 * math.log10(4 * math.pi * best["range_km"] * 1000 / wavelength)
    assert best["fspl_db"] == pytest.approx(fspl, abs=0.01)

    eirp = (10 * math.log10(assumptions["transmit_power_w"])
            + assumptions["transmit_antenna_gain_dbi"]
            - assumptions["implementation_loss_db"])
    gain_rx = 10 * math.log10(
        assumptions["receive_aperture_efficiency"]
        * (math.pi * assumptions["receive_dish_diameter_m"] / wavelength) ** 2)
    cn0 = (eirp - fspl + gain_rx
           - 10 * math.log10(assumptions["system_noise_temperature_k"]) + 228.6)
    assert best["cn0_db_hz"] == pytest.approx(cn0, abs=0.01)

    rate = 10 ** ((cn0 - assumptions["required_ebno_db"]) / 10)
    assert best["supported_rate_bps"] == pytest.approx(rate, rel=1e-2)
    assert best["margin_db"] == pytest.approx(
        cn0 - assumptions["required_ebno_db"], abs=0.01)
    assert link["closes"] is (link["worst_case"]["margin_db"] >= 0)
    assert best["range_km"] <= link["worst_case"]["range_km"]


def test_link_reports_no_downlink_when_terrain_blocks_earth():
    link = engineering_response(site_id="shackleton-rim")["link"]

    assert link["best_case"] is None and link["worst_case"] is None
    assert link["closes"] is False
    assert link["window"]["visible_hours"] == 0
    assert link["window"]["data_volume_bound_mb"] == 0
    assert "No Earth line of sight" in link["verdict"]


def test_engineering_response_is_reproducible():
    first = json.dumps(engineering_response(site_id="connecting-ridge", window="alternative"),
                       sort_keys=True)
    second = json.dumps(engineering_response(site_id="connecting-ridge", window="alternative"),
                        sort_keys=True)
    assert first == second
    assert json.loads(first) == engineering_response(
        site_id="connecting-ridge", window="alternative")


def test_http_engineering_contract(client):
    response = client.get("/api/engineering", params={"site_id": "de-gerlache-rim"})
    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == SCHEMA
    assert body["power"]["designs"][1]["id"] == "vertical_tracking"
    assert body["link"]["assumptions"]["modulation"]

    assert client.get("/api/engineering", params={"site_id": "nowhere"}).status_code == 404
    assert client.get(
        "/api/engineering",
        params={"site_id": "shackleton-rim", "window": "lunar-eclipse"}).status_code == 422


def test_markdown_report_is_complete_and_deterministic(client):
    first = client.get("/api/mission-report.md",
                       params={"site_id": "de-gerlache-rim", "window": "alternative"})
    second = client.get("/api/mission-report.md",
                        params={"site_id": "de-gerlache-rim", "window": "alternative"})

    assert first.status_code == 200
    assert first.headers["content-type"].startswith("text/markdown")
    assert "attachment" in first.headers["content-disposition"]
    body = first.text
    assert body == second.text
    for heading in ("## Terrain basis", "## Visibility against the terrain",
                    "## Mission requirements", "## Power budget",
                    "## Direct-to-Earth link budget", "## Assumptions",
                    "## What this report does not claim"):
        assert heading in body
    assert "De Gerlache" in body or "de-gerlache-rim" in body
    assert "vertical_tracking" in body or "Vertical array" in body
    assert "UNKNOWN" in body
    # Targets carry the same unit as the measured column; a bare number is ambiguous.
    assert "at least 60.0 %" in body
    assert "at most 12.0 h" in body
    assert client.get("/api/mission-report.md",
                      params={"site_id": "nowhere"}).status_code == 404
