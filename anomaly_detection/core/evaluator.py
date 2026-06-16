"""
异常检测评估器

计算FP/FN率和检测性能指标（trace级别）
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path
import math
import numpy as np
import logging
from scipy.stats import binom

from ..core.detector import AnomalyDetector, DetectionResult
from common.adapters import ParserFactory
from common.utils.trace_series import load_trace_series
from baseline_methods import config as baseline_config

logger = logging.getLogger(__name__)


@dataclass
class AnomalyPoint:
    """异常点信息"""
    time: float                     # 时间点
    value: float                    # 响应时间值
    is_detected: bool               # 是否被检测为异常
    z_scores: Dict[str, float]      # z分数字典
    p_values: Dict[str, float]      # 边缘概率字典
    best_p_value: float             # 最大边缘概率
    distribution_type: str          # 被选中的分布类型
    closest_distribution: str       # 最接近的分布
    matched_context_key: Optional[str] = None
    context_match_strategy: Optional[str] = None
    context_location_shift: float = 0.0
    detection_mode: str = "pointwise"
    best_tail_p_value: Optional[float] = None
    best_log_likelihood: Optional[float] = None
    changepoint_probability: Optional[float] = None
    most_likely_run_length: Optional[int] = None
    raw_anomaly_reasons: List[str] = field(default_factory=list)
    candidate_distribution_count: int = 0
    top_matches: List[Dict[str, float | str]] = field(default_factory=list)


@dataclass
class TraceEvaluationMetrics:
    """单个trace的评估指标（trace级别）"""
    filename: str                                   # 文件名
    classification: str                            # 'TP' | 'FP' | 'FN' | 'TN'
    has_abn1: bool                                 # 是否包含abn1段
    abn1_start_time: Optional[float]               # abn1段开始时间（如果有）
    first_detection_time: Optional[float]          # 首次检测时间（如果有）
    first_raw_anomaly_time: Optional[float]        # 首个原始异常点时间（如果有）
    detection_delay_loops: Optional[int]           # 检测延迟（loop数，可为负）
    total_detection_count: int                     # 检测到的异常点总数
    trigger_alarm_count: Optional[int] = None      # 触发时累计原始异常点数
    trigger_allowed_count: Optional[int] = None    # 触发时容忍上限
    detection_mode: str = "pointwise"
    first_detection_changepoint_probability: Optional[float] = None
    first_detection_run_length: Optional[int] = None
    first_detection_best_distribution: Optional[str] = None
    first_detection_best_tail_p_value: Optional[float] = None
    abnormal_time: float = 0.0
    abnormal_total_time: float = 0.0
    anomaly_points: List[AnomalyPoint] = field(default_factory=list)  # 所有检测到的异常点


@dataclass
class AggregatedMetrics:
    """聚合的评估指标（trace级别）"""
    total_traces: int               # 总trace数（200）
    tp_count: int                   # TP trace数
    fp_count: int                   # FP trace数
    fn_count: int                   # FN trace数
    tn_count: int                   # TN trace数
    # 约束：tp_count + fp_count + fn_count + tn_count = total_traces

    precision: float                # tp_count / (tp_count + fp_count)
    recall: float                   # tp_count / (tp_count + fn_count)
    f1_score: float                 # 2 * P * R / (P + R)

    # 延迟统计（仅TP，单位：loops）
    avg_delay_loops: Optional[float]
    min_delay_loops: Optional[int]
    max_delay_loops: Optional[int]
    abnormal_time: float = 0.0
    abnormal_total_time: float = 0.0

    trace_metrics: List[TraceEvaluationMetrics] = field(default_factory=list)


def calculate_delay_in_loops(
    time_values: np.ndarray,
    abn1_start_time: float,
    first_detection_time: float
) -> int:
    """
    计算检测延迟（loop数）

    Args:
        time_values: trace的时间序列数组
        abn1_start_time: abn1段开始时间
        first_detection_time: 首次检测时间

    Returns:
        延迟loop数（可为负）
    """
    # 找到abn1开始时间在数组中的索引
    # abn1可能恰好等于某个时间点，或位于两个时间点之间
    abn1_indices = np.where(time_values >= abn1_start_time)[0]
    if len(abn1_indices) == 0:
        raise ValueError(f"abn1_start_time {abn1_start_time} 超出trace时间范围")

    abn1_loop_index = abn1_indices[0]

    # 找到首次检测时间的索引
    detection_indices = np.where(time_values == first_detection_time)[0]
    if len(detection_indices) == 0:
        raise ValueError(f"first_detection_time {first_detection_time} 不在trace中")

    first_detection_loop_index = detection_indices[0]

    # 计算延迟
    delay = first_detection_loop_index - abn1_loop_index

    return delay


def calculate_theoretical_alarm_probability(point_anomaly_probability: float) -> float:
    """计算点级异常概率。"""
    return point_anomaly_probability


def calculate_allowed_alarm_count(
    observed_count: int,
    point_anomaly_probability: float,
    alarm_count_policy: str = "binomial_confidence_bound",
    trace_alarm_confidence: float = 0.99,
) -> int:
    """根据已观测点数和点级异常概率计算容忍的异常点个数。"""
    if observed_count <= 0:
        return 0

    if alarm_count_policy == "binomial_confidence_bound":
        return int(
            binom.ppf(
                trace_alarm_confidence,
                observed_count,
                point_anomaly_probability,
            )
        )

    return math.ceil(observed_count * calculate_theoretical_alarm_probability(point_anomaly_probability))


class AnomalyEvaluator:
    """异常检测评估器（trace级别）"""

    def __init__(
        self,
        detector: AnomalyDetector,
        system_type: str,
        alarm_count_policy: str = "binomial_confidence_bound",
        trace_alarm_confidence: float = 0.99,
    ):
        """初始化评估器

        Args:
            detector: 异常检测器
            system_type: 系统类型（rubis/bsn）
        """
        self.detector = detector
        self.system_type = system_type
        self.alarm_count_policy = alarm_count_policy
        self.trace_alarm_confidence = trace_alarm_confidence
        self.sigma_threshold = getattr(detector, "sigma_threshold", 3.0)
        self.point_anomaly_probability = getattr(detector, "point_anomaly_probability", 0.05)
        self.detection_mode = getattr(detector, "detection_mode", "pointwise")
        self.parser = ParserFactory.create(system_type)

    def evaluate_trace(self, trace_file: Path) -> TraceEvaluationMetrics:
        """评估单个trace的检测性能（trace级别分类）

        Args:
            trace_file: trace文件路径

        Returns:
            TraceEvaluationMetrics: 包含单一分类标签的评估结果
        """
        # Step 1: 解析文件名
        metadata = self.parser.parse_filename(trace_file.name)
        if metadata is None:
            raise ValueError(f"无法解析文件名: {trace_file.name}")

        trace_config = metadata.trace_config
        start_time = metadata.start_time

        # 提取abn1信息
        has_abn1 = 'abn1' in trace_config
        if has_abn1:
            abn1_index = trace_config.index('abn1')
            abn1_start_time = start_time[abn1_index]
        else:
            abn1_start_time = None

        # Step 2: 读取trace数据
        time_values, response_times = load_trace_series(trace_file, self.system_type)
        self.detector.reset_trace_state()

        # Step 3: 逐点检测，收集所有异常时间
        first_detection_time = None
        first_raw_anomaly_time = None
        raw_anomaly_count = 0
        trigger_alarm_count = None
        trigger_allowed_count = None
        first_detection_changepoint_probability = None
        first_detection_run_length = None
        first_detection_best_distribution = None
        first_detection_best_tail_p_value = None
        anomaly_points = []

        for i, (time, value) in enumerate(zip(time_values, response_times)):
            context_key, context_features = self.parser.get_point_context(metadata, float(time))
            try:
                detection_result = self.detector.detect_point(
                    value,
                    context_key=context_key,
                    context_features=context_features,
                )
            except TypeError:
                detection_result = self.detector.detect_point(value)
            if detection_result.is_anomaly:
                raw_anomaly_count += 1
                if first_raw_anomaly_time is None:
                    first_raw_anomaly_time = time
                anomaly_points.append(AnomalyPoint(
                    time=time,
                    value=value,
                    is_detected=True,
                    z_scores=detection_result.all_z_scores,
                    p_values=detection_result.all_p_values,
                    best_p_value=detection_result.best_p_value,
                    distribution_type=detection_result.distribution_type,
                    closest_distribution=detection_result.closest_distribution,
                    matched_context_key=detection_result.matched_context_key,
                    context_match_strategy=detection_result.context_match_strategy,
                    context_location_shift=detection_result.context_location_shift,
                    detection_mode=detection_result.detection_mode,
                    best_tail_p_value=detection_result.best_tail_p_value,
                    best_log_likelihood=detection_result.best_log_likelihood,
                    changepoint_probability=detection_result.changepoint_probability,
                    most_likely_run_length=detection_result.most_likely_run_length,
                    raw_anomaly_reasons=list(detection_result.raw_anomaly_reasons),
                    candidate_distribution_count=detection_result.candidate_distribution_count,
                    top_matches=list(detection_result.top_matches),
                ))

            observed_count = i + 1
            if self.detection_mode == "bocpd":
                allowed_alarm_count = 0
            else:
                allowed_alarm_count = calculate_allowed_alarm_count(
                    observed_count,
                    self.point_anomaly_probability,
                    self.alarm_count_policy,
                    self.trace_alarm_confidence,
                )
            if (
                first_detection_time is None
                and raw_anomaly_count > allowed_alarm_count
            ):
                first_detection_time = time
                trigger_alarm_count = raw_anomaly_count
                trigger_allowed_count = allowed_alarm_count
                first_detection_changepoint_probability = detection_result.changepoint_probability
                first_detection_run_length = detection_result.most_likely_run_length
                first_detection_best_distribution = detection_result.closest_distribution
                first_detection_best_tail_p_value = detection_result.best_tail_p_value

        # Step 4: Trace级别分类
        trace_duration = float(metadata.duration)
        abnormal_total_time = trace_duration if has_abn1 else 0.0
        abnormal_time = 0.0
        if has_abn1:
            if first_detection_time is None:
                # 全程未检测到异常
                classification = 'FN'
                delay_loops = None
                abnormal_time = max(trace_duration - float(abn1_start_time), 0.0)
            else:
                if first_detection_time >= abn1_start_time:
                    # 在abn1时间点或之后检测到
                    classification = 'TP'
                    abnormal_time = (
                        float(first_detection_time)
                        - float(abn1_start_time)
                        + baseline_config.TIME_UNIT_PER_LOOP[self.system_type]
                    )
                else:
                    # 在abn1时间点之前检测到（误报）
                    classification = 'FP'

                # 计算延迟（loop数）
                delay_loops = calculate_delay_in_loops(
                    time_values, abn1_start_time, first_detection_time
                )
        else:
            # 纯正常trace（如果存在）
            if first_detection_time is None:
                classification = 'TN'
            else:
                classification = 'FP'
            delay_loops = None

        # Step 5: 构造返回结果
        return TraceEvaluationMetrics(
            filename=trace_file.name,
            classification=classification,
            has_abn1=has_abn1,
            abn1_start_time=abn1_start_time,
            first_detection_time=first_detection_time,
            first_raw_anomaly_time=first_raw_anomaly_time,
            detection_delay_loops=delay_loops,
            total_detection_count=raw_anomaly_count,
            trigger_alarm_count=trigger_alarm_count,
            trigger_allowed_count=trigger_allowed_count,
            detection_mode=getattr(self.detector, "detection_mode", "pointwise"),
            first_detection_changepoint_probability=first_detection_changepoint_probability,
            first_detection_run_length=first_detection_run_length,
            first_detection_best_distribution=first_detection_best_distribution,
            first_detection_best_tail_p_value=first_detection_best_tail_p_value,
            abnormal_time=abnormal_time,
            abnormal_total_time=abnormal_total_time,
            anomaly_points=anomaly_points
        )

    def aggregate_results(self, trace_metrics: List[TraceEvaluationMetrics]) -> AggregatedMetrics:
        """聚合trace级别的评估结果

        Args:
            trace_metrics: 所有trace的评估指标列表

        Returns:
            AggregatedMetrics: 聚合指标
        """
        total_traces = len(trace_metrics)

        # 计数各分类
        tp_count = sum(1 for m in trace_metrics if m.classification == 'TP')
        fp_count = sum(1 for m in trace_metrics if m.classification == 'FP')
        fn_count = sum(1 for m in trace_metrics if m.classification == 'FN')
        tn_count = sum(1 for m in trace_metrics if m.classification == 'TN')

        # 验证总和
        assert tp_count + fp_count + fn_count + tn_count == total_traces, \
            f"分类总和 {tp_count + fp_count + fn_count + tn_count} != {total_traces}"

        # 计算性能指标
        if tp_count + fp_count > 0:
            precision = tp_count / (tp_count + fp_count)
        else:
            precision = 0.0

        if tp_count + fn_count > 0:
            recall = tp_count / (tp_count + fn_count)
        else:
            recall = 0.0

        if precision + recall > 0:
            f1_score = 2 * precision * recall / (precision + recall)
        else:
            f1_score = 0.0

        # 计算延迟统计（仅TP）
        tp_delays = [m.detection_delay_loops for m in trace_metrics
                     if m.classification == 'TP' and m.detection_delay_loops is not None]

        if tp_delays:
            avg_delay = sum(tp_delays) / len(tp_delays)
            min_delay = min(tp_delays)
            max_delay = max(tp_delays)
        else:
            avg_delay = None
            min_delay = None
            max_delay = None

        abnormal_time = sum(m.abnormal_time for m in trace_metrics)
        abnormal_total_time = sum(m.abnormal_total_time for m in trace_metrics)

        return AggregatedMetrics(
            total_traces=total_traces,
            tp_count=tp_count,
            fp_count=fp_count,
            fn_count=fn_count,
            tn_count=tn_count,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            avg_delay_loops=avg_delay,
            min_delay_loops=min_delay,
            max_delay_loops=max_delay,
            abnormal_time=abnormal_time,
            abnormal_total_time=abnormal_total_time,
            trace_metrics=trace_metrics
        )
