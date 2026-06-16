#!/usr/bin/env python3
"""Run the standardized holdout-based RQ2 protocol."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rq_methods.holdout_runner import SYSTEMS
from rq_methods.rq2_holdout_runner import RQ2_METHODS, RQ2HoldoutRunner


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--systems",
        nargs="+",
        default=SYSTEMS,
        choices=SYSTEMS,
        help="Subject systems to evaluate.",
    )
    parser.add_argument(
        "--methods",
        nargs="+",
        default=RQ2_METHODS,
        choices=RQ2_METHODS,
        help="RQ2 methods to evaluate.",
    )
    parser.add_argument("--data-root", default="data_rq1_holdout", type=Path)
    parser.add_argument("--output-dir", default="rq_results/rq2", type=Path)
    parser.add_argument("--learned-root", default="clustering_results_rq1_holdout", type=Path)
    args = parser.parse_args()

    runner = RQ2HoldoutRunner(
        systems=args.systems,
        methods=args.methods,
        data_root=args.data_root,
        output_dir=args.output_dir,
        learned_root=args.learned_root,
    )
    _, rows = runner.run()
    for row in rows:
        print(
            f"{row['system']},{row['method']}: "
            f"FN={row['FN']:.2f}%, FP={row['FP']:.2f}%, "
            f"MTD={row['MTD']:.2f}, holdouts={row['holdout_count']}"
        )
    print(f"summary: {args.output_dir / 'summary' / 'rq2_holdout_system_summary.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
