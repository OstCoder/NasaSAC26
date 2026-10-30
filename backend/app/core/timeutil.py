"""UTC time handling. Every datetime inside LunaNav is timezone-aware UTC."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np

from .errors import InvalidInputError

J2000 = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def parse_utc(value: str | datetime) -> datetime:
    """Parse an ISO-8601 string (or datetime) into an aware UTC datetime.

    Naive inputs are rejected rather than guessed, because a silent local-time
    interpretation would shift every ephemeris result.
    """
    if isinstance(value, datetime):
        dt = value
    else:
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError as exc:
            raise InvalidInputError(f"Invalid ISO-8601 timestamp: {value!r}") from exc
    if dt.tzinfo is None:
        raise InvalidInputError(
            f"Timestamp {value!r} has no timezone. Use UTC, e.g. 2027-01-15T12:00:00Z."
        )
    return dt.astimezone(timezone.utc)


def to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def time_grid(start: datetime, hours: float, step_minutes: float) -> list[datetime]:
    """Inclusive, evenly spaced UTC grid from ``start`` to ``start + hours``."""
    if step_minutes <= 0:
        raise InvalidInputError("step_minutes must be positive")
    n = int(np.floor(hours * 60.0 / step_minutes + 1e-9)) + 1
    step = timedelta(minutes=step_minutes)
    return [start + i * step for i in range(n)]


def julian_centuries_tt(times: list[datetime]) -> np.ndarray:
    """Julian centuries since J2000 (TT).

    UTC -> TT uses a fixed 69.184 s offset (37 leap seconds + 32.184 s), valid
    for 2017-present and the configured 2026-2030 window. The resulting error
    from future leap-second changes (<1 s) is negligible next to the analytic
    ephemeris accuracy.
    """
    tt_offset = 69.184
    secs = np.array([(t - J2000).total_seconds() + tt_offset for t in times])
    return secs / 86400.0 / 36525.0
