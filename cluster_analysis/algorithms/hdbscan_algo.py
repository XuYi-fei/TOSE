"""
HDBSCAN聚类算法

基于层次密度的聚类算法，自动检测聚类数量
"""
import numpy as np
from .base import ClusteringAlgorithm
from .factory import register_algorithm
from typing import Dict, Any


@register_algorithm('hdbscan')
class HDBSCANAlgorithm(ClusteringAlgorithm):
    """HDBSCAN聚类算法

    特点:
    - 基于密度的聚类
    - 自动确定聚类数量
    - 可以识别噪声点（标签为-1）
    - 适合发现不同密度的簇
    """

    def __init__(self, name: str = 'HDBSCAN', min_cluster_size: int = 10, min_samples: int = 5, **kwargs):
        """初始化HDBSCAN算法

        Args:
            name: 算法名称
            min_cluster_size: 最小簇大小
            min_samples: 核心点的最小邻居数
            **kwargs: 其他参数
        """
        super().__init__(name, min_cluster_size=min_cluster_size, min_samples=min_samples, **kwargs)
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples

    def fit_predict(self, X: np.ndarray) -> np.ndarray:
        """执行HDBSCAN聚类

        Args:
            X: 特征矩阵

        Returns:
            聚类标签数组（噪声点标签为-1）
        """
        try:
            import hdbscan
        except ImportError:
            raise ImportError("请安装hdbscan库: pip install hdbscan")

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            **{k: v for k, v in self.params.items() if k not in ['min_cluster_size', 'min_samples']}
        )

        labels = clusterer.fit_predict(X)
        return labels

    def get_n_clusters(self, labels: np.ndarray) -> int:
        """获取聚类数量（排除噪声点）

        Args:
            labels: 聚类标签

        Returns:
            聚类数量
        """
        # 排除噪声点（标签为-1）
        unique_labels = np.unique(labels)
        n_clusters = len([label for label in unique_labels if label >= 0])
        return n_clusters

    def calculate_additional_metrics(self, X: np.ndarray, labels: np.ndarray) -> Dict[str, Any]:
        """计算额外的评估指标

        Args:
            X: 特征矩阵
            labels: 聚类标签

        Returns:
            指标字典
        """
        n_noise = np.sum(labels == -1)
        noise_ratio = n_noise / len(labels) if len(labels) > 0 else 0

        return {
            'n_noise_points': int(n_noise),
            'noise_ratio': float(noise_ratio)
        }
