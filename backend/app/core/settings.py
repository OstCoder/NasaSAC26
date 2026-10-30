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
class Settings:
    raw: dict[str, Any]
    default_mode: str
    allowed_modes: tuple[str, ...]
    simulation: SimulationSettings
    reference_radius_km: float
    providers: dict[str, dict[str, str]]
    datasets: dict[str, Path]
    sun_angular_radius_deg: float
    earth_angular_radius_deg: float
    features: dict[str, bool]

    def public_dict(self) -> dict[str, Any]:
        """Subset of the config that is safe and useful for the frontend."""
        raw = self.raw
        return {
            "app": raw["app"],
            "mode": {"default": self.default_mode, "allowed": list(self.allowed_modes)},
            "simulation": raw["simulation"],
            "coordinates": raw["coordinates"],
            "providers": self.providers,
            "visibility": raw["visibility"],
            "features": self.features,
        }


def _resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def load_settings(path: Path | None = None) -> Settings:
    cfg_path = Path(os.environ.get("LUNANAV_CONFIG", path or DEFAULT_CONFIG_PATH))
    raw = json.loads(cfg_path.read_text())
    sim = raw["simulation"]
    allowed = tuple(raw["mode"]["allowed"])
    default_mode = os.environ.get("LUNANAV_MODE", raw["mode"]["default"])
    if default_mode not in allowed:
        raise ValueError(f"LUNANAV_MODE={default_mode!r} not in allowed modes {allowed}")
    return Settings(
        raw=raw,
        default_mode=default_mode,
        allowed_modes=allowed,
        simulation=SimulationSettings(
            supported_start=parse_utc(sim["supported_start_utc"]),
            supported_end=parse_utc(sim["supported_end_utc"]),
            default_landing=parse_utc(sim["default_landing_utc"]),
            default_duration_hours=float(sim["default_duration_hours"]),
            min_duration_hours=float(sim["min_duration_hours"]),
            max_duration_hours=float(sim["max_duration_hours"]),
            default_step_minutes=float(sim["default_step_minutes"]),
            min_step_minutes=float(sim["min_step_minutes"]),
            max_samples=int(sim["max_samples"]),
            lookahead_hours_for_events=float(sim["lookahead_hours_for_events"]),
        ),
        reference_radius_km=float(raw["coordinates"]["reference_radius_km"]),
        providers=raw["providers"],
        datasets={k: _resolve(v) for k, v in raw["datasets"].items()},
        sun_angular_radius_deg=float(raw["visibility"]["sun_angular_radius_deg"]),
        earth_angular_radius_deg=float(raw["visibility"]["earth_angular_radius_deg"]),
        features={k: bool(v) for k, v in raw["features"].items()},
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
