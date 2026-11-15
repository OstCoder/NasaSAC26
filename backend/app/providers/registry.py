"""Provider registry: config names -> provider instances, per operating mode.

To add a provider: write the class, add a factory below, and reference its id
in ``config/lunanav.config.json`` under ``providers.<mode>``.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

from app.core.settings import Settings, get_settings
from app.models.schemas import Mode

from .base import EphemerisProvider, LunarTerrainProvider
from .ephemeris_analytic import AnalyticMeeusEphemeris
from .ephemeris_horizons_live import HorizonsLiveEphemeris
from .ephemeris_spice import SpiceEphemeris
from .ephemeris_tabulated import HorizonsTableEphemeris
from .terrain import (
    FlatHorizonProvider,
    LolaHorizonMaskProvider,
    LolaOrFlatHorizonProvider,
    SyntheticHorizonProvider,
)

EphemerisFactory = Callable[[Settings], EphemerisProvider]
TerrainFactory = Callable[[Settings], LunarTerrainProvider]

EPHEMERIS_FACTORIES: dict[str, EphemerisFactory] = {
    "analytic_meeus": lambda s: AnalyticMeeusEphemeris(
        s.simulation.supported_start, s.simulation.supported_end
    ),
    "horizons_table": lambda s: HorizonsTableEphemeris(s.datasets["scientific_ephemeris_dir"]),
    "horizons_live": lambda s: HorizonsLiveEphemeris(
        s.jpl, s.datasets["cache_dir"], s.simulation.supported_start, s.simulation.supported_end
    ),
    "spice": lambda s: SpiceEphemeris(
        s.datasets["scientific_ephemeris_dir"].parent / "spice",
        s.simulation.supported_start,
        s.simulation.supported_end,
    ),
}

TERRAIN_FACTORIES: dict[str, TerrainFactory] = {
    "synthetic_horizon": lambda s: SyntheticHorizonProvider(s.datasets["demo_horizon_masks"]),
    "lola_horizon_mask": lambda s: LolaHorizonMaskProvider(s.datasets["scientific_horizon_dir"]),
    "lola_or_flat": lambda s: LolaOrFlatHorizonProvider(
        s.datasets["scientific_horizon_dir"],
        s.datasets.get("wide_terrain"),
        s.datasets["cache_dir"] / "lola_wide",
    ),
    "flat": lambda s: FlatHorizonProvider(),
}


@dataclass(frozen=True)
class ProviderBundle:
    mode: Mode
    ephemeris: EphemerisProvider
    terrain: LunarTerrainProvider


def build_bundle(mode: Mode, settings: Settings) -> ProviderBundle:
    cfg = settings.providers[mode.value]
    try:
        eph = EPHEMERIS_FACTORIES[cfg["ephemeris"]](settings)
        ter = TERRAIN_FACTORIES[cfg["terrain"]](settings)
    except KeyError as exc:
        raise ValueError(f"Unknown provider id {exc} in config for mode {mode.value}") from exc
    return ProviderBundle(mode=mode, ephemeris=eph, terrain=ter)


@lru_cache(maxsize=4)
def get_bundle(mode: Mode) -> ProviderBundle:
    return build_bundle(mode, get_settings())
