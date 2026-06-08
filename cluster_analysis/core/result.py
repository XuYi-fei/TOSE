"""
聚类结果数据模型

存储聚类分析的结果数据
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import numpy as np


@dataclass
class AlgorithmResult:
    """单个算法的聚类结果"""
    algorithm_name: str                    # 算法名称
    n_clusters: int                        # 聚类数量
    labels: np.ndarray                     # 数据点的聚类标签
    cluster_centers: Optional[np.ndarray] = None  # 聚类中心（如果有）
    silhouette_score: Optional[float] = None      # 轮廓系数
    execution_time: float = 0.0            # 执行时间（秒）
    additional_metrics: Dict[str, Any] = field(default_factory=dict)  # 额外的评估指标

    def __post_init__(self):
        """验证数据一致性"""
        if len(self.labels) == 0:
            raise ValueError("labels不能为空")

        if self.n_clusters <= 0:
            raise ValueError("n_clusters必须大于0")

        # 验证聚类中心数量与聚类数匹配
        if self.cluster_centers is not None:
            if len(self.cluster_centers) != self.n_clusters:
                raise ValueError(f"聚类中心数量({len(self.cluster_centers)})与聚类数({self.n_clusters})不匹配")


@dataclass
class ClusteringResult:
    """聚类分析结果"""
    system_type: str                       # 系统类型（rubis/bsn）
    total_points: int                      # 总数据点数
    feature_matrix: np.ndarray             # 特征矩阵 (n_samples, 2) [mean, variance]
    norm_labels: List[str]                 # 每个数据点对应的norm标签
    filenames: List[str]                   # 每个数据点对应的文件名
    positions: List[int]                   # 每个数据点在文件中的位置
    context_keys: List[Optional[str]] = field(default_factory=list)  # 每个数据点对应的上下文键
    context_features: List[Dict[str, float]] = field(default_factory=list)  # 每个数据点对应的上下文特征

    # 多算法结果
    algorithm_results: Dict[str, AlgorithmResult] = field(default_factory=dict)

    # 最佳算法
    best_algorithm: Optional[str] = None

    def add_algorithm_result(self, result: AlgorithmResult) -> None:
        """添加算法结果

        Args:
            result: 算法聚类结果
        """
        self.algorithm_results[result.algorithm_name] = result

        # 更新最佳算法（基于轮廓系数）
        if result.silhouette_score is not None:
            if self.best_algorithm is None:
                self.best_algorithm = result.algorithm_name
            else:
                best_result = self.algorithm_results[self.best_algorithm]
                if best_result.silhouette_score is None or \
                   result.silhouette_score > best_result.silhouette_score:
                    self.best_algorithm = result.algorithm_name

    def get_best_result(self) -> Optional[AlgorithmResult]:
        """获取最佳算法的结果

        Returns:
            最佳算法的结果，如果没有则返回None
        """
        if self.best_algorithm is None:
            return None
        return self.algorithm_results.get(self.best_algorithm)

    def get_cluster_statistics(self, algorithm_name: str) -> Dict[int, Dict[str, Any]]:
        """获取指定算法的聚类统计信息

        Args:
            algorithm_name: 算法名称

        Returns:
            字典{cluster_id: {统计信息}}
        """
        if algorithm_name not in self.algorithm_results:
            raise ValueError(f"算法{algorithm_name}的结果不存在")

        result = self.algorithm_results[algorithm_name]
        stats = {}

        valid_cluster_ids = [int(label) for label in np.unique(result.labels) if label >= 0]

        for cluster_id in valid_cluster_ids:
            # 获取该簇的所有数据点索引
            mask = result.labels == cluster_id
            cluster_points = self.feature_matrix[mask]
            cluster_norm_labels = [self.norm_labels[i] for i, m in enumerate(mask) if m]

            # 计算统计信息
            stats[cluster_id] = {
                'size': len(cluster_points),
                'mean_feature': cluster_points.mean(axis=0),
                'std_feature': cluster_points.std(axis=0),
                'norm_label_distribution': self._count_norm_labels(cluster_norm_labels)
            }

        return stats

    def _count_norm_labels(self, labels: List[str]) -> Dict[str, int]:
        """统计norm标签分布

        Args:
            labels: norm标签列表

        Returns:
            字典{norm_label: count}
        """
        counts = {}
        for label in labels:
            counts[label] = counts.get(label, 0) + 1
        return counts

    def __post_init__(self):
        """验证数据一致性"""
        if len(self.feature_matrix) != self.total_points:
            raise ValueError(f"特征矩阵行数({len(self.feature_matrix)})与总数据点数({self.total_points})不匹配")

        if len(self.norm_labels) != self.total_points:
            raise ValueError(f"norm_labels长度({len(self.norm_labels)})与总数据点数({self.total_points})不匹配")

        if len(self.filenames) != self.total_points:
            raise ValueError(f"filenames长度({len(self.filenames)})与总数据点数({self.total_points})不匹配")

        if len(self.positions) != self.total_points:
            raise ValueError(f"positions长度({len(self.positions)})与总数据点数({self.total_points})不匹配")

        if self.context_keys and len(self.context_keys) != self.total_points:
            raise ValueError(f"context_keys长度({len(self.context_keys)})与总数据点数({self.total_points})不匹配")

        if self.context_features and len(self.context_features) != self.total_points:
            raise ValueError(f"context_features长度({len(self.context_features)})与总数据点数({self.total_points})不匹配")

        if self.feature_matrix.shape[1] != 2:
            raise ValueError(f"特征矩阵必须是2维([mean, variance])，当前维度: {self.feature_matrix.shape[1]}")
