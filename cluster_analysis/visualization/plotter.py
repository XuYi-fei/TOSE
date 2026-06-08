"""
聚类可视化模块

提供多种聚类结果的可视化功能
"""
from pathlib import Path
from typing import Optional
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import seaborn as sns

from ..core.result import ClusteringResult, AlgorithmResult


class ClusteringPlotter:
    """聚类结果可视化器

    提供4种可视化类型:
    1. 散点图 - 展示聚类结果
    2. 算法对比 - 对比多个算法的聚类结果
    3. 密度曲线 - 展示特征分布的密度估计
    4. 指标对比 - 对比算法的评估指标
    """

    def __init__(self, result: ClusteringResult, output_dir: str):
        """初始化可视化器

        Args:
            result: 聚类结果
            output_dir: 输出目录
        """
        self.result = result
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 设置绘图风格
        sns.set_style('whitegrid')
        plt.rcParams['figure.figsize'] = (10, 8)
        plt.rcParams['font.size'] = 10

        # 设置中文字体支持
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

    def plot_scatter(self, algorithm_name: str, save: bool = True) -> Optional[str]:
        """绘制散点图

        Args:
            algorithm_name: 算法名称
            save: 是否保存图片

        Returns:
            保存的文件路径（如果save=True）
        """
        if algorithm_name not in self.result.algorithm_results:
            raise ValueError(f"算法{algorithm_name}的结果不存在")

        algo_result = self.result.algorithm_results[algorithm_name]

        fig, ax = plt.subplots(figsize=(12, 9))

        # 准备数据
        X = self.result.feature_matrix
        labels = algo_result.labels

        # 生成颜色映射
        unique_labels = np.unique(labels)
        colors = plt.cm.get_cmap('tab10', len(unique_labels))

        # 绘制数据点
        for i, label in enumerate(unique_labels):
            mask = labels == label
            if label == -1:
                # 噪声点用灰色
                ax.scatter(
                    X[mask, 0], X[mask, 1],
                    c='gray', marker='x', s=50, alpha=0.5,
                    label='噪声点'
                )
            else:
                ax.scatter(
                    X[mask, 0], X[mask, 1],
                    c=[colors(i)], marker='o', s=60, alpha=0.7,
                    label=f'簇 {label}'
                )

        # 绘制聚类中心
        if algo_result.cluster_centers is not None:
            centers = algo_result.cluster_centers
            ax.scatter(
                centers[:, 0], centers[:, 1],
                c='red', marker='*', s=300, alpha=0.9,
                edgecolors='black', linewidths=2,
                label='聚类中心'
            )

        # 设置标题和标签
        title = f'{algorithm_name} 聚类结果\n'
        title += f'聚类数: {algo_result.n_clusters}, '
        if algo_result.silhouette_score is not None:
            title += f'轮廓系数: {algo_result.silhouette_score:.4f}, '
        title += f'耗时: {algo_result.execution_time:.3f}秒'

        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('均值 (响应时间)', fontsize=12)
        ax.set_ylabel('方差', fontsize=12)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save:
            filename = f'scatter_{algorithm_name.lower().replace(" ", "_")}.png'
            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            return str(filepath)
        else:
            plt.show()
            return None

    def plot_algorithm_comparison(self, save: bool = True) -> Optional[str]:
        """绘制算法对比图（多子图）

        Args:
            save: 是否保存图片

        Returns:
            保存的文件路径（如果save=True）
        """
        n_algorithms = len(self.result.algorithm_results)
        if n_algorithms == 0:
            raise ValueError("没有可用的聚类结果")

        # 计算子图布局
        n_cols = min(2, n_algorithms)
        n_rows = (n_algorithms + n_cols - 1) // n_cols

        fig, axes = plt.subplots(n_rows, n_cols, figsize=(12 * n_cols, 9 * n_rows))
        if n_algorithms == 1:
            axes = [axes]
        else:
            axes = axes.flatten() if n_rows > 1 or n_cols > 1 else [axes]

        X = self.result.feature_matrix

        for idx, (algo_name, algo_result) in enumerate(self.result.algorithm_results.items()):
            ax = axes[idx]
            labels = algo_result.labels

            # 生成颜色
            unique_labels = np.unique(labels)
            colors = plt.cm.get_cmap('tab10', len(unique_labels))

            # 绘制数据点
            for i, label in enumerate(unique_labels):
                mask = labels == label
                if label == -1:
                    ax.scatter(X[mask, 0], X[mask, 1], c='gray', marker='x', s=40, alpha=0.5)
                else:
                    ax.scatter(X[mask, 0], X[mask, 1], c=[colors(i)], marker='o', s=50, alpha=0.7)

            # 绘制中心
            if algo_result.cluster_centers is not None:
                centers = algo_result.cluster_centers
                ax.scatter(centers[:, 0], centers[:, 1], c='red', marker='*', s=250,
                          edgecolors='black', linewidths=1.5)

            # 设置标题
            title = f'{algo_name}\n'
            title += f'聚类数: {algo_result.n_clusters}, '
            if algo_result.silhouette_score is not None:
                title += f'轮廓系数: {algo_result.silhouette_score:.4f}'

            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.set_xlabel('均值', fontsize=10)
            ax.set_ylabel('方差', fontsize=10)
            ax.grid(True, alpha=0.3)

        # 隐藏多余的子图
        for idx in range(n_algorithms, len(axes)):
            axes[idx].set_visible(False)

        plt.tight_layout()

        if save:
            filepath = self.output_dir / 'algorithm_comparison.png'
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            return str(filepath)
        else:
            plt.show()
            return None

    def plot_density_curves(self, save: bool = True) -> Optional[str]:
        """绘制特征密度曲线

        Args:
            save: 是否保存图片

        Returns:
            保存的文件路径（如果save=True）
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        X = self.result.feature_matrix

        # Mean的密度曲线
        ax1.hist(X[:, 0], bins=50, alpha=0.5, color='blue', density=True, label='直方图')
        try:
            from scipy.stats import gaussian_kde
            kde_mean = gaussian_kde(X[:, 0])
            x_range = np.linspace(X[:, 0].min(), X[:, 0].max(), 200)
            ax1.plot(x_range, kde_mean(x_range), 'r-', linewidth=2, label='核密度估计')
        except:
            pass

        ax1.set_title('均值（响应时间）分布', fontsize=14, fontweight='bold')
        ax1.set_xlabel('均值', fontsize=12)
        ax1.set_ylabel('密度', fontsize=12)
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)

        # Variance的密度曲线
        ax2.hist(X[:, 1], bins=50, alpha=0.5, color='green', density=True, label='直方图')
        try:
            from scipy.stats import gaussian_kde
            kde_var = gaussian_kde(X[:, 1])
            x_range = np.linspace(X[:, 1].min(), X[:, 1].max(), 200)
            ax2.plot(x_range, kde_var(x_range), 'r-', linewidth=2, label='核密度估计')
        except:
            pass

        ax2.set_title('方差分布', fontsize=14, fontweight='bold')
        ax2.set_xlabel('方差', fontsize=12)
        ax2.set_ylabel('密度', fontsize=12)
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        if save:
            filepath = self.output_dir / 'density_curves.png'
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            return str(filepath)
        else:
            plt.show()
            return None

    def plot_metrics_comparison(self, save: bool = True) -> Optional[str]:
        """绘制算法指标对比

        Args:
            save: 是否保存图片

        Returns:
            保存的文件路径（如果save=True）
        """
        if len(self.result.algorithm_results) == 0:
            raise ValueError("没有可用的聚类结果")

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        algo_names = list(self.result.algorithm_results.keys())
        n_clusters_list = [self.result.algorithm_results[name].n_clusters for name in algo_names]
        silhouette_scores = [
            self.result.algorithm_results[name].silhouette_score
            if self.result.algorithm_results[name].silhouette_score is not None else 0
            for name in algo_names
        ]
        execution_times = [self.result.algorithm_results[name].execution_time for name in algo_names]

        # 1. 聚类数量对比
        axes[0, 0].bar(algo_names, n_clusters_list, color='steelblue', alpha=0.7)
        axes[0, 0].set_title('聚类数量', fontsize=12, fontweight='bold')
        axes[0, 0].set_ylabel('数量', fontsize=10)
        axes[0, 0].tick_params(axis='x', rotation=45)
        axes[0, 0].grid(axis='y', alpha=0.3)

        # 2. 轮廓系数对比
        colors = ['green' if s > 0 else 'gray' for s in silhouette_scores]
        axes[0, 1].bar(algo_names, silhouette_scores, color=colors, alpha=0.7)
        axes[0, 1].set_title('轮廓系数', fontsize=12, fontweight='bold')
        axes[0, 1].set_ylabel('系数', fontsize=10)
        axes[0, 1].tick_params(axis='x', rotation=45)
        axes[0, 1].axhline(y=0, color='black', linestyle='--', linewidth=1)
        axes[0, 1].grid(axis='y', alpha=0.3)

        # 3. 执行时间对比
        axes[1, 0].bar(algo_names, execution_times, color='orange', alpha=0.7)
        axes[1, 0].set_title('执行时间', fontsize=12, fontweight='bold')
        axes[1, 0].set_ylabel('秒', fontsize=10)
        axes[1, 0].tick_params(axis='x', rotation=45)
        axes[1, 0].grid(axis='y', alpha=0.3)

        # 4. 综合指标表格
        axes[1, 1].axis('off')
        table_data = []
        table_data.append(['算法', '聚类数', '轮廓系数', '时间(秒)'])
        for name in algo_names:
            result = self.result.algorithm_results[name]
            sil_str = f'{result.silhouette_score:.4f}' if result.silhouette_score is not None else 'N/A'
            table_data.append([
                name,
                str(result.n_clusters),
                sil_str,
                f'{result.execution_time:.3f}'
            ])

        table = axes[1, 1].table(
            cellText=table_data,
            cellLoc='center',
            loc='center',
            colWidths=[0.35, 0.2, 0.25, 0.2]
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)

        # 设置表头样式
        for i in range(len(table_data[0])):
            table[(0, i)].set_facecolor('#4CAF50')
            table[(0, i)].set_text_props(weight='bold', color='white')

        # 高亮最佳算法
        if self.result.best_algorithm:
            best_idx = algo_names.index(self.result.best_algorithm) + 1
            for i in range(len(table_data[0])):
                table[(best_idx, i)].set_facecolor('#FFE082')

        plt.suptitle(f'算法指标对比 - {self.result.system_type.upper()}',
                    fontsize=14, fontweight='bold', y=0.98)
        plt.tight_layout(rect=[0, 0, 1, 0.96])

        if save:
            filepath = self.output_dir / 'metrics_comparison.png'
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            return str(filepath)
        else:
            plt.show()
            return None

    def plot_all(self) -> dict:
        """生成所有可视化图表

        Returns:
            字典 {图表类型: 文件路径}
        """
        results = {}

        # 1. 为每个算法生成散点图
        for algo_name in self.result.algorithm_results.keys():
            filepath = self.plot_scatter(algo_name, save=True)
            results[f'scatter_{algo_name}'] = filepath

        # 2. 算法对比图
        if len(self.result.algorithm_results) > 1:
            results['comparison'] = self.plot_algorithm_comparison(save=True)

        # 3. 密度曲线
        results['density'] = self.plot_density_curves(save=True)

        # 4. 指标对比
        results['metrics'] = self.plot_metrics_comparison(save=True)

        return results
