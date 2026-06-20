"""Validate consistency between the RQ1 GROUP matrix and the RQ4 GROUP-only matrix."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable


SHARED_FIELDS = [
    "cluster_count",
    "tp_count",
    "fp_count",
    "fn_count",
    "precision",
    "recall",
    "f1_score",
]


def _read_matrix_rows(csv_path: str | Path) -> dict[tuple[str, str], dict[str, str]]:
    with Path(csv_path).open(encoding="utf-8") as handle:
        return {
            (row["system"], row["algorithm"]): row
            for row in csv.DictReader(handle)
        }


def compare_group_matrix_rows(
    rq1_row: dict[str, str],
    rq4_row: dict[str, str],
) -> list[tuple[str, str, str]]:
    diffs: list[tuple[str, str, str]] = []
    for field in SHARED_FIELDS:
        if str(rq1_row.get(field, "")) != str(rq4_row.get(field, "")):
            diffs.append((field, str(rq1_row.get(field, "")), str(rq4_row.get(field, ""))))
    return diffs


def validate_rq4_matches_rq1_summary(
    rq1_summary_csv: str | Path,
    rq4_summary_csv: str | Path,
) -> list[dict[str, object]]:
    rq1_rows = _read_matrix_rows(rq1_summary_csv)
    rq4_rows = _read_matrix_rows(rq4_summary_csv)

    mismatches: list[dict[str, object]] = []
    for key, rq4_row in sorted(rq4_rows.items()):
        rq1_row = rq1_rows.get(key)
        if rq1_row is None:
            mismatches.append(
                {
                    "key": key,
                    "reason": "missing_in_rq1",
                }
            )
            continue
        diffs = compare_group_matrix_rows(rq1_row, rq4_row)
        if diffs:
            mismatches.append(
                {
                    "key": key,
                    "reason": "field_mismatch",
                    "diffs": diffs,
                }
            )
    return mismatches


def format_mismatches(mismatches: Iterable[dict[str, object]]) -> str:
    lines: list[str] = []
    for mismatch in mismatches:
        key = mismatch["key"]
        reason = mismatch["reason"]
        if reason == "missing_in_rq1":
            lines.append(f"{key}: missing in RQ1 summary")
            continue
        diffs = mismatch.get("diffs", [])
        diff_text = ", ".join(f"{field} rq1={rq1} rq4={rq4}" for field, rq1, rq4 in diffs)
        lines.append(f"{key}: {diff_text}")
    return "\n".join(lines)
