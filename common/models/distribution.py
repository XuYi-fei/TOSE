"""
数据模型：分布参数

定义正态分布的统计参数结构
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, List


@dataclass
class DistributionParameters:
    """单个norm段的分布参数"""
    norm_label: str             # norm标签，如'norm1'
    mean: float                 # 均值
    variance: float             # 方差
    std_dev: float              # 标准差
    min_value: float            # 最小值
    max_value: float            # 最大值
    sample_count: int           # 样本数量
    position: Optional[int] = None  # 在trace_config中的位置(1, 2, 3)
    filename: Optional[str] = None  # 来源文件名
    raw_values: Optional[List[float]] = None  # 原始样本值
    context_key: Optional[str] = None  # 该段所属的上下文键
    context_features: Dict[str, float] = field(default_factory=dict)  # 连续上下文特征
    partition_context_key: Optional[str] = None  # stage-1 分区聚类使用的上下文键
    partition_context_features: Dict[str, float] = field(default_factory=dict)  # stage-1 分区上下文特征


@dataclass
class ExpectedDistribution:
    """期望分布参数（配置中的期望值）"""
    norm_label: str             # norm标签
    mu: float                   # 期望均值
    sigma: float                # 期望标准差
    min_resp_time: Optional[float] = None  # 期望最小响应时间
    max_resp_time: Optional[float] = None  # 期望最大响应时间


@dataclass
class DistributionValidation:
    """单个分布的验证结果"""
    norm_label: str             # norm标签
    expected_mean: float        # 期望均值
    actual_mean: float          # 实际均值
    deviation_percent: float    # 偏离百分比
    expected_range: tuple       # 期望范围(min, max)
    actual_range: tuple         # 实际范围(min, max)
    in_range: bool              # 是否在范围内
    is_normal: bool             # 是否判定为正常
    sample_count: int           # 总样本数
    anomaly_count: int          # 异常样本数
