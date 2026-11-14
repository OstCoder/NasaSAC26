"""Validate the Phase 2 NASA datasets end to end (Task 5).

Usage (from backend/):

    python scripts/validate_nasa_data.py            # validate the committed files
    python scripts/validate_nasa_data.py --json     # the full report as JSON
    python scripts/validate_nasa_data.py --live     # also re-query Horizons and rewrite the evidence

Offline (the default) this recomputes every azimuth/elevation in the Task 2
series with LunaNav's independent analytic model, compares the committed records
with the committed Horizons reference table, and checks coordinates, observer,
units, UTC handling, continuity and cross-site geometry. It reads files only and
needs no network.

``--live`` additionally fetches, for each candidate site, a fresh one-hour
observer table from JPL Horizons at the initial landing date and compares it
with the committed records, then rewrites:

    data/reference/horizons_reference.json   independent 12 h Horizons sample
    data/reference/nasa_validation.json      the Task 5 report (with live evidence)

Exit status is 1 if any check fails, so the script can gate a release.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.errors import LunaNavError  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.services.nasa_validation import (  # noqa: E402
    build_reference,
    build_report,
    live_checks,
    problems,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = ROOT / "data" / "reference" / "nasa_validation.json"
DEFAULT_REFERENCE = ROOT / "data" / "reference" / "horizons_reference.json"

EXAMPLES = """examples:
  python scripts/validate_nasa_data.py
  python scripts/validate_nasa_data.py --json > /tmp/validation.json
  python scripts/validate_nasa_data.py --live
"""


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Validate the Phase 2 NASA datasets (Task 5).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EXAMPLES,
    )
    ap.add_argument("--live", action="store_true",
                    help="re-query JPL Horizons and rewrite the committed evidence files")
    ap.add_argument("--write", action="store_true",
                    help="write the report even without --live (live evidence is carried over)")
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    ap.add_argument("--timeout", type=float, default=90.0, help="per-request timeout in seconds")
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="report output path")
    ap.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE,
                    help="Horizons reference output path")
    return ap.parse_args(argv)


def _print_report(report: dict) -> None:
    summary = report["summary"]
    print(f"NASA data validation (Phase 2 Task 5) — {summary['status'].upper()}: "
          f"{summary['passed']}/{summary['checks']} checks, {summary['records_checked']} records")
    print(f"{'check':30s} {'result':7s} detail")
    for check in report["checks"]:
        print(f"{check['id']:30s} {'ok' if check['passed'] else 'FAILED':7s} {check['detail']}")
    live = report.get("live")
    if live:
        print(f"\nlive Horizons verification ({live.get('retrieved_utc')}):")
        for check in live.get("checks", []):
            print(f"{check['id']:30s} {'ok' if check['passed'] else 'FAILED':7s} {check['detail']}")


def main(argv=None) -> int:
    args = parse_args(argv)
    settings = get_settings()
    live = None
    failures: list[str] = []

    if args.live:
        previous = None
        if args.reference.exists():
            try:
                previous = json.loads(args.reference.read_text())
            except json.JSONDecodeError:
                previous = None
        try:
            reference = build_reference(settings=settings, timeout_s=args.timeout)
            live = live_checks(reference, previous, timeout_s=args.timeout, settings=settings)
        except (LunaNavError, ValueError) as exc:
            print(f"FAILED: the live Horizons verification could not run: {exc}", file=sys.stderr)
            return 1
        args.reference.parent.mkdir(parents=True, exist_ok=True)
        args.reference.write_text(json.dumps(reference, indent=2) + "\n")
        print(f"wrote {args.reference.relative_to(ROOT)}: {reference['rows']} rows, "
              f"{len(reference['requests'])} requests")
        failures.extend(
            f"{check['id']}: {problem}"
            for check in live.get("checks", [])
            if not check["passed"]
            for problem in check["problems"]
        )

    report = build_report(settings=settings, live=live)
    failures.extend(problems(report))

    if args.live or args.write:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
        print(f"wrote {args.report.relative_to(ROOT)}")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_report(report)
        for line in failures:
            print(f"  FAILED: {line}", file=sys.stderr)
        print("all checks passed" if not failures else f"{len(failures)} problem(s) found")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
