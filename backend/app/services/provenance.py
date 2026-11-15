"""Builds the provenance block attached to every result."""

from __future__ import annotations

from app.models.schemas import (
    PROVENANCE_RANK,
    EffectsIncluded,
    Provenance,
    ProvenanceLevel,
)
from app.providers.base import HorizonMask
from app.providers.registry import ProviderBundle

LABELS = {
    ProvenanceLevel.synthetic: "Illustrative data: synthetic terrain, not real lunar conditions",
    ProvenanceLevel.geometric_only: "Flat-horizon estimate: terrain obstruction not applied",
    ProvenanceLevel.analytic_approximate: "Approximate: simplified ephemeris, unverified",
    ProvenanceLevel.scientific_sourced: "Terrain-aware: NASA ephemeris and LOLA terrain",
}

STANDING_CAVEATS = [
    "Sun above the horizon does not guarantee electrical power: panel orientation, shadowing by "
    "the lander, dust and power-system design are not modelled.",
    "Earth above the horizon does not guarantee communications: antenna pointing, link budget, "
    "ground-station coverage and relay assets are not modelled.",
    "Visibility uses the apparent centre of each body; partial disks at the skyline are reported "
    "separately for the Sun.",
]


def build_provenance(bundle: ProviderBundle, mask: HorizonMask) -> Provenance:
    eph = bundle.ephemeris.info()
    ter = bundle.terrain.info()
    overall = min([eph.provenance, mask.provenance], key=lambda p: PROVENANCE_RANK[p])
    effects = EffectsIncluded(
        terrain_topography=mask.provenance == ProvenanceLevel.scientific_sourced,
        optical_libration=eph.effects.optical_libration,
        physical_libration=eph.effects.physical_libration,
        observer_parallax=eph.effects.observer_parallax,
        light_time_correction=eph.effects.light_time_correction,
        finite_solar_disk=True,
        lunar_curvature_in_horizon=mask.provenance == ProvenanceLevel.scientific_sourced,
        notes=[*eph.effects.notes, *ter.effects.notes],
    )
    caveats = list(STANDING_CAVEATS)
    if mask.provenance == ProvenanceLevel.synthetic:
        caveats.insert(0, "The terrain skyline is SYNTHETIC. Visible/blocked periods illustrate the method only.")
    if mask.provenance == ProvenanceLevel.geometric_only:
        caveats.insert(0, "No terrain profile is available here: visibility uses the flat geometric horizon, "
                          "which overestimates visibility near the poles.")
    if eph.provenance == ProvenanceLevel.analytic_approximate:
        caveats.append("Ephemeris is a truncated analytic model (~0.05-0.1 deg); near-grazing events "
                       "may shift by tens of minutes to hours.")
    prefix = "NASA data"
    return Provenance(
        mode=bundle.mode,
        overall=overall,
        label=f"{prefix} · {LABELS[overall]}",
        ephemeris=eph,
        terrain=ter,
        terrain_mask_source=mask.source,
        effects=effects,
        caveats=caveats,
    )
