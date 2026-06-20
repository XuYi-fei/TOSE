#!/usr/bin/env python3
"""Run RQ4 GROUP-only comparison across clustering algorithms."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rq_methods.rq4_ari import ALGORITHMS
from rq_methods.rq4_consistency import format_mismatches, validate_rq4_matches_rq1_summary
from rq_methods.rq4_runner import RQ4Runner
from scripts.run_rq1_detection_matrix import SYSTEM_CONFIG_MAP


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--systems",
        nargs="*",
        default=list(SYSTEM_CONFIG_MAP.keys()),
        choices=list(SYSTEM_CONFIG_MAP.keys()),
        help="Subject systems to evaluate.",
    )
    parser.add_argument(
        "--algorithms",
        nargs="*",
        default=ALGORITHMS,
        choices=ALGORITHMS,
        help="Clustering algorithms to compare under GROUP.",
    )
    parser.add_argument("--output-dir", default="rq_results/rq4", type=Path)
    parser.add_argument(
        "--detection-mode",
        choices=["pointwise", "bocpd"],
        help="Override configured GROUP detection mode.",
    )
    parser.add_argument(
        "--reuse-detection-results",
        action="store_true",
        help="Reuse existing detection_results/<system>/detection_results_<algorithm>.json instead of rerunning GROUP detection.",
    )
    parser.add_argument(
        "--skip-consistency-check",
        action="store_true",
        help="Skip checking that shared RQ4 fields match detection_results/summary/detection_matrix_summary.csv.",
    )
    parser.add_argument(
        "--rq1-summary",
        default="detection_results/summary/detection_matrix_summary.csv",
        type=Path,
        help="RQ1 GROUP four-algorithm matrix summary CSV used for consistency checking.",
    )
    args = parser.parse_args(argv)

    rows = RQ4Runner(
        systems=args.systems,
        algorithms=args.algorithms,
        output_dir=args.output_dir,
        detection_mode_override=args.detection_mode,
        reuse_detection_results=args.reuse_detection_results,
    ).run()
    for row in rows:
        print(
            f"{row['system']},{row['algorithm']}: "
            f"ARI={row['ari']:.4f}, "
            f"TP={row['tp_count']} FP={row['fp_count']} FN={row['fn_count']} "
            f"Precision={row['precision']:.4f} Recall={row['recall']:.4f}"
        )
    rq4_summary_path = args.output_dir / "summary" / "rq4_group_algorithms_summary.csv"
    print(f"summary: {rq4_summary_path}")
    if not args.skip_consistency_check:
        mismatches = validate_rq4_matches_rq1_summary(args.rq1_summary, rq4_summary_path)
        if mismatches:
            print("consistency check failed:")
            print(format_mismatches(mismatches))
            return 1
        print("consistency check: RQ4 matches the shared RQ1 GROUP matrix fields.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
