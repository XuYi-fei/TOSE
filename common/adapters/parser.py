"""
解析器抽象基类

定义trace文件解析器的统一接口
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd

from ..models.metadata import TraceMetadata
from ..models.distribution import DistributionParameters
from ..models.context import build_context_key


class TraceParser(ABC):
    """Trace文件解析器抽象基类

    所有数据集适配器都应继承此类并实现其抽象方法
    """

    def __init__(self, boundary_trim_points: int = 0):
        self.boundary_trim_points = max(0, int(boundary_trim_points))

    @abstractmethod
    def parse_filename(self, filename: str) -> Optional[TraceMetadata]:
        """解析文件名提取元数据

        Args:
            filename: trace文件名

        Returns:
            TraceMetadata对象，解析失败返回None
        """
        pass

    @abstractmethod
    def parse_trace_file(self, filepath: Path, metadata: TraceMetadata) -> Dict[str, pd.DataFrame]:
        """解析trace文件内容，按norm标签分段

        根据metadata中的start_time和trace_config，将CSV数据按时间分段

        Args:
            filepath: trace文件路径
            metadata: 文件名解析得到的元数据

        Returns:
            字典{norm_label: DataFrame}，每个DataFrame包含该norm段的数据
        """
        pass

    @abstractmethod
    def extract_parameters(
        self,
        segments: Dict[str, pd.DataFrame],
        metadata: TraceMetadata
    ) -> List[DistributionParameters]:
        """从分段数据中提取分布参数

        计算每个norm段的均值、方差、标准差、范围等统计参数

        Args:
            segments: 按norm标签分段的数据
            metadata: trace文件元数据

        Returns:
            分布参数列表
        """
        pass

    def parse_file(self, filepath: Path) -> List[DistributionParameters]:
        """解析单个trace文件的完整流程

        组合三个抽象方法的调用，提供默认的解析流程

        Args:
            filepath: trace文件路径

        Returns:
            分布参数列表
        """
        # 1. 解析文件名
        metadata = self.parse_filename(filepath.name)
        if metadata is None:
            return []

        # 2. 解析文件内容并分段
        segments = self.parse_trace_file(filepath, metadata)

        # 3. 提取分布参数
        parameters = self.extract_parameters(segments, metadata)

        return parameters

    def get_segment_context(
        self,
        metadata: TraceMetadata,
        segment_index: int,
        norm_label: str,
    ) -> Tuple[Optional[str], Dict[str, float]]:
        """返回指定段的上下文键和上下文特征。"""
        return None, {}

    def get_point_context(
        self,
        metadata: TraceMetadata,
        time_value: float,
    ) -> Tuple[Optional[str], Dict[str, float]]:
        """根据时间点推断该点所属的上下文。"""
        if not metadata.trace_config or not metadata.start_time:
            return None, {}

        active_index = len(metadata.trace_config) - 1
        for index, start in enumerate(metadata.start_time):
            if float(time_value) < float(start):
                active_index = max(0, index - 1)
                break

        norm_label = metadata.trace_config[active_index]
        return self.get_segment_context(metadata, active_index, norm_label)

    @staticmethod
    def build_context_key(context_features: Dict[str, float]) -> Optional[str]:
        """构造稳定的上下文键。"""
        return build_context_key(context_features)

    def _trim_segment_boundaries(
        self,
        segment_df: pd.DataFrame,
        segment_index: int,
        total_segments: int,
    ) -> pd.DataFrame:
        """对 identity segment 做边界点剔除。

        第一个 segment 只裁掉尾部，最后一个只裁掉头部，中间段两侧都裁掉。
        """
        trim = self.boundary_trim_points
        if trim <= 0 or segment_df.empty:
            return segment_df

        start_trim = trim if segment_index > 0 else 0
        end_trim = trim if segment_index < total_segments - 1 else 0

        if start_trim >= len(segment_df) or end_trim >= len(segment_df):
            return segment_df.iloc[0:0].copy()

        end_index = len(segment_df) - end_trim if end_trim > 0 else len(segment_df)
        if start_trim >= end_index:
            return segment_df.iloc[0:0].copy()

        return segment_df.iloc[start_trim:end_index].copy()
