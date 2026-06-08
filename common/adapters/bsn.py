"""
BSN数据集适配器

处理BSN trace文件的解析和参数提取
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd

from .parser import TraceParser
from ..models.metadata import BSNMetadata
from ..models.distribution import DistributionParameters
from ..utils import statistics as stats


class BSNParser(TraceParser):
    """BSN数据适配器"""

    BASE_PATTERN = re.compile(
        r'eval_(ident|abn)_trace-cnt-(?P<cnt>\d+)'
        r'-duration-(?P<duration>\d+)'
        r'-sensor_index-(?P<sensor_index>\d+)'
        r'-config_num-(?P<config_num>\d+)'
        r'-trace_config-(?P<trace_config>[^-]+)'
        r'-start_time-(?P<start_time>[\d,]+)'
    )

    @staticmethod
    def is_anomaly_segment(segment_label: str) -> bool:
        """判断segment是否为异常段

        Args:
            segment_label: 段标签（如norm1, norm2, abn1, abn2）

        Returns:
            True表示异常段，False表示正常段
        """
        return segment_label.startswith('abn')


    def parse_filename(self, filename: str) -> Optional[BSNMetadata]:
        """解析BSN文件名

        Args:
            filename: trace文件名

        Returns:
            BSNMetadata对象，解析失败返回None
        """
        match = self.BASE_PATTERN.search(filename)
        if not match:
            return None

        groups = match.groupdict()
        trace_config = groups['trace_config'].split(',')
        start_time = [int(x) for x in groups['start_time'].split(',')]

        return BSNMetadata(
            cnt=int(groups['cnt']),
            duration=int(groups['duration']),
            sensor_index=int(groups['sensor_index']),
            config_num=int(groups['config_num']),
            trace_config=trace_config,
            start_time=start_time,
            filename=filename,
            env_change_times=self._parse_int_list(self._extract_optional_field(filename, 'env_cptime')),
            env_offsets=self._parse_float_list(self._extract_optional_field(filename, 'offset')),
            batt_change_times=self._parse_int_list(self._extract_optional_field(filename, 'batt_cptime')),
            batt_offsets=self._parse_float_list(self._extract_optional_field(filename, 'B_offset_percent')),
            drift_coeff=self._parse_optional_float(self._extract_optional_field(filename, 'drift_coeff')),
        )

    def parse_trace_file(self, filepath: Path, metadata: BSNMetadata) -> Dict[str, pd.DataFrame]:
        """解析BSN trace文件并按norm标签分段

        Args:
            filepath: trace文件路径
            metadata: 文件名解析得到的元数据

        Returns:
            字典{norm_label: DataFrame}
        """
        # 读取CSV数据
        df = pd.read_csv(filepath)

        # 根据sensor_index确定要提取的传感器
        # sensor_index=0 -> /g3t1_1, sensor_index=1 -> /g3t1_2, 等等
        target_component = f'/g3t1_{metadata.sensor_index + 1}'

        # 只保留目标传感器的数据
        df_filtered = df[df['component'] == target_component].copy()

        if len(df_filtered) == 0:
            raise ValueError(f"文件{filepath.name}中未找到传感器{target_component}的数据")

        # 按时间分段
        segments = {}
        start_times = metadata.start_time + [df_filtered['logicalTime(s)'].max() + 1]

        for i, norm_label in enumerate(metadata.trace_config):
            start = start_times[i]
            end = start_times[i + 1]

            segment_mask = (df_filtered['logicalTime(s)'] >= start) & (df_filtered['logicalTime(s)'] < end)
            segment_df = df_filtered[segment_mask].copy()
            segment_df = self._trim_segment_boundaries(
                segment_df,
                segment_index=i,
                total_segments=len(metadata.trace_config),
            )

            if len(segment_df) >= 10:  # 最少10个数据点
                segments[norm_label] = segment_df

        return segments

    def extract_parameters(
        self,
        segments: Dict[str, pd.DataFrame],
        metadata: BSNMetadata
    ) -> List[DistributionParameters]:
        """从BSN分段数据中提取参数

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

            # 提取cost列（BSN的响应时间数据）
            if 'cost' not in segment_df.columns:
                continue

            cost_values = segment_df['cost'].values

            # 过滤样本数不足的情况
            if len(cost_values) < 10:
                continue

            # 计算统计参数
            param = DistributionParameters(
                norm_label=norm_label,
                mean=stats.calculate_mean(cost_values.tolist()),
                variance=stats.calculate_variance(cost_values.tolist()),
                std_dev=stats.calculate_std_dev(cost_values.tolist()),
                min_value=float(cost_values.min()),
                max_value=float(cost_values.max()),
                sample_count=len(cost_values),
                position=i + 1,  # 位置从1开始
                filename=metadata.filename,
                raw_values=cost_values.astype(float).tolist(),
                context_key=context_key,
                context_features=context_features,
            )

            parameters.append(param)

        return parameters

    def get_segment_context(
        self,
        metadata: BSNMetadata,
        segment_index: int,
        norm_label: str,
    ) -> Tuple[Optional[str], Dict[str, float]]:
        if segment_index >= len(metadata.start_time):
            return None, {}

        start_time = float(metadata.start_time[segment_index])
        context_features: Dict[str, float] = {}
        context_features["sensor_index"] = float(metadata.sensor_index)

        env_offset = self._resolve_piecewise_value(
            start_time,
            metadata.env_change_times,
            metadata.env_offsets,
        )
        batt_offset = self._resolve_piecewise_value(
            start_time,
            metadata.batt_change_times,
            metadata.batt_offsets,
        )

        if env_offset is not None:
            context_features["env_offset"] = float(env_offset)
        if batt_offset is not None:
            context_features["batt_offset_percent"] = float(batt_offset)

        return self.build_context_key(context_features), context_features

    @staticmethod
    def _extract_optional_field(filename: str, field_name: str) -> Optional[str]:
        pattern = rf'-{re.escape(field_name)}-(.*?)(?=-[A-Za-z_]+-|\.txt$)'
        match = re.search(pattern, filename)
        if not match:
            return None
        return match.group(1)

    @staticmethod
    def _parse_int_list(raw_value: Optional[str]) -> Optional[List[int]]:
        if raw_value is None:
            return None
        values = [
            int(part)
            for part in raw_value.split(',')
            if part and part != '-1'
        ]
        return values or None

    @staticmethod
    def _parse_float_list(raw_value: Optional[str]) -> Optional[List[float]]:
        if raw_value is None:
            return None
        cleaned = raw_value.removesuffix('.txt')
        values = [
            float(part)
            for part in cleaned.split(',')
            if part and part != '-1'
        ]
        return values or None

    @staticmethod
    def _parse_optional_float(raw_value: Optional[str]) -> Optional[float]:
        if raw_value is None or raw_value == '':
            return None
        return float(raw_value)

    @staticmethod
    def _resolve_piecewise_value(
        start_time: float,
        change_times: Optional[List[int]],
        values: Optional[List[float]],
    ) -> Optional[float]:
        if not values:
            return None

        if not change_times:
            return float(values[0])

        active_index = 0
        for change_time in change_times:
            if start_time >= float(change_time):
                active_index += 1

        active_index = min(active_index, len(values) - 1)
        return float(values[active_index])
