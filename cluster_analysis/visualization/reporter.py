"""
聚类分析报告生成器

生成Markdown格式的聚类分析报告
"""
from pathlib import Path
from typing import Dict, List, Optional
import logging
import yaml
from datetime import datetime
import numpy as np

from ..core.result import ClusteringResult, AlgorithmResult

logger = logging.getLogger(__name__)


class ClusteringReporter:
    """聚类分析报告生成器"""

    def __init__(self, result: ClusteringResult, output_dir: str):
        """初始化报告生成器

        Args:
            result: 聚类结果
            output_dir: 输出目录
        """
        self.result = result
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(self, plot_paths: Dict[str, str]) -> str:
        """生成Markdown报告

        Args:
            plot_paths: 图表路径字典

        Returns:
            报告文件路径
        """
        logger.info("生成聚类分析报告...")

        report_path = self.output_dir / 'clustering_report.md'

        with open(report_path, 'w', encoding='utf-8') as f:
            # 标题
            f.write(f"# {self.result.system_type.upper()} 聚类分析报告\n\n")

            # 1. 数据概述
            self._write_data_overview(f)

            # 2. 算法结果汇总
            self._write_algorithm_summary(f)

            # 3. 最佳算法推荐
            self._write_best_algorithm(f)

            # 4. 详细结果
            self._write_detailed_results(f)

            # 5. 可视化图表
            self._write_visualizations(f, plot_paths)

            # 6. 聚类统计信息
            self._write_cluster_statistics(f)

        logger.info(f"报告已保存: {report_path}")
        return str(report_path)

    def _write_data_overview(self, f):
        """写入数据概述"""
        f.write("## 数据概述\n\n")
        f.write(f"- **系统类型**: {self.result.system_type.upper()}\n")
        f.write(f"- **总数据点数**: {self.result.total_points}\n")
        f.write(f"- **特征维度**: 2 ([mean, variance])\n")
        f.write(f"- **Norm标签类型**: {len(set(self.result.norm_labels))} 种\n\n")

        # 特征统计
        f.write("### 特征统计\n\n")
        X = self.result.feature_matrix
        f.write("| 特征 | 最小值 | 最大值 | 均值 | 标准差 |\n")
        f.write("|------|--------|--------|------|--------|\n")
        f.write(f"| Mean | {X[:, 0].min():.6f} | {X[:, 0].max():.6f} | "
               f"{X[:, 0].mean():.6f} | {X[:, 0].std():.6f} |\n")
        f.write(f"| Variance | {X[:, 1].min():.6f} | {X[:, 1].max():.6f} | "
               f"{X[:, 1].mean():.6f} | {X[:, 1].std():.6f} |\n\n")

    def _write_algorithm_summary(self, f):
        """写入算法结果汇总"""
        f.write("## 算法结果汇总\n\n")
        f.write("| 算法 | 聚类数 | 轮廓系数 | 执行时间(s) | 状态 |\n")
        f.write("|------|--------|----------|------------|------|\n")

        for algo_name, algo_result in self.result.algorithm_results.items():
            sil_str = f"{algo_result.silhouette_score:.4f}" if algo_result.silhouette_score is not None else "N/A"
            is_best = "⭐ 最佳" if algo_name == self.result.best_algorithm else ""

            f.write(f"| {algo_name} | {algo_result.n_clusters} | {sil_str} | "
                   f"{algo_result.execution_time:.3f} | {is_best} |\n")

        f.write("\n")

    def _write_best_algorithm(self, f):
        """写入最佳算法推荐"""
        f.write("## 最佳算法推荐\n\n")

        if self.result.best_algorithm is None:
            f.write("⚠️ 未找到有效的聚类结果\n\n")
            return

        best_result = self.result.get_best_result()
        f.write(f"### ⭐ {self.result.best_algorithm}\n\n")
        f.write(f"- **聚类数量**: {best_result.n_clusters}\n")
        f.write(f"- **轮廓系数**: {best_result.silhouette_score:.4f}\n")
        f.write(f"- **执行时间**: {best_result.execution_time:.3f}s\n\n")

        # 推荐理由
        f.write("**推荐理由**:\n\n")
        if best_result.silhouette_score >= 0.5:
            f.write("- ✅ 聚类质量优秀（轮廓系数 ≥ 0.5）\n")
        elif best_result.silhouette_score >= 0.3:
            f.write("- ✅ 聚类质量良好（轮廓系数 ≥ 0.3）\n")
        else:
            f.write("- ⚠️ 聚类质量一般（轮廓系数 < 0.3）\n")

        f.write(f"- ⚡ 执行效率: {best_result.execution_time:.3f}秒\n")
        f.write(f"- 📊 发现 {best_result.n_clusters} 个分布簇\n\n")

    def _write_detailed_results(self, f):
        """写入详细结果"""
        f.write("## 详细算法结果\n\n")

        for algo_name, algo_result in self.result.algorithm_results.items():
            f.write(f"### {algo_name}\n\n")

            # 基本信息
            f.write("**基本信息**:\n\n")
            f.write(f"- 聚类数量: {algo_result.n_clusters}\n")
            sil_str = f"{algo_result.silhouette_score:.4f}" if algo_result.silhouette_score is not None else "N/A"
            f.write(f"- 轮廓系数: {sil_str}\n")
            f.write(f"- 执行时间: {algo_result.execution_time:.3f}s\n\n")

            # 聚类统计
            stats = self.result.get_cluster_statistics(algo_name)
            f.write("**聚类统计**:\n\n")
            f.write("| 聚类ID | 大小 | 均值特征 | 标准差特征 |\n")
            f.write("|--------|------|----------|------------|\n")

            for cluster_id in sorted(stats.keys()):
                stat = stats[cluster_id]
                mean_feat = stat['mean_feature']
                std_feat = stat['std_feature']
                f.write(f"| {cluster_id} | {stat['size']} | "
                       f"[{mean_feat[0]:.6f}, {mean_feat[1]:.6f}] | "
                       f"[{std_feat[0]:.6f}, {std_feat[1]:.6f}] |\n")

            f.write("\n")

            # Norm标签分布
            f.write("**各聚类的Norm标签分布**:\n\n")
            for cluster_id in sorted(stats.keys()):
                norm_dist = stats[cluster_id]['norm_label_distribution']
                f.write(f"- **Cluster {cluster_id}**: ")
                norm_strs = [f"{label}({count})" for label, count in sorted(norm_dist.items())]
                f.write(", ".join(norm_strs))
                f.write("\n")

            f.write("\n")

            # 额外指标
            if algo_result.additional_metrics:
                f.write("**额外指标**:\n\n")
                for key, value in algo_result.additional_metrics.items():
                    if isinstance(value, dict):
                        f.write(f"- {key}:\n")
                        for k, v in value.items():
                            f.write(f"  - {k}: {v}\n")
                    else:
                        f.write(f"- {key}: {value}\n")
                f.write("\n")

    def _write_visualizations(self, f, plot_paths: Dict[str, str]):
        """写入可视化图表"""
        f.write("## 可视化图表\n\n")

        # 密度曲线
        if 'density' in plot_paths:
            f.write("### 特征分布密度\n\n")
            rel_path = Path(plot_paths['density']).name
            f.write(f"![Density Curves](./{rel_path})\n\n")

        # 指标对比
        if 'metrics' in plot_paths:
            f.write("### 算法指标对比\n\n")
            rel_path = Path(plot_paths['metrics']).name
            f.write(f"![Metrics Comparison](./{rel_path})\n\n")

        # 算法对比
        if 'comparison' in plot_paths:
            f.write("### 算法聚类结果对比\n\n")
            rel_path = Path(plot_paths['comparison']).name
            f.write(f"![Algorithm Comparison](./{rel_path})\n\n")

        # 各算法散点图
        f.write("### 各算法聚类散点图\n\n")
        for algo_name in self.result.algorithm_results.keys():
            key = f'scatter_{algo_name}'
            if key in plot_paths:
                rel_path = Path(plot_paths[key]).name
                f.write(f"#### {algo_name}\n\n")
                f.write(f"![{algo_name} Scatter](./{rel_path})\n\n")

    def _write_cluster_statistics(self, f):
        """写入聚类统计信息"""
        f.write("## 聚类发现的分布参数\n\n")

        if self.result.best_algorithm is None:
            f.write("⚠️ 无可用结果\n\n")
            return

        best_result = self.result.get_best_result()
        stats = self.result.get_cluster_statistics(self.result.best_algorithm)

        f.write(f"基于最佳算法（{self.result.best_algorithm}）的聚类中心作为发现的分布参数：\n\n")
        f.write("| Cluster | Mean (μ) | Variance (σ²) | 样本数 | 主要Norm标签 |\n")
        f.write("|---------|----------|---------------|--------|-------------|\n")

        for cluster_id in sorted(stats.keys()):
            stat = stats[cluster_id]
            mean_val = stat['mean_feature'][0]
            var_val = stat['mean_feature'][1]

            # 找出主要的norm标签
            norm_dist = stat['norm_label_distribution']
            main_norm = max(norm_dist.items(), key=lambda x: x[1])[0] if norm_dist else 'N/A'

            f.write(f"| {cluster_id} | {mean_val:.6f} | {var_val:.6f} | "
                   f"{stat['size']} | {main_norm} |\n")

        f.write("\n")
        f.write("**使用建议**:\n\n")
        f.write("这些聚类中心可以作为验证框架配置文件中`expected_distributions`的参考值。\n\n")

    def save_learned_distributions(
        self,
        output_path: Optional[Path] = None,
        clustering_config_path: Optional[str] = None,
        algorithm_name: Optional[str] = None
    ) -> str:
        """保存学习到的分布参数为YAML配置文件

        Args:
            output_path: 输出文件路径，默认为output_dir/learned_distributions.yaml
            clustering_config_path: 聚类配置文件路径（用于追溯）
            algorithm_name: 指定导出的算法名称，默认导出最佳算法

        Returns:
            保存的文件路径
        """
        selected_algorithm = algorithm_name or self.result.best_algorithm
        if selected_algorithm is None:
            logger.warning("没有可用的聚类结果，跳过保存learned_distributions")
            return ""

        if selected_algorithm not in self.result.algorithm_results:
            raise ValueError(f"算法{selected_algorithm}的结果不存在")

        if output_path is None:
            output_path = self.output_dir / 'learned_distributions.yaml'
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        selected_result = self.result.algorithm_results[selected_algorithm]
        stats = self.result.get_cluster_statistics(selected_algorithm)

        # 构建配置数据
        config_data = {
            'system_type': self.result.system_type,
            'learned_at': datetime.now().isoformat(),
            'algorithm': selected_algorithm,
            'silhouette_score': float(selected_result.silhouette_score) if selected_result.silhouette_score is not None else None,
        }

        if clustering_config_path:
            config_data['clustering_config'] = str(clustering_config_path)

        distributions = self._build_distribution_export(selected_result, stats)

        context_calibration_model = selected_result.additional_metrics.get('context_calibration_model')
        if context_calibration_model:
            config_data['context_calibration_model'] = dict(context_calibration_model)
        config_data['distributions'] = distributions

        # 保存为YAML
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        logger.info(f"学习到的分布参数已保存: {output_path}")
        logger.info(f"包含 {len(distributions)} 个分布: {list(distributions.keys())}")

        return str(output_path)

    def _build_distribution_export(
        self,
        selected_result: AlgorithmResult,
        stats: Dict[int, Dict[str, Dict[str, object]]],
    ) -> Dict[str, Dict[str, object]]:
        distributions: Dict[str, Dict[str, object]] = {}
        stage2_models = selected_result.additional_metrics.get('cluster_distribution_models', {})

        if stage2_models:
            for cluster_id in sorted(stage2_models.keys(), key=int):
                cluster_model = dict(stage2_models[cluster_id])
                key = f'cluster_{int(cluster_id)}'
                cluster_model['cluster_id'] = int(cluster_id)
                distributions[key] = cluster_model
            return distributions

        # 回退到旧的高斯导出逻辑，兼容没有 stage-2 拟合信息的历史结果。
        for cluster_id in sorted(stats.keys()):
            stat = stats[cluster_id]
            mean_val = float(stat['mean_feature'][0])
            var_val = float(stat['mean_feature'][1])
            sigma = float(np.sqrt(max(var_val, 1e-12)))
            norm_dist = stat['norm_label_distribution']
            main_norm = max(norm_dist.items(), key=lambda x: x[1])[0] if norm_dist else f'cluster{cluster_id}'

            distributions[f'cluster_{cluster_id}'] = {
                'distribution_type': 'norm',
                'fitted_params': {
                    'shape_args': [],
                    'loc': mean_val,
                    'scale': sigma,
                },
                'mu': mean_val,
                'sigma': sigma,
                'variance': var_val,
                'sample_count': int(stat['size']),
                'cluster_id': int(cluster_id),
                'dominant_norm': main_norm,
                'norm_label_distribution': {
                    label: int(count) for label, count in norm_dist.items()
                },
                'goodness_of_fit': {
                    'selected_p_value': None,
                    'selection_reason': 'legacy_gaussian_fallback',
                },
            }

        return distributions
