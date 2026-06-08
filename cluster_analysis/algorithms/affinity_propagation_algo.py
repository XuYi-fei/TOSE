"""
Affinity Propagation聚类算法

基于消息传递的聚类算法，自动确定聚类数量
"""
import numpy as np
from .base import ClusteringAlgorithm
from .factory import register_algorithm
from typing import Dict, Any, Optional


@register_algorithm('affinity_propagation')
class AffinityPropagationAlgorithm(ClusteringAlgorithm):
    """Affinity Propagation聚类算法

    特点:
    - 基于消息传递机制
    - 自动确定聚类数量
    - 不需要预先指定聚类中心数
    - 选择数据点作为exemplar（代表点）
    """

    def __init__(
        self,
        name: str = 'AffinityPropagation',
        damping: float = 0.5,
        max_iter: int = 200,
        convergence_iter: int = 15,
        preference: Optional[float] = None,
        **kwargs
    ):
        """初始化Affinity Propagation算法

        Args:
            name: 算法名称
            damping: 阻尼系数（0.5-1.0），控制消息更新的平滑程度
            max_iter: 最大迭代次数
            convergence_iter: 判定收敛的迭代次数
            preference: 偏好值（控制聚类数量，None则自动设置）
            **kwargs: 其他参数
        """
        super().__init__(
            name,
            damping=damping,
            max_iter=max_iter,
            convergence_iter=convergence_iter,
            preference=preference,
            **kwargs
        )
        self.damping = damping
        self.max_iter = max_iter
        self.convergence_iter = convergence_iter
        self.preference = preference
        self.cluster_centers_indices_ = None

    def fit_predict(self, X: np.ndarray) -> np.ndarray:
        """执行Affinity Propagation聚类

        Args:
            X: 特征矩阵

        Returns:
            聚类标签数组
        """
        try:
            from sklearn.cluster import AffinityPropagation
        except ImportError:
            raise ImportError("请安装scikit-learn库: pip install scikit-learn")

        ap = AffinityPropagation(
            damping=self.damping,
            max_iter=self.max_iter,
            convergence_iter=self.convergence_iter,
            preference=self.preference,
            random_state=42
        )

        labels = ap.fit_predict(X)
        self.cluster_centers_indices_ = ap.cluster_centers_indices_

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

        Affinity Propagation直接选择数据点作为中心

        Args:
            X: 特征矩阵
            labels: 聚类标签

        Returns:
            聚类中心矩阵
        """
        if self.cluster_centers_indices_ is not None:
            return X[self.cluster_centers_indices_]
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
            'n_exemplars': len(self.cluster_centers_indices_) if self.cluster_centers_indices_ is not None else 0
        }

        return metrics
