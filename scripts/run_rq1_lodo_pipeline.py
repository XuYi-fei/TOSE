#!/usr/bin/env python3
"""End-to-end RQ1 LODO pipeline: dataset -> group clustering -> methods matrix."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def _run(cmd: list[str], cwd: Path) -> None:
    result = subprocess.run(cmd, cwd=cwd, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default="data", type=Path)
    parser.add_argument("--lodo-root", default="data_rq1_lodo", type=Path)
    parser.add_argument("--learned-root", default="clustering_results_rq1_lodo", type=Path)
    parser.add_argument("--output-dir", default="rq_results/rq1_lodo", type=Path)
    parser.add_argument("--systems", nargs="+", default=["rubis", "bsn", "swat", "wadi"])
    args = parser.parse_args()

    cwd = Path(__file__).resolve().parents[1]
    python = sys.executable

    _run(
        [
            python,
            "scripts/build_rq1_lodo_dataset.py",
            "--data-root",
            str(args.data_root),
            "--output-root",
            str(args.lodo_root),
            "--systems",
            *args.systems,
        ],
        cwd,
    )
    _run(
        [
            python,
            "scripts/build_rq1_lodo_group_distributions.py",
            "--data-root",
            str(args.lodo_root),
            "--output-root",
            str(args.learned_root),
            "--systems",
            *args.systems,
        ],
        cwd,
    )
    _run(
        [
            python,
            "scripts/run_rq1_lodo_methods_matrix.py",
            "--data-root",
            str(args.lodo_root),
            "--output-dir",
            str(args.output_dir),
            "--learned-root",
            str(args.learned_root),
            "--systems",
            *args.systems,
        ],
        cwd,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
