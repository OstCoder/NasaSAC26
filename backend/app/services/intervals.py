"""Interval detection and interval algebra.

Times are POSIX seconds (float). An interval is ``(start, end)`` with
start < end. Visibility edges are placed by linear interpolation of the
clearance (elevation minus skyline) between samples, so edge timing is much
finer than the sampling step when clearance varies smoothly.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

Span = tuple[float, float]


def intervals_from_clearance(t: np.ndarray, clearance: np.ndarray) -> list[Span]:
    """Spans where clearance > 0, with interpolated edges."""
    t = np.asarray(t, float)
    c = np.asarray(clearance, float)
    if t.size == 0:
        return []
    if t.size == 1:
        return [(t[0], t[0])] if c[0] > 0 else []
    pos = c > 0
    spans: list[Span] = []
    start = t[0] if pos[0] else None
    for i in range(len(t) - 1):
        if pos[i] != pos[i + 1]:
            denom = c[i] - c[i + 1]
            frac = c[i] / denom if denom != 0 else 0.5
            tc = t[i] + (t[i + 1] - t[i]) * float(np.clip(frac, 0.0, 1.0))
            if pos[i]:
                spans.append((start, tc))
                start = None
            else:
                start = tc
    if start is not None:
        spans.append((start, t[-1]))
    return [s for s in spans if s[1] > s[0]]


def intersect(a: Sequence[Span], b: Sequence[Span]) -> list[Span]:
    out, i, j = [], 0, 0
    while i < len(a) and j < len(b):
        lo = max(a[i][0], b[j][0])
        hi = min(a[i][1], b[j][1])
        if hi > lo:
            out.append((lo, hi))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return out


def union(a: Sequence[Span], b: Sequence[Span]) -> list[Span]:
    merged: list[list[float]] = []
    for s, e in sorted(list(a) + list(b)):
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def complement(a: Sequence[Span], window: Span) -> list[Span]:
    out, cur = [], window[0]
    for s, e in sorted(a):
        if s > cur:
            out.append((cur, min(s, window[1])))
        cur = max(cur, e)
        if cur >= window[1]:
            break
    if cur < window[1]:
        out.append((cur, window[1]))
    return [(s, e) for s, e in out if e > s]


def total_seconds(a: Sequence[Span]) -> float:
    return float(sum(e - s for s, e in a))


def longest(a: Sequence[Span], window: Span, tol: float = 1.0) -> tuple[float | None, bool]:
    """(longest duration in seconds, censored) — censored if it touches a window edge."""
    if not a:
        return None, False
    s, e = max(a, key=lambda x: x[1] - x[0])
    censored = abs(s - window[0]) < tol or abs(e - window[1]) < tol
    return e - s, censored
