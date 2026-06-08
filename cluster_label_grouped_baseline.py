#!/usr/bin/env python3
"""按 trace 文件名标签归组的 baseline 训练入口。"""
import argparse
import logging
import sys

from label_grouped_baseline.config import LabelGroupedBaselineTrainingConfig
from label_grouped_baseline.trainer import LabelGroupedBaselineTrainer


def setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def run_label_grouped_baseline_clustering(
    config_path: str,
    output_dir: str | None = None,
    verbose: bool = False,
) -> bool:
    setup_logging(verbose)
    logger = logging.getLogger(__name__)
    try:
        config = LabelGroupedBaselineTrainingConfig.from_yaml(config_path)
        if output_dir:
            config.output_dir = output_dir

        trainer = LabelGroupedBaselineTrainer(
            system_type=config.system_type,
            candidate_distributions=config.candidate_distributions,
            normality_alpha=config.normality_alpha,
        )

        trainer.fit_and_save(
            data_path=config.data_path,
            output_path=config.learned_distributions_path,
            config_path=config_path,
        )
        logger.info("label-grouped baseline 训练完成: %s", config.learned_distributions_path)
        return True
    except Exception as exc:
        logger.error("label-grouped baseline 训练失败: %s", exc, exc_info=verbose)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="按标签归组的 baseline 训练")
    parser.add_argument("--config", "-c", required=True, help="配置文件路径")
    parser.add_argument("--output", "-o", help="输出目录")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志")
    args = parser.parse_args()
    sys.exit(0 if run_label_grouped_baseline_clustering(args.config, args.output, args.verbose) else 1)


if __name__ == "__main__":
    main()
