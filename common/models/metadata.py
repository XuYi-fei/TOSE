"""
数据模型：Trace文件元数据

定义trace文件名解析后的元数据结构
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TraceMetadata:
    """Trace文件元数据基类"""
    cnt: int                    # trace文件编号
    duration: int               # 持续时间
    config_num: int             # 配置数量
    trace_config: List[str]     # norm标签列表，如['norm1', 'norm2', 'norm3']
    start_time: List[int]       # 各段开始时间列表
    filename: str               # 原始文件名


@dataclass
class RUBISMetadata(TraceMetadata):
    """RUBIS数据集元数据

    继承基类，不添加额外字段
    """
    pass


@dataclass
class BSNMetadata(TraceMetadata):
    """BSN数据集元数据

    相比基类增加BSN环境/电池上下文字段
    """
    sensor_index: int           # 传感器索引，用于选择数据列
    env_change_times: Optional[List[int]] = None
    env_offsets: Optional[List[float]] = None
    batt_change_times: Optional[List[int]] = None
    batt_offsets: Optional[List[float]] = None
    drift_coeff: Optional[float] = None
