"""
RUBIS数据集适配器

处理RUBIS trace文件的解析和参数提取
"""
import re
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

from .parser import TraceParser
from ..models.metadata import RUBISMetadata
from ..models.distribution import DistributionParameters
from ..utils import statistics as stats


class RUBISParser(TraceParser):
    """RUBIS数据适配器"""

    # RUBIS文件名格式正则表达式（支持eval_ident_trace和eval_abn_trace）
    FILENAME_PATTERN = re.compile(
        r'eval_(ident|abn)_trace-cnt-(?P<cnt>\d+)'
        r'-duration-(?P<duration>\d+)'
        r'-config_num-(?P<config_num>\d+)'
        r'-trace_config-(?P<trace_config>[^-]+)'
        r'-start_time-(?P<start_time>[^.]+)'
    )

    # RUBIS目标列名
    TARGET_COLUMN = 'measuredAvgRespTime_{k}'

    @staticmethod
    def is_anomaly_segment(segment_label: str) -> bool:
        """判断segment是否为异常段

        Args:
            segment_label: 段标签（如norm1, norm2, abn1, abn2）

        Returns:
            True表示异常段，False表示正常段
        """
        return segment_label.startswith('abn')

    def parse_filename(self, filename: str) -> Optional[RUBISMetadata]:
        """解析RUBIS文件名

        Args:
            filename: trace文件名

        Returns:
            RUBISMetadata对象，解析失败返回None
        """
        match = self.FILENAME_PATTERN.search(filename)
        if not match:
            return None

        groups = match.groupdict()
        trace_config = groups['trace_config'].split(',')
        start_time = [int(x) for x in groups['start_time'].split(',')]

        return RUBISMetadata(
            cnt=int(groups['cnt']),
            duration=int(groups['duration']),
            config_num=int(groups['config_num']),
            trace_config=trace_config,
            start_time=start_time,
            filename=filename
        )

    def parse_trace_file(self, filepath: Path, metadata: RUBISMetadata) -> Dict[str, pd.DataFrame]:
        """解析RUBIS trace文件并按norm标签分段

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

        # 按时间分段
        segments = {}
        start_times = metadata.start_time
        trace_configs = metadata.trace_config

        for i, norm_label in enumerate(trace_configs):
            start = start_times[i]
            end = start_times[i + 1] if i + 1 < len(start_times) else df_clean['simTime(s)'].max() + 1

            # 筛选时间段内的数据
            segment_df = df_clean[
                (df_clean['simTime(s)'] >= start) &
                (df_clean['simTime(s)'] < end)
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
        metadata: RUBISMetadata
    ) -> List[DistributionParameters]:
        """从RUBIS分段数据中提取参数

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

            # 提取响应时间列（RUBIS只有单列）
            if self.TARGET_COLUMN in segment_df.columns:
                resp_times = segment_df[self.TARGET_COLUMN].values
            else:
                # 如果找不到目标列，跳过
                continue

            # 过滤样本数不足的情况
            if len(resp_times) < 10:
                continue

            # 计算统计参数
            param = DistributionParameters(
                norm_label=norm_label,
                mean=stats.calculate_mean(resp_times.tolist()),
                variance=stats.calculate_variance(resp_times.tolist()),
                std_dev=stats.calculate_std_dev(resp_times.tolist()),
                min_value=float(resp_times.min()),
                max_value=float(resp_times.max()),
                sample_count=len(resp_times),
                position=i + 1,  # 位置从1开始
                filename=metadata.filename,
                raw_values=resp_times.astype(float).tolist(),
                context_key=context_key,
                context_features=context_features,
            )

            parameters.append(param)

        return parameters
