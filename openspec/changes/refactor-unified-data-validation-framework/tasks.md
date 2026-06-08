# 任务清单

## Phase 1: 核心框架搭建

### 1.1 创建项目结构
- [x] 创建 `data_validation/` 包及子目录结构
- [x] 创建 `configs/` 目录
- [x] 创建所有 `__init__.py` 文件
- [x] 验证：目录结构完整，包可导入

### 1.2 实现配置模块
- [x] 定义配置Schema（系统类型、路径、参数等）
- [x] 实现YAML配置加载 (`core/config.py`)
- [x] 实现配置验证（必填项、类型检查）
- [x] 创建RUBIS配置模板 (`configs/rubis_config.yaml`)
- [x] 创建BSN配置模板 (`configs/bsn_config.yaml`)
- [x] 验证：配置可正确加载和验证

### 1.3 定义数据模型
- [x] 定义元数据基类 (`models/metadata.py`)
- [x] 定义分布参数模型 (`models/distribution.py`)
- [x] 添加dataclass和类型注解
- [x] 验证：模型可实例化，类型检查通过

### 1.4 实现解析器抽象
- [x] 定义文件解析器抽象基类 (`core/parser.py`)
- [x] 定义必需方法：`parse_filename()`, `parse_trace_file()`, `extract_parameters()`
- [x] 添加中文注释说明接口用途
- [x] 验证：基类定义清晰，易于继承

### 1.5 实现验证引擎
- [x] 实现验证引擎核心类 (`core/validator.py`)
- [x] 实现均值偏离计算
- [x] 实现范围约束检查
- [x] 实现按位置分组分析
- [x] 支持自定义阈值（默认10%）
- [x] 验证：可正确计算偏离和判定正常/异常

### 1.6 实现报告生成器
- [x] 实现报告生成器基类 (`core/reporter.py`)
- [x] 支持简单模式：表格+摘要
- [x] 支持详细模式：完整分析+图表
- [x] 生成Markdown格式报告
- [x] 验证：可生成两种模式报告

## Phase 2: 数据集适配器

### 2.1 实现RUBIS适配器
- [x] 创建RUBISParser类 (`adapters/rubis.py`)
- [x] 实现RUBIS文件名解析（正则表达式）
- [x] 实现CSV数据读取和分段
- [x] 提取 `measuredAvgRespTime` 列
- [x] 计算每段的均值、方差、范围
- [x] 验证：处理5个RUBIS文件，输出正确

### 2.2 实现BSN适配器
- [x] 创建BSNParser类 (`adapters/bsn.py`)
- [x] 实现BSN文件名解析（包含sensor_index）
- [x] 实现多维数据读取
- [x] 根据sensor_index选择正确列 (`gt_3_{sensor_index+1}`)
- [x] 计算每段的统计参数
- [x] 验证：处理5个BSN文件，输出正确

### 2.3 适配器注册和工厂
- [x] 实现适配器工厂 (`adapters/__init__.py`)
- [x] 支持根据系统类型创建适配器
- [x] 添加适配器注册机制（便于扩展）
- [x] 验证：可根据配置自动选择适配器

## Phase 3: 工具函数实现

### 3.1 统计工具
- [x] 实现统计计算函数 (`utils/statistics.py`)
- [x] 均值、方差、标准差计算
- [x] 偏离百分比计算
- [x] 分位数和范围计算
- [x] 验证：计算结果与numpy一致

### 3.2 可视化工具
- [x] 实现图表生成函数 (`utils/visualization.py`)
- [x] 生成验证结果对比表
- [x] 生成偏离百分比柱状图
- [x] 生成按位置分组的箱线图
- [x] 生成分布密度图（详细模式）
- [x] 所有图表标签使用中文
- [x] 验证：图表清晰、信息完整

## Phase 4: CLI和启动脚本

### 4.1 实现CLI工具
- [x] 创建CLI模块 (`data_validation/cli.py`)
- [x] 使用argparse解析命令行参数
- [x] 支持参数：`--config`, `--output`, `--mode`
- [x] 实现进度显示
- [x] 实现错误处理和友好提示
- [x] 验证：命令行参数解析正确

### 4.2 创建启动脚本
- [x] 创建 `validate.py` 脚本
- [x] 集成CLI和验证流程
- [x] 添加使用帮助信息（中文）
- [x] 测试：`python validate.py --help` 输出清晰
- [x] 测试：`python validate.py --config configs/rubis_config.yaml` 正常运行

## Phase 5: 集成测试和文档

### 5.1 回归测试
- [x] 运行RUBIS验证，对比旧脚本输出
- [x] 验证norm1、norm2、norm3的统计结果一致
- [x] 运行BSN验证，对比旧脚本输出
- [x] 验证所有分布的偏离百分比一致
- [x] 确认：新框架输出与旧脚本结果匹配

### 5.2 功能测试
- [x] 测试配置切换：修改配置文件后重新运行
- [x] 测试简单模式：输出简洁清晰
- [x] 测试详细模式：包含所有图表和分析
- [x] 测试边界情况：空数据集、文件缺失、格式错误
- [x] 测试错误处理：配置错误、解析失败等
- [x] 验证：所有测试通过

### 5.3 性能测试
- [x] 测试RUBIS 200文件验证时间
- [x] 测试BSN 200文件验证时间
- [x] 确保总时间 < 10秒
- [x] 如有性能问题，优化瓶颈
- [x] 验证：性能达标

### 5.4 编写文档
- [x] 创建 `README_VALIDATION.md`
- [x] 编写快速开始指南
- [x] 说明配置文件格式和选项
- [x] 提供RUBIS和BSN使用示例
- [x] 说明如何添加新数据集适配器
- [x] 说明扩展接口（评估、辨识模块）
- [x] 添加常见问题解答
- [x] 所有文档使用中文
- [x] 验证：文档清晰易懂，示例可运行

### 5.5 代码质量
- [x] 所有函数添加中文docstring
- [x] 所有关键逻辑添加中文注释
- [x] 运行类型检查（mypy可选）
- [x] 代码格式化（black/autopep8）
- [x] 删除调试代码和无用注释
- [x] 验证：代码整洁，注释清晰

### 5.6 归档旧脚本
- [x] 创建 `archived_scripts/` 目录
- [x] 移动 `bsn_trace_analysis.py`
- [x] 移动 `rubis_data_revalidation.py`
- [x] 保留 `rubis_trace_clustering.py`（聚类功能独立）
- [x] 更新 `README.md` 说明新旧脚本关系
- [x] 在归档目录添加说明文档
- [x] 验证：项目结构清晰

## Phase 6: 可选增强

### 6.1 单元测试（可选但推荐）
- [x] 为配置模块编写测试
- [x] 为解析器编写测试
- [x] 为验证引擎编写测试
- [x] 为适配器编写测试
- [x] 运行测试，确保覆盖率>80%

### 6.2 扩展接口示例（可选）
- [x] 创建 `extensions/` 目录结构
- [x] 编写插件接口文档
- [x] 提供一个简单的扩展示例
- [x] 说明如何集成评估和辨识模块

---

## 任务依赖关系

```
Phase 1 (核心框架)
  ├── Phase 2 (适配器) - 依赖Phase 1完成
  ├── Phase 3 (工具) - 可与Phase 2并行
  └── Phase 4 (CLI) - 依赖Phase 1-3完成
       └── Phase 5 (测试文档) - 依赖Phase 4完成
            └── Phase 6 (可选增强) - 独立
```

## 里程碑

- **M1 (Day 1-2)**: Phase 1完成，核心框架可用
- **M2 (Day 2-3)**: Phase 2-3完成，适配器和工具实现
- **M3 (Day 3-4)**: Phase 4完成，CLI可用，一键启动
- **M4 (Day 4-5)**: Phase 5完成，测试通过，文档完善
- **M5 (Day 5+)**: Phase 6完成（可选），扩展接口清晰

## 验收标准

每个阶段完成后需满足：
1. 所有checkbox勾选完成
2. 验证步骤全部通过
3. 代码有中文注释和docstring
4. 相关文档已更新
