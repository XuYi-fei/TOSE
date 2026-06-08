"""
簇内分布拟合

在 stage-1 基于均值聚类之后，对每个簇内的原始样本重新选择更合适的概率分布。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import logging

import numpy as np
from scipy import stats

from common.models import DistributionParameters

logger = logging.getLogger(__name__)


SUPPORTED_DISTRIBUTIONS = {
    "norm": stats.norm,
    "lognorm": stats.lognorm,
    "gamma": stats.gamma,
    "weibull_min": stats.weibull_min,
}

POSITIVE_ONLY_DISTRIBUTIONS = {"lognorm", "gamma", "weibull_min"}


@dataclass
class ClusterDistributionModel:
    """聚类簇对应的拟合分布。"""

    cluster_id: int
    distribution_type: str
    fitted_params: Dict[str, float | List[float]]
    sample_count: int
    dominant_norm: str
    norm_label_distribution: Dict[str, int]
    mu: float
    sigma: float
    variance: float
    goodness_of_fit: Dict[str, float | str] = field(default_factory=dict)
    normality_tests: Dict[str, float | bool] = field(default_factory=dict)
    support: Dict[str, Optional[float]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "cluster_id": int(self.cluster_id),
            "distribution_type": self.distribution_type,
            "fitted_params": self.fitted_params,
            "sample_count": int(self.sample_count),
            "dominant_norm": self.dominant_norm,
            "norm_label_distribution": {
                label: int(count) for label, count in self.norm_label_distribution.items()
            },
            "mu": float(self.mu),
            "sigma": float(self.sigma),
            "variance": float(self.variance),
            "goodness_of_fit": self.goodness_of_fit,
            "normality_tests": self.normality_tests,
            "support": self.support,
        }


class ClusterDistributionFitter:
    """簇内分布拟合器。"""

    def __init__(
        self,
        candidate_distributions: Optional[List[str]] = None,
        normality_alpha: float = 0.05,
    ):
        self.candidate_distributions = candidate_distributions or [
            "norm",
            "lognorm",
            "gamma",
            "weibull_min",
        ]
        self.normality_alpha = normality_alpha

    def fit_cluster_distribution(
        self,
        cluster_id: int,
        parameters: List[DistributionParameters],
    ) -> ClusterDistributionModel:
        samples = self._collect_samples(parameters)
        if samples.size == 0:
            raise ValueError(f"cluster {cluster_id} 没有可用样本，无法拟合分布")

        norm_label_distribution = self._count_norm_labels(parameters)
        dominant_norm = max(norm_label_distribution.items(), key=lambda item: item[1])[0]

        if np.allclose(samples, samples[0]):
            sigma = 1e-6
            return ClusterDistributionModel(
                cluster_id=cluster_id,
                distribution_type="norm",
                fitted_params={"shape_args": [], "loc": float(samples[0]), "scale": sigma},
                sample_count=int(samples.size),
                dominant_norm=dominant_norm,
                norm_label_distribution=norm_label_distribution,
                mu=float(samples[0]),
                sigma=sigma,
                variance=sigma ** 2,
                goodness_of_fit={
                    "selected_p_value": 1.0,
                    "ks_p_value": 1.0,
                    "ks_statistic": 0.0,
                    "selection_reason": "constant_cluster_fallback",
                },
                normality_tests={
                    "normality_alpha": float(self.normality_alpha),
                    "passes_normality": True,
                    "shapiro_p_value": 1.0,
                    "normal_ks_p_value": 1.0,
                },
                support={"lower": float(samples[0]), "upper": float(samples[0])},
            )

        normality_tests = self._run_normality_tests(samples)
        fitted_candidates = self._fit_candidate_distributions(samples)
        if not fitted_candidates:
            raise ValueError(f"cluster {cluster_id} 无法拟合任何候选分布")

        selected = None
        selection_reason = "best_ks_p_value"
        if normality_tests["passes_normality"] and "norm" in fitted_candidates:
            selected = fitted_candidates["norm"]
            selection_reason = "normality_passed_prefer_norm"
        else:
            selected = max(
                fitted_candidates.values(),
                key=lambda item: (item["ks_p_value"], -item["ks_statistic"]),
            )

        return ClusterDistributionModel(
            cluster_id=cluster_id,
            distribution_type=selected["distribution_type"],
            fitted_params=selected["fitted_params"],
            sample_count=int(samples.size),
            dominant_norm=dominant_norm,
            norm_label_distribution=norm_label_distribution,
            mu=float(selected["mu"]),
            sigma=float(selected["sigma"]),
            variance=float(selected["variance"]),
            goodness_of_fit={
                "selected_p_value": float(selected["ks_p_value"]),
                "ks_p_value": float(selected["ks_p_value"]),
                "ks_statistic": float(selected["ks_statistic"]),
                "selection_reason": selection_reason,
            },
            normality_tests=normality_tests,
            support=selected["support"],
        )

    def _collect_samples(self, parameters: List[DistributionParameters]) -> np.ndarray:
        values: List[float] = []
        for parameter in parameters:
            if parameter.raw_values:
                values.extend(float(item) for item in parameter.raw_values)
                continue

            # 回退逻辑：如果没有原始样本，则使用均值作为退化样本，避免流程直接中断。
            values.extend([float(parameter.mean)] * max(1, int(parameter.sample_count)))

        return np.asarray(values, dtype=float)

    def _count_norm_labels(self, parameters: List[DistributionParameters]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for parameter in parameters:
            counts[parameter.norm_label] = counts.get(parameter.norm_label, 0) + 1
        return counts

    def _run_normality_tests(self, samples: np.ndarray) -> Dict[str, float | bool]:
        mu = float(np.mean(samples))
        sigma = float(np.std(samples))
        if sigma <= 0:
            return {
                "normality_alpha": float(self.normality_alpha),
                "passes_normality": True,
                "shapiro_p_value": 1.0,
                "normal_ks_p_value": 1.0,
            }

        if len(samples) <= 5000:
            _, shapiro_p = stats.shapiro(samples)
        else:
            _, shapiro_p = stats.normaltest(samples)

        _, ks_p = stats.kstest(samples, "norm", args=(mu, sigma))
        passes = bool(shapiro_p >= self.normality_alpha and ks_p >= self.normality_alpha)
        return {
            "normality_alpha": float(self.normality_alpha),
            "passes_normality": passes,
            "shapiro_p_value": float(shapiro_p),
            "normal_ks_p_value": float(ks_p),
        }

    def _fit_candidate_distributions(self, samples: np.ndarray) -> Dict[str, Dict[str, object]]:
        fitted: Dict[str, Dict[str, object]] = {}
        for distribution_name in self.candidate_distributions:
            candidate = self._fit_single_distribution(samples, distribution_name)
            if candidate is not None:
                fitted[distribution_name] = candidate
        return fitted

    def _fit_single_distribution(
        self,
        samples: np.ndarray,
        distribution_name: str,
    ) -> Optional[Dict[str, object]]:
        if distribution_name not in SUPPORTED_DISTRIBUTIONS:
            logger.warning("跳过未支持的分布类型: %s", distribution_name)
            return None

        if distribution_name in POSITIVE_ONLY_DISTRIBUTIONS and np.any(samples <= 0):
            return None

        distribution = SUPPORTED_DISTRIBUTIONS[distribution_name]
        try:
            if distribution_name == "norm":
                loc, scale = distribution.fit(samples)
                shape_args: List[float] = []
            else:
                params = distribution.fit(samples, floc=0.0)
                shape_args = [float(item) for item in params[:-2]]
                loc = float(params[-2])
                scale = float(params[-1])

            if scale <= 0:
                return None

            args = tuple(shape_args)
            ks_statistic, ks_p_value = stats.kstest(
                samples,
                distribution_name,
                args=(*args, float(loc), float(scale)),
            )

            mean_value = float(distribution.mean(*args, loc=loc, scale=scale))
            variance_value = float(distribution.var(*args, loc=loc, scale=scale))
            std_dev = float(np.sqrt(max(variance_value, 1e-12)))
            support_lower, support_upper = distribution.support(*args, loc=loc, scale=scale)

            return {
                "distribution_type": distribution_name,
                "fitted_params": {
                    "shape_args": shape_args,
                    "loc": float(loc),
                    "scale": float(scale),
                },
                "ks_statistic": float(ks_statistic),
                "ks_p_value": float(ks_p_value),
                "mu": mean_value,
                "variance": variance_value,
                "sigma": std_dev,
                "support": {
                    "lower": float(support_lower) if np.isfinite(support_lower) else None,
                    "upper": float(support_upper) if np.isfinite(support_upper) else None,
                },
            }
        except Exception as exc:
            logger.debug("拟合分布 %s 失败: %s", distribution_name, exc)
            return None
