"""Mid-project acceptance test: compare the candidates from the terminal.

Answers the Phase 3 checkpoint question without the website:

    If a lander arrives at three candidate lunar south-pole sites on
    December 1, 2026, which sites best satisfy our sunlight and direct-to-Earth
    visibility requirements? What changes if the landing is delayed to
    December 11?

It reads the committed JPL Horizons series and the committed two-tier LOLA
horizon masks (``/api/phase3`` / ``/api/mission-report`` in process - no
network), prints one table per mission window, and writes a machine-readable
document for Phase 4.

    cd backend
    python scripts/analyze_mission.py --start 2026-12-01 --days 7 --compare-all
    python scripts/analyze_mission.py --start 2026-12-11 --days 7 --compare-all

Only the mission windows that have a committed series are accepted. Another
date is an error listing the available windows: the CLI never substitutes
synthetic terrain or extrapolated ephemeris for missing Horizons data.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.errors import LunaNavError
from app.core.settings import Settings, get_settings
from app.services.mission_report import mission_report
from app.services.site_series import SeriesWindow, mission_windows

SCHEMA = "lunanav.mission_comparison.v1"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = ROOT / "backend" / "outputs"
DELTA_FIELDS = (
    ("sun_visible_pct", "Sun", " pts"),
    ("earth_visible_pct", "Earth", " pts"),
    ("both_visible_pct", "Both", " pts"),
    ("longest_sun_blackout_hours", "Darkness", " h"),
    ("longest_earth_blackout_hours", "Blackout", " h"),
)
NOTES = [
    "Sun above the skyline is a precondition for solar power, not a power estimate; Earth "
    "above the skyline is direct line of sight, not a working communications link.",
    "A requirement verdict is a constraint check, not a landing-safety or mission-feasibility "
    "claim, and it does not rank the sites.",
    "A value limited by the analysis window is shown with '>='; 'unknown' is not a pass.",
]


def _parse_start(text: str) -> datetime:
    text = text.strip()
    if "T" in text or text.endswith("Z"):
        when = parse_iso(text)
    else:
        when = datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if when.minute or when.second or when.microsecond:
        raise ValueError(
            f"start {text!r} must be on the hour, because the committed series is hourly"
        )
    return when


def parse_iso(text: str) -> datetime:
    """ISO-8601 UTC; a trailing Z is required, naive input is rejected."""
    if not text.endswith("Z"):
        raise ValueError(f"{text!r} must be UTC ISO-8601 with a trailing Z")
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def resolve_window(settings: Settings, start_text: str, days: float) -> SeriesWindow:
    """The committed mission window matching this start and duration exactly."""
    start = _parse_start(start_text)
    wanted_seconds = days * 86400.0
    for window in mission_windows(settings):
        if window.start == start and abs((window.end - window.start).total_seconds()
                                         - wanted_seconds) <= 1.0:
            return window
    available = "; ".join(
        f"{w.start:%Y-%m-%dT%H:%M}Z..{w.end:%Y-%m-%dT%H:%M}Z ({w.key})"
        for w in mission_windows(settings)
    )
    raise ValueError(
        f"No committed JPL Horizons series covers {start:%Y-%m-%dT%H:%M}Z for "
        f"{days:g} days. Available windows: {available}. Add one with "
        "scripts/fetch_horizons.py; do not substitute synthetic or extrapolated data."
    )


def build_document(settings: Settings, window: SeriesWindow,
                   sites: list[str]) -> dict:
    """Every selected site's mission report for this window, plus the delay delta."""
    if not sites:
        raise ValueError("no sites selected for the comparison")
    reports = [mission_report(site_id=site, window=window.key, settings=settings)
               for site in sites]
    others = [w for w in mission_windows(settings) if w.key != window.key]
    delay = []
    for index, site in enumerate(sites):
        row = {"site_id": site, "compare_to_window": others[0].key if others else None,
               "available": False, "deltas": {}, "censored_metrics": []}
        if others:
            try:
                other = mission_report(site_id=site, window=others[0].key, settings=settings)
            except LunaNavError as exc:
                row["reason"] = str(getattr(exc, "message", exc))
            else:
                row.update({
                    "available": True,
                    "satisfied": other["requirements"]["satisfied"],
                    "checks": other["requirements"]["checks"],
                    "metric_source": f"/api/mission-report?site_id={site}"
                                     f"&window={others[0].key}",
                })
                deltas: dict[str, float | None] = {}
                censored: list[str] = []
                for name, _, _ in DELTA_FIELDS:
                    value, limited = _delta(other["metrics"], reports[index]["metrics"], name)
                    deltas[name] = value
                    if limited:
                        censored.append(name)
                row["deltas"] = deltas
                row["censored_metrics"] = censored
        delay.append(row)
    return {
        "schema": SCHEMA,
        "window": {
            "key": window.key,
            "label": window.label,
            "start_utc": reports[0]["window"]["start_utc"],
            "stop_utc": reports[0]["window"]["stop_utc"],
            "steps": reports[0]["window"]["step"],
            "samples": reports[0]["window"]["samples"],
        },
        "requirements_source": reports[0]["requirements"]["source"],
        "thresholds": {
            check["id"]: check["threshold"] for check in reports[0]["requirements"]["checks"]
        },
        "sites": reports,
        "delay": delay,
        "notes": NOTES,
    }


def _metric(metrics: list[dict], metric_id: str) -> tuple[float | None, bool]:
    for metric in metrics:
        if metric["id"] == metric_id:
            return metric.get("value"), bool(metric.get("censored"))
    return None, False


def _delta(metrics: list[dict], base_metrics: list[dict],
           metric_id: str) -> tuple[float | None, bool]:
    """Difference and whether either side is window-limited (a lower bound)."""
    value, value_censored = _metric(metrics, metric_id)
    base, base_censored = _metric(base_metrics, metric_id)
    if value is None or base is None:
        return None, False
    return round(float(value) - float(base), 4), bool(value_censored or base_censored)


def _fmt_hours(value: float | None, censored: bool = False) -> str:
    if value is None:
        return "n/a"
    return f"{'≥' if censored else ''}{value:.1f} h"


def _fmt_pct(value: float | None, censored: bool = False) -> str:
    if value is None:
        return "n/a"
    return f"{'≥' if censored else ''}{value:.1f}%"


def render_report(document: dict) -> str:
    """The human-readable table plus per-requirement explanations."""
    window = document["window"]
    lines = [
        "LunaNav — Phase 3 mid-project comparison",
        f"Window: {window['label']}  ({window['start_utc']} to {window['stop_utc']} UTC, "
        f"{window['samples']} hourly samples)",
        "Basis:  terrain-adjusted geometry (committed LOLA horizon mask), "
        "NASA JPL Horizons Sun/Earth positions",
        f"Requirements: {document['requirements_source']}",
        "",
        f"{'Site':20s} {'Sun':>8s} {'Earth':>8s} {'Both':>8s} "
        f"{'Longest darkness':>17s} {'Longest blackout':>17s}  Verdict",
        "-" * 96,
    ]
    for report in document["sites"]:
        metrics = report["metrics"]
        sun, sun_c = _metric(metrics, "sun_visible_pct")
        earth, earth_c = _metric(metrics, "earth_visible_pct")
        both, both_c = _metric(metrics, "both_visible_pct")
        dark, dark_c = _metric(metrics, "longest_sun_blackout_hours")
        blackout, blackout_c = _metric(metrics, "longest_earth_blackout_hours")
        satisfied = report["requirements"]["satisfied"]
        verdict = {True: "met", False: "not met", None: "undecided"}[satisfied]
        lines.append(
            f"{report['site']['site_id']:20s} {_fmt_pct(sun, sun_c):>8s} "
            f"{_fmt_pct(earth, earth_c):>8s} {_fmt_pct(both, both_c):>8s} "
            f"{_fmt_hours(dark, dark_c):>17s} {_fmt_hours(blackout, blackout_c):>17s}  {verdict}"
        )

    lines.extend(["", "Requirement detail:"])
    for report in document["sites"]:
        for check in report["requirements"]["checks"]:
            if check["status"] == "met":
                continue
            comparison = "at least" if check["comparison"] == "at_least" else "at most"
            value = check["value"]
            shown = ("n/a" if value is None
                     else f"{value:.1f}{check['unit']}")
            if check["censored"] and check["status"] == "unknown":
                censored = " (window-limited: the true value cannot be decided from this window)"
            elif check["censored"]:
                censored = " (the true interval is at least this long)"
            else:
                censored = ""
            lines.append(
                f"  {report['site']['site_id']}: {check['label']} — {shown} measured "
                f"against {comparison} {check['threshold']:.1f}{check['unit']}: "
                f"{check['status']}{censored}"
            )

    if document.get("delay"):
        compare_key = (document["delay"][0].get("compare_to_window")
                       if document["delay"] else None) or "other window"
        lines.extend([
            "",
            f"Delay effect ({compare_key} window minus {document['window']['key']} window):",
        ])
        header = "  " + f"{'Site':20s}" + "".join(f"{label:>12s}" for _, label, _ in DELTA_FIELDS)
        lines.append(header)
        for row in document["delay"]:
            if not row["available"]:
                lines.append(f"  {row['site_id']:20s}  not available: {row.get('reason', '')}")
                continue
            cells = ""
            for name, _, unit in DELTA_FIELDS:
                value = row["deltas"].get(name)
                text = "n/a" if value is None else f"{value:+.1f}{unit}"
                if name in row.get("censored_metrics", []):
                    text += "*"
                cells += f"{text:>12s}"
            lines.append(f"  {row['site_id']:20s}{cells}")
        lines.append("  * delta uses a window-limited (lower-bound) metric: indicative, not exact.")

    lines.extend(["", *[f"Note: {note}" for note in document["notes"]]])
    return "\n".join(lines)


def write_json(document: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    return path


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        description="Compare the Phase 3 candidate sites against the mission requirements."
    )
    parser.add_argument("--start", default=settings.simulation.default_landing.strftime("%Y-%m-%d"),
                        help="UTC landing date or ISO-8601 timestamp (default: 2026-12-01)")
    parser.add_argument("--days", type=float, default=settings.raw["mission"]["duration_days"],
                        help="mission duration in Earth days (default: 7)")
    parser.add_argument("--site", action="append", dest="sites",
                        help="candidate site id; repeatable (default: every mission candidate)")
    parser.add_argument("--compare-all", action="store_true",
                        help="compare every candidate site (the default)")
    parser.add_argument("--json", type=Path, default=None,
                        help="JSON output path (default: backend/outputs/mission_comparison_<window>.json)")
    args = parser.parse_args(argv)

    sites = args.sites or list(settings.raw["mission"]["candidate_sites"])
    try:
        window = resolve_window(settings, args.start, args.days)
        document = build_document(settings, window, sites)
    except (ValueError, LunaNavError) as exc:
        print(f"error: {getattr(exc, 'message', exc)}")
        return 2

    print(render_report(document))
    output = args.json or DEFAULT_OUTPUT_DIR / f"mission_comparison_{window.key}.json"
    print(f"\nJSON: {write_json(document, output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
