"""Central configuration loader.

All tunable values (supported date range, providers per mode, dataset paths,
feature flags) live in ``config/lunanav.config.json`` at the repository root.
Environment variables override a few values for local work:

- ``LUNANAV_CONFIG``  path to an alternative config JSON
- ``LUNANAV_MODE``    default operating mode ("demo" | "scientific")
- ``LUNANAV_ROOT``    repository root used to resolve relative dataset paths
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from .timeutil import parse_utc

REPO_ROOT = Path(os.environ.get("LUNANAV_ROOT", Path(__file__).resolve().parents[3]))
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "lunanav.config.json"


def rel(path) -> str:
    """Repo-relative path for user-facing messages (never leak absolute server paths)."""
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return Path(path).name


@dataclass(frozen=True)
class LandingPreset:
    """A named landing date from ``simulation.landing_presets`` (primary, alternate, ...)."""

    key: str
    label: str
    utc: datetime


@dataclass(frozen=True)
class RequirementThresholds:
    """Phase 1 mission requirements (``requirements`` in the config).

    Thresholds live in the config, never in code, so a change of target is a
    one-line edit that backend, frontend and docs all pick up.
    """

    min_sun_visible_pct: float
    min_earth_visible_pct: float
    max_earth_blackout_hours: float
    psr_proximity: str
    basis: str
    # Phase 5 demonstration defaults. Kept on the dataclass so callers that
    # construct thresholds directly (tests, scripts) keep their previous
    # five-field form working.
    max_darkness_hours: float = 16.0
    power_demand_w: float = 40.0


@dataclass(frozen=True)
class SimulationSettings:
    supported_start: datetime
    supported_end: datetime
    default_landing: datetime
    default_duration_hours: float
    min_duration_hours: float
    max_duration_hours: float
    default_step_minutes: float
    min_step_minutes: float
    max_samples: int
    lookahead_hours_for_events: float


@dataclass(frozen=True)
class JplSettings:
    horizons_api_url: str
    horizons_step: str
    horizons_timeout_s: float
    horizons_lon_sign: int
    horizons_crosscheck_tolerance_deg: float
    trek_tiles_url: str
    trek_timeout_s: float
    trek_max_parallel_requests: int


@dataclass(frozen=True)
class Settings:
    raw: dict[str, Any]
    default_mode: str
    allowed_modes: tuple[str, ...]
    simulation: SimulationSettings
    landing_presets: tuple[LandingPreset, ...]
    requirements: RequirementThresholds
    reference_radius_km: float
    providers: dict[str, dict[str, str]]
    datasets: dict[str, Path]
    sun_angular_radius_deg: float
    earth_angular_radius_deg: float
    features: dict[str, bool]
    jpl: JplSettings
    imagery: dict[str, Any]

    def public_dict(self) -> dict[str, Any]:
        """Subset of the config that is safe and useful for the frontend."""
        raw = self.raw
        return {
            "app": raw["app"],
            "mission": raw["mission"],
            "mode": {"default": self.default_mode, "allowed": list(self.allowed_modes)},
            "simulation": raw["simulation"],
            "requirements": {k: v for k, v in raw["requirements"].items() if not k.startswith("$")},
            "coordinates": raw["coordinates"],
            "providers": self.providers,
            "visibility": raw["visibility"],
            "features": self.features,
            "imagery": {
                "default_layer": self.imagery["default_layer"],
                "relief_layer": self.imagery["relief_layer"],
                "layers": {k: {"label": v["label"], "credit": v["credit"], "max_zoom": v["max_zoom"]}
                           for k, v in self.imagery["layers"].items()},
            },
        }


def _resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


_MISSION_FIELDS = ("name", "label", "objective", "duration_days", "landing_dates", "spacecraft", "candidate_sites")


def _validate_mission(mission: dict[str, Any], sim: dict[str, Any]) -> None:
    """Refuse to start when the mission block contradicts the simulation defaults.

    The mission is the deliverable, so a half-edited config should fail loudly here
    instead of serving a default scenario that is not the mission.
    """
    missing = [key for key in _MISSION_FIELDS if key not in mission]
    if missing:
        raise ValueError(f"config mission is missing {missing}")
    for key in ("power", "communication", "crewed"):
        if key not in mission["spacecraft"]:
            raise ValueError(f"config mission.spacecraft is missing {key!r}")
    if not mission["candidate_sites"]:
        raise ValueError("config mission.candidate_sites must list at least one site id")

    days = float(mission["duration_days"])
    default_days = float(sim["default_duration_hours"]) / 24
    if days != default_days:
        raise ValueError(
            f"mission.duration_days ({days:g}) must equal simulation.default_duration_hours/24 ({default_days:g})"
        )

    initial = parse_utc(mission["landing_dates"]["initial"])
    alternative = parse_utc(mission["landing_dates"]["alternative"])
    if initial != parse_utc(sim["default_landing_utc"]):
        raise ValueError("mission.landing_dates.initial must equal simulation.default_landing_utc")
    if alternative <= initial:
        raise ValueError("mission.landing_dates.alternative must be later than the initial date")
    window_start = parse_utc(sim["supported_start_utc"])
    window_end = parse_utc(sim["supported_end_utc"])
    for label, when in (("initial", initial), ("alternative", alternative)):
        if not window_start <= when <= window_end:
            raise ValueError(f"mission.landing_dates.{label} ({when.isoformat()}) is outside the supported window")
    presets = sim.get("landing_presets") or []
    out_of_window = [p for p in presets if not window_start <= parse_utc(p["utc"]) <= window_end]
    if presets and not out_of_window:
        if parse_utc(presets[0]["utc"]) != initial:
            raise ValueError(
                "simulation.landing_presets[0] must be the initial landing date "
                f"({initial.isoformat()}); the primary preset is the default scenario"
            )
        for label, when in (("initial", initial), ("alternative", alternative)):
            if not any(parse_utc(p["utc"]) == when for p in presets):
                raise ValueError(
                    f"simulation.landing_presets must include mission.landing_dates.{label} ({when.isoformat()})"
                )


def load_settings(path: Path | None = None) -> Settings:
    cfg_path = Path(os.environ.get("LUNANAV_CONFIG", path or DEFAULT_CONFIG_PATH))
    raw = json.loads(cfg_path.read_text())
    sim = raw["simulation"]
    _validate_mission(raw["mission"], sim)
    jpl = raw["jpl"]
    req = raw["requirements"]
    allowed = tuple(raw["mode"]["allowed"])
    default_mode = os.environ.get("LUNANAV_MODE", raw["mode"]["default"])
    if default_mode not in allowed:
        raise ValueError(f"LUNANAV_MODE={default_mode!r} not in allowed modes {allowed}")

    supported_start = parse_utc(sim["supported_start_utc"])
    supported_end = parse_utc(sim["supported_end_utc"])
    default_landing = parse_utc(sim["default_landing_utc"])
    if not supported_start <= default_landing <= supported_end:
        raise ValueError(
            f"simulation.default_landing_utc {sim['default_landing_utc']} is outside the supported "
            f"window {sim['supported_start_utc']} .. {sim['supported_end_utc']}"
        )
    presets = tuple(
        LandingPreset(key=str(p["key"]), label=str(p["label"]), utc=parse_utc(p["utc"]))
        for p in sim.get("landing_presets", [])
    )
    for preset in presets:
        if not supported_start <= preset.utc <= supported_end:
            raise ValueError(
                f"simulation.landing_presets[{preset.key!r}] = {preset.utc.isoformat()} is outside the "
                f"supported window {sim['supported_start_utc']} .. {sim['supported_end_utc']}"
            )

    return Settings(
        raw=raw,
        default_mode=default_mode,
        allowed_modes=allowed,
        simulation=SimulationSettings(
            supported_start=supported_start,
            supported_end=supported_end,
            default_landing=default_landing,
            default_duration_hours=float(sim["default_duration_hours"]),
            min_duration_hours=float(sim["min_duration_hours"]),
            max_duration_hours=float(sim["max_duration_hours"]),
            default_step_minutes=float(sim["default_step_minutes"]),
            min_step_minutes=float(sim["min_step_minutes"]),
            max_samples=int(sim["max_samples"]),
            lookahead_hours_for_events=float(sim["lookahead_hours_for_events"]),
        ),
        landing_presets=presets,
        requirements=RequirementThresholds(
            min_sun_visible_pct=float(req["min_sun_visible_pct"]),
            min_earth_visible_pct=float(req["min_earth_visible_pct"]),
            max_earth_blackout_hours=float(req["max_earth_blackout_hours"]),
            max_darkness_hours=float(req.get("max_darkness_hours", 16.0)),
            power_demand_w=float(req.get("power_demand_w", 40.0)),
            psr_proximity=str(req.get("psr_proximity", "optional")),
            basis=str(req.get("basis", "")),
        ),
        reference_radius_km=float(raw["coordinates"]["reference_radius_km"]),
        providers=raw["providers"],
        datasets={
            **{k: _resolve(v) for k, v in raw["datasets"].items()},
            **({"cache_dir": Path(os.environ["LUNANAV_CACHE_DIR"])} if os.environ.get("LUNANAV_CACHE_DIR") else {}),
        },
        sun_angular_radius_deg=float(raw["visibility"]["sun_angular_radius_deg"]),
        earth_angular_radius_deg=float(raw["visibility"]["earth_angular_radius_deg"]),
        features={k: bool(v) for k, v in raw["features"].items() if not k.startswith("$")},
        jpl=JplSettings(
            horizons_api_url=os.environ.get("LUNANAV_HORIZONS_URL", jpl["horizons_api_url"]),
            horizons_step=jpl["horizons_step"],
            horizons_timeout_s=float(jpl["horizons_timeout_s"]),
            horizons_lon_sign=int(jpl["horizons_lon_sign"]),
            horizons_crosscheck_tolerance_deg=float(jpl["horizons_crosscheck_tolerance_deg"]),
            trek_tiles_url=os.environ.get("LUNANAV_TREK_URL", jpl["trek_tiles_url"]).rstrip("/"),
            trek_timeout_s=float(jpl["trek_timeout_s"]),
            trek_max_parallel_requests=int(jpl["trek_max_parallel_requests"]),
        ),
        imagery=raw["imagery"],
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
