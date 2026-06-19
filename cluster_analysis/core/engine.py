"""
聚类引擎

负责协调整个聚类分析流程
"""
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging
import numpy as np

from common.adapters import ParserFactory, TraceParser
from common.models import ContextCalibrationModel, DistributionParameters, build_context_key
from .result import ClusteringResult, AlgorithmResult
from .distribution_fitting import ClusterDistributionFitter
from ..algorithms.factory import ClusteringFactory

logger = logging.getLogger(__name__)


class ClusteringEngine:
    """聚类分析引擎

    协调数据加载、特征提取、聚类执行和结果汇总
    """

    def __init__(
        self,
        system_type: str,
        algorithm_names: List[str],
        algorithm_params: Optional[Dict[str, dict]] = None,
        stage1_clustering_feature: str = "mu",
        candidate_distributions: Optional[List[str]] = None,
        normality_alpha: float = 0.05,
        enable_context_calibration: bool = True,
        context_modeling_method: str = "linear_mu",
        partition_context_features: Optional[List[str]] = None,
        boundary_trim_points: int = 0,
    ):
        """初始化聚类引擎

        Args:
            system_type: 系统类型（'rubis' 或 'bsn'）
            algorithm_names: 要使用的算法名称列表
            algorithm_params: 算法参数字典 {algorithm_name: {param: value}}
        """
        self.system_type = system_type
        self.algorithm_names = algorithm_names
        self.algorithm_params = algorithm_params or {}
        self.stage1_clustering_feature = stage1_clustering_feature
        self.distribution_fitter = ClusterDistributionFitter(
            candidate_distributions=candidate_distributions,
            normality_alpha=normality_alpha,
        )
        self.enable_context_calibration = enable_context_calibration
        self.context_modeling_method = context_modeling_method
        self.partition_context_features = list(partition_context_features or [])

        # 创建解析器
        self.parser = ParserFactory.create(
            system_type,
            boundary_trim_points=boundary_trim_points,
        )

        # 验证算法可用性
        for algo_name in algorithm_names:
            if not ClusteringFactory.is_registered(algo_name):
                available = ', '.join(ClusteringFactory.list_algorithms())
                raise ValueError(f"未注册的聚类算法: {algo_name}。可用算法: {available}")

    def load_data(self, data_path: str) -> List[DistributionParameters]:
        """加载trace数据并提取分布参数

        Args:
            data_path: 数据目录路径

        Returns:
            分布参数列表
        """
        data_dir = Path(data_path)
        if not data_dir.exists():
            raise FileNotFoundError(f"数据路径不存在: {data_path}")

        logger.info(f"开始加载{self.system_type}数据集: {data_path}")

        # 获取所有trace文件
        trace_files = sorted(data_dir.glob('*.txt'))
        if not trace_files:
            raise ValueError(f"目录{data_path}中未找到trace文件")

        logger.info(f"找到{len(trace_files)}个trace文件")

        # 解析所有文件
        all_parameters = []
        parsed_count = 0

        for trace_file in trace_files:
            try:
                parameters = self.parser.parse_file(trace_file)
                self._attach_partition_context(parameters)
                all_parameters.extend(parameters)
                parsed_count += 1
            except Exception as e:
                logger.warning(f"解析文件{trace_file.name}失败: {e}")

        logger.info(f"成功解析{parsed_count}个文件，提取{len(all_parameters)}个数据点")

        if len(all_parameters) == 0:
            raise ValueError("未提取到任何有效数据点")

        return all_parameters

    def extract_features(self, parameters: List[DistributionParameters]) -> tuple:
        """从分布参数中提取特征矩阵

        Args:
            parameters: 分布参数列表

        Returns:
            元组 (report_feature_matrix, clustering_matrix, norm_labels, filenames, positions, context_keys, context_features)
        """
        logger.info("提取特征矩阵...")

        feature_matrix = []
        clustering_matrix = []
        norm_labels = []
        filenames = []
        positions = []
        context_keys = []
        context_features = []

        for param in parameters:
            # 特征: [mean, variance]
            feature_matrix.append([param.mean, param.variance])
            if self.stage1_clustering_feature == "mu":
                clustering_matrix.append([param.mean])
            else:
                raise ValueError(f"不支持的stage1聚类特征: {self.stage1_clustering_feature}")
            norm_labels.append(param.norm_label)
            filenames.append(param.filename)
            positions.append(param.position)
            context_keys.append(param.context_key)
            context_features.append(dict(param.context_features))

        feature_matrix = np.array(feature_matrix)
        clustering_matrix = np.array(clustering_matrix)

        logger.info(f"特征矩阵维度: {feature_matrix.shape}")
        logger.info(f"stage-1 聚类矩阵维度: {clustering_matrix.shape}")
        logger.info(f"特征统计 - 均值范围: [{feature_matrix[:, 0].min():.6f}, {feature_matrix[:, 0].max():.6f}]")
        logger.info(f"特征统计 - 方差范围: [{feature_matrix[:, 1].min():.6f}, {feature_matrix[:, 1].max():.6f}]")

        return feature_matrix, clustering_matrix, norm_labels, filenames, positions, context_keys, context_features

    def run_clustering(self, data_path: str) -> ClusteringResult:
        """执行完整的聚类分析流程

        Args:
            data_path: 数据目录路径

        Returns:
            ClusteringResult对象
        """
        # 1. 加载数据
        parameters = self.load_data(data_path)

        # 2. 提取特征
        (
            feature_matrix,
            clustering_matrix,
            norm_labels,
            filenames,
            positions,
            context_keys,
            context_features,
        ) = self.extract_features(parameters)

        # 3. 创建结果对象
        result = ClusteringResult(
            system_type=self.system_type,
            total_points=len(parameters),
            feature_matrix=feature_matrix,
            norm_labels=norm_labels,
            filenames=filenames,
            positions=positions,
            context_keys=context_keys,
            context_features=context_features,
        )

        context_calibration_model = None
        if self.enable_context_calibration:
            context_calibration_model = ContextCalibrationModel.fit(
                parameters,
                modeling_method=self.context_modeling_method,
            )

        # 4. 运行所有算法
        logger.info(f"开始运行{len(self.algorithm_names)}个聚类算法...")

        for algo_name in self.algorithm_names:
            logger.info(f"运行算法: {algo_name}")

            try:
                # 获取算法参数
                params = self.algorithm_params.get(algo_name, {})

                # 创建算法实例
                algorithm = self._create_algorithm_for_rq4(algo_name)

                # 执行聚类
                if self.partition_context_features:
                    algo_result = self._run_partitioned_algorithm(
                        algo_name,
                        feature_matrix,
                        clustering_matrix,
                        parameters,
                    )
                else:
                    algo_result = algorithm.run(clustering_matrix)
                algo_result.cluster_centers = self._calculate_report_space_centers(feature_matrix, algo_result.labels)
                algo_result.additional_metrics['stage1_clustering_feature'] = self.stage1_clustering_feature
                if self.partition_context_features:
                    algo_result.additional_metrics['partition_context_features'] = list(self.partition_context_features)
                algo_result.additional_metrics['cluster_distribution_models'] = self._fit_cluster_distribution_models(
                    parameters,
                    algo_result.labels,
                )
                if context_calibration_model is not None:
                    algo_result.additional_metrics['context_calibration_model'] = context_calibration_model.to_dict()

                # 添加到结果
                result.add_algorithm_result(algo_result)

                # 格式化轮廓系数
                sil_str = f"{algo_result.silhouette_score:.4f}" if algo_result.silhouette_score is not None else "N/A"

                logger.info(
                    f"  - 聚类数: {algo_result.n_clusters}, "
                    f"轮廓系数: {sil_str}, "
                    f"耗时: {algo_result.execution_time:.3f}s"
                )

            except Exception as e:
                logger.error(f"算法{algo_name}执行失败: {e}", exc_info=True)

        # 5. 汇总结果
        if result.best_algorithm:
            logger.info(f"最佳算法: {result.best_algorithm}")
        else:
            logger.warning("未找到有效的聚类结果")

        return result

    def _create_algorithm_for_rq4(self, algorithm_name: str):
        """Create a clustering algorithm instance with configured params.

        Kept as a small helper so RQ4 ARI evaluation can reuse the exact same
        algorithm construction path as the standard clustering pipeline.
        """
        params = self.algorithm_params.get(algorithm_name, {})
        return ClusteringFactory.create(algorithm_name, **params)

    def _attach_partition_context(self, parameters: List[DistributionParameters]) -> None:
        if not self.partition_context_features:
            return

        for parameter in parameters:
            partition_features = {
                feature_name: float(parameter.context_features[feature_name])
                for feature_name in self.partition_context_features
                if feature_name in parameter.context_features
            }
            parameter.partition_context_features = partition_features
            parameter.partition_context_key = build_context_key(partition_features)

    def _run_partitioned_algorithm(
        self,
        algorithm_name: str,
        feature_matrix: np.ndarray,
        clustering_matrix: np.ndarray,
        parameters: List[DistributionParameters],
    ) -> AlgorithmResult:
        partition_groups: Dict[str, List[int]] = {}
        for index, parameter in enumerate(parameters):
            key = parameter.partition_context_key or "__global__"
            partition_groups.setdefault(key, []).append(index)

        global_labels = np.full(len(parameters), -1, dtype=int)
        global_centers: List[np.ndarray] = []
        cluster_offset = 0
        execution_time = 0.0
        silhouette_parts: List[float] = []
        partition_summaries: Dict[str, Dict[str, object]] = {}

        for partition_key in sorted(partition_groups.keys()):
            indices = partition_groups[partition_key]
            partition_matrix = clustering_matrix[indices]
            algorithm = ClusteringFactory.create(
                algorithm_name,
                **self.algorithm_params.get(algorithm_name, {}),
            )
            partition_result = algorithm.run(partition_matrix)
            execution_time += partition_result.execution_time

            unique_labels = sorted(int(label) for label in np.unique(partition_result.labels) if label >= 0)
            label_mapping = {
                old_label: cluster_offset + new_index
                for new_index, old_label in enumerate(unique_labels)
            }
            remapped_labels = np.asarray(
                [label_mapping.get(int(label), -1) for label in partition_result.labels],
                dtype=int,
            )
            for local_index, global_index in enumerate(indices):
                global_labels[global_index] = remapped_labels[local_index]

            if partition_result.cluster_centers is not None:
                global_centers.extend(np.asarray(partition_result.cluster_centers, dtype=float))

            if partition_result.silhouette_score is not None:
                silhouette_parts.append(float(partition_result.silhouette_score))

            partition_summaries[partition_key] = {
                "size": len(indices),
                "n_clusters": partition_result.n_clusters,
                "cluster_id_offset": cluster_offset,
            }
            cluster_offset += len(unique_labels)

        return AlgorithmResult(
            algorithm_name=algorithm_name,
            n_clusters=cluster_offset,
            labels=global_labels,
            cluster_centers=np.asarray(global_centers, dtype=float) if global_centers else None,
            silhouette_score=(float(np.mean(silhouette_parts)) if silhouette_parts else None),
            execution_time=execution_time,
            additional_metrics={
                "partition_summaries": partition_summaries,
                "partition_context_features": list(self.partition_context_features),
            },
        )

    def _calculate_report_space_centers(self, feature_matrix: np.ndarray, labels: np.ndarray) -> Optional[np.ndarray]:
        valid_cluster_ids = sorted(int(label) for label in np.unique(labels) if label >= 0)
        if not valid_cluster_ids:
            return None

        centers = []
        for cluster_id in valid_cluster_ids:
            cluster_points = feature_matrix[labels == cluster_id]
            centers.append(cluster_points.mean(axis=0))

        return np.array(centers)

    def _fit_cluster_distribution_models(
        self,
        parameters: List[DistributionParameters],
        labels: np.ndarray,
    ) -> Dict[int, Dict[str, object]]:
        cluster_models: Dict[int, Dict[str, object]] = {}
        valid_cluster_ids = sorted(int(label) for label in np.unique(labels) if label >= 0)

        for cluster_id in valid_cluster_ids:
            cluster_parameters = [
                parameter for index, parameter in enumerate(parameters)
                if labels[index] == cluster_id
            ]
            if not cluster_parameters:
                continue

            model = self.distribution_fitter.fit_cluster_distribution(cluster_id, cluster_parameters)
            model_dict = model.to_dict()
            context_key, context_features = self._summarize_cluster_context(cluster_parameters)
            if context_key is not None:
                model_dict['context_key'] = context_key
            if context_features:
                model_dict['context_features'] = context_features
            partition_context_key, partition_context_features = self._summarize_cluster_partition_context(cluster_parameters)
            if partition_context_key is not None:
                model_dict['partition_context_key'] = partition_context_key
            if partition_context_features:
                model_dict['partition_context_features'] = partition_context_features
            cluster_models[cluster_id] = model_dict

        return cluster_models

    def _summarize_cluster_context(
        self,
        parameters: List[DistributionParameters],
    ) -> Tuple[Optional[str], Dict[str, float]]:
        feature_names = sorted({
            key
            for parameter in parameters
            for key in parameter.context_features.keys()
        })
        if not feature_names:
            return None, {}

        summarized = {
            feature_name: float(np.mean([
                parameter.context_features.get(feature_name, 0.0)
                for parameter in parameters
            ]))
            for feature_name in feature_names
        }
        return build_context_key(summarized), summarized

    def _summarize_cluster_partition_context(
        self,
        parameters: List[DistributionParameters],
    ) -> Tuple[Optional[str], Dict[str, float]]:
        feature_names = sorted({
            key
            for parameter in parameters
            for key in parameter.partition_context_features.keys()
        })
        if not feature_names:
            return None, {}

        summarized = {
            feature_name: float(np.mean([
                parameter.partition_context_features.get(feature_name, 0.0)
                for parameter in parameters
            ]))
            for feature_name in feature_names
        }
        return build_context_key(summarized), summarized
