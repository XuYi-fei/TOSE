"""
聚类算法抽象基类

定义聚类算法的统一接口
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import numpy as np
from ..core.result import AlgorithmResult


class ClusteringAlgorithm(ABC):
    """聚类算法抽象基类

    所有聚类算法都应继承此类并实现其抽象方法
    """

    def __init__(self, name: str, **kwargs):
        """初始化聚类算法

        Args:
            name: 算法名称
            **kwargs: 算法特定的参数
        """
        self.name = name
        self.params = kwargs

    @abstractmethod
    def fit_predict(self, X: np.ndarray) -> np.ndarray:
        """执行聚类并返回标签

        Args:
            X: 特征矩阵 (n_samples, n_features)

        Returns:
            聚类标签数组 (n_samples,)
        """
        pass

    @abstractmethod
    def get_n_clusters(self, labels: np.ndarray) -> int:
        """获取聚类数量

        Args:
            labels: 聚类标签

        Returns:
            聚类数量
        """
        pass

    def get_cluster_centers(self, X: np.ndarray, labels: np.ndarray) -> Optional[np.ndarray]:
        """计算聚类中心

        默认实现：计算每个簇的均值作为中心
        子类可以重写此方法提供特定实现

        Args:
            X: 特征矩阵
            labels: 聚类标签

        Returns:
            聚类中心矩阵 (n_clusters, n_features)，如果无法计算则返回None
        """
        n_clusters = self.get_n_clusters(labels)

        # 过滤噪声点（标签为-1）
        valid_labels = [label for label in np.unique(labels) if label >= 0]

        if len(valid_labels) == 0:
            return None

        centers = []
        for label in sorted(valid_labels):
            mask = labels == label
            cluster_points = X[mask]
            center = cluster_points.mean(axis=0)
            centers.append(center)

        return np.array(centers)

    def calculate_additional_metrics(
        self,
        X: np.ndarray,
        labels: np.ndarray
    ) -> Dict[str, Any]:
        """计算额外的评估指标

        子类可以重写此方法添加算法特定的指标

        Args:
            X: 特征矩阵
            labels: 聚类标签

        Returns:
            指标字典
        """
        return {}

    def run(self, X: np.ndarray) -> AlgorithmResult:
        """执行完整的聚类流程

        包括聚类、评估和结果封装

        Args:
            X: 特征矩阵

        Returns:
            AlgorithmResult对象
        """
        import time
        from sklearn.metrics import silhouette_score

        # 执行聚类
        start_time = time.time()
        labels = self.fit_predict(X)
        execution_time = time.time() - start_time

        # 获取聚类数量
        n_clusters = self.get_n_clusters(labels)

        # 计算聚类中心
        centers = self.get_cluster_centers(X, labels)

        # 计算轮廓系数
        silhouette = None
        if n_clusters > 1 and n_clusters < len(X):
            # 只在有效范围内计算轮廓系数
            valid_mask = labels >= 0  # 排除噪声点
            if valid_mask.sum() > 0 and len(np.unique(labels[valid_mask])) > 1:
                try:
                    silhouette = silhouette_score(X[valid_mask], labels[valid_mask])
                except:
                    silhouette = None

        # 计算额外指标
        additional_metrics = self.calculate_additional_metrics(X, labels)

        # 封装结果
        return AlgorithmResult(
            algorithm_name=self.name,
            n_clusters=n_clusters,
            labels=labels,
            cluster_centers=centers,
            silhouette_score=silhouette,
            execution_time=execution_time,
            additional_metrics=additional_metrics
        )

    def __repr__(self) -> str:
        """字符串表示"""
        params_str = ', '.join(f'{k}={v}' for k, v in self.params.items())
        return f"{self.name}({params_str})"
