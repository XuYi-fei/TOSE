#!/usr/bin/env python3
"""
RQ2 kmeans 数值聚类 baseline 训练入口。
"""
import argparse
import logging
import sys

from rq2_kmeans_baseline.config import BaselineTrainingConfig
from rq2_kmeans_baseline.trainer import KMeansNumericBaselineTrainer


def setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def run_kmeans_baseline_clustering(config_path: str, output_dir: str | None = None, verbose: bool = False) -> bool:
    setup_logging(verbose)
    logger = logging.getLogger(__name__)
    try:
        config = BaselineTrainingConfig.from_yaml(config_path)
        if output_dir:
            config.output_dir = output_dir

        trainer = KMeansNumericBaselineTrainer(
            system_type=config.system_type,
            random_state=config.random_state,
            n_init=config.n_init,
        )
        saved_paths = trainer.fit_all(config.data_path, config.k_values, config.output_dir)
        logger.info("已生成 %s 个baseline模型", len(saved_paths))
        return True
    except Exception as exc:
        logger.error("RQ2 baseline 训练失败: %s", exc, exc_info=verbose)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="RQ2 kmeans 数值聚类 baseline 训练")
    parser.add_argument("--config", "-c", required=True, help="配置文件路径")
    parser.add_argument("--output", "-o", help="输出目录")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志")
    args = parser.parse_args()
    sys.exit(0 if run_kmeans_baseline_clustering(args.config, args.output, args.verbose) else 1)


if __name__ == "__main__":
    main()
