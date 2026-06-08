"""
统计工具函数

提供统计计算和偏离分析功能
"""
import numpy as np
from typing import List


def calculate_mean(values: List[float]) -> float:
    """计算均值"""
    return float(np.mean(values))


def calculate_variance(values: List[float]) -> float:
    """计算样本方差"""
    return float(np.var(values, ddof=1))


def calculate_std_dev(values: List[float]) -> float:
    """计算标准差"""
    return float(np.std(values, ddof=1))


def calculate_deviation_percent(actual: float, expected: float) -> float:
    """计算偏离百分比

    Args:
        actual: 实际值
        expected: 期望值

    Returns:
        偏离百分比
    """
    if expected == 0:
        return 0.0
    return abs(actual - expected) / abs(expected) * 100.0


def is_in_range(value: float, min_val: float, max_val: float) -> bool:
    """检查值是否在范围内

    Args:
        value: 待检查的值
        min_val: 最小值
        max_val: 最大值

    Returns:
        是否在范围内
    """
    return min_val <= value <= max_val


def is_normal(deviation: float, threshold: float, in_range: bool = True) -> bool:
    """判定是否正常

    Args:
        deviation: 偏离百分比
        threshold: 偏离阈值
        in_range: 是否在期望范围内

    Returns:
        是否判定为正常
    """
    return deviation < threshold and in_range
