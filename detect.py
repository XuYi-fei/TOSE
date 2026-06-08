#!/usr/bin/env python3
"""
异常检测脚本入口

使用方法:
    python detect.py --config configs/rubis_detection_config.yaml
"""
import argparse
import logging
import sys
from pathlib import Path
import time

from anomaly_detection.config.config import DetectionConfig
from anomaly_detection.core.detector import AnomalyDetector, BOCPDDetector
from anomaly_detection.core.evaluator import AnomalyEvaluator
from anomaly_detection.visualization.reporter import DetectionReporter


def setup_logging(verbose: bool = False):
    """配置日志输出"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='[%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def run_detection(config_path: str, output_dir: str = None, verbose: bool = False) -> bool:
    """执行异常检测流程

    Args:
        config_path: 配置文件路径
        output_dir: 输出目录（覆盖配置文件中的设置）
        verbose: 是否输出详细日志

    Returns:
        检测是否成功
    """
    setup_logging(verbose)
    logger = logging.getLogger(__name__)

    try:
        start_time = time.time()

        # 1. 加载配置
        logger.info(f"加载配置文件: {config_path}")
        config = DetectionConfig.from_yaml(config_path)

        # 命令行参数覆盖
        if output_dir:
            config.output.dir = output_dir
            logger.info(f"输出目录已覆盖: {output_dir}")

        logger.info(f"系统类型: {config.system_type}")
        logger.info(f"测试数据路径: {config.test_data_path}")
        logger.info(f"分布参数文件: {config.learned_distributions}")
        logger.info(f"检测模式: {config.detection.mode}")
        logger.info(f"Sigma阈值: {config.detection.sigma_threshold}")
        logger.info(f"P值阈值: {config.detection.p_value_alpha}")
        logger.info(f"报警触发策略: {config.detection.alarm_count_policy}")
        logger.info(f"trace报警置信度: {config.detection.trace_alarm_confidence}")
        logger.info(f"点级聚合策略: {config.detection.aggregation_method}")
        logger.info(f"上下文匹配策略: {config.detection.context_matching_strategy}")
        logger.info(f"启用上下文均值校准: {config.detection.apply_context_mu_shift}")
        if config.detection.mode == "bocpd":
            logger.info(f"BOCPD hazard_lambda: {config.detection.bocpd.hazard_lambda}")
            logger.info(f"BOCPD max_run_length: {config.detection.bocpd.max_run_length}")
            logger.info(f"BOCPD state_prior: {config.detection.bocpd.state_prior}")
            logger.info(
                "BOCPD changepoint threshold: %s",
                config.detection.bocpd.changepoint_posterior_threshold,
            )
            logger.info(f"BOCPD raw anomaly rule: {config.detection.bocpd.raw_anomaly_rule}")

        # 2. 初始化检测器
        logger.info("初始化异常检测器...")
        if config.detection.mode == "bocpd":
            detector = BOCPDDetector.from_yaml(
                config.learned_distributions,
                sigma_threshold=config.detection.sigma_threshold,
                p_value_alpha=config.detection.p_value_alpha,
                hazard_lambda=config.detection.bocpd.hazard_lambda,
                max_run_length=config.detection.bocpd.max_run_length,
                state_prior=config.detection.bocpd.state_prior,
                changepoint_posterior_threshold=config.detection.bocpd.changepoint_posterior_threshold,
                raw_anomaly_rule=config.detection.bocpd.raw_anomaly_rule,
                tail_persistence_threshold=config.detection.bocpd.tail_persistence_threshold,
            )
        else:
            detector = AnomalyDetector.from_yaml(
                config.learned_distributions,
                sigma_threshold=config.detection.sigma_threshold,
                p_value_alpha=config.detection.p_value_alpha,
            )
        detector.context_matching_strategy = config.detection.context_matching_strategy
        detector.apply_context_mu_shift = config.detection.apply_context_mu_shift

        # 3. 初始化评估器
        logger.info("初始化评估器...")
        evaluator = AnomalyEvaluator(
            detector,
            config.system_type,
            alarm_count_policy=config.detection.alarm_count_policy,
            trace_alarm_confidence=config.detection.trace_alarm_confidence,
        )

        # 4. 扫描测试数据
        test_dir = Path(config.test_data_path)
        trace_files = sorted(test_dir.glob('*.txt'))

        if not trace_files:
            logger.error(f"在{config.test_data_path}中未找到trace文件")
            return False

        logger.info(f"找到{len(trace_files)}个trace文件")

        # 5. 逐个检测和评估
        logger.info("开始异常检测...")
        trace_metrics = []

        for i, trace_file in enumerate(trace_files):
            if (i + 1) % 10 == 0 or (i + 1) == len(trace_files):
                logger.info(f"处理进度: {i + 1}/{len(trace_files)}")

            try:
                metrics = evaluator.evaluate_trace(trace_file)
                trace_metrics.append(metrics)
            except Exception as e:
                logger.warning(f"处理文件{trace_file.name}失败: {e}")

        # 6. 聚合结果
        logger.info("聚合检测结果...")
        aggregated = evaluator.aggregate_results(trace_metrics)

        # 7. 生成报告（Markdown、JSON、CSV）
        logger.info("生成检测报告...")
        reporter = DetectionReporter(
            config.output.dir,
            file_suffix=config.output.file_suffix,
            cluster_count=len(detector.distributions),
            clustering_algorithm=detector.clustering_algorithm,
            alarm_count_policy=config.detection.alarm_count_policy,
            sigma_threshold=config.detection.sigma_threshold,
            point_anomaly_probability=detector.point_anomaly_probability,
            aggregation_method=config.detection.aggregation_method,
            trace_alarm_confidence=config.detection.trace_alarm_confidence,
            context_matching_strategy=config.detection.context_matching_strategy,
            apply_context_mu_shift=config.detection.apply_context_mu_shift,
            context_calibration_enabled=detector.context_calibration_model is not None,
            detection_mode=getattr(detector, "detection_mode", "pointwise"),
            bocpd_config=(
                {
                    "hazard_lambda": config.detection.bocpd.hazard_lambda,
                    "max_run_length": config.detection.bocpd.max_run_length,
                    "state_prior": config.detection.bocpd.state_prior,
                    "changepoint_posterior_threshold": config.detection.bocpd.changepoint_posterior_threshold,
                    "raw_anomaly_rule": config.detection.bocpd.raw_anomaly_rule,
                    "tail_persistence_threshold": config.detection.bocpd.tail_persistence_threshold,
                }
                if config.detection.mode == "bocpd"
                else None
            ),
        )
        report_path = reporter.generate_report(aggregated, config.system_type)

        # 生成标准化JSON格式结果
        json_path = reporter.generate_json_report(aggregated, config.system_type, config_path)

        # 生成CSV格式详细结果
        csv_path = reporter.generate_csv_report(aggregated, config.system_type)

        elapsed_time = time.time() - start_time

        # 8. 输出结果摘要（trace级别）
        print("\\n" + "="*60)
        print("异常检测结果摘要（trace级别）")
        print("="*60)
        print(f"总trace数: {aggregated.total_traces}")
        print(f"\\n混淆矩阵（trace计数）:")
        print(f"  TP={aggregated.tp_count}, FP={aggregated.fp_count}")
        print(f"  FN={aggregated.fn_count}, TN={aggregated.tn_count}")
        print(f"  总和验证: {aggregated.tp_count + aggregated.fp_count + aggregated.fn_count + aggregated.tn_count} = {aggregated.total_traces}")
        print(f"\\n性能指标:")
        print(f"  Precision: {aggregated.precision:.4f}")
        print(f"  Recall: {aggregated.recall:.4f}")
        print(f"  F1 Score: {aggregated.f1_score:.4f}")

        if aggregated.avg_delay_loops is not None:
            print(f"\\n检测延迟（loops）:")
            print(f"  平均: {aggregated.avg_delay_loops:.2f} loops")
            print(f"  最小: {aggregated.min_delay_loops} loops")
            print(f"  最大: {aggregated.max_delay_loops} loops")
        print(f"处理时间: {elapsed_time:.2f}秒")
        print("="*60)
        print(f"\\n✅ 报告已生成:")
        print(f"  - Markdown: {report_path}")
        print(f"  - JSON: {json_path}")
        print(f"  - CSV: {csv_path}")
        print(f"\\n输出目录: {config.output.dir}")

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
        description='异常检测框架 - 使用3-sigma规则检测RUBIS/BSN异常数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 使用RUBIS配置进行异常检测
  python detect.py --config configs/rubis_detection_config.yaml

  # 使用BSN配置进行异常检测
  python detect.py --config configs/bsn_detection_config.yaml

  # 指定输出目录
  python detect.py --config configs/rubis_detection_config.yaml --output results

  # 输出详细日志
  python detect.py --config configs/rubis_detection_config.yaml --verbose
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

    # 执行检测
    success = run_detection(
        config_path=args.config,
        output_dir=args.output,
        verbose=args.verbose
    )

    # 设置退出码
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
