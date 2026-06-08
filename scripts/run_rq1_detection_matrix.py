#!/usr/bin/env python3
"""
运行 RQ1 四系统 × 四算法 的统一检测矩阵。
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from anomaly_detection.config.config import DetectionConfig
from anomaly_detection.core.detector import AnomalyDetector, BOCPDDetector
from anomaly_detection.core.evaluator import AnomalyEvaluator
from anomaly_detection.visualization.reporter import DetectionReporter


SYSTEM_CONFIG_MAP = {
    "rubis": "configs/rubis_detection_config.yaml",
    "bsn": "configs/bsn_detection_config.yaml",
    "swat": "configs/swat_detection_config.yaml",
    "wadi": "configs/wadi_generic_detection_config.yaml",
}

ALGORITHMS = [
    "hdbscan",
    "gmm",
    "affinity_propagation",
    "mean_shift",
]


def evaluate_system_algorithm(
    system: str,
    algorithm: str,
    config_path: str,
    detection_mode_override: str | None = None,
) -> Dict[str, float | int | str]:
    config = DetectionConfig.from_yaml(config_path)
    if detection_mode_override:
        config.detection.mode = detection_mode_override
    learned_path = Path(f"clustering_results/{system}/learned_distributions_{algorithm}.yaml")
    if not learned_path.exists():
        raise FileNotFoundError(f"缺少辨识结果: {learned_path}")

    if config.detection.mode == "bocpd":
        detector = BOCPDDetector.from_yaml(
            str(learned_path),
            sigma_threshold=config.detection.sigma_threshold,
            p_value_alpha=config.detection.p_value_alpha,
            hazard_lambda=config.detection.bocpd.hazard_lambda,
            max_run_length=config.detection.bocpd.max_run_length,
            state_prior=config.detection.bocpd.state_prior,
            changepoint_posterior_threshold=config.detection.bocpd.changepoint_posterior_threshold,
            raw_anomaly_rule=config.detection.bocpd.raw_anomaly_rule,
            tail_persistence_threshold=config.detection.bocpd.tail_persistence_threshold,
        )
    else:
        detector = AnomalyDetector.from_yaml(
            str(learned_path),
            sigma_threshold=config.detection.sigma_threshold,
            p_value_alpha=config.detection.p_value_alpha,
        )
    detector.context_matching_strategy = config.detection.context_matching_strategy
    detector.apply_context_mu_shift = config.detection.apply_context_mu_shift

    evaluator = AnomalyEvaluator(
        detector,
        config.system_type,
        alarm_count_policy=config.detection.alarm_count_policy,
        trace_alarm_confidence=config.detection.trace_alarm_confidence,
    )

    trace_files = sorted(Path(config.test_data_path).glob("*.txt"))
    trace_metrics = [evaluator.evaluate_trace(trace_file) for trace_file in trace_files]
    aggregated = evaluator.aggregate_results(trace_metrics)

    reporter = DetectionReporter(
        config.output.dir,
        file_suffix=algorithm,
        cluster_count=len(detector.distributions),
        clustering_algorithm=detector.clustering_algorithm,
        alarm_count_policy=config.detection.alarm_count_policy,
        sigma_threshold=config.detection.sigma_threshold,
        point_anomaly_probability=detector.point_anomaly_probability,
        aggregation_method=config.detection.aggregation_method,
        trace_alarm_confidence=config.detection.trace_alarm_confidence,
        context_matching_strategy=config.detection.context_matching_strategy,
        apply_context_mu_shift=config.detection.apply_context_mu_shift,
        context_calibration_enabled=detector.context_calibration_model is not None,
        detection_mode=getattr(detector, "detection_mode", config.detection.mode),
        bocpd_config=(
            {
                "hazard_lambda": config.detection.bocpd.hazard_lambda,
                "max_run_length": config.detection.bocpd.max_run_length,
                "state_prior": config.detection.bocpd.state_prior,
                "changepoint_posterior_threshold": config.detection.bocpd.changepoint_posterior_threshold,
                "raw_anomaly_rule": config.detection.bocpd.raw_anomaly_rule,
                "tail_persistence_threshold": config.detection.bocpd.tail_persistence_threshold,
            }
            if config.detection.mode == "bocpd"
            else None
        ),
    )
    reporter.generate_report(aggregated, config.system_type)
    reporter.generate_json_report(aggregated, config.system_type, config_path)
    reporter.generate_csv_report(aggregated, config.system_type)

    total = aggregated.total_traces or 1
    return {
        "system": system,
        "algorithm": algorithm,
        "detection_mode": config.detection.mode,
        "cluster_count": len(detector.distributions),
        "total_traces": aggregated.total_traces,
        "tp_count": aggregated.tp_count,
        "fp_count": aggregated.fp_count,
        "fn_count": aggregated.fn_count,
        "tn_count": aggregated.tn_count,
        "tp_rate": aggregated.tp_count / total,
        "fp_rate": aggregated.fp_count / total,
        "fn_rate": aggregated.fn_count / total,
        "precision": aggregated.precision,
        "recall": aggregated.recall,
        "f1_score": aggregated.f1_score,
        "hazard_lambda": config.detection.bocpd.hazard_lambda if config.detection.mode == "bocpd" else "",
        "max_run_length": config.detection.bocpd.max_run_length if config.detection.mode == "bocpd" else "",
        "state_prior": config.detection.bocpd.state_prior if config.detection.mode == "bocpd" else "",
        "changepoint_posterior_threshold": (
            config.detection.bocpd.changepoint_posterior_threshold
            if config.detection.mode == "bocpd"
            else ""
        ),
        "raw_anomaly_rule": config.detection.bocpd.raw_anomaly_rule if config.detection.mode == "bocpd" else "",
        "tail_persistence_threshold": (
            config.detection.bocpd.tail_persistence_threshold if config.detection.mode == "bocpd" else ""
        ),
    }


def write_summary(rows: List[Dict[str, float | int | str]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "detection_matrix_summary.csv"
    json_path = output_dir / "detection_matrix_summary.json"

    fieldnames = [
        "system",
        "algorithm",
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

    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

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


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 RQ1 检测矩阵")
    parser.add_argument(
        "--systems",
        nargs="*",
        default=list(SYSTEM_CONFIG_MAP.keys()),
        help="要运行的系统列表",
    )
    parser.add_argument(
        "--algorithms",
        nargs="*",
        default=ALGORITHMS,
        help="要运行的聚类算法列表",
    )
    parser.add_argument(
        "--summary-dir",
        default="detection_results/summary",
        help="汇总结果输出目录",
    )
    parser.add_argument(
        "--detection-mode",
        choices=["pointwise", "bocpd"],
        help="覆盖配置中的检测模式",
    )
    args = parser.parse_args()

    rows: List[Dict[str, float | int | str]] = []
    for system in args.systems:
        config_path = SYSTEM_CONFIG_MAP[system]
        for algorithm in args.algorithms:
            row = evaluate_system_algorithm(
                system,
                algorithm,
                config_path,
                detection_mode_override=args.detection_mode,
            )
            rows.append(row)
            print(
                f"[RQ1] {system}/{algorithm}/{row['detection_mode']}: "
                f"TP={row['tp_count']} FP={row['fp_count']} FN={row['fn_count']} "
                f"Precision={row['precision']:.4f} Recall={row['recall']:.4f}"
            )

    write_summary(rows, Path(args.summary_dir))


if __name__ == "__main__":
    main()
