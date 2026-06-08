"""
异常检测配置类

负责加载、验证检测配置
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional
import yaml


@dataclass
class BOCPDParameters:
    """BOCPD 检测参数。"""

    hazard_lambda: float = 50.0
    max_run_length: int = 200
    state_prior: str = "sample_count"
    changepoint_posterior_threshold: float = 0.5
    raw_anomaly_rule: str = "cp_and_tail"
    tail_persistence_threshold: int = 2


@dataclass
class DetectionParameters:
    """检测参数配置"""
    mode: str = "pointwise"                      # 检测模式：pointwise | bocpd
    sigma_threshold: float = 3.0                  # 兼容保留的sigma阈值
    p_value_alpha: Optional[float] = None         # 假设检验的边缘概率阈值
    min_samples_for_detection: int = 1            # 最小检测样本数
    alarm_count_policy: str = "binomial_confidence_bound"  # trace级报警触发策略
    trace_alarm_confidence: float = 0.99          # trace级报警的一侧置信度
    aggregation_method: str = "max_p_value"       # 点级分布聚合策略
    context_matching_strategy: str = "nearest"    # 上下文匹配策略
    apply_context_mu_shift: bool = True           # 是否启用上下文驱动的位置参数校准
    bocpd: BOCPDParameters = field(default_factory=BOCPDParameters)


@dataclass
class OutputConfig:
    """输出配置"""
    dir: str = 'detection_results'                # 输出目录
    generate_visualizations: bool = True          # 是否生成可视化
    save_anomaly_points: bool = True              # 是否保存异常点详细信息
    file_suffix: str = ''                         # 输出文件名后缀


@dataclass
class DetectionConfig:
    """异常检测配置类"""

    system_type: str                               # 系统类型（rubis/bsn）
    learned_distributions: str                     # 学习到的分布参数文件路径
    test_data_path: str                            # 测试数据路径（包含abn的trace）
    detection: DetectionParameters = field(default_factory=DetectionParameters)
    output: OutputConfig = field(default_factory=OutputConfig)

    @classmethod
    def from_yaml(cls, config_path: str) -> 'DetectionConfig':
        """从YAML文件加载配置

        Args:
            config_path: 配置文件路径

        Returns:
            DetectionConfig对象

        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置格式错误
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_file, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f)

        # 获取基本配置
        system_type = raw_config.get('system_type', '')
        learned_distributions = raw_config.get('learned_distributions', '')
        test_data_path = raw_config.get('test_data_path', '')

        # 获取检测参数
        detection_config = raw_config.get('detection', {})
        bocpd_config = detection_config.get('bocpd', {})
        detection = DetectionParameters(
            mode=detection_config.get('mode', 'pointwise'),
            sigma_threshold=detection_config.get('sigma_threshold', 3.0),
            p_value_alpha=detection_config.get('p_value_alpha'),
            min_samples_for_detection=detection_config.get('min_samples_for_detection', 1),
            alarm_count_policy=detection_config.get('alarm_count_policy', 'binomial_confidence_bound'),
            trace_alarm_confidence=float(detection_config.get('trace_alarm_confidence', 0.99)),
            aggregation_method=detection_config.get('aggregation_method', 'max_p_value'),
            context_matching_strategy=detection_config.get('context_matching_strategy', 'nearest'),
            apply_context_mu_shift=bool(detection_config.get('apply_context_mu_shift', True)),
            bocpd=BOCPDParameters(
                hazard_lambda=float(bocpd_config.get('hazard_lambda', 50.0)),
                max_run_length=int(bocpd_config.get('max_run_length', 200)),
                state_prior=bocpd_config.get('state_prior', 'sample_count'),
                changepoint_posterior_threshold=float(
                    bocpd_config.get('changepoint_posterior_threshold', 0.5)
                ),
                raw_anomaly_rule=bocpd_config.get('raw_anomaly_rule', 'cp_and_tail'),
                tail_persistence_threshold=int(bocpd_config.get('tail_persistence_threshold', 2)),
            ),
        )

        # 获取输出配置
        output_config = raw_config.get('output', {})
        output = OutputConfig(
            dir=output_config.get('dir', f'detection_results/{system_type}'),
            generate_visualizations=output_config.get('generate_visualizations', True),
            save_anomaly_points=output_config.get('save_anomaly_points', True),
            file_suffix=output_config.get('file_suffix', '')
        )

        # 构建配置对象
        config = cls(
            system_type=system_type,
            learned_distributions=learned_distributions,
            test_data_path=test_data_path,
            detection=detection,
            output=output
        )

        # 验证配置
        config.validate()

        return config

    def validate(self) -> None:
        """验证配置完整性

        Raises:
            ValueError: 配置无效
            FileNotFoundError: 文件或目录不存在
        """
        # 验证必填字段
        if not self.system_type:
            raise ValueError("缺少必填字段: system_type")

        if not self.learned_distributions:
            raise ValueError("缺少必填字段: learned_distributions")

        if not self.test_data_path:
            raise ValueError("缺少必填字段: test_data_path")

        # 验证system_type有效性
        valid_types = ['rubis', 'bsn', 'swat', 'wadi']
        if self.system_type not in valid_types:
            raise ValueError(
                f"不支持的系统类型: {self.system_type}\\n"
                f"支持的类型: {', '.join(valid_types)}"
            )

        # 验证learned_distributions文件存在性
        dist_file = Path(self.learned_distributions)
        if not dist_file.exists():
            raise FileNotFoundError(
                f"分布参数文件不存在: {self.learned_distributions}\\n"
                f"请先运行聚类分析生成learned_distributions.yaml文件"
            )

        # 验证test_data_path目录存在性
        test_dir = Path(self.test_data_path)
        if not test_dir.exists():
            raise ValueError(f"测试数据路径不存在: {self.test_data_path}")

        if not test_dir.is_dir():
            raise ValueError(f"测试数据路径不是目录: {self.test_data_path}")

        # 检查目录中是否有trace文件
        trace_files = list(test_dir.glob('*.txt'))
        if not trace_files:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"警告: 测试数据目录{self.test_data_path}中未找到trace文件")

        # 验证检测参数
        if self.detection.sigma_threshold < 0.5:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"警告: sigma_threshold={self.detection.sigma_threshold} 过低(<0.5)，"
                f"可能导致大量误报"
            )

        if self.detection.p_value_alpha is not None and not 0 < self.detection.p_value_alpha < 1:
            raise ValueError("p_value_alpha必须位于(0, 1)区间内")

        if not 0 < self.detection.trace_alarm_confidence < 1:
            raise ValueError("trace_alarm_confidence必须位于(0, 1)区间内")

        valid_modes = ['pointwise', 'bocpd']
        if self.detection.mode not in valid_modes:
            raise ValueError(
                f"不支持的detection.mode: {self.detection.mode}\n"
                f"支持的模式: {', '.join(valid_modes)}"
            )

        valid_alarm_policies = [
            'theoretical_3sigma_count',
            'theoretical_point_probability_count',
            'binomial_confidence_bound',
        ]
        if self.detection.alarm_count_policy not in valid_alarm_policies:
            raise ValueError(
                f"不支持的alarm_count_policy: {self.detection.alarm_count_policy}\n"
                f"支持的策略: {', '.join(valid_alarm_policies)}"
            )

        valid_aggregation_methods = ['max_p_value']
        if self.detection.aggregation_method not in valid_aggregation_methods:
            raise ValueError(
                f"不支持的aggregation_method: {self.detection.aggregation_method}\n"
                f"支持的策略: {', '.join(valid_aggregation_methods)}"
            )

        valid_context_matching_strategies = ['nearest', 'global']
        if self.detection.context_matching_strategy not in valid_context_matching_strategies:
            raise ValueError(
                f"不支持的context_matching_strategy: {self.detection.context_matching_strategy}\n"
                f"支持的策略: {', '.join(valid_context_matching_strategies)}"
            )

        valid_state_priors = ['uniform', 'sample_count']
        if self.detection.bocpd.state_prior not in valid_state_priors:
            raise ValueError(
                f"不支持的bocpd.state_prior: {self.detection.bocpd.state_prior}\n"
                f"支持的策略: {', '.join(valid_state_priors)}"
            )

        valid_raw_rules = ['cp_and_tail', 'cp_only', 'tail_only']
        if self.detection.bocpd.raw_anomaly_rule not in valid_raw_rules:
            raise ValueError(
                f"不支持的bocpd.raw_anomaly_rule: {self.detection.bocpd.raw_anomaly_rule}\n"
                f"支持的策略: {', '.join(valid_raw_rules)}"
            )

        if self.detection.bocpd.hazard_lambda <= 1.0:
            raise ValueError("bocpd.hazard_lambda必须大于1.0")

        if self.detection.bocpd.max_run_length < 1:
            raise ValueError("bocpd.max_run_length必须大于等于1")

        if not 0 < self.detection.bocpd.changepoint_posterior_threshold <= 1:
            raise ValueError("bocpd.changepoint_posterior_threshold必须位于(0, 1]区间内")

        if self.detection.bocpd.tail_persistence_threshold < 1:
            raise ValueError("bocpd.tail_persistence_threshold必须大于等于1")

    def to_dict(self) -> dict:
        """转换为字典

        Returns:
            配置字典
        """
        return {
            'system_type': self.system_type,
            'learned_distributions': self.learned_distributions,
            'test_data_path': self.test_data_path,
            'detection': {
                'mode': self.detection.mode,
                'sigma_threshold': self.detection.sigma_threshold,
                'p_value_alpha': self.detection.p_value_alpha,
                'min_samples_for_detection': self.detection.min_samples_for_detection,
                'alarm_count_policy': self.detection.alarm_count_policy,
                'trace_alarm_confidence': self.detection.trace_alarm_confidence,
                'aggregation_method': self.detection.aggregation_method,
                'context_matching_strategy': self.detection.context_matching_strategy,
                'apply_context_mu_shift': self.detection.apply_context_mu_shift,
                'bocpd': {
                    'hazard_lambda': self.detection.bocpd.hazard_lambda,
                    'max_run_length': self.detection.bocpd.max_run_length,
                    'state_prior': self.detection.bocpd.state_prior,
                    'changepoint_posterior_threshold': self.detection.bocpd.changepoint_posterior_threshold,
                    'raw_anomaly_rule': self.detection.bocpd.raw_anomaly_rule,
                    'tail_persistence_threshold': self.detection.bocpd.tail_persistence_threshold,
                },
            },
            'output': {
                'dir': self.output.dir,
                'generate_visualizations': self.output.generate_visualizations,
                'save_anomaly_points': self.output.save_anomaly_points,
                'file_suffix': self.output.file_suffix
            }
        }
