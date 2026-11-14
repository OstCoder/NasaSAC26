"""Phase 2 Task 2 series: Sun/Earth tracks -> per-timestamp records.

One definition of the on-disk series shape, shared by
``scripts/horizons_site.py`` (one site, any window) and
``scripts/generate_site_series.py`` (every candidate site, both mission
windows), so the two cannot drift apart.

A record is exactly the Task 2 structure::

    {"site_id": "shackleton-rim",
     "timestamp_utc": "2026-12-01T00:00:00Z",
     "sun":   {"azimuth_deg": ..., "elevation_deg": ..., "range_km": ...},
     "earth": {"azimuth_deg": ..., "elevation_deg": ..., "range_km": ...}}

Timestamps are UTC ISO-8601, strictly chronological, and shared by both bodies.
A timestamp where only one body has a value is dropped and counted in
``incomplete_timestamps_dropped`` — it is never filled with a placeholder.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.settings import Settings
from app.core.timeutil import parse_utc, to_iso
from app.providers.horizons_site import ObserverSite, SkyTrack

SCHEMA = "lunanav.site_series.v1"
BODIES = ("sun", "earth")

SOURCE = (
    "NASA JPL Horizons API observer table: CENTER='coord@301', "
    "COORD_TYPE='GEODETIC', QUANTITIES='4,20' (apparent az/el, airless)"
)

CONVENTIONS = {
    "longitude": "selenographic, east-positive",
    "azimuth_deg": "degrees clockwise from local lunar north, [0, 360)",
    "elevation_deg": "degrees above the local horizontal, airless (no refraction), no terrain",
    "altitude_km": "height above the 1737.4 km IAU mean sphere (site elevation + observer height)",
    "time": "UTC, ISO-8601 with Z; both bodies share one timestamp",
}


@dataclass(frozen=True)
class SeriesWindow:
    """One mission period to sample: the landing date plus the mission length."""

    key: str
    label: str
    start: datetime
    end: datetime

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "start_utc": to_iso(self.start),
            "stop_utc": to_iso(self.end),
        }


def mission_windows(settings: Settings) -> list[SeriesWindow]:
    """The initial and delayed mission periods from the mission config.

    Task 2 names "December 1-8" and "December 11-18, 2026"; both are the
    mission's landing date plus its 7-day duration, so they are derived from
    the config rather than typed in twice.
    """
    mission = settings.raw["mission"]
    days = float(mission["duration_days"])
    labels = {"initial": "Initial analysis period", "alternative": "Delayed mission period"}
    out = []
    for key in ("initial", "alternative"):
        start = parse_utc(mission["landing_dates"][key])
        end = start + timedelta(days=days)
        out.append(SeriesWindow(key=key, label=f"{labels[key]} ({start:%d %b} - {end:%d %b %Y})", start=start, end=end))
    return out


def expected_samples(window: SeriesWindow, step_minutes: float) -> int:
    """Inclusive sample count for a window and step (169 for 7 days at 1 h)."""
    if step_minutes <= 0:
        raise ValueError("step_minutes must be positive")
    return int((window.end - window.start).total_seconds() / 60.0 / step_minutes) + 1


def merged_samples(tracks: dict[str, SkyTrack], site_id: str | None) -> tuple[list[dict], int]:
    """One record per timestamp where both bodies have a value, chronological."""
    per_time: dict[datetime, dict] = {}
    for body, track in tracks.items():
        ranges = track.range_km if track.range_km is not None else [None] * len(track)
        for when, az, el, distance in zip(track.times_utc, track.azimuth_deg, track.elevation_deg, ranges):
            sample = {"azimuth_deg": round(float(az), 6), "elevation_deg": round(float(el), 6)}
            if distance is not None:
                sample["range_km"] = round(float(distance), 3)
            per_time.setdefault(when, {})[body] = sample
    complete = [t for t in sorted(per_time) if all(body in per_time[t] for body in BODIES)]
    records = [{"site_id": site_id, "timestamp_utc": to_iso(t), **per_time[t]} for t in complete]
    return records, len(per_time) - len(complete)


def series_checks(records: list[dict]) -> dict[str, bool]:
    """The Task 2 guarantees, re-derivable from the stored records alone."""
    times = [parse_utc(record["timestamp_utc"]) for record in records]
    return {
        "chronological": all(later > earlier for earlier, later in zip(times, times[1:])),
        "matching_timestamps": all(all(body in record for body in BODIES) for record in records),
        "no_missing_values": all(
            isinstance(record[body].get("azimuth_deg"), (int, float))
            and isinstance(record[body].get("elevation_deg"), (int, float))
            for record in records
            for body in BODIES
        ),
        "non_empty": bool(records),
    }


def series_payload(
    *,
    observer: ObserverSite,
    label: dict,
    tracks: dict[str, SkyTrack],
    crosschecks: dict,
    start: datetime,
    stop: datetime,
    step: str,
    window: SeriesWindow | None = None,
) -> dict:
    """Self-describing payload: source, request, conventions, checks and records."""
    samples, dropped = merged_samples(tracks, label.get("site_id"))
    payload = {
        "schema": SCHEMA,
        "generated_utc": to_iso(datetime.now(timezone.utc)),
        "site": {**label, **observer.as_dict()},
        "request": {
            "start_utc": to_iso(start),
            "stop_utc": to_iso(stop),
            "step": step,
            "bodies": list(BODIES),
            "queries": {body: track.query_url for body, track in tracks.items()},
        },
        "source": SOURCE,
        "conventions": dict(CONVENTIONS),
        "crosscheck": {body: check.as_dict() for body, check in crosschecks.items()},
        "checks": series_checks(samples),
        "series": samples,
        "incomplete_timestamps_dropped": dropped,
    }
    if window is not None:
        payload["window"] = window.as_dict()
    return payload
