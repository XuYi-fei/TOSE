# 通用数据验证框架重构

## 变更ID
`refactor-unified-data-validation-framework`

## 状态
🔄 提案中

## 变更概述

将现有的RUBIS和BSN数据验证代码重构为一个通用的、可配置的数据验证框架，支持多种自适应系统的identity数据验证，并为未来的评估和辨识模型集成预留扩展空间。

## 问题描述

当前存在以下问题：

1. **代码重复**: `rubis_trace_clustering.py`、`bsn_trace_analysis.py`、`rubis_data_revalidation.py`包含大量重复的解析和验证逻辑
2. **缺乏通用性**: 每个数据集需要单独的脚本，无法快速适配新数据集
3. **配置硬编码**: 期望参数、文件路径等都硬编码在脚本中
4. **启动复杂**: 需要手动修改代码或传递多个参数
5. **输出不统一**: 不同脚本生成的报告格式不一致
6. **扩展困难**: 难以添加新的数据集类型或分析功能

## 目标

### 核心目标

1. **通用数据验证**: 支持RUBIS和BSN两种数据集，验证identity数据是否符合期望的正态分布
2. **配置驱动**: 通过简单配置文件切换数据集和验证参数
3. **灵活输出**: 支持简单/复杂两种报告复杂度，自动生成相应的图表
4. **一键启动**: 提供命令行工具，无需修改代码即可执行验证
5. **中文文档**: 所有注释和文档使用中文，避免过度文档化
6. **可扩展**: 为未来集成评估和辨识模型预留架构空间

### 技术要求

1. **数据源适配**:
   - RUBIS: 单列数据源(`measuredAvgRespTime`)
   - BSN: 多维数据源，通过`sensor_index`选择列(`gt_3_{sensor_index+1}`)

2. **文件名解析**:
   - RUBIS格式: `eval_ident_trace-cnt-X-duration-Y-config_num-Z-trace_config-...-start_time-...`
   - BSN格式: `eval_ident_trace-cnt-X-duration-Y-sensor_index-W-config_num-Z-trace_config-...-start_time-...`

3. **配置项**:
   - 系统类型 (rubis/bsn)
   - 数据集路径
   - 期望分布参数 (μ, σ)
   - 报告复杂度 (simple/detailed)
   - 输出目录

4. **报告复杂度**:
   - **简单**: 仅验证结果表格、关键统计信息
   - **详细**: 包含所有图表、详细分析、异常样本列表

## 架构设计

### 核心组件

```
data_validation/
├── __init__.py
├── core/                    # 核心框架
│   ├── __init__.py
│   ├── config.py           # 配置加载和验证
│   ├── parser.py           # 文件名和数据解析抽象基类
│   ├── validator.py        # 数据验证引擎
│   └── reporter.py         # 报告生成器
├── adapters/               # 数据集适配器
│   ├── __init__.py
│   ├── rubis.py           # RUBIS适配器
│   └── bsn.py             # BSN适配器
├── models/                 # 数据模型
│   ├── __init__.py
│   ├── metadata.py        # 元数据模型
│   └── distribution.py    # 分布参数模型
├── utils/                  # 工具函数
│   ├── __init__.py
│   ├── statistics.py      # 统计计算
│   └── visualization.py   # 图表生成
└── cli.py                  # 命令行接口

configs/                     # 配置文件目录
├── rubis_config.yaml       # RUBIS验证配置
└── bsn_config.yaml         # BSN验证配置

validate.py                  # 一键启动脚本
```

### 设计原则

1. **策略模式**: 使用适配器模式处理不同数据集的差异
2. **配置外部化**: 所有可变参数通过YAML配置文件管理
3. **模块化**: 每个组件职责单一，易于测试和扩展
4. **可扩展性**: 预留插件接口，支持未来添加新功能

## 影响范围

### 新增文件

- `data_validation/` - 完整的验证框架包
- `configs/rubis_config.yaml` - RUBIS配置示例
- `configs/bsn_config.yaml` - BSN配置示例
- `validate.py` - 命令行启动脚本
- `README_VALIDATION.md` - 框架使用文档

### 修改文件

- `README.md` - 更新项目结构和使用说明

### 可归档文件

以下文件将被新框架替代，可移至`archived_scripts/`：
- `rubis_trace_clustering.py` → 聚类功能保留，验证部分移至新框架
- `bsn_trace_analysis.py` → 由新框架替代
- `rubis_data_revalidation.py` → 由新框架替代

## 成功标准

### 功能验证

1. ✅ 使用RUBIS配置，能正确验证200个trace文件
2. ✅ 使用BSN配置，能正确验证200个trace文件
3. ✅ 简单模式输出：验证结果表、统计摘要
4. ✅ 详细模式输出：完整报告、多种图表
5. ✅ 配置切换：修改配置文件后无需改代码即可切换数据集
6. ✅ 一键启动：`python validate.py --config configs/rubis_config.yaml`

### 质量标准

1. ✅ 所有注释和文档使用中文
2. ✅ 代码覆盖率 > 80%
3. ✅ 通过现有测试用例
4. ✅ 与旧脚本输出结果一致（回归测试）
5. ✅ 响应时间 < 10秒（200个文件）

### 扩展性验证

1. ✅ 能在30分钟内添加新数据集适配器
2. ✅ 插件接口明确，易于集成评估/辨识模块
3. ✅ 配置schema清晰，便于理解和修改

## 实施计划

### Phase 1: 核心框架搭建（优先级：高）

1. 创建项目结构和包
2. 实现配置加载模块 (`config.py`)
3. 定义抽象基类 (`parser.py`)
4. 实现验证引擎 (`validator.py`)
5. 实现报告生成器 (`reporter.py`)

### Phase 2: 数据集适配器（优先级：高）

1. 实现RUBIS适配器 (`adapters/rubis.py`)
2. 实现BSN适配器 (`adapters/bsn.py`)
3. 迁移现有解析逻辑
4. 测试适配器功能

### Phase 3: 配置和CLI（优先级：中）

1. 创建YAML配置模板
2. 实现CLI工具 (`cli.py`)
3. 创建启动脚本 (`validate.py`)
4. 编写使用文档

### Phase 4: 可视化和报告（优先级：中）

1. 实现统计工具 (`utils/statistics.py`)
2. 实现图表生成 (`utils/visualization.py`)
3. 支持简单/详细两种模式
4. 生成示例报告

### Phase 5: 测试和文档（优先级：高）

1. 编写单元测试
2. 回归测试（对比旧脚本输出）
3. 完善中文文档
4. 归档旧脚本

## 风险评估

### 技术风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 配置复杂度过高 | 中 | 中 | 提供详细示例和默认值 |
| 性能下降 | 低 | 低 | 保持简单实现，必要时优化 |
| 破坏现有功能 | 低 | 高 | 完整回归测试，保留旧脚本 |

### 实施风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 开发时间超预期 | 中 | 中 | 分阶段实施，核心功能优先 |
| 文档不完善 | 低 | 中 | 边开发边文档，示例充足 |

## 验证计划

### 回归测试

1. 使用RUBIS配置验证，输出应与`rubis_data_revalidation.py`一致
2. 使用BSN配置验证，输出应与`bsn_trace_analysis.py`一致

### 功能测试

1. 配置切换测试：修改配置文件，验证不同数据集
2. 报告复杂度测试：验证简单/详细模式输出差异
3. 边界测试：空数据集、缺失文件、格式错误等

### 性能测试

1. 验证200个RUBIS文件的时间 < 10秒
2. 验证200个BSN文件的时间 < 10秒

## 后续扩展方向

1. **评估模块集成**: 在验证后自动评估数据质量分数
2. **辨识模型集成**: 支持运行GMM、HDBSCAN等聚类算法
3. **多数据集对比**: 支持同时加载多个数据集进行对比分析
4. **Web界面**: 提供可视化的配置和报告查看界面
5. **持续监控**: 支持周期性验证和异常告警

## 依赖关系

### 现有依赖保持不变

- Python >= 3.8
- pandas
- numpy
- matplotlib
- scikit-learn

### 新增依赖

- PyYAML - 配置文件解析
- click - CLI框架（可选，可用argparse替代）

## 交付物

1. **代码**:
   - `data_validation/` 包（~1500行）
   - `validate.py` 启动脚本（~100行）
   - 配置文件模板（2个YAML）

2. **文档**:
   - `README_VALIDATION.md` - 框架使用指南
   - 代码注释（中文）

3. **测试**:
   - 单元测试（覆盖率>80%）
   - 回归测试脚本

4. **示例**:
   - RUBIS验证示例报告
   - BSN验证示例报告

---

**提案创建时间**: 2026-01-14
**预计完成时间**: 5个工作日
**责任人**: Claude (TOSE项目)
