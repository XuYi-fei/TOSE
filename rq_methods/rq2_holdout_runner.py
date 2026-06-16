"""Unified RQ2 runner for holdout-based evaluation."""

from __future__ import annotations

import csv
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from baseline_methods.evaluator import BaselineEvaluator, aggregate_results
from baseline_methods.identifier import BaselineIdentifier

from .group_adapter import GroupMethodRunner
from .holdout_runner import SYSTEMS, SUMMARY_FIELDS, aggregate_holdout_rows, build_holdout_paths
from .metrics import enrich_summary_row


RQ2_METHODS = ["GROUP", "PRO", "GPD"]
RQ2_BASELINE_METHOD_MAP = {
    "PRO": "PRD",
    "GPD": "GPD",
}


class RQ2HoldoutRunner:
    """Run the standardized RQ2 protocol.

    All methods are trained and tested per holdout unit:

    - GROUP: use holdout-specific learned distributions
    - PRO: identify PRD on the holdout identity split, report as PRO
    - GPD: identify GPD on the holdout identity split
    """

    def __init__(
        self,
        data_root: str | Path = "data_rq1_holdout",
        methods: list[str] | None = None,
        systems: list[str] | None = None,
        output_dir: str | Path = "rq_results/rq2",
        learned_root: str | Path = "clustering_results_rq1_holdout",
    ):
        self.data_root = Path(data_root)
        self.methods = [method.upper() for method in (methods or RQ2_METHODS)]
        self.systems = list(systems or SYSTEMS)
        self.output_dir = Path(output_dir)
        self.learned_root = Path(learned_root)

    def _iter_holdout_dirs(self, system: str) -> list[Path]:
        system_dir = self.data_root / system
        return sorted(path for path in system_dir.glob("holdout_*") if path.is_dir())

    def _run_group_for_system(self, system: str, holdout_dirs: list[Path]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if "GROUP" not in self.methods:
            return rows

        group_runner = GroupMethodRunner(
            output_dir=self.output_dir,
            learned_root=self.learned_root,
        )
        for holdout_dir in holdout_dirs:
            holdout_name = holdout_dir.name
            paths = build_holdout_paths(self.data_root, system, holdout_name)
            row = group_runner.run_system_with_overrides(
                system,
                learned_path=self.learned_root / system / holdout_name / "learned_distributions.yaml",
                test_data_path=paths["abnormal"],
                output_dir=self.output_dir / system / holdout_name,
            )
            rows.append(enrich_summary_row({**row, "holdout_unit": holdout_name.removeprefix("holdout_")}))
        return rows

    def _run_holdout_baselines_for_system(self, system: str, holdout_dirs: list[Path]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        baseline_methods = [method for method in self.methods if method in RQ2_BASELINE_METHOD_MAP]
        if not baseline_methods:
            return rows

        identifier = BaselineIdentifier(system)
        for holdout_dir in holdout_dirs:
            holdout_name = holdout_dir.name
            paths = build_holdout_paths(self.data_root, system, holdout_name)

            for rq2_method in baseline_methods:
                baseline_method = RQ2_BASELINE_METHOD_MAP[rq2_method]
                baseline_config = identifier.identify(baseline_method, paths["identity"])
                method_output_dir = self.output_dir / "baseline_methods" / system / holdout_name
                baseline_config.write_json(method_output_dir / f"{rq2_method}.json")

                evaluator = BaselineEvaluator(system, baseline_config)
                trace_results = evaluator.evaluate_directory(paths["abnormal"])
                output_path = method_output_dir / f"detection_results_{rq2_method}.json"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(
                    json.dumps([result.__dict__ for result in trace_results], indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                row = aggregate_results(system, rq2_method, trace_results)
                rows.append(enrich_summary_row({**row, "holdout_unit": holdout_name.removeprefix("holdout_")}))

        return rows

    def run(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        per_holdout_rows: list[dict[str, Any]] = []

        for system in self.systems:
            holdout_dirs = self._iter_holdout_dirs(system)
            per_holdout_rows.extend(self._run_holdout_baselines_for_system(system, holdout_dirs))
            per_holdout_rows.extend(self._run_group_for_system(system, holdout_dirs))

        summary_rows = aggregate_holdout_rows(per_holdout_rows)
        self._write_reports(per_holdout_rows, summary_rows)
        return per_holdout_rows, summary_rows

    def _write_reports(self, per_holdout_rows: list[dict[str, Any]], summary_rows: list[dict[str, Any]]) -> None:
        summary_dir = self.output_dir / "summary"
        summary_dir.mkdir(parents=True, exist_ok=True)
        holdout_csv = summary_dir / "rq2_holdout_per_holdout_summary.csv"
        holdout_json = summary_dir / "rq2_holdout_per_holdout_summary.json"
        system_csv = summary_dir / "rq2_holdout_system_summary.csv"
        system_json = summary_dir / "rq2_holdout_system_summary.json"

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
