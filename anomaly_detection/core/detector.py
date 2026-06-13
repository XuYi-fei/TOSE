"""
异常检测引擎

支持两种检测模式：

- pointwise: 基于 learned distributions 的静态边缘概率检测
- bocpd: 基于 learned distributions 的 BOCPD 在线变点检测
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
import math

import numpy as np
from scipy import stats
import yaml

from .distribution import LearnedDistribution
from common.models import ContextCalibrationModel

logger = logging.getLogger(__name__)


def _load_learned_distribution_bundle(
    yaml_path: str,
) -> Tuple[dict, Dict[str, LearnedDistribution]]:
    yaml_file = Path(yaml_path)
    if not yaml_file.exists():
        raise FileNotFoundError(
            f"分布参数文件不存在: {yaml_path}\n"
            f"请先运行聚类分析生成learned_distributions.yaml文件"
        )

    with open(yaml_file, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    if "distributions" not in config:
        raise ValueError(f"配置文件{yaml_path}缺少distributions字段")

    distributions = {
        label: LearnedDistribution.from_dict(label, params)
        for label, params in config["distributions"].items()
    }
    return config, distributions


@dataclass
class DetectionResult:
    """单个数据点的检测结果。"""

    is_anomaly: bool
    closest_distribution: str
    best_p_value: float
    all_p_values: Dict[str, float]
    distribution_type: str
    min_z_score: Optional[float] = None
    all_z_scores: Dict[str, float] = field(default_factory=dict)
    matched_context_key: Optional[str] = None
    context_match_strategy: str = "global"
    context_location_shift: float = 0.0
    detection_mode: str = "pointwise"
    best_tail_p_value: Optional[float] = None
    best_log_likelihood: Optional[float] = None
    changepoint_probability: Optional[float] = None
    most_likely_run_length: Optional[int] = None
    raw_anomaly_reasons: List[str] = field(default_factory=list)
    candidate_distribution_count: int = 0
    top_matches: List[Dict[str, float | str]] = field(default_factory=list)


class AnomalyDetector:
    """异常检测器。"""

    detection_mode = "pointwise"

    def __init__(
        self,
        distributions: Dict[str, LearnedDistribution],
        sigma_threshold: Optional[float] = 3.0,
        p_value_alpha: Optional[float] = None,
        clustering_algorithm: Optional[str] = None,
        aggregation_method: str = "max_p_value",
        context_calibration_model: Optional[ContextCalibrationModel] = None,
        context_matching_strategy: str = "nearest",
        apply_context_mu_shift: bool = True,
    ):
        if not distributions:
            raise ValueError("distributions不能为空")

        if p_value_alpha is None:
            if sigma_threshold is None or sigma_threshold <= 0:
                raise ValueError("sigma_threshold必须大于0，或显式提供p_value_alpha")
            p_value_alpha = math.erfc(sigma_threshold / math.sqrt(2.0))
        elif not 0 < p_value_alpha < 1:
            raise ValueError(f"p_value_alpha必须位于(0, 1)区间内, 当前值: {p_value_alpha}")

        if aggregation_method != "max_p_value":
            raise ValueError("当前仅支持 aggregation_method=max_p_value")
        if context_matching_strategy not in {"nearest", "global"}:
            raise ValueError("当前仅支持 context_matching_strategy in {'nearest', 'global'}")

        self.distributions = distributions
        self.p_value_alpha = float(p_value_alpha)
        self.point_anomaly_probability = float(p_value_alpha)
        self.clustering_algorithm = clustering_algorithm
        self.aggregation_method = aggregation_method
        self.context_calibration_model = context_calibration_model
        self.context_matching_strategy = context_matching_strategy
        self.apply_context_mu_shift = apply_context_mu_shift
        self.partition_context_features: List[str] = []
        self._distributions_by_context_key: Dict[Optional[str], Dict[str, LearnedDistribution]] = {}
        self._distributions_by_partition_context_key: Dict[Optional[str], Dict[str, LearnedDistribution]] = {}
        for label, distribution in self.distributions.items():
            self._distributions_by_context_key.setdefault(distribution.context_key, {})[label] = distribution
            self._distributions_by_partition_context_key.setdefault(
                distribution.partition_context_key,
                {},
            )[label] = distribution
        self._context_candidate_cache: Dict[
            Tuple[Optional[str], Tuple[Tuple[str, float], ...]],
            Tuple[Dict[str, LearnedDistribution], Optional[str], str],
        ] = {}
        self._context_shift_cache: Dict[Tuple[str, Tuple[Tuple[str, float], ...]], float] = {}

        if sigma_threshold is None:
            sigma_threshold = float(stats.norm.isf(self.p_value_alpha / 2.0))
        self.sigma_threshold = float(sigma_threshold)

        logger.info(
            "初始化异常检测器: mode=%s, distributions=%s, alpha=%.6f, aggregation=%s",
            self.detection_mode,
            len(distributions),
            self.p_value_alpha,
            aggregation_method,
        )
        logger.info("已知分布: %s", list(distributions.keys()))
        if self.context_calibration_model is not None:
            logger.info(
                "启用上下文均值校准: features=%s, r2=%.4f",
                self.context_calibration_model.feature_names,
                self.context_calibration_model.r_squared,
            )

    @classmethod
    def from_yaml(
        cls,
        yaml_path: str,
        sigma_threshold: Optional[float] = 3.0,
        p_value_alpha: Optional[float] = None,
    ) -> "AnomalyDetector":
        config, distributions = _load_learned_distribution_bundle(yaml_path)
        logger.info("从%s加载了%s个分布", yaml_path, len(distributions))

        detector = cls(
            distributions=distributions,
            sigma_threshold=sigma_threshold,
            p_value_alpha=p_value_alpha,
            clustering_algorithm=config.get("algorithm"),
            aggregation_method=config.get("aggregation_method", "max_p_value"),
            context_calibration_model=(
                ContextCalibrationModel.from_dict(config["context_calibration_model"])
                if config.get("context_calibration_model")
                else None
            ),
            context_matching_strategy=config.get("context_matching_strategy", "nearest"),
            apply_context_mu_shift=bool(config.get("apply_context_mu_shift", True)),
        )

        detector.partition_context_features = list(config.get("partition_context_features", []))
        return detector

    def reset_trace_state(self) -> None:
        """为统一评估器提供兼容接口。pointwise 模式无需维护 trace 状态。"""
        return None

    def detect_point(
        self,
        value: float,
        context_key: Optional[str] = None,
        context_features: Optional[Dict[str, float]] = None,
    ) -> DetectionResult:
        score_bundle = self._score_candidates(
            value=value,
            context_key=context_key,
            context_features=context_features,
        )

        closest_label = max(score_bundle["p_values"], key=score_bundle["p_values"].get)
        best_distribution = score_bundle["candidate_distributions"][closest_label]
        best_p_value = float(score_bundle["p_values"][closest_label])
        is_anomaly = best_p_value < self.p_value_alpha

        return DetectionResult(
            is_anomaly=is_anomaly,
            closest_distribution=closest_label,
            best_p_value=best_p_value,
            all_p_values=score_bundle["p_values"],
            distribution_type=best_distribution.distribution_type,
            min_z_score=score_bundle["z_scores"].get(closest_label),
            all_z_scores=score_bundle["z_scores"],
            matched_context_key=score_bundle["matched_context_key"],
            context_match_strategy=score_bundle["match_strategy"],
            context_location_shift=float(score_bundle["location_shifts"][closest_label]),
            detection_mode=self.detection_mode,
            best_tail_p_value=best_p_value,
            best_log_likelihood=score_bundle["log_likelihoods"].get(closest_label),
            candidate_distribution_count=len(score_bundle["candidate_distributions"]),
            top_matches=score_bundle["top_matches"],
        )

    def _score_candidates(
        self,
        value: float,
        context_key: Optional[str],
        context_features: Optional[Dict[str, float]],
    ) -> Dict[str, object]:
        observed_context = context_features or {}
        candidate_distributions, matched_context_key, match_strategy = self._select_candidate_distributions(
            context_key=context_key,
            context_features=observed_context,
        )

        labels = list(candidate_distributions.keys())
        distributions = [candidate_distributions[label] for label in labels]
        location_shifts = {
            distribution.label: self._context_location_shift(distribution, observed_context)
            for distribution in distributions
        }

        p_values: Dict[str, float] = {}
        z_scores: Dict[str, float] = {}
        log_likelihoods: Dict[str, float] = {}

        norm_distributions = [
            distribution for distribution in distributions
            if distribution.distribution_type == "norm" and distribution.sigma is not None and distribution.sigma > 0
        ]
        if norm_distributions:
            norm_labels = [distribution.label for distribution in norm_distributions]
            mus = np.array([float(distribution.mu or 0.0) for distribution in norm_distributions], dtype=float)
            sigmas = np.array([float(distribution.sigma or 1.0) for distribution in norm_distributions], dtype=float)
            shifts = np.array(
                [float(location_shifts[distribution.label]) for distribution in norm_distributions],
                dtype=float,
            )
            z_array = (float(value) - (mus + shifts)) / sigmas
            p_array = 2.0 * np.minimum(stats.norm.cdf(z_array), 1.0 - stats.norm.cdf(z_array))
            p_array = np.clip(p_array, 0.0, 1.0)
            log_pdf_array = stats.norm.logpdf(float(value), loc=mus + shifts, scale=sigmas)
            for label, z_value, p_value, log_pdf in zip(
                norm_labels,
                z_array.tolist(),
                p_array.tolist(),
                log_pdf_array.tolist(),
            ):
                z_scores[label] = float(z_value)
                p_values[label] = float(p_value)
                log_likelihoods[label] = float(log_pdf)

        for distribution in distributions:
            if distribution.label not in p_values:
                shift = location_shifts[distribution.label]
                p_values[distribution.label] = distribution.tail_probability(value, location_shift=shift)
                z_scores[distribution.label] = distribution.standardized_distance(value, location_shift=shift)
            if distribution.label not in log_likelihoods:
                shift = location_shifts[distribution.label]
                log_likelihoods[distribution.label] = distribution.log_likelihood(value, location_shift=shift)

        top_matches: List[Dict[str, float | str]] = []
        for label in sorted(
            labels,
            key=lambda item: (p_values[item], log_likelihoods[item]),
            reverse=True,
        )[:3]:
            top_matches.append(
                {
                    "distribution_label": label,
                    "tail_probability": float(p_values[label]),
                    "log_likelihood": float(log_likelihoods[label]),
                }
            )

        return {
            "candidate_distributions": candidate_distributions,
            "matched_context_key": matched_context_key,
            "match_strategy": match_strategy,
            "location_shifts": location_shifts,
            "p_values": p_values,
            "z_scores": z_scores,
            "log_likelihoods": log_likelihoods,
            "top_matches": top_matches,
        }

    def _select_candidate_distributions(
        self,
        context_key: Optional[str],
        context_features: Dict[str, float],
    ) -> Tuple[Dict[str, LearnedDistribution], Optional[str], str]:
        cache_key = (
            context_key,
            tuple(sorted((key, float(value)) for key, value in context_features.items())),
        )
        cached = self._context_candidate_cache.get(cache_key)
        if cached is not None:
            return cached

        if self.partition_context_features:
            partition_features = {
                feature_name: float(context_features[feature_name])
                for feature_name in self.partition_context_features
                if feature_name in context_features
            }
            if partition_features:
                partition_key = self._build_context_key(partition_features)
                exact_partition = self._distributions_by_partition_context_key.get(partition_key, {})
                if exact_partition:
                    selected = (exact_partition, partition_key, "partition_exact")
                    self._context_candidate_cache[cache_key] = selected
                    return selected

        if context_key:
            exact = self._distributions_by_context_key.get(context_key, {})
            if exact:
                selected = (exact, context_key, "exact")
                self._context_candidate_cache[cache_key] = selected
                return selected

        if context_features and self.context_matching_strategy == "nearest":
            nearest = self._nearest_context_distributions(context_features)
            if nearest:
                matched_key = next(iter(nearest.values())).context_key
                selected = (nearest, matched_key, "nearest")
                self._context_candidate_cache[cache_key] = selected
                return selected

        selected = (self.distributions, None, "global")
        self._context_candidate_cache[cache_key] = selected
        return selected

    @staticmethod
    def _build_context_key(context_features: Dict[str, float]) -> Optional[str]:
        if not context_features:
            return None
        items = [f"{key}={float(context_features[key]):.6f}" for key in sorted(context_features.keys())]
        return "|".join(items)

    def _nearest_context_distributions(
        self,
        context_features: Dict[str, float],
    ) -> Dict[str, LearnedDistribution]:
        best_distance = None
        matched_context_key = None

        for distribution in self.distributions.values():
            if not distribution.context_features:
                continue
            distance = self._context_distance(context_features, distribution.context_features)
            if distance is None:
                continue
            if best_distance is None or distance < best_distance - 1e-12:
                best_distance = distance
                matched_context_key = distribution.context_key

        if matched_context_key is None:
            return {}

        return dict(self._distributions_by_context_key.get(matched_context_key, {}))

    @staticmethod
    def _context_distance(
        observed: Dict[str, float],
        reference: Dict[str, float],
    ) -> Optional[float]:
        shared = sorted(set(observed.keys()) & set(reference.keys()))
        if not shared:
            return None
        return float(math.sqrt(sum(
            (float(observed[key]) - float(reference[key])) ** 2
            for key in shared
        )))

    def _context_location_shift(
        self,
        distribution: LearnedDistribution,
        context_features: Dict[str, float],
    ) -> float:
        if (
            not self.apply_context_mu_shift
            or self.context_calibration_model is None
            or not context_features
            or not distribution.context_features
        ):
            return 0.0

        context_signature = tuple(sorted((key, float(value)) for key, value in context_features.items()))
        cache_key = (distribution.label, context_signature)
        cached = self._context_shift_cache.get(cache_key)
        if cached is not None:
            return cached

        shift = self.context_calibration_model.compute_location_shift(
            observed_context=context_features,
            reference_context=distribution.context_features,
        )
        self._context_shift_cache[cache_key] = shift
        return shift


class BOCPDDetector(AnomalyDetector):
    """基于已学习分布集合的 BOCPD 在线检测器。"""

    detection_mode = "bocpd"
    _likelihood_floor = 1e-300

    def __init__(
        self,
        distributions: Dict[str, LearnedDistribution],
        sigma_threshold: Optional[float] = 3.0,
        p_value_alpha: Optional[float] = None,
        clustering_algorithm: Optional[str] = None,
        aggregation_method: str = "max_p_value",
        context_calibration_model: Optional[ContextCalibrationModel] = None,
        context_matching_strategy: str = "nearest",
        apply_context_mu_shift: bool = True,
        hazard_lambda: float = 50.0,
        max_run_length: int = 200,
        state_prior: str = "sample_count",
        changepoint_posterior_threshold: float = 0.5,
        raw_anomaly_rule: str = "cp_and_tail",
        tail_persistence_threshold: int = 2,
    ):
        super().__init__(
            distributions=distributions,
            sigma_threshold=sigma_threshold,
            p_value_alpha=p_value_alpha,
            clustering_algorithm=clustering_algorithm,
            aggregation_method=aggregation_method,
            context_calibration_model=context_calibration_model,
            context_matching_strategy=context_matching_strategy,
            apply_context_mu_shift=apply_context_mu_shift,
        )

        if hazard_lambda <= 1.0:
            raise ValueError("hazard_lambda必须大于1.0")
        if max_run_length < 1:
            raise ValueError("max_run_length必须大于等于1")
        if state_prior not in {"uniform", "sample_count"}:
            raise ValueError("state_prior必须为uniform或sample_count")
        if not 0.0 < changepoint_posterior_threshold <= 1.0:
            raise ValueError("changepoint_posterior_threshold必须位于(0, 1]区间内")
        if raw_anomaly_rule not in {"cp_and_tail", "cp_only", "tail_only"}:
            raise ValueError("raw_anomaly_rule必须为cp_and_tail/cp_only/tail_only之一")
        if tail_persistence_threshold < 1:
            raise ValueError("tail_persistence_threshold必须大于等于1")

        self.hazard_lambda = float(hazard_lambda)
        self.hazard = 1.0 / self.hazard_lambda
        self.max_run_length = int(max_run_length)
        self.state_prior_mode = state_prior
        self.changepoint_posterior_threshold = float(changepoint_posterior_threshold)
        self.raw_anomaly_rule = raw_anomaly_rule
        self.tail_persistence_threshold = int(tail_persistence_threshold)
        self._label_order = list(self.distributions.keys())
        self._label_to_index = {label: index for index, label in enumerate(self._label_order)}
        self._distribution_prior = self._build_distribution_prior()
        self._run_probs = np.array([1.0], dtype=float)
        self._state_weights = np.array([self._distribution_prior.copy()], dtype=float)
        self._consecutive_low_tail_count = 0

        logger.info(
            "初始化BOCPD检测器: hazard_lambda=%.3f, max_run_length=%s, state_prior=%s, cp_threshold=%.3f, rule=%s",
            self.hazard_lambda,
            self.max_run_length,
            self.state_prior_mode,
            self.changepoint_posterior_threshold,
            self.raw_anomaly_rule,
        )

    @classmethod
    def from_yaml(
        cls,
        yaml_path: str,
        sigma_threshold: Optional[float] = 3.0,
        p_value_alpha: Optional[float] = None,
        hazard_lambda: float = 50.0,
        max_run_length: int = 200,
        state_prior: str = "sample_count",
        changepoint_posterior_threshold: float = 0.5,
        raw_anomaly_rule: str = "cp_and_tail",
        tail_persistence_threshold: int = 2,
    ) -> "BOCPDDetector":
        config, distributions = _load_learned_distribution_bundle(yaml_path)
        logger.info("从%s加载了%s个分布", yaml_path, len(distributions))

        return cls(
            distributions=distributions,
            sigma_threshold=sigma_threshold,
            p_value_alpha=p_value_alpha,
            clustering_algorithm=config.get("algorithm"),
            aggregation_method=config.get("aggregation_method", "max_p_value"),
            context_calibration_model=(
                ContextCalibrationModel.from_dict(config["context_calibration_model"])
                if config.get("context_calibration_model")
                else None
            ),
            context_matching_strategy=config.get("context_matching_strategy", "nearest"),
            apply_context_mu_shift=bool(config.get("apply_context_mu_shift", True)),
            hazard_lambda=hazard_lambda,
            max_run_length=max_run_length,
            state_prior=state_prior,
            changepoint_posterior_threshold=changepoint_posterior_threshold,
            raw_anomaly_rule=raw_anomaly_rule,
            tail_persistence_threshold=tail_persistence_threshold,
        )

    def reset_trace_state(self) -> None:
        self._run_probs = np.array([1.0], dtype=float)
        self._state_weights = np.array([self._distribution_prior.copy()], dtype=float)
        self._consecutive_low_tail_count = 0

    def detect_point(
        self,
        value: float,
        context_key: Optional[str] = None,
        context_features: Optional[Dict[str, float]] = None,
    ) -> DetectionResult:
        score_bundle = self._score_candidates(
            value=value,
            context_key=context_key,
            context_features=context_features,
        )

        closest_label = max(score_bundle["p_values"], key=score_bundle["p_values"].get)
        best_distribution = score_bundle["candidate_distributions"][closest_label]
        best_p_value = float(score_bundle["p_values"][closest_label])
        best_log_likelihood = float(score_bundle["log_likelihoods"][closest_label])

        likelihood_vector = np.full(len(self._label_order), self._likelihood_floor, dtype=float)
        for label, log_likelihood in score_bundle["log_likelihoods"].items():
            likelihood_vector[self._label_to_index[label]] = max(
                self._likelihood_floor,
                float(math.exp(min(700.0, log_likelihood))),
            )

        changepoint_probability, most_likely_run_length = self._update_bocpd(likelihood_vector)

        high_cp = changepoint_probability >= self.changepoint_posterior_threshold
        immediate_low_tail = best_p_value < self.p_value_alpha
        if immediate_low_tail:
            self._consecutive_low_tail_count += 1
        else:
            self._consecutive_low_tail_count = 0
        low_tail = self._consecutive_low_tail_count >= self.tail_persistence_threshold
        raw_anomaly_reasons: List[str] = []
        if high_cp:
            raw_anomaly_reasons.append("high_changepoint_probability")
        if immediate_low_tail:
            raw_anomaly_reasons.append("low_tail_probability")
        if low_tail and self._consecutive_low_tail_count > 1:
            raw_anomaly_reasons.append("tail_persistence_satisfied")

        if self.raw_anomaly_rule == "cp_and_tail":
            is_anomaly = high_cp and low_tail
        elif self.raw_anomaly_rule == "cp_only":
            is_anomaly = high_cp
        else:
            is_anomaly = low_tail

        return DetectionResult(
            is_anomaly=is_anomaly,
            closest_distribution=closest_label,
            best_p_value=best_p_value,
            all_p_values=score_bundle["p_values"],
            distribution_type=best_distribution.distribution_type,
            min_z_score=score_bundle["z_scores"].get(closest_label),
            all_z_scores=score_bundle["z_scores"],
            matched_context_key=score_bundle["matched_context_key"],
            context_match_strategy=score_bundle["match_strategy"],
            context_location_shift=float(score_bundle["location_shifts"][closest_label]),
            detection_mode=self.detection_mode,
            best_tail_p_value=best_p_value,
            best_log_likelihood=best_log_likelihood,
            changepoint_probability=changepoint_probability,
            most_likely_run_length=most_likely_run_length,
            raw_anomaly_reasons=raw_anomaly_reasons,
            candidate_distribution_count=len(score_bundle["candidate_distributions"]),
            top_matches=score_bundle["top_matches"],
        )

    def _build_distribution_prior(self) -> np.ndarray:
        if self.state_prior_mode == "uniform":
            return np.full(len(self._label_order), 1.0 / len(self._label_order), dtype=float)

        counts = np.array(
            [max(1, int(self.distributions[label].sample_count)) for label in self._label_order],
            dtype=float,
        )
        return counts / counts.sum()

    def _update_bocpd(self, likelihood_vector: np.ndarray) -> Tuple[float, int]:
        prev_run_probs = self._run_probs
        prev_state_weights = self._state_weights
        new_state_count = min(len(prev_run_probs) + 1, self.max_run_length + 1)
        state_mass = np.zeros((new_state_count, len(self._label_order)), dtype=float)

        # changepoint branch (run length resets to 0)
        state_mass[0, :] += self.hazard * self._distribution_prior * likelihood_vector

        # growth branch
        for run_index in range(len(prev_run_probs)):
            new_index = min(run_index + 1, new_state_count - 1)
            state_mass[new_index, :] += (
                (1.0 - self.hazard)
                * prev_run_probs[run_index]
                * prev_state_weights[run_index]
                * likelihood_vector
            )

        run_mass = state_mass.sum(axis=1)
        total_mass = float(run_mass.sum())
        if total_mass <= 0.0 or not np.isfinite(total_mass):
            logger.warning("BOCPD状态质量退化，回退到先验状态")
            self.reset_trace_state()
            return self.hazard, 0

        self._run_probs = run_mass / total_mass
        self._state_weights = np.zeros_like(state_mass)
        for run_index in range(new_state_count):
            row_total = float(state_mass[run_index].sum())
            if row_total > 0.0 and np.isfinite(row_total):
                self._state_weights[run_index] = state_mass[run_index] / row_total
            else:
                self._state_weights[run_index] = self._distribution_prior.copy()

        changepoint_probability = float(self._run_probs[0])
        most_likely_run_length = int(np.argmax(self._run_probs))
        return changepoint_probability, most_likely_run_length
