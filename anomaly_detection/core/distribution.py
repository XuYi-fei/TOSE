"""
学习到的分布参数模型

支持从聚类阶段导出的异构分布模型中加载，并在检测阶段计算边缘概率。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import math

import numpy as np
from scipy import stats


SUPPORTED_DISTRIBUTIONS = {
    "norm": stats.norm,
    "lognorm": stats.lognorm,
    "gamma": stats.gamma,
    "weibull_min": stats.weibull_min,
}


@dataclass
class LearnedDistribution:
    """从聚类学习到的异构分布参数。"""

    label: str
    distribution_type: str
    fitted_params: Dict[str, float | List[float]]
    sample_count: int
    mu: Optional[float] = None
    sigma: Optional[float] = None
    variance: Optional[float] = None
    cluster_id: Optional[int] = None
    dominant_norm: Optional[str] = None
    norm_label_distribution: Dict[str, int] = field(default_factory=dict)
    goodness_of_fit: Dict[str, float | str | None] = field(default_factory=dict)
    normality_tests: Dict[str, float | bool] = field(default_factory=dict)
    support: Dict[str, Optional[float]] = field(default_factory=dict)
    context_key: Optional[str] = None
    context_features: Dict[str, float] = field(default_factory=dict)
    partition_context_key: Optional[str] = None
    partition_context_features: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if self.distribution_type not in SUPPORTED_DISTRIBUTIONS:
            raise ValueError(f"不支持的分布类型: {self.distribution_type}")

        if self.sample_count <= 0:
            raise ValueError(f"sample_count必须大于0, 当前值: {self.sample_count}")

        if self.scale <= 0:
            raise ValueError(f"scale必须大于0, 当前值: {self.scale}")

        if self.variance is None and self.sigma is not None:
            self.variance = float(self.sigma ** 2)
        if self.sigma is None and self.variance is not None:
            self.sigma = float(np.sqrt(max(self.variance, 1e-12)))

        if self.mu is None or self.variance is None:
            distribution = self._get_distribution()
            args = self.shape_args
            self.mu = float(distribution.mean(*args, loc=self.loc, scale=self.scale))
            self.variance = float(distribution.var(*args, loc=self.loc, scale=self.scale))
            self.sigma = float(np.sqrt(max(self.variance, 1e-12)))

        if not self.support:
            distribution = self._get_distribution()
            lower, upper = distribution.support(*self.shape_args, loc=self.loc, scale=self.scale)
            self.support = {
                "lower": float(lower) if np.isfinite(lower) else None,
                "upper": float(upper) if np.isfinite(upper) else None,
            }

    @property
    def shape_args(self) -> tuple[float, ...]:
        return tuple(float(item) for item in self.fitted_params.get("shape_args", []))

    @property
    def loc(self) -> float:
        if "loc" in self.fitted_params:
            return float(self.fitted_params["loc"])
        return float(self.mu or 0.0)

    @property
    def scale(self) -> float:
        if "scale" in self.fitted_params:
            return float(self.fitted_params["scale"])
        if self.sigma is not None:
            return float(self.sigma)
        raise ValueError("缺少scale参数")

    def _get_distribution(self):
        return SUPPORTED_DISTRIBUTIONS[self.distribution_type]

    def standardized_distance(self, value: float, location_shift: float = 0.0) -> float:
        if self.sigma is None or self.sigma <= 0 or self.mu is None:
            return 0.0
        return (value - (self.mu + location_shift)) / self.sigma

    def z_score(self, value: float, location_shift: float = 0.0) -> float:
        return self.standardized_distance(value, location_shift=location_shift)

    def _is_outside_support(self, value: float, location_shift: float = 0.0) -> bool:
        lower = self.support.get("lower")
        upper = self.support.get("upper")
        if lower is not None and value < lower + location_shift:
            return True
        if upper is not None and value > upper + location_shift:
            return True
        return False

    def tail_probability(self, value: float, location_shift: float = 0.0) -> float:
        if self._is_outside_support(value, location_shift=location_shift):
            return 0.0

        distribution = self._get_distribution()
        shifted_loc = self.loc + location_shift
        cdf_value = float(distribution.cdf(value, *self.shape_args, loc=shifted_loc, scale=self.scale))
        cdf_value = float(np.clip(cdf_value, 0.0, 1.0))
        return float(max(0.0, min(1.0, 2.0 * min(cdf_value, 1.0 - cdf_value))))

    def log_likelihood(self, value: float, location_shift: float = 0.0) -> float:
        if self._is_outside_support(value, location_shift=location_shift):
            return float(np.log(1e-300))

        distribution = self._get_distribution()
        shifted_loc = self.loc + location_shift
        try:
            log_pdf = float(distribution.logpdf(value, *self.shape_args, loc=shifted_loc, scale=self.scale))
        except AttributeError:
            pdf = float(distribution.pdf(value, *self.shape_args, loc=shifted_loc, scale=self.scale))
            log_pdf = float(np.log(max(pdf, 1e-300)))
        if not np.isfinite(log_pdf):
            return float(np.log(1e-300))
        return log_pdf

    def is_outlier(self, value: float, p_value_alpha: float = 0.05) -> bool:
        return self.tail_probability(value) < p_value_alpha

    @classmethod
    def from_dict(cls, label: str, data: Dict) -> "LearnedDistribution":
        distribution_type = data.get("distribution_type", "norm")
        fitted_params = data.get("fitted_params")

        if fitted_params is None:
            mu = float(data["mu"])
            sigma = float(data["sigma"])
            fitted_params = {
                "shape_args": [],
                "loc": mu,
                "scale": sigma,
            }

        return cls(
            label=label,
            distribution_type=distribution_type,
            fitted_params=fitted_params,
            sample_count=int(data["sample_count"]),
            mu=float(data["mu"]) if data.get("mu") is not None else None,
            sigma=float(data["sigma"]) if data.get("sigma") is not None else None,
            variance=float(data["variance"]) if data.get("variance") is not None else None,
            cluster_id=int(data["cluster_id"]) if data.get("cluster_id") is not None else None,
            dominant_norm=data.get("dominant_norm"),
            norm_label_distribution={
                str(key): int(value) for key, value in (data.get("norm_label_distribution") or {}).items()
            },
            goodness_of_fit=data.get("goodness_of_fit") or {},
            normality_tests=data.get("normality_tests") or {},
            support=data.get("support") or {},
            context_key=data.get("context_key"),
            context_features={
                str(key): float(value)
                for key, value in (data.get("context_features") or {}).items()
            },
            partition_context_key=data.get("partition_context_key"),
            partition_context_features={
                str(key): float(value)
                for key, value in (data.get("partition_context_features") or {}).items()
            },
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "label": self.label,
            "distribution_type": self.distribution_type,
            "fitted_params": self.fitted_params,
            "mu": self.mu,
            "sigma": self.sigma,
            "variance": self.variance,
            "sample_count": self.sample_count,
            "cluster_id": self.cluster_id,
            "dominant_norm": self.dominant_norm,
            "norm_label_distribution": self.norm_label_distribution,
            "goodness_of_fit": self.goodness_of_fit,
            "normality_tests": self.normality_tests,
            "support": self.support,
            "context_key": self.context_key,
            "context_features": self.context_features,
            "partition_context_key": self.partition_context_key,
            "partition_context_features": self.partition_context_features,
        }
