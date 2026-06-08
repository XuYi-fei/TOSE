"""Unified RQ1 method runner for baselines and GROUP."""

from __future__ import annotations

import csv
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from baseline_methods.config import METHODS as BASELINE_METHODS
from baseline_methods.evaluator import BaselineExperimentRunner

from .group_adapter import GroupMethodRunner, SYSTEM_CONFIG_MAP


RQ1_METHODS = ["SWD", "ARD", "PRD", "GPD", "GROUP"]
SYSTEMS = ["rubis", "bsn", "swat", "wadi"]

SUMMARY_FIELDS = [
    "system",
    "method",
    "total_traces",
    "tp_count",
    "fp_count",
    "fn_count",
    "tn_count",
    "tp_rate",
    "fp_rate",
    "fn_rate",
    "FN",
    "FP",
    "MTD",
    "MLD",
    "AR",
    "precision",
    "recall",
    "f1_score",
    "cluster_count",
    "clustering_algorithm",
    "detection_mode",
    "learned_distributions",
]


def build_system_paths(systems: list[str], data_root: Path) -> dict[str, dict[str, Path]]:
    return {
        system: {
            "identity": data_root / system / "identity",
            "abnormal": data_root / system / "abnormal",
        }
        for system in systems
    }


class RQ1MethodsRunner:
    """Run all RQ1 methods through one reproducible entry point."""

    def __init__(
        self,
        systems: list[str] | dict[str, dict[str, Path | str]] | None = None,
        methods: list[str] | None = None,
        data_root: str | Path = "data",
        output_dir: str | Path = "rq_results/rq1",
        group_config_map: dict[str, str | Path] | None = None,
        learned_root: str | Path = "clustering_results",
        detection_mode_override: str | None = None,
    ):
        if isinstance(systems, dict):
            self.system_paths = systems
            self.systems = list(systems)
        else:
            self.systems = list(systems or SYSTEMS)
            self.system_paths = build_system_paths(self.systems, Path(data_root))
        self.methods = [method.upper() for method in (methods or RQ1_METHODS)]
        unsupported = sorted(set(self.methods) - set(RQ1_METHODS))
        if unsupported:
            raise ValueError(f"不支持的 RQ1 方法: {', '.join(unsupported)}")

        self.output_dir = Path(output_dir)
        self.group_config_map = group_config_map or SYSTEM_CONFIG_MAP
        self.learned_root = Path(learned_root)
        self.detection_mode_override = detection_mode_override

    def run(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        baseline_methods = [method for method in self.methods if method in BASELINE_METHODS]
        if baseline_methods:
            baseline_runner = BaselineExperimentRunner(
                systems=self.system_paths,
                output_dir=self.output_dir / "baseline_methods",
                methods=baseline_methods,
            )
            rows.extend(baseline_runner.run())

        if "GROUP" in self.methods:
            group_runner = GroupMethodRunner(
                config_map=self.group_config_map,
                output_dir=self.output_dir,
                learned_root=self.learned_root,
                detection_mode_override=self.detection_mode_override,
            )
            for system in self.systems:
                rows.append(group_runner.run_system(system))

        self.write_summary(rows)
        return rows

    def write_summary(self, rows: list[dict[str, Any]]) -> None:
        summary_dir = self.output_dir / "summary"
        summary_dir.mkdir(parents=True, exist_ok=True)
        csv_path = summary_dir / "rq1_methods_summary.csv"
        json_path = summary_dir / "rq1_methods_summary.json"

        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        json_path.write_text(
            json.dumps(
                {
                    "generated_at": datetime.now().isoformat(),
                    "systems": self.systems,
                    "methods": self.methods,
                    "rows": rows,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
