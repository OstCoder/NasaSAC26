"""Check that every dataset is present, consistent and self-describing.

This is the Phase 2 Task 4 acceptance check: it reads the site catalogue, the
Task 2 series, the Task 3 terrain reference and the LROC/IAU reference files,
then verifies that the same site is the same point in every one of them.

Usage (from backend/):
    python scripts/check_datasets.py           # table + problems; exit 1 on problems
    python scripts/check_datasets.py --json    # the full catalogue payload
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.dataset_catalogue import build_catalogue  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="print the catalogue payload and exit")
    args = ap.parse_args(argv)

    payload = build_catalogue()
    problems = payload["problems"]
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0 if not problems else 1

    print(f"{'dataset':16s} {'kind':13s} {'records':>8s}  {'status':11s}  path")
    for entry in payload["datasets"]:
        records = "-" if entry["records"] is None else str(entry["records"])
        status = "ok" if entry["available"] else "unavailable"
        print(f"{entry['id']:16s} {entry['kind']:13s} {records:>8s}  {status:11s}  {entry['path']}")
        if not entry["available"]:
            print(f"{'':16s} {'':13s} {'':>8s}  -> {entry['unavailable_reason']}")

    cache = next(d for d in payload["datasets"] if d["id"] == "cache")
    print(f"\ncache: Horizons months {cache['details']['horizons_months']}, "
          f"{cache['details']['trek_tiles']} Moon Trek tile files")

    print("\nall datasets consistent" if not problems else f"\n{len(problems)} problem(s) found")
    for problem in problems:
        print(f"  FAILED: {problem}", file=sys.stderr)
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
