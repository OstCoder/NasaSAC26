"""Metric registry.

Every number shown in the scenario summary, comparison table and rescheduler
comes from a :class:`MetricDef` registered here. Adding a metric = writing a
function of :class:`MetricContext` and calling :func:`register`. The comparison
service picks it up automatically.

``availability_direction`` is purely descriptive (+1: larger means more time
with the body available; -1: larger means a longer outage; 0: neutral). It is
used to phrase trade-offs factually, never to rank or recommend sites.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Optional

import numpy as np

from app.models.schemas import MetricValue

from . import intervals as iv

Category = Literal["sun", "earth", "combined", "geometry"]


@dataclass
class MetricContext:
    window: iv.Span
    t: np.ndarray
    spans: dict[str, list[iv.Span]]
    sun_el: np.ndarray
    earth_el: np.ndarray
    sun_clear: np.ndarray
    earth_clear: np.ndarray

    @property
    def window_seconds(self) -> float:
        return self.window[1] - self.window[0]


@dataclass(frozen=True)
class MetricDef:
    id: str
    label: str
    unit: str
    category: Category
    description: str
    availability_direction: int
    fn: Callable[[MetricContext], tuple[Optional[float], bool]]


REGISTRY: dict[str, MetricDef] = {}


def register(m: MetricDef) -> MetricDef:
    REGISTRY[m.id] = m
    return m


def _hours(seconds):
    return None if seconds is None else seconds / 3600.0


def _total_h(key):
    return lambda c: (_hours(iv.total_seconds(c.spans[key])), False)


def _pct(key):
    return lambda c: (100.0 * iv.total_seconds(c.spans[key]) / c.window_seconds, False)


def _longest_h(key):
    def f(c):
        sec, cen = iv.longest(c.spans[key], c.window)
        return (_hours(sec) if sec is not None else 0.0), cen
    return f


def _first_end_h(key):
    """Hours from window start until the first interval (in progress at start) ends."""
    def f(c):
        spans = c.spans[key]
        if not spans or spans[0][0] > c.window[0] + 1.0:
            return None, False  # not visible at landing: no "first set" to report
        end = spans[0][1]
        if abs(end - c.window[1]) < 1.0:
            return _hours(end - c.window[0]), True  # still visible at window end
        return _hours(end - c.window[0]), False
    return f


for _m in [
    MetricDef("sun_visible_hours", "Sun above terrain", "h", "sun",
              "Total time the Sun's centre is above the terrain horizon.", 1, _total_h("sun_visible")),
    MetricDef("sun_visible_pct", "Sun above terrain", "%", "sun",
              "Share of the mission window with the Sun's centre above the terrain horizon.", 1, _pct("sun_visible")),
    MetricDef("longest_sun_visible_hours", "Longest continuous sunlight", "h", "sun",
              "Longest single interval with the Sun above the terrain horizon.", 1, _longest_h("sun_visible")),
    MetricDef("longest_sun_blackout_hours", "Longest Sun blackout", "h", "sun",
              "Longest interval with the Sun below the terrain horizon (or geometrically set).", -1,
              _longest_h("sun_blocked")),
    MetricDef("hours_until_first_sunset", "Time to first sunset", "h", "sun",
              "From landing until the Sun first drops below the terrain horizon (empty if not visible at landing).",
              1, _first_end_h("sun_visible")),
    MetricDef("earth_visible_hours", "Earth above terrain", "h", "earth",
              "Total time Earth's centre is above the terrain horizon.", 1, _total_h("earth_visible")),
    MetricDef("earth_visible_pct", "Earth above terrain", "%", "earth",
              "Share of the mission window with Earth's centre above the terrain horizon.", 1, _pct("earth_visible")),
    MetricDef("longest_earth_blackout_hours", "Longest Earth blackout", "h", "earth",
              "Longest interval with Earth below the terrain horizon (no direct line of sight).", -1,
              _longest_h("earth_blocked")),
    MetricDef("hours_until_first_earthset", "Time to first Earthset", "h", "earth",
              "From landing until Earth first drops below the terrain horizon (empty if not visible at landing).",
              1, _first_end_h("earth_visible")),
    MetricDef("both_visible_hours", "Sun and Earth simultaneously", "h", "combined",
              "Time with both the Sun and Earth above the terrain horizon.", 1, _total_h("both_visible")),
    MetricDef("both_visible_pct", "Sun and Earth simultaneously", "%", "combined",
              "Share of the window with both bodies above the terrain horizon.", 1, _pct("both_visible")),
    MetricDef("neither_visible_hours", "Neither Sun nor Earth", "h", "combined",
              "Time with both bodies below the terrain horizon.", -1, _total_h("neither_visible")),
    MetricDef("longest_no_simultaneous_hours", "Longest gap without simultaneous visibility", "h", "combined",
              "Longest interval in which Sun and Earth are not both above the terrain horizon.", -1,
              _longest_h("not_both")),
    MetricDef("max_sun_elevation_deg", "Peak Sun elevation", "deg", "geometry",
              "Maximum geometric solar elevation in the window (not terrain-adjusted).", 0,
              lambda c: (float(np.max(c.sun_el)), False)),
    MetricDef("max_earth_elevation_deg", "Peak Earth elevation", "deg", "geometry",
              "Maximum geometric Earth elevation in the window (not terrain-adjusted).", 0,
              lambda c: (float(np.max(c.earth_el)), False)),
]:
    register(_m)


def evaluate_all(ctx: MetricContext) -> list[MetricValue]:
    out = []
    for m in REGISTRY.values():
        value, censored = m.fn(ctx)
        out.append(
            MetricValue(
                id=m.id, label=m.label, value=None if value is None else round(float(value), 4),
                unit=m.unit, description=m.description, category=m.category, censored=censored,
            )
        )
    return out
