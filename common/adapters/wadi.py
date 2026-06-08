"""
WaDi数据集适配器

处理通用多算法框架下的WaDi trace文件解析和参数提取。
"""
from typing import Dict, List

import pandas as pd

from .rubis import RUBISParser
from ..models.distribution import DistributionParameters
from ..models.metadata import RUBISMetadata
from ..utils import statistics as stats


class WADIParser(RUBISParser):
    """WaDi数据适配器。

    通用框架下的WaDi trace与RUBIS共享相同的文件名格式和时间分段逻辑，
    仅目标度量列不同。
    """

    TARGET_COLUMN = "HMI_2_LT_001.PV"

    def extract_parameters(
        self,
        segments: Dict[str, pd.DataFrame],
        metadata: RUBISMetadata
    ) -> List[DistributionParameters]:
        """从WaDi分段数据中提取参数。

        WaDi转换后的通用trace可能包含较短段，因而不沿用其他系统的10点门槛。
        """
        parameters = []

        for i, norm_label in enumerate(metadata.trace_config):
            if norm_label not in segments:
                continue

            segment_df = segments[norm_label]
            context_key, context_features = self.get_segment_context(metadata, i, norm_label)
            if self.TARGET_COLUMN not in segment_df.columns:
                continue

            metric_values = segment_df[self.TARGET_COLUMN].values
            if len(metric_values) == 0:
                continue

            param = DistributionParameters(
                norm_label=norm_label,
                mean=stats.calculate_mean(metric_values.tolist()),
                variance=stats.calculate_variance(metric_values.tolist()),
                std_dev=stats.calculate_std_dev(metric_values.tolist()),
                min_value=float(metric_values.min()),
                max_value=float(metric_values.max()),
                sample_count=len(metric_values),
                position=i + 1,
                filename=metadata.filename,
                raw_values=metric_values.astype(float).tolist(),
                context_key=context_key,
                context_features=context_features,
            )
            parameters.append(param)

        return parameters
