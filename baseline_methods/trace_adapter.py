"""Trace loading helpers for ASE-style baseline experiments."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from common.adapters import ParserFactory
from common.utils.trace_series import load_trace_series


@dataclass(frozen=True)
class BaselineTrace:
    path: Path
    filename: str
    times: np.ndarray
    values: np.ndarray
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

        times, values = load_trace_series(trace_file, self.system_type)
        abn_start_time = None
        if "abn1" in metadata.trace_config:
            abn_start_time = float(metadata.start_time[metadata.trace_config.index("abn1")])

        return BaselineTrace(
            path=trace_file,
            filename=trace_file.name,
            times=times,
            values=values.astype(float),
            duration=int(metadata.duration),
            abn_start_time=abn_start_time,
            sensor_index=getattr(metadata, "sensor_index", None),
        )

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
