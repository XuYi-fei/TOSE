#!/usr/bin/env python3
"""Check whether the shared GROUP fields in RQ4 match the RQ1 detection matrix."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rq_methods.rq4_consistency import format_mismatches, validate_rq4_matches_rq1_summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rq1-summary",
        default="detection_results/summary/detection_matrix_summary.csv",
        type=Path,
        help="RQ1 GROUP four-algorithm matrix summary CSV.",
    )
    parser.add_argument(
        "--rq4-summary",
        default="rq_results/rq4/summary/rq4_group_algorithms_summary.csv",
        type=Path,
        help="RQ4 GROUP-only summary CSV.",
    )
    args = parser.parse_args()

    mismatches = validate_rq4_matches_rq1_summary(args.rq1_summary, args.rq4_summary)
    if mismatches:
        print("RQ4 does not match the shared RQ1 GROUP matrix fields:")
        print(format_mismatches(mismatches))
        return 1

    print("RQ4 matches the shared RQ1 GROUP matrix fields.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
