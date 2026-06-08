"""
聚类分析配置模块

负责加载、验证和提供YAML配置
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import yaml


@dataclass
class ClusteringConfig:
    """聚类分析配置类"""

    system_type: str                          # 系统类型: 'rubis' 或 'bsn'
    data_path: str                            # 数据集路径
    algorithms: List[str]                     # 要使用的聚类算法列表
    algorithm_params: Dict[str, dict] = field(default_factory=dict)  # 算法参数
    output_dir: str = ''                      # 输出目录
    generate_visualizations: bool = True      # 是否生成可视化
    generate_report: bool = True              # 是否生成报告
    save_learned_distributions: bool = True   # 是否保存学习到的分布参数
    save_per_algorithm_distributions: bool = False  # 是否为每个算法分别保存分布参数
    learned_distributions_path: Optional[str] = None  # 分布参数保存路径
    stage1_clustering_feature: str = 'mu'  # stage-1 聚类使用的特征
    candidate_distributions: List[str] = field(default_factory=lambda: ['norm', 'lognorm', 'gamma', 'weibull_min'])
    normality_alpha: float = 0.05  # stage-2 正态性检验阈值
    enable_context_calibration: bool = True  # 是否拟合上下文到均值的线性校准模型
    context_modeling_method: str = 'linear_mu'  # 上下文校准模型类型
    boundary_trim_points: int = 0  # identity 中切换边界前后各剔除的点数

    @classmethod
    def from_yaml(cls, config_path: str) -> 'ClusteringConfig':
        """从YAML文件加载配置

        Args:
            config_path: 配置文件路径

        Returns:
            ClusteringConfig对象

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
        data_path = raw_config.get('data_path', '')
        algorithms = raw_config.get('algorithms', [])

        # 获取算法参数
        algorithm_params = raw_config.get('algorithm_params', {})

        # 获取输出配置
        output_config = raw_config.get('output', {})
        output_dir = output_config.get('dir', f'clustering_results/{system_type}')
        generate_visualizations = output_config.get('visualizations', True)
        generate_report = output_config.get('report', True)
        save_learned_distributions = output_config.get('save_learned_distributions', True)
        save_per_algorithm_distributions = output_config.get('save_per_algorithm_distributions', False)
        learned_distributions_path = output_config.get('learned_distributions_path', None)

        # 获取两阶段分布建模配置
        distribution_modeling = raw_config.get('distribution_modeling', {})
        stage1_clustering_feature = distribution_modeling.get('stage1_clustering_feature', 'mu')
        candidate_distributions = distribution_modeling.get(
            'candidate_distributions',
            ['norm', 'lognorm', 'gamma', 'weibull_min']
        )
        normality_alpha = float(distribution_modeling.get('normality_alpha', 0.05))
        enable_context_calibration = bool(distribution_modeling.get('enable_context_calibration', True))
        context_modeling_method = distribution_modeling.get('context_modeling_method', 'linear_mu')
        boundary_trim_points = int(distribution_modeling.get('boundary_trim_points', 0))

        # 构建配置对象
        config = cls(
            system_type=system_type,
            data_path=data_path,
            algorithms=algorithms,
            algorithm_params=algorithm_params,
            output_dir=output_dir,
            generate_visualizations=generate_visualizations,
            generate_report=generate_report,
            save_learned_distributions=save_learned_distributions,
            save_per_algorithm_distributions=save_per_algorithm_distributions,
            learned_distributions_path=learned_distributions_path,
            stage1_clustering_feature=stage1_clustering_feature,
            candidate_distributions=candidate_distributions,
            normality_alpha=normality_alpha,
            enable_context_calibration=enable_context_calibration,
            context_modeling_method=context_modeling_method,
            boundary_trim_points=boundary_trim_points,
        )

        # 验证配置
        config.validate()

        return config

    def validate(self) -> None:
        """验证配置完整性

        Raises:
            ValueError: 配置无效
        """
        # 验证必填字段
        if not self.system_type:
            raise ValueError("缺少必填字段: system_type")

        if not self.data_path:
            raise ValueError("缺少必填字段: data_path")

        if not self.algorithms:
            raise ValueError("缺少必填字段: algorithms（至少需要一个算法）")

        # 验证system_type有效性
        valid_types = ['rubis', 'bsn', 'swat', 'wadi']
        if self.system_type not in valid_types:
            raise ValueError(f"不支持的系统类型: {self.system_type}，支持的类型: {valid_types}")

        # 验证数据路径存在性
        data_dir = Path(self.data_path)
        if not data_dir.exists():
            raise ValueError(f"数据路径不存在: {self.data_path}")

        # 验证算法列表
        if not isinstance(self.algorithms, list):
            raise ValueError("algorithms必须是列表类型")

        # 验证算法参数
        if not isinstance(self.algorithm_params, dict):
            raise ValueError("algorithm_params必须是字典类型")

        if self.stage1_clustering_feature != 'mu':
            raise ValueError("当前仅支持 stage1_clustering_feature=mu")

        if not self.candidate_distributions:
            raise ValueError("candidate_distributions不能为空")

        valid_distributions = {'norm', 'lognorm', 'gamma', 'weibull_min'}
        invalid_distributions = [name for name in self.candidate_distributions if name not in valid_distributions]
        if invalid_distributions:
            raise ValueError(
                f"不支持的候选分布: {invalid_distributions}，支持的类型: {sorted(valid_distributions)}"
            )

        if not 0 < self.normality_alpha < 1:
            raise ValueError("normality_alpha必须位于(0, 1)区间内")

        if self.boundary_trim_points < 0:
            raise ValueError("boundary_trim_points必须大于等于0")

        valid_context_methods = {'linear_mu'}
        if self.context_modeling_method not in valid_context_methods:
            raise ValueError(
                f"不支持的context_modeling_method: {self.context_modeling_method}，"
                f"支持的类型: {sorted(valid_context_methods)}"
            )

    def to_dict(self) -> dict:
        """转换为字典

        Returns:
            配置字典
        """
        return {
            'system_type': self.system_type,
            'data_path': self.data_path,
            'algorithms': self.algorithms,
            'algorithm_params': self.algorithm_params,
            'output': {
                'dir': self.output_dir,
                'visualizations': self.generate_visualizations,
                'report': self.generate_report,
                'save_learned_distributions': self.save_learned_distributions,
                'save_per_algorithm_distributions': self.save_per_algorithm_distributions,
                'learned_distributions_path': self.learned_distributions_path
            },
            'distribution_modeling': {
                'stage1_clustering_feature': self.stage1_clustering_feature,
                'candidate_distributions': self.candidate_distributions,
                'normality_alpha': self.normality_alpha,
                'enable_context_calibration': self.enable_context_calibration,
                'context_modeling_method': self.context_modeling_method,
                'boundary_trim_points': self.boundary_trim_points,
            }
        }
