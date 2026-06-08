#!/usr/bin/env python3
"""Run ASE-style RQ1 baseline matrix on TOSE data."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from baseline_methods.config import METHODS
from baseline_methods.evaluator import BaselineExperimentRunner


def build_system_paths(systems: list[str], data_root: Path) -> dict[str, dict[str, Path]]:
    return {
        system: {
            "identity": data_root / system / "identity",
            "abnormal": data_root / system / "abnormal",
        }
        for system in systems
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--systems",
        nargs="+",
        default=["rubis", "bsn", "swat", "wadi"],
        choices=["rubis", "bsn", "swat", "wadi"],
        help="Subject systems to evaluate.",
    )
    parser.add_argument(
        "--methods",
        nargs="+",
        default=list(METHODS),
        choices=list(METHODS),
        help="Baseline methods to evaluate.",
    )
    parser.add_argument("--data-root", default="data", type=Path)
    parser.add_argument("--output-dir", default="baseline_results", type=Path)
    args = parser.parse_args()

    runner = BaselineExperimentRunner(
        systems=build_system_paths(args.systems, args.data_root),
        output_dir=args.output_dir,
        methods=args.methods,
    )
    rows = runner.run()
    for row in rows:
        print(
            f"{row['system']},{row['method']}: "
            f"FN={row['FN']:.2f}%, FP={row['FP']:.2f}%, MTD={row['MTD']:.2f}, AR={row['AR']:.2f}%"
        )
    print(f"summary: {args.output_dir / 'summary' / 'rq1_baseline_summary.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
