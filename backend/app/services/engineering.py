"""Phase 5 Tasks 1-2: solar-power and direct-to-Earth budgets from committed geometry.

The rest of LunaNav answers *when* the Sun and Earth clear the terrain. A mission
team's next two questions are *can the lander keep running* and *can it talk*.
This module answers both with textbook engineering formulas, using only numbers
the project already commits:

- Sun elevation, Earth elevation and **Earth range** from the Phase 2 Task 2
  hourly series;
- the terrain-adjusted visibility flags from :func:`phase3.visibility_response`,
  so a sample the skyline blocks contributes no power and no downlink.

Power: ``P = S * r_sun^-2 * A * eta_cell * packing * harness * incidence``, where
incidence is ``sin(elevation)`` for a fixed horizontal array and ``cos(elevation)``
for a vertical array that tracks the Sun's azimuth. At the lunar south pole the
Sun never rises more than ~2 deg, so the horizontal case is nearly useless and the
vertical case is the point: this is the trade the model makes visible.

Link: a representative X-band budget, ``C/N0 = EIRP - FSPL + G/T + 228.6`` with
``FSPL = 20 log10(4 pi d / lambda)`` and a 34 m dish; the supported data rate is
``C/N0 - Eb/N0_required`` in dB-Hz.

What this is **not**: a flight power or communications budget. Panel efficiency,
loads, battery capacity, antenna gains and noise temperature are fixed
assumptions in ``config/lunanav.config.json -> power / link``, not measured
hardware. The budgets say what follows from those assumptions and the committed
geometry; they do not predict a real spacecraft. Every response carries the
assumptions and prints them next to the numbers.
"""

from __future__ import annotations

import math
from datetime import datetime

import numpy as np

from app.core.errors import DataUnavailableError, InvalidInputError
from app.core.settings import Settings, get_settings
from app.services.phase3 import visibility_response
from app.services.site_data import load_series

SCHEMA = "lunanav.engineering_budget.v1"
WINDOWS = ("initial", "alternative")
WINDOW_FOR_PRESET = {"primary": "initial", "alternate": "alternative"}
AU_KM = 149_597_870.7
SPEED_OF_LIGHT_M_S = 299_792_458.0
BOLTZMANN_DB = -228.6

# (id, label, incidence rule in words)
DESIGNS = (
    ("horizontal", "Fixed horizontal array", "sin(elevation): a horizontal panel sees cos(zenith)"),
    ("vertical_tracking", "Vertical array, azimuth-tracking",
     "cos(elevation): a vertical panel facing the Sun's azimuth"),
)
PANEL_DESIGNS = ("horizontal", "vertical_tracking", "fixed")
RECOMMENDED_DESIGN = "vertical_tracking"

POWER_LIMITS = [
    "Panel efficiency, packing, harness loss, load and battery capacity are fixed "
    "assumptions in the config, not measured hardware.",
    "Irradiance is scaled by the actual Sun range in the series (~1.0 AU); no "
    "temperature derating, dust deposition, panel degradation or partial shading "
    "is modelled beyond the terrain visibility flag.",
    "Energy is a left-rectangle sum on the stored hourly samples, so the total has "
    "the step's error and is not an integration of a continuous curve.",
    "Sunlight-clears-the-skyline is a precondition for power, not a power guarantee; "
    "a real array also depends on pointing, thermal state and cell health.",
]

LINK_LIMITS = [
    "Transmit power, antenna gains, dish size, noise temperature and the required "
    "Eb/N0 are fixed assumptions in the config, not a negotiated DSN service.",
    "Only free-space path loss is modelled: no atmospheric or ionospheric loss, no "
    "rain (none on the Moon), no scintillation, no polarization loss, no pointing loss.",
    "Earth line of sight is not a link: the budget says whether the geometry closes "
    "under the assumptions, and what rate follows if it does.",
    "The Earth range is the committed phase-centre distance; light-time and station "
    "scheduling are out of scope.",
    "The data volume is a bound: it assumes the link runs for every visible second at the "
    "supported peak rate, with no recorder limit, no station schedule and no duty cycle.",
]

NOTES = [
    "Every input is committed: the Sun/Earth track and ranges are the Phase 2 Task 2 "
    "series, and visibility is the terrain-adjusted Phase 3 answer.",
    "Both budgets are engineering estimates under stated assumptions. Neither is a "
    "flight power budget or a negotiated communications link.",
]


def _block(settings: Settings, key: str) -> dict:
    block = (settings.raw.get(key) or {})
    if not block or block.get("$comment") == "":
        raise DataUnavailableError(
            f"config/lunanav.config.json -> {key} is missing, so the {key} budget cannot be built.",
            details={"code": "ASSUMPTIONS_UNAVAILABLE", "block": key},
        )
    return {k: v for k, v in block.items() if not k.startswith("$")}


def _window(window: str) -> str:
    if window not in WINDOWS:
        raise InvalidInputError(
            f"unknown window {window!r}; expected one of {', '.join(WINDOWS)}",
            details={"window": window, "allowed": list(WINDOWS)},
        )
    return window


def window_for_landing(landing: datetime, settings: Settings) -> str | None:
    """Return the committed engineering window for an exact landing preset."""
    for preset in settings.landing_presets:
        if preset.utc == landing:
            return WINDOW_FOR_PRESET.get(preset.key)
    return None


def _samples(site_id: str, window: str, settings: Settings) -> dict:
    """Aligned per-sample arrays: time, elevations, terrain visibility, ranges."""
    report = visibility_response(site_id=site_id, window=window, settings=settings)
    table = load_series(site_id, window, settings)
    series = report["series"]
    if len(series) != len(table.records):
        raise DataUnavailableError(
            "the visibility series and the stored track disagree in length, so the "
            "engineering budgets would be misaligned.",
            details={"series": len(series), "records": len(table.records)},
        )
    times = np.array([when.timestamp() for when in table.times], float)
    hours = (times - times[0]) / 3600.0
    return {
        "report": report,
        "times": table.times,
        "hours": hours,
        "sun_el": np.array([row["sun"]["elevation_deg"] for row in series], float),
        "sun_az": np.array([row["sun"]["azimuth_deg"] for row in series], float),
        "sun_visible": np.array([row["sun"]["visible"] for row in series], bool),
        "sun_range_km": np.array([row["sun"].get("range_km") for row in table.records], float),
        "earth_el": np.array([row["earth"]["elevation_deg"] for row in series], float),
        "earth_visible": np.array([row["earth"]["visible"] for row in series], bool),
        "earth_range_km": np.array([row["earth"].get("range_km") for row in table.records], float),
    }


def _panel_config(panel_design: str | None, tilt_deg: float | None,
                  azimuth_deg: float | None, cfg: dict) -> tuple[str, float, float | None, bool]:
    """Resolve and validate the selectable array orientation."""
    design = panel_design or cfg.get("default_panel_design", RECOMMENDED_DESIGN)
    if design not in PANEL_DESIGNS:
        raise InvalidInputError(
            f"unknown panel_design {design!r}; expected one of {', '.join(PANEL_DESIGNS)}",
            details={"panel_design": design, "allowed": list(PANEL_DESIGNS)},
        )
    if design == "fixed":
        tilt = float(cfg.get("default_panel_tilt_deg", 90.0) if tilt_deg is None else tilt_deg)
        azimuth = float(cfg.get("default_panel_azimuth_deg", 180.0) if azimuth_deg is None else azimuth_deg)
    else:
        tilt = 90.0 if design == "vertical_tracking" else 0.0
        azimuth = None
    if not 0.0 <= tilt <= 90.0:
        raise InvalidInputError("panel_tilt_deg must be between 0 and 90 degrees",
                                details={"panel_tilt_deg": tilt})
    if azimuth is not None and not 0.0 <= azimuth < 360.0:
        raise InvalidInputError("panel_azimuth_deg must be in [0, 360) degrees",
                                details={"panel_azimuth_deg": azimuth})
    return design, tilt, azimuth, design == "vertical_tracking"


def _incidence(data: dict, design: str, tilt_deg: float,
               azimuth_deg: float | None) -> np.ndarray:
    """Incidence for the two reference arrays and an arbitrary fixed orientation."""
    elevation = np.radians(data["sun_el"])
    if design == "horizontal":
        value = np.sin(elevation)
    elif design == "vertical_tracking":
        value = np.cos(elevation)
    else:
        tilt = math.radians(tilt_deg)
        panel_az = math.radians(azimuth_deg or 0.0)
        sun_az = np.radians(data["sun_az"])
        value = (
            math.sin(tilt) * np.cos(elevation) * np.cos(sun_az - panel_az)
            + math.cos(tilt) * np.sin(elevation)
        )
    return np.where(data["sun_visible"], np.clip(value, 0.0, None), 0.0)


def _sensitivity(selected_power: np.ndarray, cfg: dict, duration_hours: float,
                 load_w: float, hours: np.ndarray, design_energy_wh: float,
                 design: str) -> dict:
    """One-at-a-time sensitivity around solar conversion, load and capacity."""
    dt = np.diff(hours, prepend=hours[0])
    capacity = cfg["battery_capacity_wh"]
    dod = cfg["battery_max_depth_of_discharge"]
    soc0 = cfg["initial_state_of_charge"]

    def case(case_id: str, label: str, parameter: str, factor: float,
             power_scale: float = 1.0, load_scale: float = 1.0,
             capacity_scale: float = 1.0) -> dict:
        power = selected_power * power_scale
        energy = float(np.sum(power * dt))
        case_load = load_w * load_scale
        battery = _slice(
            duration_hours, case_load, capacity * capacity_scale, dod, soc0,
            energy, power, hours,
        )
        return {
            "id": case_id,
            "label": label,
            "parameter": parameter,
            "factor": factor,
            "load_w": round(case_load, 3),
            "array_energy_wh": round(energy, 3),
            "min_soc_pct": battery["min_soc_pct"],
            "unserved_wh": battery["unserved_wh"],
            "reserve_respected": battery["reserve_respected"],
        }

    cases = [
        case("base", "Base case", "none", 1.0),
        case("solar_low", "Solar conversion −10%", "solar_conversion", 0.9, power_scale=0.9),
        case("solar_high", "Solar conversion +10%", "solar_conversion", 1.1, power_scale=1.1),
        case("load_low", "Load −20%", "load", 0.8, load_scale=0.8),
        case("load_high", "Load +20%", "load", 1.2, load_scale=1.2),
        case("battery_low", "Battery capacity −10%", "battery_capacity", 0.9, capacity_scale=0.9),
        case("battery_high", "Battery capacity +10%", "battery_capacity", 1.1, capacity_scale=1.1),
    ]
    return {
        "method": (
            "One-at-a-time sensitivity: each case changes one assumption and returns "
            "the same deterministic battery model. It is not a probability distribution."
        ),
        "design": design,
        "base_energy_wh": round(design_energy_wh, 3),
        "cases": cases,
        "min_soc_range_pct": [
            min(item["min_soc_pct"] for item in cases),
            max(item["min_soc_pct"] for item in cases),
        ],
        "max_unserved_wh": max(item["unserved_wh"] for item in cases),
        "limits": [
            "Cases are deterministic bounds around a point-estimate config, not measured uncertainty.",
            "Correlations between assumptions are not modelled; only one parameter changes per case.",
        ],
    }


def _slice(duration_hours: float, load_w: float, capacity_wh: float, dod: float,
           soc0: float, design_energy_wh: float, power: np.ndarray, hours: np.ndarray,
           trace: bool = False) -> dict:
    """Step the battery through the window on the stored sampling.

    The depth-of-discharge limit is a floor, not a suggestion: charge below it is
    not available, so it is counted as unserved load instead of being spent.
    """
    floor_wh = capacity_wh * (1.0 - dod)
    dt = np.diff(hours, prepend=hours[0])
    soc = capacity_wh * soc0
    minimum = soc
    unserved = 0.0
    soc_trace: list[float] = []
    unserved_trace: list[float] = []
    for p, step in zip(power, dt):
        soc += (float(p) - load_w) * float(step)
        soc = min(soc, capacity_wh)
        if soc < floor_wh:
            unserved += floor_wh - soc
            soc = floor_wh
        minimum = min(minimum, soc)
        soc_trace.append(soc)
        unserved_trace.append(unserved)
    reserve_pct = (1.0 - dod) * 100.0
    minimum_pct = 100.0 * minimum / capacity_wh
    depleted = unserved > 0.0
    if design_energy_wh <= 1e-9:
        verdict = (
            "No sunlight clears the skyline in this window, so the array produces nothing "
            f"and the battery supplies the full {load_w:g} W load until it is empty."
        )
    elif depleted:
        verdict = (
            f"The array makes {design_energy_wh:.0f} Wh against a {load_w * duration_hours:.0f} Wh "
            f"load, so the battery runs dry and {unserved:.0f} Wh of load cannot be served."
        )
    elif minimum_pct < reserve_pct:
        verdict = (
            f"The array makes {design_energy_wh:.0f} Wh against a {load_w * duration_hours:.0f} Wh "
            f"load, but the battery dips to {minimum_pct:.0f}%, below the {reserve_pct:.0f}% reserve."
        )
    else:
        verdict = (
            f"The array makes {design_energy_wh:.0f} Wh against a {load_w * duration_hours:.0f} Wh "
            f"load and the battery never drops below {minimum_pct:.0f}%, above the "
            f"{reserve_pct:.0f}% reserve."
        )
    out = {
        "capacity_wh": capacity_wh,
        "usable_wh": round(capacity_wh * dod, 2),
        "initial_soc_pct": round(soc0 * 100.0, 2),
        "min_soc_pct": round(minimum_pct, 2),
        "final_soc_pct": round(100.0 * soc / capacity_wh, 2),
        "unserved_wh": round(unserved, 2),
        "depleted": depleted,
        "reserve_pct": round(reserve_pct, 2),
        "reserve_respected": (not depleted) and minimum_pct >= reserve_pct,
        "verdict": verdict,
    }
    if trace:
        out["trace"] = {
            "battery_wh": [round(float(value), 4) for value in soc_trace],
            "unserved_wh": [round(float(value), 4) for value in unserved_trace],
        }
    return out


def power_budget(site_id: str, window: str = "initial",
                 settings: Settings | None = None, load_w: float | None = None,
                 panel_design: str | None = None,
                 panel_tilt_deg: float | None = None,
                 panel_azimuth_deg: float | None = None) -> dict:
    """Solar-array energy and battery state for one site and mission window.

    ``load_w`` overrides the configured housekeeping load for a decision
    scenario. ``panel_design`` selects the horizontal, vertical-tracking or an
    arbitrary fixed array; a fixed array uses ``panel_tilt_deg`` (0 = horizontal,
    90 = vertical) and ``panel_azimuth_deg`` (0 = north, clockwise). The battery,
    trace and sensitivity all follow the selected design, not a hidden default.
    """
    settings = settings or get_settings()
    window = _window(window)
    cfg = _block(settings, "power")
    if load_w is not None and load_w < 0:
        raise InvalidInputError("load_w must be zero or more watts", details={"load_w": load_w})
    effective_load_w = float(cfg["load_w"] if load_w is None else load_w)
    selected_design, tilt, azimuth, tracking = _panel_config(
        panel_design, panel_tilt_deg, panel_azimuth_deg, cfg)
    data = _samples(site_id, window, settings)
    report = data["report"]

    irradiance = cfg["solar_constant_w_m2"] * (AU_KM / data["sun_range_km"]) ** 2
    conversion = cfg["panel_area_m2"] * cfg["cell_efficiency"] * cfg["packing_factor"] * \
        cfg["harness_and_soiling_factor"]
    hours = data["hours"]
    dt = np.diff(hours, prepend=hours[0])
    duration_hours = float(hours[-1] - hours[0])

    design_rows = list(DESIGNS)
    incidence = {
        design_id: _incidence(data, design_id, tilt, azimuth)
        for design_id, _, _ in design_rows
    }
    if selected_design == "fixed":
        design_rows.append((
            "fixed",
            f"Fixed array · tilt {tilt:g}°, facing {azimuth:g}°",
            "dot product of the panel normal and the Sun direction",
        ))
        incidence["fixed"] = _incidence(data, "fixed", tilt, azimuth)

    designs = []
    powers: dict[str, np.ndarray] = {}
    for design_id, label, rule in design_rows:
        power = irradiance * conversion * incidence[design_id]
        powers[design_id] = power
        energy = float(np.sum(power * dt))
        designs.append({
            "id": design_id,
            "label": label,
            "incidence_rule": rule,
            "tilt_deg": tilt if design_id == "fixed" else (90.0 if design_id == "vertical_tracking" else 0.0),
            "azimuth_deg": azimuth if design_id == "fixed" else None,
            "tracking": design_id == "vertical_tracking",
            "peak_w": round(float(power.max()), 3) if len(power) else 0.0,
            "mean_w": round(energy / duration_hours, 3) if duration_hours else 0.0,
            "energy_wh": round(energy, 3),
            "capacity_factor_pct": round(100.0 * energy / (power.max() * duration_hours), 3)
            if len(power) and power.max() > 0 and duration_hours else 0.0,
        })

    chosen = next(d for d in designs if d["id"] == selected_design)
    chosen_power = powers[selected_design]
    load_wh = effective_load_w * duration_hours
    sunlit_hours = float(np.sum(dt[data["sun_visible"]]))
    battery = _slice(
        duration_hours, effective_load_w, cfg["battery_capacity_wh"],
        cfg["battery_max_depth_of_discharge"], cfg["initial_state_of_charge"],
        chosen["energy_wh"], chosen_power, hours, trace=True,
    )
    battery_trace = battery.pop("trace")
    soc_pct_trace = [
        round(100.0 * float(value) / cfg["battery_capacity_wh"], 4)
        for value in battery_trace["battery_wh"]
    ]
    times_utc = [
        when.isoformat().replace("+00:00", "Z") for when in data["times"]
    ]
    shortage = chosen_power < effective_load_w

    return {
        "assumptions": {
            **cfg,
            "load_w": effective_load_w,
            "derived": {
                "dc_w_per_m2_at_normal_incidence": round(conversion / cfg["panel_area_m2"], 4),
                "conversion_factor": round(conversion, 6),
                "irradiance_au": round(float(np.median(irradiance)), 3),
            },
        },
        "design": {
            "recommended": RECOMMENDED_DESIGN,
            "selected": selected_design,
            "tilt_deg": tilt,
            "azimuth_deg": azimuth,
            "tracking": tracking,
            "reason": (
                "At the lunar south pole the Sun stays within a few degrees of the horizon, so "
                "a horizontal panel sees almost no incidence and a vertical, azimuth-tracking "
                "panel sees almost full incidence. The fixed design exposes an arbitrary tilt "
                "and azimuth; it is not an optimiser."
            ),
        },
        "designs": designs,
        "sensitivity": _sensitivity(
            chosen_power, cfg, duration_hours, effective_load_w, hours,
            chosen["energy_wh"], selected_design,
        ),
        "window": {
            "hours": round(duration_hours, 4),
            "sunlit_hours": round(sunlit_hours, 4),
            "dark_hours": round(max(0.0, duration_hours - sunlit_hours), 4),
            "sunlit_pct": round(100.0 * sunlit_hours / duration_hours, 3) if duration_hours else 0.0,
        },
        "budget": {
            "load_w": effective_load_w,
            "load_wh": round(load_wh, 2),
            "array_energy_wh": chosen["energy_wh"],
            "net_wh": round(chosen["energy_wh"] - load_wh, 3),
            "battery": battery,
        },
        "series": {
            "times_utc": times_utc,
            "solar_w": [round(float(value), 4) for value in chosen_power],
            "load_w": [round(effective_load_w, 4) for _ in times_utc],
            "battery_wh": battery_trace["battery_wh"],
            "battery_soc_pct": soc_pct_trace,
            "sun_visible": [bool(value) for value in data["sun_visible"]],
            "charging": [bool(float(value) > effective_load_w) for value in chosen_power],
            "discharging": [bool(float(value) < effective_load_w) for value in chosen_power],
            "unserved_wh": battery_trace["unserved_wh"],
        },
        "extremes": {
            "min_battery_wh": round(float(min(battery_trace["battery_wh"])), 4)
            if battery_trace["battery_wh"] else 0.0,
            "min_battery_soc_pct": round(min(soc_pct_trace), 4) if soc_pct_trace else 0.0,
            "min_battery_index": int(np.argmin(battery_trace["battery_wh"]))
            if battery_trace["battery_wh"] else 0,
            "shortage_samples": int(np.count_nonzero(shortage)),
            "shortage_hours": round(float(np.sum(dt[shortage])), 4),
        },
        "limits": POWER_LIMITS,
    }


def link_budget(site_id: str, window: str = "initial",
                settings: Settings | None = None) -> dict:
    """Direct-to-Earth X-band budget for one site and mission window."""
    settings = settings or get_settings()
    window = _window(window)
    cfg = _block(settings, "link")
    data = _samples(site_id, window, settings)

    wavelength_m = SPEED_OF_LIGHT_M_S / (cfg["frequency_ghz"] * 1e9)
    eirp_dbw = 10.0 * math.log10(cfg["transmit_power_w"]) + cfg["transmit_antenna_gain_dbi"] - \
        cfg["implementation_loss_db"]
    receive_gain_dbi = 10.0 * math.log10(
        cfg["receive_aperture_efficiency"]
        * (math.pi * cfg["receive_dish_diameter_m"] / wavelength_m) ** 2
    )
    g_over_t = receive_gain_dbi - 10.0 * math.log10(cfg["system_noise_temperature_k"])

    distance_m = data["earth_range_km"] * 1000.0
    fspl_db = 20.0 * np.log10(4.0 * math.pi * distance_m / wavelength_m)
    cn0_db_hz = eirp_dbw - fspl_db + g_over_t + abs(BOLTZMANN_DB)
    supported_bps = np.where(
        data["earth_visible"],
        10.0 ** ((cn0_db_hz - cfg["required_ebno_db"]) / 10.0),
        0.0,
    )
    margin_db = np.where(data["earth_visible"],
                         cn0_db_hz - cfg["required_ebno_db"], -np.inf)

    hours = data["hours"]
    dt = np.diff(hours, prepend=hours[0])
    visible = data["earth_visible"]
    visible_hours = float(np.sum(dt[visible]))
    duration_hours = float(hours[-1] - hours[0])
    bits = float(np.sum(supported_bps * dt * 3600.0))
    outage_hours = float(np.sum(dt[visible & (margin_db < 0)]))
    closes = bool(np.any(visible) and np.all(margin_db[visible] >= 0))

    def case(index: int) -> dict:
        return {
            "range_km": round(float(data["earth_range_km"][index]), 3),
            "fspl_db": round(float(fspl_db[index]), 3),
            "cn0_db_hz": round(float(cn0_db_hz[index]), 3),
            "supported_rate_bps": round(float(supported_bps[index]), 1),
            "margin_db": round(float(margin_db[index]), 3),
        }

    if closes:
        verdict = (
            f"Earth line of sight closes the link at every visible sample; the worst case "
            f"({float(np.max(data['earth_range_km'][visible])):.0f} km) keeps "
            f"{float(np.min(margin_db[visible])):.1f} dB of margin and supports up to "
            f"{float(np.min(supported_bps[visible])) / 1e6:.2f} Mbps."
        )
    elif np.any(visible):
        verdict = (
            "Earth clears the terrain but the budget does not close at this range: the link "
            f"is short by {abs(float(np.min(margin_db[visible]))):.1f} dB at worst. "
            "Terrain geometry is not a communications guarantee."
        )
    else:
        verdict = (
            "No Earth line of sight clears the terrain in this window, so there is no "
            "downlink regardless of the radio budget."
        )

    return {
        "assumptions": {
            **cfg,
            "derived": {
                "wavelength_m": round(wavelength_m, 6),
                "eirp_dbw": round(eirp_dbw, 3),
                "receive_gain_dbi": round(receive_gain_dbi, 3),
                "g_over_t_db_k": round(g_over_t, 3),
            },
        },
        "window": {
            "hours": round(duration_hours, 4),
            "visible_hours": round(visible_hours, 4),
            "data_volume_bound_mb": round(bits / 8.0 / 1e6, 3),
            "outage_hours": round(outage_hours, 4),
        },
        "best_case": case(int(np.argmin(np.where(visible, distance_m, np.inf))))
        if np.any(visible) else None,
        "worst_case": case(int(np.argmax(np.where(visible, distance_m, -np.inf))))
        if np.any(visible) else None,
        "closes": closes,
        "verdict": verdict,
        "limits": LINK_LIMITS,
    }


def engineering_response(*, site_id: str, window: str = "initial",
                         settings: Settings | None = None,
                         load_w: float | None = None,
                         panel_design: str | None = None,
                         panel_tilt_deg: float | None = None,
                         panel_azimuth_deg: float | None = None) -> dict:
    """Phase 5: the power and link budgets for one site and window, with provenance."""
    settings = settings or get_settings()
    window = _window(window)
    report = visibility_response(site_id=site_id, window=window, settings=settings)
    return {
        "schema": SCHEMA,
        "site": report["site"],
        "window": {
            "key": report["window"]["key"],
            "label": report["window"]["label"],
            "start_utc": report["window"]["start_utc"],
            "stop_utc": report["window"]["stop_utc"],
            "step": report["window"]["step"],
            "samples": report["window"]["samples"],
        },
        "power": power_budget(
            site_id, window, settings, load_w=load_w,
            panel_design=panel_design, panel_tilt_deg=panel_tilt_deg,
            panel_azimuth_deg=panel_azimuth_deg,
        ),
        "link": link_budget(site_id, window, settings),
        "provenance": {
            "ephemeris": report["provenance"]["ephemeris"],
            "terrain": report["provenance"]["terrain"],
            "visibility": "terrain-adjusted, from /api/phase3",
            "assumptions": "config/lunanav.config.json -> power / link",
        },
        "notes": NOTES,
    }
