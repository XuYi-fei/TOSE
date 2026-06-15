#!/usr/bin/env python3
"""Generate standardized holdout RQ1 datasets."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rq_methods.holdout_dataset import generate_holdout_dataset_root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default="data", type=Path)
    parser.add_argument("--output-root", default="data_rq1_holdout", type=Path)
    parser.add_argument("--systems", nargs="+", default=["rubis", "bsn", "swat", "wadi"])
    parser.add_argument("--identity-traces", type=int, default=200)
    parser.add_argument("--abnormal-traces", type=int, default=200)
    parser.add_argument("--boundary-trim-points", type=int, default=10)
    args = parser.parse_args()

    layouts = generate_holdout_dataset_root(
        data_root=args.data_root,
        output_root=args.output_root,
        systems=args.systems,
        identity_trace_count=args.identity_traces,
        abnormal_trace_count=args.abnormal_traces,
        boundary_trim_points=args.boundary_trim_points,
    )
    for system, layout in layouts.items():
        print(f"{system}: holdout_units={len(layout.holdout_units)}")
    print(f"output: {args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
