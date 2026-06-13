#!/usr/bin/env python3
"""Run baseline and GROUP RQ1 methods on leave-one-distribution-out datasets."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rq_methods.lodo_runner import RQ1LodoRunner, RQ1_METHODS


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default="data_rq1_lodo", type=Path)
    parser.add_argument("--output-dir", default="rq_results/rq1_lodo", type=Path)
    parser.add_argument("--learned-root", default="clustering_results_rq1_lodo", type=Path)
    parser.add_argument("--systems", nargs="+", default=["rubis", "bsn", "swat", "wadi"])
    parser.add_argument("--methods", nargs="+", default=RQ1_METHODS, choices=RQ1_METHODS)
    args = parser.parse_args()

    runner = RQ1LodoRunner(
        data_root=args.data_root,
        output_dir=args.output_dir,
        learned_root=args.learned_root,
        systems=args.systems,
        methods=args.methods,
    )
    _, summary_rows = runner.run()
    for row in summary_rows:
        print(
            f"{row['system']},{row['method']}: "
            f"FN={row['FN']:.2f}%, FP={row['FP']:.2f}%, "
            f"MTD={row['MTD']:.2f}, holdouts={row['holdout_count']}"
        )
    print(f"summary: {args.output_dir / 'summary' / 'rq1_lodo_system_summary.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
