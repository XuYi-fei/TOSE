"""Run RQ1 methods over leave-one-distribution-out datasets."""

from __future__ import annotations

import csv
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from baseline_methods.config import METHODS as BASELINE_METHODS
from baseline_methods.evaluator import BaselineExperimentRunner

from .group_adapter import GroupMethodRunner


RQ1_METHODS = ["SWD", "ARD", "PRD", "GPD", "GROUP"]
SUMMARY_FIELDS = [
    "system",
    "method",
    "holdout_count",
    "total_traces",
    "tp_count",
    "fp_count",
    "fn_count",
    "tn_count",
    "FN",
    "FP",
    "MTD",
    "MLD",
    "AR",
    "precision",
    "recall",
    "f1_score",
]


def build_lodo_system_paths(data_root: Path, system: str, holdout_dir_name: str) -> dict[str, Path]:
    base_dir = data_root / system / holdout_dir_name
    return {
        "identity": base_dir / "identity",
        "abnormal": base_dir / "abnormal",
    }


def aggregate_holdout_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["system"], row["method"]), []).append(row)

    summary_rows = []
    for (system, method), group in sorted(grouped.items()):
        holdout_count = len(group)
        summary_rows.append(
            {
                "system": system,
                "method": method,
                "holdout_count": holdout_count,
                "total_traces": sum(int(row["total_traces"]) for row in group),
                "tp_count": sum(int(row["tp_count"]) for row in group),
                "fp_count": sum(int(row["fp_count"]) for row in group),
                "fn_count": sum(int(row["fn_count"]) for row in group),
                "tn_count": sum(int(row["tn_count"]) for row in group),
                "FN": sum(float(row["FN"]) for row in group) / holdout_count,
                "FP": sum(float(row["FP"]) for row in group) / holdout_count,
                "MTD": sum(float(row["MTD"]) for row in group) / holdout_count,
                "MLD": sum(float(row["MLD"]) for row in group) / holdout_count,
                "AR": sum(float(row["AR"]) for row in group) / holdout_count,
                "precision": sum(float(row["precision"]) for row in group) / holdout_count,
                "recall": sum(float(row["recall"]) for row in group) / holdout_count,
                "f1_score": sum(float(row["f1_score"]) for row in group) / holdout_count,
            }
        )
    return summary_rows


class RQ1LodoRunner:
    """Run baseline and GROUP methods for every holdout-unit dataset."""

    def __init__(
        self,
        data_root: str | Path = "data_rq1_lodo",
        methods: list[str] | None = None,
        systems: list[str] | None = None,
        output_dir: str | Path = "rq_results/rq1_lodo",
        learned_root: str | Path = "clustering_results_rq1_lodo",
    ):
        self.data_root = Path(data_root)
        self.methods = [method.upper() for method in (methods or RQ1_METHODS)]
        self.systems = systems or ["rubis", "bsn", "swat", "wadi"]
        self.output_dir = Path(output_dir)
        self.learned_root = Path(learned_root)

    def _iter_holdout_dirs(self, system: str) -> list[Path]:
        system_dir = self.data_root / system
        return sorted(path for path in system_dir.glob("holdout_*") if path.is_dir())

    def run(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        per_holdout_rows: list[dict[str, Any]] = []
        baseline_methods = [method for method in self.methods if method in BASELINE_METHODS]
        include_group = "GROUP" in self.methods

        for system in self.systems:
            holdout_dirs = self._iter_holdout_dirs(system)
            for holdout_dir in holdout_dirs:
                holdout_name = holdout_dir.name
                paths = build_lodo_system_paths(self.data_root, system, holdout_name)
                if baseline_methods:
                    baseline_runner = BaselineExperimentRunner(
                        systems={system: paths},
                        output_dir=self.output_dir / "baseline_methods" / system / holdout_name,
                        methods=baseline_methods,
                    )
                    for row in baseline_runner.run():
                        per_holdout_rows.append({**row, "holdout_unit": holdout_name.removeprefix("holdout_")})

                if include_group:
                    group_runner = GroupMethodRunner(
                        config_map={system: _build_lodo_config_path(system)},
                        output_dir=self.output_dir / system / holdout_name,
                        learned_root=self.learned_root,
                    )
                    row = group_runner.run_system_with_overrides(
                        system,
                        learned_path=self.learned_root / system / holdout_name / "learned_distributions.yaml",
                        test_data_path=paths["abnormal"],
                        output_dir=self.output_dir / system / holdout_name,
                    )
                    per_holdout_rows.append({**row, "holdout_unit": holdout_name.removeprefix("holdout_")})

        summary_rows = aggregate_holdout_rows(per_holdout_rows)
        self._write_reports(per_holdout_rows, summary_rows)
        return per_holdout_rows, summary_rows

    def _write_reports(self, per_holdout_rows: list[dict[str, Any]], summary_rows: list[dict[str, Any]]) -> None:
        summary_dir = self.output_dir / "summary"
        summary_dir.mkdir(parents=True, exist_ok=True)
        holdout_csv = summary_dir / "rq1_lodo_per_holdout_summary.csv"
        holdout_json = summary_dir / "rq1_lodo_per_holdout_summary.json"
        system_csv = summary_dir / "rq1_lodo_system_summary.csv"
        system_json = summary_dir / "rq1_lodo_system_summary.json"

        holdout_fields = sorted({key for row in per_holdout_rows for key in row.keys()})
        with holdout_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=holdout_fields)
            writer.writeheader()
            writer.writerows(per_holdout_rows)
        holdout_json.write_text(
            json.dumps(
                {"generated_at": datetime.now().isoformat(), "rows": per_holdout_rows},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        with system_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
            writer.writeheader()
            writer.writerows(summary_rows)
        system_json.write_text(
            json.dumps(
                {"generated_at": datetime.now().isoformat(), "rows": summary_rows},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )


def _build_lodo_config_path(system: str) -> str:
    return {
        "rubis": "configs/rubis_detection_config.yaml",
        "bsn": "configs/bsn_detection_config.yaml",
        "swat": "configs/swat_detection_config.yaml",
        "wadi": "configs/wadi_generic_detection_config.yaml",
    }[system]
