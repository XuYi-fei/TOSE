"""
Trace 时序读取工具

为训练和检测提供跨系统的统一数值读取逻辑。
"""
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

from common.adapters import ParserFactory


TRACE_COLUMN_MAP = {
    "rubis": ("simTime(s)", "measuredAvgRespTime_{k}"),
    "swat": ("time", "y_0"),
    "wadi": ("simTime(s)", "HMI_2_LT_001.PV"),
}


def get_target_metric_name(system_type: str) -> str:
    """返回系统默认目标度量列名。"""
    if system_type == "bsn":
        return "cost"
    if system_type not in TRACE_COLUMN_MAP:
        raise ValueError(f"不支持的系统类型: {system_type}")
    return TRACE_COLUMN_MAP[system_type][1]


def load_trace_series(trace_file: Path, system_type: str) -> Tuple[np.ndarray, np.ndarray]:
    """读取单个 trace 的时间序列和值序列。"""
    df = pd.read_csv(trace_file).dropna()

    if system_type == "bsn":
        parser = ParserFactory.create(system_type)
        metadata = parser.parse_filename(trace_file.name)
        if metadata is None:
            raise ValueError(f"无法解析BSN文件名: {trace_file.name}")

        target_component = f"/g3t1_{metadata.sensor_index + 1}"
        df = df[df["component"] == target_component].copy()
        if df.empty:
            raise ValueError(f"文件{trace_file.name}中未找到传感器{target_component}的数据")

        time_column = "logicalTime(s)"
        value_column = "cost"
    else:
        if system_type not in TRACE_COLUMN_MAP:
            raise ValueError(f"不支持的系统类型: {system_type}")
        time_column, value_column = TRACE_COLUMN_MAP[system_type]

    if time_column not in df.columns:
        raise ValueError(f"未找到列: {time_column}")
    if value_column not in df.columns:
        raise ValueError(f"未找到列: {value_column}")

    time_values = df[time_column].to_numpy()
    metric_values = df[value_column].to_numpy(dtype=float)
    return time_values, metric_values


def load_all_metric_values(data_path: str, system_type: str) -> np.ndarray:
    """加载目录下全部 trace 的原始数值。"""
    data_dir = Path(data_path)
    trace_files = sorted(data_dir.glob("*.txt"))
    if not trace_files:
        raise ValueError(f"目录{data_path}中未找到trace文件")

    all_values = []
    for trace_file in trace_files:
        _, metric_values = load_trace_series(trace_file, system_type)
        if len(metric_values) == 0:
            continue
        all_values.append(metric_values)

    if not all_values:
        raise ValueError(f"目录{data_path}中未提取到任何有效数值")

    return np.concatenate(all_values)
