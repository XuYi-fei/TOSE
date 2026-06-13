"""
CLI命令行接口模块

提供命令行参数解析和聚类执行功能
"""
import argparse
import logging
import sys
from pathlib import Path

from .config.config import ClusteringConfig
from .core.engine import ClusteringEngine
from .visualization.reporter import ClusteringReporter


def build_algorithm_distribution_path(base_path: str, algorithm_name: str) -> Path:
    """基于默认分布文件路径构造按算法命名的分布文件路径。"""
    path = Path(base_path)
    return path.with_name(f"{path.stem}_{algorithm_name}{path.suffix}")


def setup_logging(verbose: bool = False):
    """配置日志输出

    Args:
        verbose: 是否输出详细日志
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='[%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def run_clustering(config_path: str, output_dir: str = None, verbose: bool = False) -> bool:
    """执行聚类分析流程

    Args:
        config_path: 配置文件路径
        output_dir: 输出目录（覆盖配置文件中的设置）
        verbose: 是否输出详细日志

    Returns:
        聚类是否成功
    """
    setup_logging(verbose)
    logger = logging.getLogger(__name__)

    try:
        # 1. 加载配置
        logger.info(f"加载配置文件: {config_path}")
        config = ClusteringConfig.from_yaml(config_path)

        # 命令行参数覆盖
        if output_dir:
            config.output_dir = output_dir
            logger.info(f"输出目录已覆盖: {output_dir}")

        logger.info(f"系统类型: {config.system_type}")
        logger.info(f"数据路径: {config.data_path}")
        logger.info(f"聚类算法: {', '.join(config.algorithms)}")

        # 2. 创建聚类引擎
        logger.info("初始化聚类引擎...")
        engine = ClusteringEngine(
            system_type=config.system_type,
            algorithm_names=config.algorithms,
            algorithm_params=config.algorithm_params,
            stage1_clustering_feature=config.stage1_clustering_feature,
            candidate_distributions=config.candidate_distributions,
            normality_alpha=config.normality_alpha,
            enable_context_calibration=config.enable_context_calibration,
            context_modeling_method=config.context_modeling_method,
            partition_context_features=config.partition_context_features,
            boundary_trim_points=config.boundary_trim_points,
        )

        # 3. 执行聚类
        logger.info("开始聚类分析...")
        result = engine.run_clustering(config.data_path)

        logger.info(f"聚类完成: 分析了{result.total_points}个数据点")

        # 4. 生成可视化
        plot_paths = {}
        if config.generate_visualizations:
            from .visualization.plotter import ClusteringPlotter

            logger.info("生成可视化图表...")
            plotter = ClusteringPlotter(result, config.output_dir)
            plot_paths = plotter.plot_all()
            logger.info(f"生成了{len(plot_paths)}个图表")

        # 5. 生成报告
        reporter = None
        if config.generate_report:
            logger.info("生成聚类分析报告...")
            reporter = ClusteringReporter(result, config.output_dir)
            report_path = reporter.generate_report(plot_paths)
            logger.info(f"报告已保存: {report_path}")

        # 6. 保存学习到的分布参数
        if config.save_learned_distributions:
            if reporter is None:
                reporter = ClusteringReporter(result, config.output_dir)

            logger.info("保存学习到的分布参数...")
            output_path = Path(config.learned_distributions_path) if config.learned_distributions_path else None
            learned_path = reporter.save_learned_distributions(
                output_path=output_path,
                clustering_config_path=config_path
            )
            if learned_path:
                logger.info(f"分布参数已保存: {learned_path}")

            if config.save_per_algorithm_distributions:
                logger.info("为每个算法分别保存分布参数...")
                if config.learned_distributions_path:
                    base_distribution_path = config.learned_distributions_path
                else:
                    base_distribution_path = str(Path(config.output_dir) / 'learned_distributions.yaml')

                for algo_name in result.algorithm_results.keys():
                    algo_output_path = build_algorithm_distribution_path(base_distribution_path, algo_name)
                    algo_learned_path = reporter.save_learned_distributions(
                        output_path=algo_output_path,
                        clustering_config_path=config_path,
                        algorithm_name=algo_name
                    )
                    if algo_learned_path:
                        logger.info(f"  - {algo_name}: {algo_learned_path}")

        # 7. 输出结果摘要
        print("\\n" + "="*60)
        print("聚类分析结果摘要")
        print("="*60)

        for algo_name, algo_result in result.algorithm_results.items():
            is_best = "⭐" if algo_name == result.best_algorithm else "  "
            sil_str = f"{algo_result.silhouette_score:.4f}" if algo_result.silhouette_score else "N/A"
            print(f"{is_best} {algo_name}: "
                  f"聚类数={algo_result.n_clusters}, "
                  f"轮廓系数={sil_str}, "
                  f"耗时={algo_result.execution_time:.3f}s")

        print("="*60)

        if result.best_algorithm:
            print(f"\\n✅ 最佳算法: {result.best_algorithm}")
            print(f"输出目录: {config.output_dir}")
        else:
            print("\\n⚠️ 未找到有效的聚类结果")

        return True

    except FileNotFoundError as e:
        logger.error(f"文件不存在: {e}")
        return False
    except ValueError as e:
        logger.error(f"配置错误: {e}")
        return False
    except Exception as e:
        logger.error(f"执行出错: {e}", exc_info=verbose)
        return False


def main():
    """CLI主入口函数"""
    parser = argparse.ArgumentParser(
        description='聚类分析框架 - 自动发现RUBIS/BSN数据分布参数',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 使用RUBIS配置进行聚类
  python cluster.py --config configs/rubis_clustering_config.yaml

  # 使用BSN配置进行聚类
  python cluster.py --config configs/bsn_clustering_config.yaml

  # 指定输出目录
  python cluster.py --config configs/rubis_clustering_config.yaml --output results

  # 输出详细日志
  python cluster.py --config configs/rubis_clustering_config.yaml --verbose
        """
    )

    parser.add_argument(
        '--config', '-c',
        required=True,
        help='配置文件路径（YAML格式）'
    )

    parser.add_argument(
        '--output', '-o',
        help='输出目录（覆盖配置文件中的设置）'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='输出详细日志'
    )

    args = parser.parse_args()

    # 执行聚类
    success = run_clustering(
        config_path=args.config,
        output_dir=args.output,
        verbose=args.verbose
    )

    # 设置退出码
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
