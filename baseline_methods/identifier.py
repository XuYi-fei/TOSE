"""Identify ASE-style baseline configurations from TOSE identity traces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import math
import random

import numpy as np

from . import config
from .trace_adapter import TraceAdapter


@dataclass(frozen=True)
class BaselineConfig:
    method: str
    system: str
    detector_count: int
    detectors: list[dict]

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "system": self.system,
            "detector_count": self.detector_count,
            "detectors": self.detectors,
        }

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


class BaselineIdentifier:
    """Generate detector configs following ASE baseline identification logic."""

    def __init__(self, system_type: str):
        self.system_type = system_type
        self.adapter = TraceAdapter(system_type)

    def identify(
        self,
        method: str,
        identity_dir: Path | str,
        secondary_identity_dir: Path | str | None = None,
    ) -> BaselineConfig:
        method = method.upper()
        identity_dir = Path(identity_dir)
        secondary_identity_path = Path(secondary_identity_dir) if secondary_identity_dir else None

        if method == "SWD":
            detectors = self._identify_swd(identity_dir)
        elif method == "ARD":
            detectors = self._identify_ard()
        elif method == "GPD":
            detectors = self._identify_gpd(identity_dir)
        elif method == "PRD":
            detectors = self._identify_prd(identity_dir, secondary_identity_path)
        else:
            raise ValueError(f"不支持的 baseline 方法: {method}")

        return BaselineConfig(
            method=method,
            system=self.system_type,
            detector_count=len(detectors),
            detectors=detectors,
        )

    def _identity_values(self, identity_dir: Path) -> np.ndarray:
        return self.adapter.load_all_values(identity_dir).astype(float)

    def _identity_values_by_detector(self, identity_dir: Path) -> list[np.ndarray]:
        return [values.astype(float) for values in self.adapter.load_all_matrix_values(identity_dir)]

    def _trace_values_by_detector(self, identity_dir: Path) -> list[list[np.ndarray]]:
        matrices = self.adapter.load_directory_matrices(identity_dir)
        detector_count = matrices[0].shape[1]
        return [[matrix[:, detector_index].astype(float) for matrix in matrices] for detector_index in range(detector_count)]

    def _identify_swd(self, identity_dir: Path) -> list[dict]:
        all_trace_values = self._trace_values_by_detector(identity_dir)
        window_size = config.SWD_WINDOW_SIZE
        sample_ratios = config.SWD_SAMPLE_RATIO.get(self.system_type, 0.0)
        if not isinstance(sample_ratios, list):
            sample_ratios = [sample_ratios] * len(all_trace_values)
        detectors = []
        for detector_index, trace_values in enumerate(all_trace_values):
            averages: list[float] = []
            for values in trace_values:
                if len(values) < window_size:
                    averages.append(float(np.mean(values)))
                    continue
                for start in range(0, len(values) - window_size + 1):
                    averages.append(float(np.mean(values[start : start + window_size])))

            if not averages:
                raise ValueError(f"SWD 无法从 {identity_dir} 辨识窗口均值")

            detectors.append({
                "window_size": window_size,
                "avg_y_min": float(min(averages)),
                "avg_y_max": float(max(averages)),
                "sample_ratio": float(sample_ratios[detector_index]),
            })
        return detectors

    def _identify_ard(self) -> list[dict]:
        return [
            {
                "r": config.ARD_ORDER,
                "threshold": config.THRESHOLD,
                "window_size": config.ARD_WINDOW_SIZE,
            }
            for _ in range(config.DETECTOR_COUNT[self.system_type])
        ]

    def _identify_gpd(self, identity_dir: Path) -> list[dict]:
        values_by_detector = self._trace_values_by_detector(identity_dir)
        r_k = config.GPD_IDENTIFY_RK
        q_k = config.GPD_QK[self.system_type]
        h_k = config.GPD_HK[self.system_type]
        f_k = 1.0
        detectors = []

        for trace_values in values_by_detector:
            estimated_values = []
            p_values = []
            for values in trace_values:
                estimated_y = float(np.mean(values))
                p = config.GPD_IDENTIFY_P[self.system_type]
                for y in values:
                    estimated_condition = estimated_y * f_k
                    p_condition = f_k * p * f_k + q_k
                    denominator = h_k * p * h_k + r_k
                    gain = p_condition * h_k / denominator if denominator != 0 else 0.0
                    estimated_y = estimated_condition + gain * (float(y) - h_k * estimated_condition)
                    p = (1.0 - gain * h_k) * p_condition
                estimated_values.append(float(estimated_y))
                p_values.append(float(max(p, 1e-12)))

            detectors.append({
                "R_k": config.GPD_RK[self.system_type],
                "Q_k": q_k,
                "F_k": f_k,
                "H_k": h_k,
                "estimated_y0": float(np.mean(estimated_values)),
                "p0": float(np.mean(p_values)),
                "estimated_y_low": float(min(estimated_values)),
                "estimated_y_high": float(max(estimated_values)),
                "threshold": config.THRESHOLD,
            })
        return detectors

    def _identify_prd(self, identity_dir: Path, secondary_identity_dir: Path | None) -> list[dict]:
        split_values = self._split_prd_values(identity_dir, secondary_identity_dir)
        detectors = []
        for epsilon_values, fit_values in split_values:
            detectors.append(self._identify_one_prd(epsilon_values, fit_values))
        return detectors

    def _identify_one_prd(self, epsilon_values: np.ndarray, fit_values: np.ndarray) -> dict:
        epsilon_mu = float(np.mean(epsilon_values))
        epsilon_std = float(np.std(epsilon_values))
        epsilon_std = max(epsilon_std, 1e-12)
        lower = epsilon_mu - 3.0 * epsilon_std
        upper = epsilon_mu + 3.0 * epsilon_std
        outside_count = int(np.sum((epsilon_values < lower) | (epsilon_values > upper)))
        epsilon = outside_count / len(epsilon_values)
        if epsilon <= 0:
            epsilon = 1.0 / max(len(epsilon_values), 1)

        sample_num = self._safe_prd_sample_num(epsilon)
        rng = random.Random(config.RANDOM_SEED)
        fit_list = [float(x) for x in fit_values]
        if sample_num < len(fit_list):
            fit_sample = rng.sample(fit_list, sample_num)
        else:
            fit_sample = fit_list

        return {
            "mu": float(np.mean(fit_sample)),
            "std": float(max(np.std(fit_sample), 1e-12)),
            "epsilon": float(epsilon),
            "threshold": config.THRESHOLD,
            "n": config.PRD_N[self.system_type],
            "beta0": config.PRD_BETA0,
            "N_user": config.PRD_N_USER,
            "warning_num": config.PRD_WARNING_NUM[self.system_type],
            "first_scenario_gap": config.PRD_FIRST_SCENARIO_GAP,
            "sample_num": int(min(sample_num, len(fit_list))),
        }

    def _split_prd_values(
        self,
        identity_dir: Path,
        secondary_identity_dir: Path | None,
    ) -> list[tuple[np.ndarray, np.ndarray]]:
        if secondary_identity_dir is not None and secondary_identity_dir.exists():
            return list(zip(
                self._identity_values_by_detector(identity_dir),
                self._identity_values_by_detector(secondary_identity_dir),
            ))

        trace_files = sorted(identity_dir.glob("*.txt"))
        if len(trace_files) < 2:
            values_by_detector = self._identity_values_by_detector(identity_dir)
            return [(values, values) for values in values_by_detector]

        split_index = max(1, len(trace_files) // 2)
        epsilon_matrices = [self.adapter.load_trace_matrix(path)[1] for path in trace_files[:split_index]]
        fit_matrices = [self.adapter.load_trace_matrix(path)[1] for path in trace_files[split_index:]]
        if not fit_matrices:
            fit_matrices = epsilon_matrices
        epsilon_matrix = np.vstack(epsilon_matrices)
        fit_matrix = np.vstack(fit_matrices)
        return [
            (epsilon_matrix[:, detector_index], fit_matrix[:, detector_index])
            for detector_index in range(epsilon_matrix.shape[1])
        ]

    def _safe_prd_sample_num(self, epsilon: float) -> int:
        numerator = math.log(config.THRESHOLD * 2.0)
        denominator = math.log(max(1.0 - epsilon, 1e-12))
        if denominator == 0:
            return 1
        return max(1, int(numerator / denominator))
