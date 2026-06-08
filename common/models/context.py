"""
上下文条件建模数据结构

为辨识和检测链路提供统一的上下文特征编码与线性均值校准。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

import numpy as np

from .distribution import DistributionParameters


def build_context_key(context_features: Dict[str, float] | None) -> Optional[str]:
    """将上下文特征编码成稳定的字符串键。"""
    if not context_features:
        return None

    items = []
    for key in sorted(context_features.keys()):
        value = float(context_features[key])
        items.append(f"{key}={value:.6f}")
    return "|".join(items)


@dataclass
class ContextCalibrationModel:
    """基于上下文特征预测期望均值的线性校准模型。"""

    feature_names: List[str]
    intercept: float
    coefficients: Dict[str, float]
    sample_count: int
    r_squared: float
    modeling_method: str = "linear_mu"

    @classmethod
    def fit(
        cls,
        parameters: Iterable[DistributionParameters],
        modeling_method: str = "linear_mu",
    ) -> Optional["ContextCalibrationModel"]:
        rows = [parameter for parameter in parameters if parameter.context_features]
        if len(rows) < 2:
            return None

        feature_names = sorted({
            key
            for parameter in rows
            for key in parameter.context_features.keys()
        })
        if not feature_names:
            return None

        unique_contexts = {
            tuple(round(float(parameter.context_features.get(name, 0.0)), 12) for name in feature_names)
            for parameter in rows
        }
        if len(unique_contexts) < 2:
            return None

        design_matrix = []
        target = []
        for parameter in rows:
            design_matrix.append([1.0] + [float(parameter.context_features.get(name, 0.0)) for name in feature_names])
            target.append(float(parameter.mean))

        X = np.asarray(design_matrix, dtype=float)
        y = np.asarray(target, dtype=float)
        beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        fitted = X @ beta
        centered = y - float(np.mean(y))
        residual = y - fitted
        total_sum_squares = float(np.sum(centered ** 2))
        residual_sum_squares = float(np.sum(residual ** 2))
        if total_sum_squares <= 0:
            r_squared = 1.0
        else:
            r_squared = max(0.0, 1.0 - residual_sum_squares / total_sum_squares)

        return cls(
            feature_names=feature_names,
            intercept=float(beta[0]),
            coefficients={
                name: float(beta[index + 1])
                for index, name in enumerate(feature_names)
            },
            sample_count=len(rows),
            r_squared=r_squared,
            modeling_method=modeling_method,
        )

    def predict(self, context_features: Dict[str, float] | None) -> Optional[float]:
        if not context_features:
            return None

        prediction = self.intercept
        used_feature = False
        for name in self.feature_names:
            if name not in context_features:
                continue
            prediction += self.coefficients.get(name, 0.0) * float(context_features[name])
            used_feature = True

        if not used_feature:
            return None
        return float(prediction)

    def compute_location_shift(
        self,
        observed_context: Dict[str, float] | None,
        reference_context: Dict[str, float] | None,
    ) -> float:
        observed_prediction = self.predict(observed_context)
        reference_prediction = self.predict(reference_context)
        if observed_prediction is None or reference_prediction is None:
            return 0.0
        return float(observed_prediction - reference_prediction)

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "ContextCalibrationModel":
        return cls(
            feature_names=[str(item) for item in data.get("feature_names", [])],
            intercept=float(data.get("intercept", 0.0)),
            coefficients={
                str(key): float(value)
                for key, value in (data.get("coefficients") or {}).items()
            },
            sample_count=int(data.get("sample_count", 0)),
            r_squared=float(data.get("r_squared", 0.0)),
            modeling_method=str(data.get("modeling_method", "linear_mu")),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "modeling_method": self.modeling_method,
            "feature_names": self.feature_names,
            "intercept": float(self.intercept),
            "coefficients": {
                key: float(value)
                for key, value in self.coefficients.items()
            },
            "sample_count": int(self.sample_count),
            "r_squared": float(self.r_squared),
        }
