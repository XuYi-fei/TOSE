#!/usr/bin/env python3
"""
RQ2 kmeans 数值聚类 baseline 检测入口。
"""
import argparse
import logging
import re
import sys
from pathlib import Path

from anomaly_detection.core.evaluator import AnomalyEvaluator
from anomaly_detection.visualization.reporter import DetectionReporter
from rq2_kmeans_baseline.config import BaselineDetectionConfig
from rq2_kmeans_baseline.detector import KMeansDistanceDetector
from rq2_kmeans_baseline.summary import write_summary


MODEL_PATTERN = re.compile(r"baseline_model_k(?P<k>\d+)\.yaml$")


def setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def _discover_model_paths(models_dir: str) -> list[tuple[int, Path]]:
    discovered = []
    for path in sorted(Path(models_dir).glob("baseline_model_k*.yaml")):
        match = MODEL_PATTERN.match(path.name)
        if match:
            discovered.append((int(match.group("k")), path))
    if not discovered:
        raise ValueError(f"目录{models_dir}中未找到baseline_model_k*.yaml")
    return discovered


def run_kmeans_baseline_detection(config_path: str, output_dir: str | None = None, verbose: bool = False) -> bool:
    setup_logging(verbose)
    logger = logging.getLogger(__name__)
    try:
        config = BaselineDetectionConfig.from_yaml(config_path)
        if output_dir:
            config.output_dir = output_dir

        trace_files = sorted(Path(config.test_data_path).glob("*.txt"))
        if not trace_files:
            raise ValueError(f"目录{config.test_data_path}中未找到trace文件")

        summary_rows = []
        for k, model_path in _discover_model_paths(config.baseline_models_dir):
            detector = KMeansDistanceDetector.from_yaml(model_path)
            evaluator = AnomalyEvaluator(detector, config.system_type)
            trace_metrics = [evaluator.evaluate_trace(trace_file) for trace_file in trace_files]
            aggregated = evaluator.aggregate_results(trace_metrics)

            reporter = DetectionReporter(
                config.output_dir,
                file_suffix=f"k{k}",
                cluster_count=k,
                clustering_algorithm="kmeans_numeric_distance",
            )
            reporter.generate_report(aggregated, config.system_type)
            reporter.generate_json_report(aggregated, config.system_type, str(model_path))
            reporter.generate_csv_report(aggregated, config.system_type)

            summary_rows.append(
                {
                    "k": k,
                    "cluster_count": k,
                    "tp_count": aggregated.tp_count,
                    "fp_count": aggregated.fp_count,
                    "fn_count": aggregated.fn_count,
                    "tn_count": aggregated.tn_count,
                    "precision": aggregated.precision,
                    "recall": aggregated.recall,
                    "f1_score": aggregated.f1_score,
                    "avg_delay_loops": aggregated.avg_delay_loops,
                    "model_path": str(model_path),
                }
            )

        write_summary(config.output_dir, config.best_k_metric, summary_rows)
        logger.info("已生成 %s 组RQ2 baseline检测结果", len(summary_rows))
        return True
    except Exception as exc:
        logger.error("RQ2 baseline 检测失败: %s", exc, exc_info=verbose)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="RQ2 kmeans 数值聚类 baseline 检测")
    parser.add_argument("--config", "-c", required=True, help="配置文件路径")
    parser.add_argument("--output", "-o", help="输出目录")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志")
    args = parser.parse_args()
    sys.exit(0 if run_kmeans_baseline_detection(args.config, args.output, args.verbose) else 1)


if __name__ == "__main__":
    main()
