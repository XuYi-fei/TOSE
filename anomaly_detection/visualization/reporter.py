"""
异常检测报告生成器

生成Markdown、JSON和CSV格式的检测报告
"""
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import logging
import json
import csv
import math

from ..core.evaluator import TraceEvaluationMetrics, AggregatedMetrics

logger = logging.getLogger(__name__)


class DetectionReporter:
    """异常检测报告生成器"""

    def __init__(
        self,
        output_dir: str,
        file_suffix: str = "",
        cluster_count: int | None = None,
        clustering_algorithm: str | None = None,
        alarm_count_policy: str | None = None,
        sigma_threshold: float | None = None,
        point_anomaly_probability: float | None = None,
        aggregation_method: str | None = None,
        trace_alarm_confidence: float | None = None,
        context_matching_strategy: str | None = None,
        apply_context_mu_shift: bool | None = None,
        context_calibration_enabled: bool | None = None,
        detection_mode: str = "pointwise",
        bocpd_config: Dict[str, Any] | None = None,
    ):
        """初始化报告生成器

        Args:
            output_dir: 输出目录
            file_suffix: 输出文件名后缀
            cluster_count: 辨识得到的聚类簇数
            clustering_algorithm: 生成分布参数的聚类算法名称
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.file_suffix = file_suffix.strip().strip("_")
        self.cluster_count = cluster_count
        self.clustering_algorithm = clustering_algorithm
        self.alarm_count_policy = alarm_count_policy
        self.sigma_threshold = sigma_threshold
        self.point_anomaly_probability = point_anomaly_probability
        self.aggregation_method = aggregation_method
        self.trace_alarm_confidence = trace_alarm_confidence
        self.context_matching_strategy = context_matching_strategy
        self.apply_context_mu_shift = apply_context_mu_shift
        self.context_calibration_enabled = context_calibration_enabled
        self.detection_mode = detection_mode
        self.bocpd_config = bocpd_config or {}

    def _theoretical_alarm_probability(self) -> float | None:
        if self.point_anomaly_probability is not None:
            return self.point_anomaly_probability
        if self.sigma_threshold is None:
            return None
        return math.erfc(self.sigma_threshold / math.sqrt(2.0))

    def _build_output_path(self, stem: str, suffix: str) -> Path:
        filename = f"{stem}_{self.file_suffix}{suffix}" if self.file_suffix else f"{stem}{suffix}"
        return self.output_dir / filename

    def generate_report(
        self,
        aggregated_metrics: AggregatedMetrics,
        system_type: str
    ) -> str:
        """生成Markdown报告

        Args:
            aggregated_metrics: 聚合的评估指标
            system_type: 系统类型

        Returns:
            报告文件路径
        """
        logger.info("生成异常检测报告...")

        report_path = self._build_output_path('detection_report', '.md')

        with open(report_path, 'w', encoding='utf-8') as f:
            # 标题
            f.write(f"# {system_type.upper()} 异常检测报告\\n\\n")

            # 1. 检测概览
            self._write_overview(f, aggregated_metrics, system_type)

            # 2. 性能指标
            self._write_performance_metrics(f, aggregated_metrics)

            # 3. 检测延迟分析
            if aggregated_metrics.avg_delay_loops is not None:
                self._write_detection_delay(f, aggregated_metrics)

            # 4. 异常案例
            self._write_anomaly_cases(f, aggregated_metrics)

        logger.info(f"报告已保存: {report_path}")
        return str(report_path)

    def _write_overview(self, f, metrics: AggregatedMetrics, system_type: str):
        """写入检测概览（trace级别）"""
        f.write("## 检测概览\\n\\n")
        f.write(f"- **系统类型**: {system_type.upper()}\\n")
        if self.clustering_algorithm:
            f.write(f"- **辨识算法**: {self.clustering_algorithm}\\n")
        if self.cluster_count is not None:
            f.write(f"- **聚类簇数**: {self.cluster_count}\\n")
        if self.alarm_count_policy:
            f.write(f"- **报警触发策略**: {self.alarm_count_policy}\\n")
        if self.trace_alarm_confidence is not None:
            f.write(f"- **trace报警置信度**: {self.trace_alarm_confidence}\\n")
        if self.aggregation_method:
            f.write(f"- **点级聚合策略**: {self.aggregation_method}\\n")
        if self.context_matching_strategy:
            f.write(f"- **上下文匹配策略**: {self.context_matching_strategy}\\n")
        if self.apply_context_mu_shift is not None:
            f.write(f"- **上下文均值校准**: {self.apply_context_mu_shift}\\n")
        if self.context_calibration_enabled is not None:
            f.write(f"- **已加载上下文校准模型**: {self.context_calibration_enabled}\\n")
        f.write(f"- **检测模式**: {self.detection_mode}\\n")
        if self.detection_mode == "bocpd":
            f.write(f"- **BOCPD hazard_lambda**: {self.bocpd_config.get('hazard_lambda')}\\n")
            f.write(f"- **BOCPD max_run_length**: {self.bocpd_config.get('max_run_length')}\\n")
            f.write(f"- **BOCPD state_prior**: {self.bocpd_config.get('state_prior')}\\n")
            f.write(
                f"- **BOCPD 变点后验阈值**: {self.bocpd_config.get('changepoint_posterior_threshold')}\\n"
            )
            f.write(f"- **BOCPD raw anomaly rule**: {self.bocpd_config.get('raw_anomaly_rule')}\\n")
        if self.sigma_threshold is not None:
            f.write(f"- **Sigma阈值**: {self.sigma_threshold}\\n")
        theoretical_probability = self._theoretical_alarm_probability()
        if theoretical_probability is not None:
            f.write(f"- **点级异常概率阈值**: {theoretical_probability:.6f}\\n")
        f.write(f"- **总trace数**: {metrics.total_traces}\\n")
        f.write(f"- **TP trace数**: {metrics.tp_count}\\n")
        f.write(f"- **FP trace数**: {metrics.fp_count}\\n")
        f.write(f"- **FN trace数**: {metrics.fn_count}\\n")
        f.write(f"- **TN trace数**: {metrics.tn_count}\\n\\n")

    def _write_performance_metrics(self, f, metrics: AggregatedMetrics):
        """写入性能指标（trace级别）"""
        f.write("## 性能指标\\n\\n")
        f.write("### 混淆矩阵（trace级别）\\n\\n")
        f.write("| 指标 | trace数 |\\n")
        f.write("|------|---------|\\n")
        f.write(f"| TP (真阳性) | {metrics.tp_count} |\\n")
        f.write(f"| FP (假阳性) | {metrics.fp_count} |\\n")
        f.write(f"| FN (假阴性) | {metrics.fn_count} |\\n")
        f.write(f"| TN (真阴性) | {metrics.tn_count} |\\n")
        f.write(f"| **总计** | {metrics.tp_count + metrics.fp_count + metrics.fn_count + metrics.tn_count} |\\n\\n")
        f.write("### 性能指标\\n\\n")
        f.write("| 指标 | 数值 | 百分比 |\\n")
        f.write("|------|------|--------|\\n")
        f.write(f"| Precision (精确率) | {metrics.precision:.4f} | {metrics.precision * 100:.2f}% |\\n")
        f.write(f"| Recall (召回率) | {metrics.recall:.4f} | {metrics.recall * 100:.2f}% |\\n")
        f.write(f"| F1 Score | {metrics.f1_score:.4f} | - |\\n\\n")

    def _write_detection_delay(self, f, metrics: AggregatedMetrics):
        """写入检测延迟统计（loops单位）"""
        f.write("## 检测延迟分析\\n\\n")
        f.write(f"- **平均检测延迟**: {metrics.avg_delay_loops:.2f} loops\\n")
        f.write(f"- **最小检测延迟**: {metrics.min_delay_loops} loops\\n")
        f.write(f"- **最大检测延迟**: {metrics.max_delay_loops} loops\\n\\n")

    def _write_anomaly_cases(self, f, metrics: AggregatedMetrics):
        """写入异常检测案例（trace级别分类）"""
        f.write("## Trace分类示例（前10个TP案例）\\n\\n")

        # 找出所有TP trace，按延迟排序
        tp_metrics = sorted(
            [m for m in metrics.trace_metrics if m.classification == 'TP'],
            key=lambda m: m.detection_delay_loops if m.detection_delay_loops is not None else 0
        )[:10]

        if not tp_metrics:
            f.write("未检测到TP trace\\n\\n")
            return

        f.write("| 文件名 | 分类 | 延迟(loops) | 检测点数 |\\n")
        f.write("|--------|------|-------------|----------|\\n")

        for m in tp_metrics:
            delay_str = f"{m.detection_delay_loops}" if m.detection_delay_loops is not None else "N/A"
            f.write(f"| {m.filename[:50]}... | {m.classification} | {delay_str} | {m.total_detection_count} |\\n")

        f.write("\\n")

    def generate_json_report(
        self,
        aggregated_metrics: AggregatedMetrics,
        system_type: str,
        config_path: str = None
    ) -> str:
        """生成JSON格式的检测结果（trace级别）

        Args:
            aggregated_metrics: 聚合的评估指标
            system_type: 系统类型
            config_path: 配置文件路径

        Returns:
            JSON文件路径
        """
        logger.info("生成JSON格式检测结果...")

        json_path = self._build_output_path('detection_results', '.json')

        # 构建结构化的检测结果（trace级别）
        results = {
            "metadata": {
                "system_type": system_type,
                "detection_time": datetime.now().isoformat(),
                "config_path": config_path,
                "clustering_algorithm": self.clustering_algorithm,
                "cluster_count": self.cluster_count,
                "alarm_count_policy": self.alarm_count_policy,
                "sigma_threshold": self.sigma_threshold,
                "p_value_alpha": self.point_anomaly_probability,
                "point_anomaly_probability": self._theoretical_alarm_probability(),
                "aggregation_method": self.aggregation_method,
                "trace_alarm_confidence": self.trace_alarm_confidence,
                "context_matching_strategy": self.context_matching_strategy,
                "apply_context_mu_shift": self.apply_context_mu_shift,
                "context_calibration_enabled": self.context_calibration_enabled,
                "detection_mode": self.detection_mode,
                "bocpd": self.bocpd_config if self.detection_mode == "bocpd" else None,
            },
            "summary": {
                "clustering_algorithm": self.clustering_algorithm,
                "cluster_count": self.cluster_count,
                "alarm_count_policy": self.alarm_count_policy,
                "sigma_threshold": self.sigma_threshold,
                "p_value_alpha": self.point_anomaly_probability,
                "point_anomaly_probability": self._theoretical_alarm_probability(),
                "aggregation_method": self.aggregation_method,
                "trace_alarm_confidence": self.trace_alarm_confidence,
                "context_matching_strategy": self.context_matching_strategy,
                "apply_context_mu_shift": self.apply_context_mu_shift,
                "context_calibration_enabled": self.context_calibration_enabled,
                "detection_mode": self.detection_mode,
                "bocpd": self.bocpd_config if self.detection_mode == "bocpd" else None,
                "total_traces": aggregated_metrics.total_traces,
                "tp_traces": aggregated_metrics.tp_count,
                "fp_traces": aggregated_metrics.fp_count,
                "fn_traces": aggregated_metrics.fn_count,
                "tn_traces": aggregated_metrics.tn_count,
                "alarm_trigger_rule": (
                    "first_raw_anomaly_triggers_trace_alarm"
                    if self.detection_mode == "bocpd"
                    else (
                        "raw_anomaly_count > binom_ppf(trace_alarm_confidence, observed_count, point_anomaly_probability)"
                        if self.alarm_count_policy
                        else None
                    )
                ),
            },
            "confusion_matrix": {
                "TP": aggregated_metrics.tp_count,
                "FP": aggregated_metrics.fp_count,
                "FN": aggregated_metrics.fn_count,
                "TN": aggregated_metrics.tn_count
            },
            "performance_metrics": {
                "precision": float(aggregated_metrics.precision),
                "recall": float(aggregated_metrics.recall),
                "f1_score": float(aggregated_metrics.f1_score)
            },
            "detection_delay": {
                "average_loops": float(aggregated_metrics.avg_delay_loops) if aggregated_metrics.avg_delay_loops else None,
                "minimum_loops": int(aggregated_metrics.min_delay_loops) if aggregated_metrics.min_delay_loops is not None else None,
                "maximum_loops": int(aggregated_metrics.max_delay_loops) if aggregated_metrics.max_delay_loops is not None else None
            },
            "trace_details": []
        }

        # 添加每个trace的详细信息
        for trace_metric in aggregated_metrics.trace_metrics:
            trace_detail = {
                "filename": trace_metric.filename,
                "classification": trace_metric.classification,
                "has_abn1": trace_metric.has_abn1,
                "abn1_start_time": float(trace_metric.abn1_start_time) if trace_metric.abn1_start_time is not None else None,
                "first_detection_time": float(trace_metric.first_detection_time) if trace_metric.first_detection_time is not None else None,
                "first_raw_anomaly_time": float(trace_metric.first_raw_anomaly_time) if trace_metric.first_raw_anomaly_time is not None else None,
                "detection_delay_loops": int(trace_metric.detection_delay_loops) if trace_metric.detection_delay_loops is not None else None,
                "total_detection_count": trace_metric.total_detection_count,
                "trigger_alarm_count": trace_metric.trigger_alarm_count,
                "trigger_allowed_count": trace_metric.trigger_allowed_count,
                "detection_mode": trace_metric.detection_mode,
                "first_detection_changepoint_probability": (
                    float(trace_metric.first_detection_changepoint_probability)
                    if trace_metric.first_detection_changepoint_probability is not None
                    else None
                ),
                "first_detection_run_length": trace_metric.first_detection_run_length,
                "first_detection_best_distribution": trace_metric.first_detection_best_distribution,
                "first_detection_best_tail_p_value": (
                    float(trace_metric.first_detection_best_tail_p_value)
                    if trace_metric.first_detection_best_tail_p_value is not None
                    else None
                ),
                "anomaly_points": [
                    {
                        "time": float(point.time),
                        "value": float(point.value),
                        "closest_distribution": point.closest_distribution,
                        "distribution_type": point.distribution_type,
                        "best_p_value": float(point.best_p_value),
                        "best_tail_p_value": (
                            float(point.best_tail_p_value)
                            if point.best_tail_p_value is not None
                            else None
                        ),
                        "best_log_likelihood": (
                            float(point.best_log_likelihood)
                            if point.best_log_likelihood is not None
                            else None
                        ),
                        "changepoint_probability": (
                            float(point.changepoint_probability)
                            if point.changepoint_probability is not None
                            else None
                        ),
                        "most_likely_run_length": point.most_likely_run_length,
                        "raw_anomaly_reasons": list(point.raw_anomaly_reasons),
                        "candidate_distribution_count": point.candidate_distribution_count,
                        "top_matches": point.top_matches,
                        "detection_mode": point.detection_mode,
                        "matched_context_key": point.matched_context_key,
                        "context_match_strategy": point.context_match_strategy,
                        "context_location_shift": float(point.context_location_shift),
                    }
                    for point in trace_metric.anomaly_points
                ],
            }
            results["trace_details"].append(trace_detail)

        # 保存JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"JSON结果已保存: {json_path}")
        return str(json_path)

    def generate_csv_report(
        self,
        aggregated_metrics: AggregatedMetrics,
        system_type: str
    ) -> str:
        """生成CSV格式的详细检测结果（trace级别）

        Args:
            aggregated_metrics: 聚合的评估指标
            system_type: 系统类型

        Returns:
            CSV文件路径
        """
        logger.info("生成CSV格式检测结果...")

        csv_path = self._build_output_path('detection_results', '.csv')

        # 定义CSV列（trace级别）
        fieldnames = [
            'clustering_algorithm',
            'cluster_count',
            'aggregation_method',
            'context_matching_strategy',
            'apply_context_mu_shift',
            'detection_mode',
            'filename',
            'classification',
            'abn1_start_time',
            'first_detection_time',
            'first_raw_anomaly_time',
            'delay_loops',
            'total_detections',
            'trigger_alarm_count',
            'trigger_allowed_count',
            'first_detection_changepoint_probability',
            'first_detection_run_length',
            'first_detection_best_distribution',
            'first_detection_best_tail_p_value',
        ]

        # 写入CSV
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for trace_metric in aggregated_metrics.trace_metrics:
                row = {
                    'clustering_algorithm': self.clustering_algorithm or "N/A",
                    'cluster_count': self.cluster_count if self.cluster_count is not None else "N/A",
                    'aggregation_method': self.aggregation_method or "N/A",
                    'context_matching_strategy': self.context_matching_strategy or "N/A",
                    'apply_context_mu_shift': self.apply_context_mu_shift if self.apply_context_mu_shift is not None else "N/A",
                    'detection_mode': trace_metric.detection_mode,
                    'filename': trace_metric.filename,
                    'classification': trace_metric.classification,
                    'abn1_start_time': trace_metric.abn1_start_time if trace_metric.abn1_start_time is not None else "N/A",
                    'first_detection_time': trace_metric.first_detection_time if trace_metric.first_detection_time is not None else "N/A",
                    'first_raw_anomaly_time': trace_metric.first_raw_anomaly_time if trace_metric.first_raw_anomaly_time is not None else "N/A",
                    'delay_loops': trace_metric.detection_delay_loops if trace_metric.detection_delay_loops is not None else "N/A",
                    'total_detections': trace_metric.total_detection_count,
                    'trigger_alarm_count': trace_metric.trigger_alarm_count if trace_metric.trigger_alarm_count is not None else "N/A",
                    'trigger_allowed_count': trace_metric.trigger_allowed_count if trace_metric.trigger_allowed_count is not None else "N/A",
                    'first_detection_changepoint_probability': (
                        trace_metric.first_detection_changepoint_probability
                        if trace_metric.first_detection_changepoint_probability is not None
                        else "N/A"
                    ),
                    'first_detection_run_length': (
                        trace_metric.first_detection_run_length
                        if trace_metric.first_detection_run_length is not None
                        else "N/A"
                    ),
                    'first_detection_best_distribution': trace_metric.first_detection_best_distribution or "N/A",
                    'first_detection_best_tail_p_value': (
                        trace_metric.first_detection_best_tail_p_value
                        if trace_metric.first_detection_best_tail_p_value is not None
                        else "N/A"
                    ),
                }
                writer.writerow(row)

        logger.info(f"CSV结果已保存: {csv_path}")
        return str(csv_path)
