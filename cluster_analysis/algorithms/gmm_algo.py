"""
GMM with BIC聚类算法

使用贝叶斯信息准则（BIC）自动选择最优聚类数量的高斯混合模型
"""
import numpy as np
from .base import ClusteringAlgorithm
from .factory import register_algorithm
from typing import Dict, Any


@register_algorithm('gmm')
class GMMAlgorithm(ClusteringAlgorithm):
    """GMM聚类算法

    特点:
    - 基于概率模型的聚类
    - 使用BIC自动选择聚类数量
    - 假设数据服从高斯分布
    - 软聚类（每个点有属于各簇的概率）
    """

    def __init__(
        self,
        name: str = 'GMM',
        min_clusters: int = 2,
        max_clusters: int = 10,
        covariance_type: str = 'full',
        **kwargs
    ):
        """初始化GMM算法

        Args:
            name: 算法名称
            min_clusters: 最小聚类数
            max_clusters: 最大聚类数
            covariance_type: 协方差类型 ('full', 'tied', 'diag', 'spherical')
            **kwargs: 其他参数
        """
        super().__init__(
            name,
            min_clusters=min_clusters,
            max_clusters=max_clusters,
            covariance_type=covariance_type,
            **kwargs
        )
        self.min_clusters = min_clusters
        self.max_clusters = max_clusters
        self.covariance_type = covariance_type
        self.best_n_clusters = None
        self.bic_scores = {}

    def fit_predict(self, X: np.ndarray) -> np.ndarray:
        """执行GMM聚类，使用BIC选择最优聚类数

        Args:
            X: 特征矩阵

        Returns:
            聚类标签数组
        """
        try:
            from sklearn.mixture import GaussianMixture
        except ImportError:
            raise ImportError("请安装scikit-learn库: pip install scikit-learn")

        # 调整聚类数范围
        max_possible = min(self.max_clusters, len(X) - 1)
        min_clusters = min(self.min_clusters, max_possible)

        if min_clusters >= max_possible:
            # 数据点太少，只能用一个聚类
            self.best_n_clusters = 1
            self.bic_scores = {1: 0.0}
            return np.zeros(len(X), dtype=int)

        # 尝试不同的聚类数
        best_bic = float('inf')
        best_labels = None

        for n_clusters in range(min_clusters, max_possible + 1):
            try:
                gmm = GaussianMixture(
                    n_components=n_clusters,
                    covariance_type=self.covariance_type,
                    random_state=42
                )
                labels = gmm.fit_predict(X)
                bic = gmm.bic(X)

                self.bic_scores[n_clusters] = bic

                if bic < best_bic:
                    best_bic = bic
                    best_labels = labels
                    self.best_n_clusters = n_clusters

            except Exception as e:
                # 某些聚类数可能导致收敛问题
                continue

        if best_labels is None:
            # 所有尝试都失败，使用单簇
            self.best_n_clusters = 1
            self.bic_scores = {1: 0.0}
            return np.zeros(len(X), dtype=int)

        return best_labels

    def get_n_clusters(self, labels: np.ndarray) -> int:
        """获取聚类数量

        Args:
            labels: 聚类标签

        Returns:
            聚类数量
        """
        if self.best_n_clusters is not None:
            return self.best_n_clusters
        return len(np.unique(labels))

    def calculate_additional_metrics(self, X: np.ndarray, labels: np.ndarray) -> Dict[str, Any]:
        """计算额外的评估指标

        Args:
            X: 特征矩阵
            labels: 聚类标签

        Returns:
            指标字典
        """
        metrics = {
            'bic_scores': self.bic_scores,
            'selected_n_clusters': self.best_n_clusters
        }

        # 计算每个聚类的大小
        unique_labels = np.unique(labels)
        cluster_sizes = {int(label): int(np.sum(labels == label)) for label in unique_labels}
        metrics['cluster_sizes'] = cluster_sizes

        return metrics
