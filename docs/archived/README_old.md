# 自适应系统数据分析框架

一个通用的、配置驱动的数据分析系统，支持聚类分析和异常检测。支持多种自适应系统：RUBIS、BSN和SWAT。

## 🚀 快速开始

### 环境要求

**Python版本**：Python 3.8或更高

**依赖安装**：
```bash
pip install -r requirements.txt
```

### 聚类分析（自动发现分布参数）

```bash
# RUBIS系统
python cluster.py --config configs/rubis_clustering_config.yaml

# BSN系统
python cluster.py --config configs/bsn_clustering_config.yaml

# SWAT系统
python cluster.py --config configs/swat_clustering_config.yaml
```

### 异常检测（基于学习到的分布）

```bash
# RUBIS系统
python detect.py --config configs/rubis_detection_config.yaml

# BSN系统
python detect.py --config configs/bsn_detection_config.yaml

# SWAT系统
python detect.py --config configs/swat_detection_config.yaml
```

### 数据验证（验证identity数据分布）

```bash
# RUBIS系统
python validate.py --config configs/rubis_config.yaml

# BSN系统
python validate.py --config configs/bsn_config.yaml
```

## ✨ 核心特性

- ⚙️ **配置驱动**：通过YAML配置文件轻松切换数据集和参数
- 🔌 **多系统支持**：原生支持RUBIS、BSN和SWAT，可扩展到其他系统
- 📊 **三大功能**：
  - **聚类分析**：自动发现数据分布参数（4种聚类算法）
  - **异常检测**：基于3-sigma原则的统计异常检测
  - **数据验证**：验证identity数据是否符合期望分布
- 🎯 **一键执行**：无需修改代码，直接运行分析
- 📈 **丰富可视化**：自动生成散点图、密度曲线、算法对比等可视化
- 🔧 **易于扩展**：清晰的适配器接口和算法注册机制

## 📖 使用说明

### 命令行选项

```bash
python validate.py [选项]

必需选项:
  --config, -c CONFIG    配置文件路径（YAML格式）

可选选项:
  --output, -o DIR       输出目录（覆盖配置文件设置）
  --mode, -m MODE        报告模式: simple 或 detailed
  --verbose, -v          显示详细日志
  --help, -h             显示帮助信息
```

### 配置文件示例

**RUBIS配置** (`configs/rubis_config.yaml`)：
```yaml
system_type: rubis
data_path: rubis_evaluation_data/eval_ident_traces
output_dir: validation_results/rubis
report_mode: detailed

expected_distributions:
  norm1:
    mu: 0.0526
    sigma: 0.0024
    min_resp_time: 0.0454
    max_resp_time: 0.0598
  norm2:
    mu: 0.1154
    sigma: 0.0127
  norm3:
    mu: 0.0285
    sigma: 0.0018

validation:
  deviation_threshold: 10.0  # 偏离阈值（百分比）
  min_samples: 10            # 最小样本数
```

**BSN配置** (`configs/bsn_config.yaml`)：
```yaml
system_type: bsn
data_path: bsn_evaluation_data/eval_ident_traces
output_dir: validation_results/bsn
report_mode: detailed

expected_distributions:
  norm1:
    mu: 0.8999
    sigma: 0.0107
  norm2:
    mu: 1.0349
    sigma: 0.0108
  norm3:
    mu: 0.9674
    sigma: 0.0108

validation:
  deviation_threshold: 10.0
  min_samples: 10
```

### 验证报告

运行验证后，会在输出目录生成Markdown格式的验证报告：

**简单模式** 包含：
- 验证摘要表格（期望值 vs 实际值）
- 统计摘要（文件数、正常/异常分布数）
- 验证结论

**详细模式** 额外包含：
- 按位置（1/2/3）分组的统计分析
- 异常样本详细列表
- 完整的偏离分析

**示例输出**：
```
============================================================
验证结果摘要
============================================================
norm1: 期望=0.0526, 实际=0.0525, 偏离=0.11% ✓ 正常
norm2: 期望=0.1154, 实际=0.1152, 偏离=0.14% ✓ 正常
norm3: 期望=0.0285, 实际=0.0285, 偏离=0.17% ✓ 正常
============================================================
✅ 验证通过
```

## 🏗️ 项目结构

```
TOSE/
├── README.md                    # 项目主文档（本文件）
├── validate.py                  # 启动脚本
│
├── data_validation/             # 验证框架
│   ├── core/                    # 核心模块
│   │   ├── config.py            # 配置加载
│   │   ├── parser.py            # 解析器抽象
│   │   ├── validator.py         # 验证引擎
│   │   └── reporter.py          # 报告生成
│   ├── adapters/                # 数据集适配器
│   │   ├── rubis.py             # RUBIS适配器
│   │   ├── bsn.py               # BSN适配器
│   │   └── __init__.py          # 工厂模式
│   ├── models/                  # 数据模型
│   ├── utils/                   # 工具函数
│   └── cli.py                   # 命令行接口
│
├── configs/                     # 配置文件
│   ├── rubis_config.yaml
│   └── bsn_config.yaml
│
├── validation_results/          # 验证结果输出
│   ├── rubis/
│   │   └── validation_report.md
│   └── bsn/
│       └── validation_report.md
│
├── data/                        # 统一数据目录
│   ├── rubis/
│   │   ├── identity/           # RUBIS辨识数据
│   │   └── abnormal/           # RUBIS异常数据
│   ├── bsn/
│   │   ├── identity/           # BSN辨识数据
│   │   └── abnormal/           # BSN异常数据
│   ├── swat/
│   │   ├── identity/           # SWAT辨识数据
│   │   └── abnormal/           # SWAT异常数据
│   └── wadi/
│       ├── identity/           # WADI辨识数据（预留）
│       └── abnormal/           # WADI异常数据（预留）
│
├── cluster_analysis/            # 聚类分析框架
│   ├── core/                    # 聚类引擎和结果模型
│   ├── algorithms/              # 聚类算法实现
│   ├── visualization/           # 可视化和报告生成
│   └── config/                  # 聚类配置管理
│
├── anomaly_detection/           # 异常检测框架
│   ├── core/                    # 检测器和评估器
│   ├── config/                  # 检测配置管理
│   └── visualization/           # 可视化输出
│
├── common/                      # 共享组件层
│   ├── adapters/                # 数据适配器
│   │   ├── rubis.py            # RUBIS解析器
│   │   ├── bsn.py              # BSN解析器
│   │   ├── swat.py             # SWAT解析器
│   │   └── __init__.py         # ParserFactory
│   ├── models/                  # 数据模型
│   └── utils/                   # 统计工具
│
├── clustering_results/          # 聚类分析结果
│   ├── rubis/
│   │   ├── clustering_report.md
│   │   ├── learned_distributions.yaml
│   │   └── *.png               # 可视化图表
│   ├── bsn/
│   └── swat/
│
├── detection_results/           # 异常检测结果
│   ├── rubis/
│   │   ├── detection_report.md
│   │   ├── anomaly_points.csv
│   │   └── *.png
│   ├── bsn/
│   └── swat/
│
└── archived_scripts/            # 已归档的旧脚本
    ├── README.md
    ├── rubis_data_revalidation.py
    └── bsn_trace_analysis.py
```

## 🔧 扩展框架

### 添加新数据集支持

1. **创建适配器类**（继承`TraceParser`）：

```python
# data_validation/adapters/mysystem.py
from ..core.parser import TraceParser
from ..models.metadata import TraceMetadata
from ..models.distribution import DistributionParameters

class MySystemParser(TraceParser):
    FILENAME_PATTERN = re.compile(r'...')

    def parse_filename(self, filename: str):
        # 实现文件名解析
        pass

    def parse_trace_file(self, filepath, metadata):
        # 实现文件读取和分段
        pass

    def extract_parameters(self, segments, metadata):
        # 实现参数提取
        pass
```

2. **注册适配器**：

```python
from data_validation.adapters import ParserFactory
from data_validation.adapters.mysystem import MySystemParser

ParserFactory.register('mysystem', MySystemParser)
```

3. **创建配置文件**（`configs/mysystem_config.yaml`）

4. **运行验证**：

```bash
python validate.py --config configs/mysystem_config.yaml
```

## 📊 数据格式要求

### RUBIS格式

**文件名**：
```
eval_ident_trace-cnt-000-duration-64800-config_num-3-trace_config-norm1,norm2,norm3-start_time-960,33660,47580.txt
```

**CSV格式**：必须包含列
- `simTime(s)` - 仿真时间
- `measuredAvgRespTime_{k}` - 平均响应时间

**特点**：
- 单列响应时间数据
- 按时间段分为3个norm标签
- 数据位置：`data/rubis/identity/`（辨识）或 `data/rubis/abnormal/`（异常）

### BSN格式

**文件名**：
```
eval_ident_trace-cnt-005-duration-64800-sensor_index-2-config_num-3-trace_config-norm1,norm2,norm3-start_time-960,33660,47580.txt
```

**CSV格式**：必须包含列
- `logicalTime(s)` - 逻辑时间
- `component` - 组件标识
- `cost` - 任务执行时间

**特点**：
- 多维数据，根据`sensor_index`选择传感器
- `sensor_index=i` 对应 `component=/g3t1_{i+1}`
- 数据位置：`data/bsn/identity/`（辨识）或 `data/bsn/abnormal/`（异常）

### SWAT格式

**文件名**：
```
eval_ident_trace-cnt-000-duration-64800-config_num-3-trace_config-norm1,norm2,norm3-start_time-960,33660,47580.txt
```

**CSV格式**：必须包含列
- `time` - 时间戳（第一列）
- `y_0` - 目标指标（最后一列）
- 其他列：`water_tank`, `noisy_B_in`, `noisy_B_out`, `u_1_in`, `u_1_out` 等

**特点**：
- 与RUBIS相似的文件命名格式（可复用解析逻辑）
- 列名不同：time（而非simTime）, y_0（而非measuredAvgRespTime）
- 数据位置：`data/swat/identity/`（辨识）或 `data/swat/abnormal/`（异常）

## 🔍 验证逻辑

框架执行以下验证：

1. **均值偏离检查**：计算实际均值与期望均值的偏离百分比
2. **范围约束检查**：验证响应时间范围是否在期望范围内
3. **按位置分组**：分析norm标签在不同位置（1/2/3）的表现
4. **异常样本识别**：标记偏离超过阈值的样本

**判定规则**：
- ✅ **正常**：偏离 < 阈值 **且** 范围约束满足
- ❌ **异常**：偏离 >= 阈值 **或** 范围约束违反

## ❓ 常见问题

**Q: 如何调整偏离阈值？**
A: 在配置文件的`validation.deviation_threshold`中修改，单位为百分比。

**Q: 为什么偏离很小但仍显示异常？**
A: 可能是实际响应时间范围超出了期望范围。检查配置文件中的`min_resp_time`和`max_resp_time`设置。

**Q: 如何只关注均值偏离，忽略范围约束？**
A: 在配置文件中删除或注释掉`min_resp_time`和`max_resp_time`字段。

**Q: 可以同时验证多个数据集吗？**
A: 可以编写脚本循环调用validate.py，或扩展CLI以支持批量验证。

## 📚 相关文档

完整的框架文档和设计说明，请参考：

- **OpenSpec变更提案**：`openspec/changes/refactor-unified-data-validation-framework/`
  - `proposal.md` - 重构提案和目标
  - `design.md` - 详细架构设计
  - `tasks.md` - 实施任务清单
  - `specs/` - 能力规范文件

## 🎓 其他功能

### RUBIS聚类分析

本项目还包含RUBIS数据的高斯分布聚类分析功能：

```bash
# 运行聚类分析
python rubis_trace_clustering.py

# 运行测试
python test_rubis_trace_clustering.py
```

**输出文件**：
- `clustering_results/clustering_parameter_space.png`
- `clustering_results/distributions_*.png`
- `clustering_results/clustering_analysis_report.txt`

**支持的聚类算法**：HDBSCAN、GMM+BIC、Affinity Propagation、Mean Shift

---

## 📝 版本信息

**当前版本**：2.0.0（验证框架重构）
**最后更新**：2026-01-14
**开发基于**：OpenSpec工作流

## 📧 联系与支持

如有问题或建议，请查看OpenSpec文档或提交issue。

---

**🎉 项目状态：生产就绪**
