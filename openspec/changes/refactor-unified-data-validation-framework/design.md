# 架构设计文档

## 设计概述

本文档描述通用数据验证框架的架构设计，包括核心组件、交互流程、扩展机制和关键技术决策。

## 架构原则

1. **分层架构**: 清晰的层次划分，降低耦合
2. **策略模式**: 使用适配器处理不同数据源
3. **配置驱动**: 行为由配置决定，无需修改代码
4. **开放扩展**: 预留插件接口，支持功能扩展
5. **简约设计**: 避免过度设计，保持实现简单

## 系统架构

### 层次结构

```
┌─────────────────────────────────────────────────────────┐
│                    用户交互层                            │
│  ┌──────────────────────────────────────────────────┐   │
│  │  validate.py (CLI入口)                           │   │
│  │  - 参数解析                                       │   │
│  │  - 进度显示                                       │   │
│  │  - 错误处理                                       │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    配置层                                │
│  ┌──────────────────────────────────────────────────┐   │
│  │  core/config.py                                  │   │
│  │  - YAML加载                                       │   │
│  │  - Schema验证                                     │   │
│  │  - 默认值处理                                     │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    业务逻辑层                            │
│  ┌────────────────┐  ┌────────────────┐  ┌───────────┐ │
│  │ core/validator │  │ core/reporter  │  │ core/     │ │
│  │  - 验证引擎     │  │  - 报告生成    │  │  parser   │ │
│  │  - 统计分析     │  │  - 模式控制    │  │  (抽象)   │ │
│  └────────────────┘  └────────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    适配器层                              │
│  ┌──────────────────┐        ┌──────────────────┐      │
│  │ adapters/rubis   │        │ adapters/bsn     │      │
│  │  - 文件名解析     │        │  - 文件名解析     │      │
│  │  - CSV读取       │        │  - 多维数据处理   │      │
│  │  - 单列提取       │        │  - 列选择         │      │
│  └──────────────────┘        └──────────────────┘      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    工具层                                │
│  ┌─────────────────┐         ┌─────────────────┐       │
│  │ utils/statistics│         │ utils/          │       │
│  │  - 统计计算      │         │  visualization  │       │
│  │  - 偏离分析      │         │  - 图表生成      │       │
│  └─────────────────┘         └─────────────────┘       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    数据模型层                            │
│  ┌─────────────────┐         ┌─────────────────┐       │
│  │ models/metadata │         │ models/         │       │
│  │  - 文件元数据    │         │  distribution   │       │
│  └─────────────────┘         └─────────────────┘       │
└─────────────────────────────────────────────────────────┘
```

## 核心组件设计

### 1. 配置管理 (core/config.py)

**职责**: 加载、验证和提供配置

**接口**:
```python
class ValidationConfig:
    """验证配置"""
    system_type: str              # 'rubis' 或 'bsn'
    data_path: str                # 数据集路径
    expected_distributions: Dict  # 期望分布参数
    output_dir: str               # 输出目录
    report_mode: str              # 'simple' 或 'detailed'
    deviation_threshold: float    # 偏离阈值（默认10%）

    @classmethod
    def from_yaml(cls, path: str) -> 'ValidationConfig':
        """从YAML文件加载配置"""

    def validate(self) -> None:
        """验证配置完整性"""
```

**配置文件格式**:
```yaml
# configs/rubis_config.yaml
system_type: rubis
data_path: rubis_evaluation_data/eval_ident_traces
output_dir: validation_results/rubis
report_mode: detailed  # simple | detailed

expected_distributions:
  norm1:
    mu: 0.0526
    sigma: 0.0024
  norm2:
    mu: 0.1154
    sigma: 0.0127
  norm3:
    mu: 0.0285
    sigma: 0.0018

validation:
  deviation_threshold: 10.0  # 百分比
  min_samples: 10            # 最小样本数
```

### 2. 解析器抽象 (core/parser.py)

**职责**: 定义数据解析接口

**接口**:
```python
class TraceParser(ABC):
    """Trace文件解析器抽象基类"""

    @abstractmethod
    def parse_filename(self, filename: str) -> Optional[TraceMetadata]:
        """解析文件名提取元数据"""

    @abstractmethod
    def parse_trace_file(self, filepath: Path) -> Dict[str, pd.DataFrame]:
        """解析trace文件内容，按norm标签分段"""

    @abstractmethod
    def extract_parameters(
        self,
        segments: Dict[str, pd.DataFrame],
        metadata: TraceMetadata
    ) -> List[DistributionParameters]:
        """从分段数据中提取分布参数"""
```

### 3. 验证引擎 (core/validator.py)

**职责**: 执行数据验证逻辑

**核心流程**:
```python
class DataValidator:
    """数据验证引擎"""

    def __init__(self, config: ValidationConfig, parser: TraceParser):
        self.config = config
        self.parser = parser

    def validate_dataset(self) -> ValidationResult:
        """验证整个数据集"""
        # 1. 扫描所有trace文件
        # 2. 解析并提取参数
        # 3. 按norm标签分组
        # 4. 计算统计信息
        # 5. 判定正常/异常
        # 6. 返回验证结果

    def validate_distribution(
        self,
        norm_label: str,
        parameters: List[DistributionParameters]
    ) -> DistributionValidation:
        """验证单个分布"""
        # 1. 计算总体均值和标准差
        # 2. 计算偏离百分比
        # 3. 检查范围约束
        # 4. 按位置分组分析
        # 5. 识别异常样本
```

**验证算法**:
```python
def calculate_deviation(actual: float, expected: float) -> float:
    """计算偏离百分比"""
    return abs(actual - expected) / expected * 100

def is_normal(
    deviation: float,
    threshold: float,
    in_range: bool
) -> bool:
    """判定是否正常"""
    return deviation < threshold and in_range
```

### 4. 报告生成器 (core/reporter.py)

**职责**: 生成验证报告

**模式设计**:
```python
class ReportGenerator:
    """报告生成器"""

    def generate(
        self,
        result: ValidationResult,
        mode: str
    ) -> None:
        """生成报告"""
        if mode == 'simple':
            self._generate_simple_report(result)
        else:
            self._generate_detailed_report(result)

    def _generate_simple_report(self, result: ValidationResult):
        """生成简单报告
        - 验证结果表格
        - 统计摘要
        - 结论
        """

    def _generate_detailed_report(self, result: ValidationResult):
        """生成详细报告
        - 简单报告内容
        - 按位置分析
        - 异常样本列表
        - 多种图表
        """
```

### 5. 适配器实现

#### RUBIS适配器 (adapters/rubis.py)

```python
class RUBISParser(TraceParser):
    """RUBIS数据适配器"""

    FILENAME_PATTERN = re.compile(
        r'eval_ident_trace-cnt-(?P<cnt>\d+)'
        r'-duration-(?P<duration>\d+)'
        r'-config_num-(?P<config_num>\d+)'
        r'-trace_config-(?P<trace_config>[^-]+)'
        r'-start_time-(?P<start_time>[^.]+)'
    )

    TARGET_COLUMN = 'measuredAvgRespTime_{k}'

    def parse_filename(self, filename: str) -> Optional[RUBISMetadata]:
        """解析RUBIS文件名"""

    def parse_trace_file(self, filepath: Path) -> Dict[str, pd.DataFrame]:
        """解析RUBIS trace文件"""
        # 读取CSV
        # 按start_time分段
        # 返回{norm_label: DataFrame}

    def extract_parameters(self, segments, metadata) -> List[...]:
        """从单列数据提取参数"""
        # 提取measuredAvgRespTime列
        # 计算均值、方差、范围
```

#### BSN适配器 (adapters/bsn.py)

```python
class BSNParser(TraceParser):
    """BSN数据适配器"""

    FILENAME_PATTERN = re.compile(
        r'eval_ident_trace-cnt-(?P<cnt>\d+)'
        r'-duration-(?P<duration>\d+)'
        r'-sensor_index-(?P<sensor_index>\d+)'  # BSN特有
        r'-config_num-(?P<config_num>\d+)'
        r'-trace_config-(?P<trace_config>[^-]+)'
        r'-start_time-(?P<start_time>[^.]+)'
    )

    def get_target_column(self, sensor_index: int) -> str:
        """根据sensor_index确定目标列"""
        return f'gt_3_{sensor_index + 1}'

    def parse_trace_file(self, filepath: Path) -> Dict[str, pd.DataFrame]:
        """解析BSN trace文件（多维数据）"""
        # 读取CSV
        # 根据sensor_index选择列
        # 按start_time分段
```

### 6. 适配器工厂 (adapters/__init__.py)

```python
class ParserFactory:
    """解析器工厂"""

    _registry = {
        'rubis': RUBISParser,
        'bsn': BSNParser
    }

    @classmethod
    def create(cls, system_type: str) -> TraceParser:
        """根据系统类型创建解析器"""
        parser_class = cls._registry.get(system_type)
        if not parser_class:
            raise ValueError(f"未知系统类型: {system_type}")
        return parser_class()

    @classmethod
    def register(cls, system_type: str, parser_class: Type[TraceParser]):
        """注册新的解析器（用于扩展）"""
        cls._registry[system_type] = parser_class
```

## 数据流

### 完整验证流程

```
1. 用户启动
   └─> python validate.py --config configs/rubis_config.yaml

2. CLI解析参数
   └─> 加载配置文件

3. 配置模块验证
   └─> 检查必填项、路径存在性

4. 创建适配器
   └─> ParserFactory.create('rubis') -> RUBISParser

5. 创建验证引擎
   └─> DataValidator(config, parser)

6. 扫描文件
   └─> 遍历data_path下的所有.txt文件

7. 逐文件处理
   ├─> 解析文件名 (RUBISParser.parse_filename)
   ├─> 解析文件内容 (RUBISParser.parse_trace_file)
   ├─> 提取参数 (RUBISParser.extract_parameters)
   └─> 累积到结果集

8. 按norm标签分组
   └─> {norm1: [...], norm2: [...], norm3: [...]}

9. 验证各分布
   ├─> 计算总体统计
   ├─> 计算偏离百分比
   ├─> 检查范围约束
   ├─> 按位置分组分析
   └─> 识别异常样本

10. 生成报告
    ├─> 创建输出目录
    ├─> 生成Markdown报告
    └─> 生成图表（如果是detailed模式）

11. 输出结果
    └─> 打印摘要到控制台
    └─> 显示报告路径
```

## 扩展机制

### 1. 添加新数据集适配器

```python
# 步骤1: 创建新适配器类
class MySystemParser(TraceParser):
    """自定义系统适配器"""

    FILENAME_PATTERN = re.compile(r'...')  # 定义正则

    def parse_filename(self, filename):
        # 实现文件名解析

    def parse_trace_file(self, filepath):
        # 实现文件读取和分段

    def extract_parameters(self, segments, metadata):
        # 实现参数提取

# 步骤2: 注册适配器
ParserFactory.register('mysystem', MySystemParser)

# 步骤3: 创建配置文件
# configs/mysystem_config.yaml
system_type: mysystem
data_path: ...
expected_distributions: ...
```

### 2. 集成评估模块

```python
# 预留扩展接口
class ValidationResult:
    """验证结果"""
    ...

    def to_evaluation_input(self) -> EvaluationData:
        """转换为评估模块的输入格式"""
        # 预留方法，供评估模块使用

# 使用方式
result = validator.validate_dataset()
evaluation_score = evaluator.evaluate(result.to_evaluation_input())
```

### 3. 集成辨识模块

```python
# 扩展目录结构
data_validation/
├── extensions/
│   ├── __init__.py
│   ├── evaluation.py    # 评估模块
│   └── identification.py  # 辨识模块

# 插件接口
class Extension(ABC):
    """扩展插件基类"""

    @abstractmethod
    def process(self, result: ValidationResult) -> Any:
        """处理验证结果"""
```

## 关键技术决策

### 决策1: 配置格式选择YAML

**理由**:
- 人类可读性好，易于编辑
- 支持注释，便于说明
- Python生态成熟（PyYAML）
- 无需JSON的严格语法

**替代方案**: JSON、TOML
**决策**: 使用YAML

### 决策2: 使用抽象基类而非协议

**理由**:
- 明确接口契约
- 提供更好的IDE支持
- 便于文档说明
- Python 3.8+原生支持

**替代方案**: typing.Protocol、鸭子类型
**决策**: 使用ABC

### 决策3: CLI使用argparse而非click

**理由**:
- 无额外依赖，标准库自带
- 满足当前需求
- 降低项目复杂度

**替代方案**: click、typer
**决策**: 使用argparse（可选升级到click）

### 决策4: 报告格式为Markdown

**理由**:
- 人类可读
- Git友好，易于版本控制
- 可转换为HTML/PDF
- 支持表格和代码块

**替代方案**: HTML、PDF、JSON
**决策**: 使用Markdown

### 决策5: 适配器注册采用字典而非装饰器

**理由**:
- 实现简单
- 易于理解和维护
- 满足当前需求

**替代方案**: 装饰器注册、插件系统
**决策**: 字典注册（可选升级）

## 性能考虑

### 瓶颈分析

1. **文件I/O**: 读取200个CSV文件
   - 优化: 使用pandas高效读取
   - 预期: 3-5秒

2. **数据解析**: 正则表达式匹配
   - 优化: 预编译正则
   - 预期: <1秒

3. **统计计算**: numpy数组运算
   - 优化: 向量化操作
   - 预期: <1秒

4. **图表生成**: matplotlib绘图
   - 优化: 仅在detailed模式生成
   - 预期: 2-3秒

**总预期时间**: < 10秒（200文件）

### 内存考虑

- 每个trace文件约500行，200个文件共100K行
- pandas DataFrame内存占用约10-20MB
- 峰值内存预期 < 100MB
- 无需特殊优化

## 测试策略

### 单元测试

- 配置加载和验证
- 文件名解析（RUBIS、BSN）
- 统计计算准确性
- 偏离判定逻辑

### 集成测试

- 端到端验证流程
- RUBIS数据集验证
- BSN数据集验证
- 报告生成完整性

### 回归测试

- 输出与旧脚本对比
- 统计结果精度验证
- 性能基准测试

## 未来扩展方向

1. **Web界面**: Flask/FastAPI + Vue.js
2. **数据库存储**: SQLite存储历史验证结果
3. **持续监控**: 定时任务 + 异常告警
4. **分布式处理**: 并行处理大规模数据集
5. **机器学习集成**: 自动学习期望参数
6. **多数据集对比**: 同时验证多个数据集并对比

---

**设计版本**: v1.0
**创建时间**: 2026-01-14
**最后更新**: 2026-01-14
