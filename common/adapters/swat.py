"""
SWAT数据集适配器

处理SWAT trace文件的解析和参数提取

SWAT (Secure Water Treatment) 数据格式与RUBIS非常相似：
- 文件名格式完全相同
- 第一列是时间（time vs simTime(s)）
- 最后一列是目标指标（y_0 vs measuredAvgRespTime_{k}）

因此继承RUBISParser，只需覆盖列名配置
"""
from pathlib import Path
from typing import Dict, List
import pandas as pd

from .rubis import RUBISParser
from ..models.metadata import RUBISMetadata
from ..models.distribution import DistributionParameters
from ..utils import statistics as stats


# SWAT元数据使用与RUBIS相同的结构（文件名格式完全一致）
SWATMetadata = RUBISMetadata


class SWATParser(RUBISParser):
    """SWAT数据适配器

    SWAT数据格式说明：
    - CSV列: time, water_tank, noisy_B_in, noisy_B_out, u_1_in, u_1_out, y_0
    - 时间列: time (第一列)
    - 目标指标: y_0 (最后一列，水箱液位)
    - 文件名格式: 与RUBIS完全相同

    继承自RUBISParser以重用文件名解析逻辑
    """

    # SWAT目标列名（最后一列）
    TARGET_COLUMN = 'y_0'

    # SWAT时间列名（第一列）
    TIME_COLUMN = 'time'

    def parse_trace_file(self, filepath: Path, metadata: SWATMetadata) -> Dict[str, pd.DataFrame]:
        """解析SWAT trace文件并按norm标签分段

        Args:
            filepath: trace文件路径
            metadata: 文件名解析得到的元数据

        Returns:
            字典{norm_label: DataFrame}
        """
        # 读取CSV数据
        df = pd.read_csv(filepath)

        # 清理数据（去除空行）
        df_clean = df.dropna()

        # 按时间分段（使用SWAT的time列）
        segments = {}
        start_times = metadata.start_time
        trace_configs = metadata.trace_config

        for i, norm_label in enumerate(trace_configs):
            start = start_times[i]
            end = start_times[i + 1] if i + 1 < len(start_times) else df_clean[self.TIME_COLUMN].max() + 1

            # 筛选时间段内的数据
            segment_df = df_clean[
                (df_clean[self.TIME_COLUMN] >= start) &
                (df_clean[self.TIME_COLUMN] < end)
            ].copy()

            segments[norm_label] = self._trim_segment_boundaries(
                segment_df,
                segment_index=i,
                total_segments=len(trace_configs),
            )

        return segments

    def extract_parameters(
        self,
        segments: Dict[str, pd.DataFrame],
        metadata: SWATMetadata
    ) -> List[DistributionParameters]:
        """从SWAT分段数据中提取参数

        Args:
            segments: 按norm标签分段的数据
            metadata: trace文件元数据

        Returns:
            分布参数列表
        """
        parameters = []

        for i, norm_label in enumerate(metadata.trace_config):
            if norm_label not in segments:
                continue

            segment_df = segments[norm_label]
            context_key, context_features = self.get_segment_context(metadata, i, norm_label)

            # 提取目标指标列（SWAT的y_0列）
            if self.TARGET_COLUMN in segment_df.columns:
                metric_values = segment_df[self.TARGET_COLUMN].values
            else:
                # 如果找不到目标列，跳过
                continue

            # 过滤样本数不足的情况
            if len(metric_values) < 10:
                continue

            # 计算统计参数
            param = DistributionParameters(
                norm_label=norm_label,
                mean=stats.calculate_mean(metric_values.tolist()),
                variance=stats.calculate_variance(metric_values.tolist()),
                std_dev=stats.calculate_std_dev(metric_values.tolist()),
                min_value=float(metric_values.min()),
                max_value=float(metric_values.max()),
                sample_count=len(metric_values),
                position=i + 1,  # 位置从1开始
                filename=metadata.filename,
                raw_values=metric_values.astype(float).tolist(),
                context_key=context_key,
                context_features=context_features,
            )

            parameters.append(param)

        return parameters
