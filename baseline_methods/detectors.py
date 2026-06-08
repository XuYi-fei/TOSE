"""ASE-style baseline detectors."""

from __future__ import annotations

from dataclasses import dataclass
from math import erf, sqrt

import numpy as np


def _normal_cdf(value: float, mu: float, sigma: float) -> float:
    sigma = max(abs(float(sigma)), 1e-12)
    z = (float(value) - float(mu)) / (sigma * sqrt(2.0))
    return 0.5 * (1.0 + erf(z))


class BaseDetector:
    def reset(self) -> None:
        pass

    def detect(self, value: float) -> tuple[float, bool]:
        raise NotImplementedError


@dataclass
class SWDDetector(BaseDetector):
    window_size: int
    avg_y_min: float
    avg_y_max: float

    def __post_init__(self) -> None:
        self.values: list[float] = []

    def reset(self) -> None:
        self.values = []

    def detect(self, value: float) -> tuple[float, bool]:
        self.values.append(float(value))
        if len(self.values) < self.window_size:
            return 0.0, False
        avg = float(np.mean(self.values))
        self.values = self.values[1:]
        return avg, avg < self.avg_y_min or avg > self.avg_y_max


@dataclass
class ARDDetector(BaseDetector):
    order: int
    threshold: float
    window_size: int

    def __post_init__(self) -> None:
        self.values: list[float] = []

    def reset(self) -> None:
        self.values = []

    def detect(self, value: float) -> tuple[float, bool]:
        if len(self.values) < self.order + self.window_size:
            self.values.append(float(value))
            return 1.0, False

        y = np.array(self.values[self.order : self.order + self.window_size], dtype=float)
        x = np.array(
            [
                [self.values[i - j] for j in range(1, self.order + 1)]
                for i in range(self.order, self.order + self.window_size)
            ],
            dtype=float,
        )
        coef, *_ = np.linalg.lstsq(x, y, rcond=None)
        predictions = x @ coef
        errors = y - predictions
        sigma = float(np.std(errors)) or 1e-7
        prediction_error = float(errors[-1])
        cdf = _normal_cdf(prediction_error, 0.0, sigma)
        self.values = self.values[1:] + [float(value)]
        return cdf, cdf < self.threshold or cdf > 1.0 - self.threshold


@dataclass
class GPDDetector(BaseDetector):
    r_k: float
    q_k: float
    f_k: float
    h_k: float
    estimated_y0: float
    p0: float
    estimated_y_low: float
    estimated_y_high: float
    threshold: float

    def __post_init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.estimated_y = float(self.estimated_y0)
        self.p = max(float(self.p0), 1e-12)

    def detect(self, value: float) -> tuple[float, bool]:
        estimated_condition = self.f_k * self.estimated_y
        p_condition = self.f_k * self.p * self.f_k + self.q_k
        denominator = self.h_k * self.p * self.h_k + self.r_k
        gain = p_condition * self.h_k / denominator if denominator != 0 else 0.0
        self.estimated_y = estimated_condition + gain * (float(value) - self.h_k * estimated_condition)
        self.p = max((1.0 - gain * self.h_k) * p_condition, 1e-12)
        sigma = sqrt(self.p)
        probability = _normal_cdf(self.estimated_y_high, self.estimated_y, sigma) - _normal_cdf(
            self.estimated_y_low,
            self.estimated_y,
            sigma,
        )
        return probability, probability < self.threshold


@dataclass
class PRDDetector(BaseDetector):
    mu: float
    sigma: float
    threshold: float
    warning_num: int

    def __post_init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.current_time = 0
        self.warning_times: list[int] = []

    def detect(self, value: float) -> tuple[float, bool]:
        self.current_time += 1
        cdf = _normal_cdf(value, self.mu, self.sigma)
        if cdf < self.threshold or cdf > 1.0 - self.threshold:
            self.warning_times.append(self.current_time)

        alarm = len(self.warning_times) > self.warning_num or (
            len(self.warning_times) > 1 and self.warning_times[-1] - self.warning_times[-2] == 1
        )
        if alarm:
            self.warning_times = []
        return cdf, alarm


def create_detector(method: str, detector_config: dict) -> BaseDetector:
    method = method.upper()
    if method == "SWD":
        return SWDDetector(
            window_size=int(detector_config["window_size"]),
            avg_y_min=float(detector_config["avg_y_min"]),
            avg_y_max=float(detector_config["avg_y_max"]),
        )
    if method == "ARD":
        return ARDDetector(
            order=int(detector_config["r"]),
            threshold=float(detector_config["threshold"]),
            window_size=int(detector_config["window_size"]),
        )
    if method == "GPD":
        return GPDDetector(
            r_k=float(detector_config["R_k"]),
            q_k=float(detector_config["Q_k"]),
            f_k=float(detector_config["F_k"]),
            h_k=float(detector_config["H_k"]),
            estimated_y0=float(detector_config["estimated_y0"]),
            p0=float(detector_config["p0"]),
            estimated_y_low=float(detector_config["estimated_y_low"]),
            estimated_y_high=float(detector_config["estimated_y_high"]),
            threshold=float(detector_config["threshold"]),
        )
    if method == "PRD":
        return PRDDetector(
            mu=float(detector_config["mu"]),
            sigma=float(detector_config["std"]),
            threshold=float(detector_config["threshold"]),
            warning_num=int(detector_config["warning_num"]),
        )
    raise ValueError(f"不支持的 baseline 方法: {method}")
