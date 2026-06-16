#!/usr/bin/env python3
"""Run RQ3 anomaly-rate and utility summary on top of the official RQ1 workflow."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rq_methods.holdout_runner import RQ1_METHODS, SYSTEMS
from rq_methods.rq3_runner import RQ3Runner


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
        default=RQ1_METHODS,
        choices=RQ1_METHODS,
        help="RQ3 reuses the official RQ1 methods.",
    )
    parser.add_argument("--data-root", default="data_rq1_holdout", type=Path)
    parser.add_argument("--output-dir", default="rq_results/rq3", type=Path)
    parser.add_argument("--learned-root", default="clustering_results_rq1_holdout", type=Path)
    parser.add_argument("--baseline-identity-root", default="data", type=Path)
    args = parser.parse_args()

    runner = RQ3Runner(
        systems=args.systems,
        methods=args.methods,
        data_root=args.data_root,
        output_dir=args.output_dir,
        learned_root=args.learned_root,
        baseline_identity_root=args.baseline_identity_root,
    )
    _, rows = runner.run()
    for row in rows:
        print(
            f"{row['system']},{row['method']}: "
            f"AR={row['AR']:.4f}%, utility={row['utility']:.4f}%, "
            f"FN={row['FN']:.2f}%, FP={row['FP']:.2f}%"
        )
    print(f"summary: {args.output_dir / 'summary' / 'rq3_system_summary.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
