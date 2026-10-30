"""VisibilityCalculator: ephemeris + terrain -> time series, intervals, metrics, events."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np

from app.core.coords import topocentric_az_el
from app.core.errors import DataUnavailableError, InvalidInputError, OutOfSupportedRangeError
from app.core.settings import Settings
from app.core.timeutil import time_grid, to_iso
from app.models.schemas import (
    BodyState,
    HorizonMaskOut,
    Interval,
    IntervalSet,
    ResolvedLocation,
    ScenarioResult,
    Snapshot,
    TimeSeries,
)
from app.providers.base import HorizonMask
from app.providers.registry import ProviderBundle

from . import intervals as iv
from .horizon import HorizonCalculator
from .metrics import MetricContext, evaluate_all
from .provenance import build_provenance


def _dt(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _to_intervals(spans, window) -> list[Interval]:
    return [
        Interval(
            start_utc=_dt(s), end_utc=_dt(e), duration_hours=round((e - s) / 3600.0, 4),
            clipped_start=abs(s - window[0]) < 1.0, clipped_end=abs(e - window[1]) < 1.0,
        )
        for s, e in spans
    ]


class VisibilityCalculator:
    def __init__(self, bundle: ProviderBundle, settings: Settings):
        self.bundle = bundle
        self.settings = settings
        self.horizon = HorizonCalculator()

    # ------------------------------------------------------------ helpers --
    def supported_window(self) -> tuple[datetime, datetime]:
        info = self.bundle.ephemeris.info()
        if not info.available:
            raise DataUnavailableError(
                f"Ephemeris provider '{info.id}' unavailable: {info.unavailable_reason}",
                details={"provider": info.id, "mode": self.bundle.mode.value},
            )
        p_start, p_end = self.bundle.ephemeris.supported_range()
        sim = self.settings.simulation
        return max(p_start, sim.supported_start), min(p_end, sim.supported_end)

    def check_range(self, start: datetime, end: datetime) -> None:
        lo, hi = self.supported_window()
        if start < lo or end > hi:
            raise OutOfSupportedRangeError(
                f"Requested window {to_iso(start)} to {to_iso(end)} is outside the supported range "
                f"{to_iso(lo)} to {to_iso(hi)} for {self.bundle.mode.value} mode.",
                details={"supported_start_utc": to_iso(lo), "supported_end_utc": to_iso(hi)},
            )

    def mask_for(self, loc: ResolvedLocation) -> HorizonMask:
        return self.bundle.terrain.horizon_mask(loc.latitude_deg, loc.longitude_deg, loc.site_id)

    def _geometry(self, loc: ResolvedLocation, times: list[datetime]):
        r = self.settings.reference_radius_km
        h = loc.height_m / 1000.0
        out = {}
        for body in ("sun", "earth"):
            vec = self.bundle.ephemeris.body_vectors_km(body, times)
            az, el = topocentric_az_el(loc.latitude_deg, loc.longitude_deg, vec, r, h)
            out[body] = (az, el)
        return out

    def _evaluate(self, loc, mask, times):
        geo = self._geometry(loc, times)
        s = self.settings
        sun = self.horizon.evaluate(mask, *geo["sun"], s.sun_angular_radius_deg)
        earth = self.horizon.evaluate(mask, *geo["earth"], s.earth_angular_radius_deg)
        return geo, sun, earth

    # ----------------------------------------------------------- scenario --
    def scenario(
        self,
        loc: ResolvedLocation,
        landing: datetime,
        duration_hours: float,
        step_minutes: float | None = None,
        label: str | None = None,
    ) -> ScenarioResult:
        sim = self.settings.simulation
        if not sim.min_duration_hours <= duration_hours <= sim.max_duration_hours:
            raise InvalidInputError(
                f"duration_hours must be between {sim.min_duration_hours} and {sim.max_duration_hours}"
            )
        step = max(step_minutes or sim.default_step_minutes, sim.min_step_minutes)
        # Keep sample count bounded by coarsening the step (reported back to the client).
        min_step = duration_hours * 60.0 / (sim.max_samples - 1)
        step = max(step, min_step)

        end = landing + timedelta(hours=duration_hours)
        self.check_range(landing, end)
        mask = self.mask_for(loc)
        times = time_grid(landing, duration_hours, step)
        if times[-1] < end:
            times.append(end)
        geo, sun, earth = self._evaluate(loc, mask, times)

        t = np.array([x.timestamp() for x in times])
        window = (t[0], t[-1])
        sv = iv.intervals_from_clearance(t, sun.clearance_deg)
        ev = iv.intervals_from_clearance(t, earth.clearance_deg)
        both = iv.intersect(sv, ev)
        spans = {
            "sun_visible": sv,
            "earth_visible": ev,
            "both_visible": both,
            "sun_blocked": iv.complement(sv, window),
            "earth_blocked": iv.complement(ev, window),
            "neither_visible": iv.complement(iv.union(sv, ev), window),
            "not_both": iv.complement(both, window),
        }
        ctx = MetricContext(window, t, spans, geo["sun"][1], geo["earth"][1],
                            sun.clearance_deg, earth.clearance_deg)

        r4 = lambda a: [round(float(x), 4) for x in a]  # noqa: E731
        return ScenarioResult(
            label=label,
            location=loc,
            landing_utc=landing,
            end_utc=end,
            duration_hours=duration_hours,
            step_minutes=round(step, 4),
            series=TimeSeries(
                times_utc=times,
                sun_azimuth_deg=r4(geo["sun"][0]),
                sun_elevation_deg=r4(geo["sun"][1]),
                sun_terrain_horizon_deg=r4(sun.terrain_horizon_deg),
                sun_disk_fraction=r4(sun.disk_fraction),
                sun_visible=[bool(x) for x in sun.visible],
                earth_azimuth_deg=r4(geo["earth"][0]),
                earth_elevation_deg=r4(geo["earth"][1]),
                earth_terrain_horizon_deg=r4(earth.terrain_horizon_deg),
                earth_visible=[bool(x) for x in earth.visible],
            ),
            intervals=IntervalSet(**{k: _to_intervals(v, window) for k, v in spans.items() if k != "not_both"}),
            metrics=evaluate_all(ctx),
            horizon_mask=HorizonMaskOut(
                azimuth_deg=r4(mask.azimuth_deg), elevation_deg=r4(mask.elevation_deg),
                source=mask.source, provenance=mask.provenance,
            ),
            provenance=build_provenance(self.bundle, mask),
        )

    # ----------------------------------------------------------- snapshot --
    def snapshot(self, loc: ResolvedLocation, when: datetime, lookahead_hours: float | None = None) -> Snapshot:
        lookahead = lookahead_hours or self.settings.simulation.lookahead_hours_for_events
        lo, hi = self.supported_window()
        self.check_range(when, when)
        horizon_end = min(when + timedelta(hours=lookahead), hi)
        effective_lookahead = (horizon_end - when).total_seconds() / 3600.0
        mask = self.mask_for(loc)

        coarse = time_grid(when, max(effective_lookahead, 0.0), 30.0)
        geo, sun, earth = self._evaluate(loc, mask, coarse)
        states = {}
        for body, vis, radius in (
            ("sun", sun, self.settings.sun_angular_radius_deg),
            ("earth", earth, self.settings.earth_angular_radius_deg),
        ):
            c = vis.clearance_deg
            now_vis = bool(c[0] > 0)
            flips = np.nonzero((c[1:] > 0) != now_vis)[0]
            nxt, hours, kind = None, None, None
            if flips.size:
                i = int(flips[0])
                t_cross = self._refine(loc, mask, body, coarse[i], coarse[i + 1], now_vis)
                nxt = t_cross
                hours = round((t_cross - when).total_seconds() / 3600.0, 3)
                kind = "set" if now_vis else "rise"
            states[body] = BodyState(
                azimuth_deg=round(float(geo[body][0][0]), 4),
                elevation_deg=round(float(geo[body][1][0]), 4),
                terrain_horizon_deg=round(float(vis.terrain_horizon_deg[0]), 4),
                clearance_deg=round(float(c[0]), 4),
                visible=now_vis,
                disk_fraction=round(float(vis.disk_fraction[0]), 4) if body == "sun" else None,
                next_transition_utc=nxt,
                hours_until_transition=hours,
                transition_kind=kind,
                transition_beyond_lookahead=nxt is None,
            )
        return Snapshot(
            location=loc, time_utc=when, sun=states["sun"], earth=states["earth"],
            lookahead_hours=round(effective_lookahead, 3), provenance=build_provenance(self.bundle, mask),
        )

    def _refine(self, loc, mask, body, t0: datetime, t1: datetime, visible_at_t0: bool) -> datetime:
        """Bisection on the clearance sign change to ~30 s."""
        radius = self.settings.sun_angular_radius_deg if body == "sun" else self.settings.earth_angular_radius_deg
        for _ in range(16):
            if (t1 - t0).total_seconds() <= 30:
                break
            mid = t0 + (t1 - t0) / 2
            geo = self._geometry(loc, [mid])
            vis = self.horizon.evaluate(mask, *geo[body], radius)
            if bool(vis.clearance_deg[0] > 0) == visible_at_t0:
                t0 = mid
            else:
                t1 = mid
        return t0 + (t1 - t0) / 2
