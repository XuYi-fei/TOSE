"""Trace loading helpers for ASE-style baseline experiments."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from common.adapters import ParserFactory
from common.utils.trace_series import load_trace_series


@dataclass(frozen=True)
class BaselineTrace:
    path: Path
    filename: str
    times: np.ndarray
    values: np.ndarray
    values_matrix: np.ndarray
    duration: int
    abn_start_time: Optional[float]
    sensor_index: Optional[int]


class TraceAdapter:
    """Load TOSE traces into the minimal format used by ASE baselines."""

    def __init__(self, system_type: str):
        self.system_type = system_type
        self.parser = ParserFactory.create(system_type)

    def load(self, trace_file: Path) -> BaselineTrace:
        metadata = self.parser.parse_filename(trace_file.name)
        if metadata is None:
            raise ValueError(f"无法解析文件名: {trace_file.name}")

        times, values_matrix = self.load_trace_matrix(trace_file)
        values = values_matrix[:, self._target_sensor_index(metadata)]
        abn_start_time = None
        if "abn1" in metadata.trace_config:
            abn_start_time = float(metadata.start_time[metadata.trace_config.index("abn1")])

        return BaselineTrace(
            path=trace_file,
            filename=trace_file.name,
            times=times,
            values=values.astype(float),
            values_matrix=values_matrix.astype(float),
            duration=int(metadata.duration),
            abn_start_time=abn_start_time,
            sensor_index=getattr(metadata, "sensor_index", None),
        )

    def load_trace_matrix(self, trace_file: Path) -> tuple[np.ndarray, np.ndarray]:
        if self.system_type != "bsn":
            times, values = load_trace_series(trace_file, self.system_type)
            return times, values.astype(float).reshape(-1, 1)

        df = pd.read_csv(trace_file).dropna()
        time_column = "logicalTime(s)"
        value_column = "cost"
        components = [f"/g3t1_{index + 1}" for index in range(6)]
        pivot = (
            df[df["component"].isin(components)]
            .pivot_table(index=time_column, columns="component", values=value_column, aggfunc="first")
            .sort_index()
        )
        missing = [component for component in components if component not in pivot.columns]
        if missing:
            raise ValueError(f"文件{trace_file.name}缺少BSN传感器数据: {missing}")
        pivot = pivot[components].dropna()
        return pivot.index.to_numpy(), pivot.to_numpy(dtype=float)

    def load_directory_values(self, trace_dir: Path) -> list[np.ndarray]:
        values = []
        for trace_file in sorted(trace_dir.glob("*.txt")):
            trace = self.load(trace_file)
            if len(trace.values) > 0:
                values.append(trace.values)
        if not values:
            raise ValueError(f"目录中未找到有效 trace 数据: {trace_dir}")
        return values

    def load_all_values(self, trace_dir: Path) -> np.ndarray:
        return np.concatenate(self.load_directory_values(trace_dir))

    def load_directory_matrices(self, trace_dir: Path) -> list[np.ndarray]:
        matrices = []
        for trace_file in sorted(trace_dir.glob("*.txt")):
            _, matrix = self.load_trace_matrix(trace_file)
            if matrix.size > 0:
                matrices.append(matrix)
        if not matrices:
            raise ValueError(f"目录中未找到有效 trace 矩阵数据: {trace_dir}")
        return matrices

    def load_all_matrix_values(self, trace_dir: Path) -> list[np.ndarray]:
        matrix = np.vstack(self.load_directory_matrices(trace_dir))
        return [matrix[:, detector_index] for detector_index in range(matrix.shape[1])]

    @staticmethod
    def _target_sensor_index(metadata) -> int:
        return int(getattr(metadata, "sensor_index", 0) or 0)
