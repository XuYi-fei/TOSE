"""RQ4 GROUP-only comparison across clustering algorithms with ARI."""

from __future__ import annotations

import csv
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from scripts.run_rq1_detection_matrix import ALGORITHMS, SYSTEM_CONFIG_MAP, evaluate_system_algorithm
from .detection_matrix_results import load_detection_result_row

from .rq4_ari import (
    SYSTEM_CLUSTERING_CONFIG_MAP,
    build_clustering_result_for_ari,
    compute_ari_from_result,
)


class RQ4Runner:
    """Run GROUP detection across four clustering algorithms and append ARI."""

    def __init__(
        self,
        systems: list[str] | None = None,
        algorithms: list[str] | None = None,
        output_dir: str | Path = "rq_results/rq4",
        detection_mode_override: str | None = None,
        reuse_detection_results: bool = False,
    ):
        self.systems = list(systems or list(SYSTEM_CONFIG_MAP.keys()))
        self.algorithms = list(algorithms or ALGORITHMS)
        self.output_dir = Path(output_dir)
        self.detection_mode_override = detection_mode_override
        self.reuse_detection_results = reuse_detection_results

    def run(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for system in self.systems:
            detection_config_path = SYSTEM_CONFIG_MAP[system]
            clustering_config_path = SYSTEM_CLUSTERING_CONFIG_MAP[system]
            clustering_result = build_clustering_result_for_ari(
                system,
                algorithms=self.algorithms,
                config_path=clustering_config_path,
            )
            for algorithm in self.algorithms:
                row = self._load_or_evaluate_detection_row(
                    system,
                    algorithm,
                    detection_config_path,
                )
                row["ari"] = compute_ari_from_result(
                    system,
                    algorithm,
                    clustering_result,
                )
                rows.append(row)
        self._write_reports(rows)
        return rows

    def _load_or_evaluate_detection_row(
        self,
        system: str,
        algorithm: str,
        detection_config_path: str,
    ) -> dict[str, Any]:
        if self.reuse_detection_results:
            reused = load_detection_result_row(system, algorithm)
            if reused is not None:
                return reused
        return evaluate_system_algorithm(
            system,
            algorithm,
            detection_config_path,
            detection_mode_override=self.detection_mode_override,
        )

    def _write_reports(self, rows: list[dict[str, Any]]) -> None:
        summary_dir = self.output_dir / "summary"
        summary_dir.mkdir(parents=True, exist_ok=True)
        csv_path = summary_dir / "rq4_group_algorithms_summary.csv"
        json_path = summary_dir / "rq4_group_algorithms_summary.json"

        fieldnames = [
            "system",
            "algorithm",
            "ari",
            "detection_mode",
            "cluster_count",
            "total_traces",
            "tp_count",
            "fp_count",
            "fn_count",
            "tn_count",
            "tp_rate",
            "fp_rate",
            "fn_rate",
            "precision",
            "recall",
            "f1_score",
            "hazard_lambda",
            "max_run_length",
            "state_prior",
            "changepoint_posterior_threshold",
            "raw_anomaly_rule",
            "tail_persistence_threshold",
        ]

        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        json_path.write_text(
            json.dumps(
                {
                    "generated_at": datetime.now().isoformat(),
                    "rows": rows,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
