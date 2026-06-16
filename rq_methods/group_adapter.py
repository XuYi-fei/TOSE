"""GROUP adapter for the unified RQ1 method workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from anomaly_detection.config.config import DetectionConfig
from anomaly_detection.core.detector import AnomalyDetector, BOCPDDetector
from anomaly_detection.core.evaluator import AggregatedMetrics, AnomalyEvaluator
from anomaly_detection.visualization.reporter import DetectionReporter
from .metrics import enrich_summary_row


SYSTEM_CONFIG_MAP = {
    "rubis": "configs/rubis_detection_config.yaml",
    "bsn": "configs/bsn_detection_config.yaml",
    "swat": "configs/swat_detection_config.yaml",
    "wadi": "configs/wadi_generic_detection_config.yaml",
}


def _build_detector(config: DetectionConfig, learned_path: Path) -> AnomalyDetector:
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
    return detector


def group_summary_row(
    system: str,
    aggregate: AggregatedMetrics,
    detector: AnomalyDetector,
    learned_path: Path,
) -> dict[str, Any]:
    total = aggregate.total_traces or 1
    avg_delay = aggregate.avg_delay_loops if aggregate.avg_delay_loops is not None else 0.0
    return enrich_summary_row({
        "system": system,
        "method": "GROUP",
        "total_traces": aggregate.total_traces,
        "tp_count": aggregate.tp_count,
        "fp_count": aggregate.fp_count,
        "fn_count": aggregate.fn_count,
        "tn_count": aggregate.tn_count,
        "tp_rate": aggregate.tp_count / total,
        "fp_rate": aggregate.fp_count / total,
        "fn_rate": aggregate.fn_count / total,
        "FN": aggregate.fn_count / total * 100.0,
        "FP": aggregate.fp_count / total * 100.0,
        "MTD": avg_delay,
        "MLD": avg_delay,
        "AR": (
            aggregate.abnormal_time / aggregate.abnormal_total_time * 100.0
            if aggregate.abnormal_total_time
            else 0.0
        ),
        "precision": aggregate.precision,
        "recall": aggregate.recall,
        "f1_score": aggregate.f1_score,
        "cluster_count": len(detector.distributions),
        "clustering_algorithm": detector.clustering_algorithm or "",
        "detection_mode": getattr(detector, "detection_mode", "pointwise"),
        "learned_distributions": str(learned_path),
    })


class GroupMethodRunner:
    """Run the current TOSE GROUP detector as one RQ1 method."""

    def __init__(
        self,
        config_map: dict[str, str | Path] | None = None,
        output_dir: str | Path = "rq_results/rq1",
        learned_root: str | Path = "clustering_results",
        detection_mode_override: str | None = None,
    ):
        self.config_map = dict(config_map or SYSTEM_CONFIG_MAP)
        self.output_dir = Path(output_dir)
        self.learned_root = Path(learned_root)
        self.detection_mode_override = detection_mode_override

    def run_system(self, system: str) -> dict[str, Any]:
        return self.run_system_with_overrides(system)

    def run_system_with_overrides(
        self,
        system: str,
        *,
        learned_path: Path | None = None,
        test_data_path: Path | None = None,
        output_dir: Path | None = None,
    ) -> dict[str, Any]:
        if system not in self.config_map:
            raise KeyError(f"缺少 {system} 的 GROUP 检测配置")

        config_path = Path(self.config_map[system])
        config = DetectionConfig.from_yaml(str(config_path))
        if self.detection_mode_override:
            config.detection.mode = self.detection_mode_override

        resolved_learned_path = learned_path or (self.learned_root / system / "learned_distributions.yaml")
        if not resolved_learned_path.exists():
            raise FileNotFoundError(f"缺少最佳聚类辨识结果: {resolved_learned_path}")
        config.learned_distributions = str(resolved_learned_path)

        if test_data_path is not None:
            config.test_data_path = str(test_data_path)

        if output_dir is not None:
            config.output.dir = str(output_dir / system / "GROUP")
        else:
            config.output.dir = str(self.output_dir / system / "GROUP")

        detector = _build_detector(config, resolved_learned_path)
        evaluator = AnomalyEvaluator(
            detector,
            config.system_type,
            alarm_count_policy=config.detection.alarm_count_policy,
            trace_alarm_confidence=config.detection.trace_alarm_confidence,
        )
        trace_metrics = [
            evaluator.evaluate_trace(trace_file)
            for trace_file in sorted(Path(config.test_data_path).glob("*.txt"))
        ]
        aggregate = evaluator.aggregate_results(trace_metrics)

        reporter = DetectionReporter(
            config.output.dir,
            file_suffix="GROUP",
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
                    "changepoint_posterior_threshold": (
                        config.detection.bocpd.changepoint_posterior_threshold
                    ),
                    "raw_anomaly_rule": config.detection.bocpd.raw_anomaly_rule,
                    "tail_persistence_threshold": config.detection.bocpd.tail_persistence_threshold,
                }
                if config.detection.mode == "bocpd"
                else None
            ),
        )
        reporter.generate_report(aggregate, config.system_type)
        reporter.generate_json_report(aggregate, config.system_type, str(config_path))
        reporter.generate_csv_report(aggregate, config.system_type)

        return group_summary_row(system, aggregate, detector, resolved_learned_path)
