"""
Mean Shift聚类算法

基于密度峰值的聚类算法，自动确定聚类数量
"""
import numpy as np
from .base import ClusteringAlgorithm
from .factory import register_algorithm
from typing import Dict, Any, Optional


@register_algorithm('mean_shift')
class MeanShiftAlgorithm(ClusteringAlgorithm):
    """Mean Shift聚类算法

    特点:
    - 基于密度峰值检测
    - 自动确定聚类数量
    - 向密度最大的方向移动
    - 不需要预先指定聚类数
    """

    def __init__(
        self,
        name: str = 'MeanShift',
        bandwidth: Optional[float] = None,
        bin_seeding: bool = False,
        min_bin_freq: int = 1,
        **kwargs
    ):
        """初始化Mean Shift算法

        Args:
            name: 算法名称
            bandwidth: 带宽参数（None则自动估计）
            bin_seeding: 是否使用binning seed加速
            min_bin_freq: 最小bin频率
            **kwargs: 其他参数
        """
        super().__init__(
            name,
            bandwidth=bandwidth,
            bin_seeding=bin_seeding,
            min_bin_freq=min_bin_freq,
            **kwargs
        )
        self.bandwidth = bandwidth
        self.bin_seeding = bin_seeding
        self.min_bin_freq = min_bin_freq
        self.cluster_centers_ = None

    def fit_predict(self, X: np.ndarray) -> np.ndarray:
        """执行Mean Shift聚类

        Args:
            X: 特征矩阵

        Returns:
            聚类标签数组
        """
        try:
            from sklearn.cluster import MeanShift, estimate_bandwidth
        except ImportError:
            raise ImportError("请安装scikit-learn库: pip install scikit-learn")

        # 自动估计bandwidth
        bandwidth = self.bandwidth
        if bandwidth is None:
            # 使用较小的quantile以获得更多聚类
            bandwidth = estimate_bandwidth(X, quantile=0.2, n_samples=min(500, len(X)))

        ms = MeanShift(
            bandwidth=bandwidth,
            bin_seeding=self.bin_seeding,
            min_bin_freq=self.min_bin_freq
        )

        labels = ms.fit_predict(X)
        self.cluster_centers_ = ms.cluster_centers_

        return labels

    def get_n_clusters(self, labels: np.ndarray) -> int:
        """获取聚类数量

        Args:
            labels: 聚类标签

        Returns:
            聚类数量
        """
        return len(np.unique(labels))

    def get_cluster_centers(self, X: np.ndarray, labels: np.ndarray) -> Optional[np.ndarray]:
        """获取聚类中心

        Mean Shift直接计算中心

        Args:
            X: 特征矩阵
            labels: 聚类标签

        Returns:
            聚类中心矩阵
        """
        if self.cluster_centers_ is not None:
            return self.cluster_centers_
        return super().get_cluster_centers(X, labels)

    def calculate_additional_metrics(self, X: np.ndarray, labels: np.ndarray) -> Dict[str, Any]:
        """计算额外的评估指标

        Args:
            X: 特征矩阵
            labels: 聚类标签

        Returns:
            指标字典
        """
        unique_labels = np.unique(labels)
        cluster_sizes = {int(label): int(np.sum(labels == label)) for label in unique_labels}

        metrics = {
            'cluster_sizes': cluster_sizes,
            'bandwidth_used': float(self.bandwidth) if self.bandwidth is not None else 'auto'
        }

        return metrics
