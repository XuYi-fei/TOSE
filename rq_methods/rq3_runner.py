"""RQ3 utility/anomaly-rate summary derived from the official RQ1 matrix."""

from __future__ import annotations

import csv
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from .holdout_runner import RQ1HoldoutRunner, RQ1_METHODS, SYSTEMS
from .metrics import enrich_summary_row


RQ3_FIELDS = [
    "system",
    "method",
    "holdout_count",
    "AR",
    "utility",
    "FN",
    "FP",
    "MTD",
    "MLD",
    "precision",
    "recall",
    "f1_score",
]


class RQ3Runner:
    """Compute RQ3 metrics on top of the official RQ1 protocol."""

    def __init__(
        self,
        data_root: str | Path = "data_rq1_holdout",
        methods: list[str] | None = None,
        systems: list[str] | None = None,
        output_dir: str | Path = "rq_results/rq3",
        learned_root: str | Path = "clustering_results_rq1_holdout",
        baseline_identity_root: str | Path = "data",
    ):
        self.data_root = Path(data_root)
        self.methods = [method.upper() for method in (methods or RQ1_METHODS)]
        self.systems = list(systems or SYSTEMS)
        self.output_dir = Path(output_dir)
        self.learned_root = Path(learned_root)
        self.baseline_identity_root = Path(baseline_identity_root)

    def run(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        runner = RQ1HoldoutRunner(
            data_root=self.data_root,
            methods=self.methods,
            systems=self.systems,
            output_dir=self.output_dir / "_rq1_replay",
            learned_root=self.learned_root,
            baseline_identity_root=self.baseline_identity_root,
        )
        per_holdout_rows, summary_rows = runner.run()
        rq3_holdout_rows = [enrich_summary_row(dict(row)) for row in per_holdout_rows]
        rq3_summary_rows = [enrich_summary_row(dict(row)) for row in summary_rows]
        self._write_reports(rq3_holdout_rows, rq3_summary_rows)
        return rq3_holdout_rows, rq3_summary_rows

    def _write_reports(self, per_holdout_rows: list[dict[str, Any]], summary_rows: list[dict[str, Any]]) -> None:
        summary_dir = self.output_dir / "summary"
        summary_dir.mkdir(parents=True, exist_ok=True)
        holdout_csv = summary_dir / "rq3_per_holdout_summary.csv"
        holdout_json = summary_dir / "rq3_per_holdout_summary.json"
        system_csv = summary_dir / "rq3_system_summary.csv"
        system_json = summary_dir / "rq3_system_summary.json"

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
            writer = csv.DictWriter(handle, fieldnames=RQ3_FIELDS)
            writer.writeheader()
            writer.writerows(
                {
                    key: row.get(key)
                    for key in RQ3_FIELDS
                }
                for row in summary_rows
            )
        system_json.write_text(
            json.dumps(
                {"generated_at": datetime.now().isoformat(), "rows": summary_rows},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
