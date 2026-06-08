#!/usr/bin/env python3
"""Convert `data/wadi_trace` CSV traces into generic-framework `.txt` traces."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict


SOURCE_METRIC_COLUMN = "HMI_2_LT_001.PV"
TARGET_TIME_COLUMN = "simTime(s)"
TARGET_SEGMENT_COLUMN = "segment_label"
SPLITS = ("identity", "abnormal")


def _convert_trace_file(source_path: Path, output_path: Path) -> None:
    with source_path.open(newline="", encoding="utf-8") as source_handle:
        reader = csv.DictReader(source_handle)
        if SOURCE_METRIC_COLUMN not in (reader.fieldnames or []):
            raise ValueError(f"Missing required metric column in {source_path}: {SOURCE_METRIC_COLUMN}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as output_handle:
            writer = csv.DictWriter(
                output_handle,
                fieldnames=[TARGET_TIME_COLUMN, SOURCE_METRIC_COLUMN, TARGET_SEGMENT_COLUMN],
            )
            writer.writeheader()

            for index, row in enumerate(reader, start=1):
                metric_value = row.get(SOURCE_METRIC_COLUMN)
                if metric_value in (None, ""):
                    continue

                writer.writerow(
                    {
                        TARGET_TIME_COLUMN: index,
                        SOURCE_METRIC_COLUMN: metric_value,
                        TARGET_SEGMENT_COLUMN: row.get(TARGET_SEGMENT_COLUMN, ""),
                    }
                )


def convert_trace_dataset(source_root: Path | str, output_root: Path | str) -> Dict[str, int]:
    """Convert all WaDi trace CSV files into generic `.txt` traces."""
    source_root = Path(source_root)
    output_root = Path(output_root)

    summary = {
        "identity_count": 0,
        "abnormal_count": 0,
        "total_count": 0,
    }

    for split in SPLITS:
        source_dir = source_root / split
        output_dir = output_root / split
        if not source_dir.exists():
            raise FileNotFoundError(f"Missing source split directory: {source_dir}")

        converted_count = 0
        for source_path in sorted(source_dir.glob("*.csv")):
            output_path = output_dir / f"{source_path.stem}.txt"
            _convert_trace_file(source_path, output_path)
            converted_count += 1

        summary[f"{split}_count"] = converted_count
        summary["total_count"] += converted_count

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert WaDi trace CSV files into the generic multi-algorithm dataset layout."
    )
    parser.add_argument(
        "--source-root",
        default="data/wadi_trace",
        help="Source directory containing identity/abnormal CSV traces.",
    )
    parser.add_argument(
        "--output-root",
        default="data/wadi",
        help="Output directory for the generic identity/abnormal TXT traces.",
    )
    args = parser.parse_args()

    summary = convert_trace_dataset(args.source_root, args.output_root)
    print(
        "Converted WaDi generic dataset: "
        f"identity={summary['identity_count']}, "
        f"abnormal={summary['abnormal_count']}, "
        f"total={summary['total_count']}"
    )


if __name__ == "__main__":
    main()
