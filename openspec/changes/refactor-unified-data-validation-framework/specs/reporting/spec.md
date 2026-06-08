# 报告生成能力规范

## ADDED Requirements

### Requirement: 支持简单和详细两种报告模式

The system MUST support two complexity levels of validation reports, selectable by users through configuration.

系统必须支持两种复杂度的验证报告,用户可通过配置选择。

#### Scenario: 生成简单模式报告

**Given** 配置文件中 `report_mode: simple`
**And** 验证已完成，结果包含3个norm分布
**When** 生成验证报告
**Then** 报告应包含以下内容:
- 验证摘要表格（norm标签、期望均值、实际均值、偏离百分比、判定结果）
- 统计摘要（总样本数、正常/异常分布数量）
- 简要结论（是否通过验证）
**And** 报告文件保存为 `{output_dir}/validation_report.md`
**And** 无需生成可视化图表

#### Scenario: 生成详细模式报告

**Given** 配置文件中 `report_mode: detailed`
**And** 验证已完成
**When** 生成验证报告
**Then** 报告应包含简单模式的所有内容
**And** 额外包含:
- 按位置分组的统计表（位置1/2/3的样本数、均值、偏离）
- 异常样本详细列表（文件名、偏离值、异常原因）
- 可视化图表:
  - 偏离百分比柱状图
  - 按位置分组的箱线图
  - 分布密度图（可选）
**And** 所有图表保存到 `{output_dir}/charts/` 目录

### Requirement: Markdown格式输出

The system MUST generate well-structured Markdown format reports, facilitating reading and version control.

系统必须生成结构良好的Markdown格式报告,便于阅读和版本控制。

#### Scenario: 验证摘要表格格式

**Given** 验证结果包含norm1、norm2、norm3三个分布
**When** 生成Markdown报告
**Then** 摘要表格应使用如下格式:
```markdown
| Norm标签 | 期望均值 | 实际均值 | 偏离(%) | 期望范围 | 实际范围 | 判定 |
|---------|---------|---------|--------|---------|---------|------|
| norm1   | 0.0526  | 0.0525  | 0.19   | [0.0454,0.0598] | [0.0455,0.0597] | ✓ 正常 |
| norm2   | 0.1154  | 0.1152  | 0.17   | [0.0773,0.1535] | [0.0774,0.1534] | ✓ 正常 |
| norm3   | 0.0285  | 0.0284  | 0.35   | [0.0231,0.0339] | [0.0232,0.0338] | ✓ 正常 |
```

#### Scenario: 处理异常分布标记

**Given** norm3分布偏离超过阈值24.78%
**When** 生成报告
**Then** 判定列应显示 `✗ 异常`
**And** 报告应高亮显示该行（使用Markdown加粗或特殊标记）

### Requirement: 输出目录管理

The system MUST automatically create output directories and organize report file structure.

系统必须自动创建输出目录,并组织报告文件结构。

#### Scenario: 自动创建输出目录

**Given** 配置文件中 `output_dir: validation_results/rubis`
**And** 该目录不存在
**When** 开始生成报告
**Then** 系统应自动创建目录 `validation_results/rubis/`
**And** 无需用户手动创建

#### Scenario: 详细模式的目录结构

**Given** `report_mode: detailed`
**When** 生成报告和图表
**Then** 输出目录结构应为:
```
validation_results/rubis/
├── validation_report.md
└── charts/
    ├── deviation_bar_chart.png
    ├── position_boxplot.png
    └── distribution_density.png
```

### Requirement: 图表生成和定制

The system MUST generate clear data visualization charts with all labels in Chinese.

系统必须生成清晰的数据可视化图表,所有标签使用中文。

#### Scenario: 生成偏离百分比柱状图

**Given** 验证结果包含3个norm分布的偏离百分比
**When** 生成详细报告
**Then** 应生成柱状图 `charts/deviation_bar_chart.png`
**And** X轴标签为 `Norm标签`
**And** Y轴标签为 `偏离百分比 (%)`
**And** 图表标题为 `各分布均值偏离百分比`
**And** 阈值线应以红色虚线显示（默认10%）

#### Scenario: 生成按位置分组的箱线图

**Given** 验证结果包含按位置(1, 2, 3)分组的统计数据
**When** 生成详细报告
**Then** 应生成箱线图 `charts/position_boxplot.png`
**And** X轴标签为 `位置（在trace_config中的顺序）`
**And** Y轴标签为 `响应时间均值`
**And** 每个norm分布应有不同颜色的箱线
**And** 图例应显示norm标签

#### Scenario: 处理图表生成失败

**Given** matplotlib库未安装或生成图表时出错
**When** 尝试生成详细报告
**Then** 系统应记录警告日志
**And** 报告仍应生成（不包含图表）
**And** 不应中断验证流程

### Requirement: 自定义报告内容

The system MUST support adjusting report detail level based on configuration.

系统必须支持根据配置调整报告详细程度。

#### Scenario: 控制异常样本列表长度

**Given** 配置文件中 `reporting.max_anomalies: 10`
**And** 验证发现20个异常样本
**When** 生成详细报告
**Then** 异常样本列表应只显示前10个
**And** 报告应注明 `（共20个异常，仅显示前10个）`

#### Scenario: 跳过可选图表

**Given** 配置文件中 `reporting.include_density_plot: false`
**When** 生成详细报告
**Then** 应生成偏离柱状图和位置箱线图
**And** 不应生成分布密度图

### Requirement: 错误处理和日志记录

The system MUST provide clear error messages and logging during report generation.

系统必须在报告生成过程中提供清晰的错误提示和日志。

#### Scenario: 输出目录无写权限

**Given** 配置文件中 `output_dir: /root/protected_dir`
**And** 当前用户无写权限
**When** 尝试生成报告
**Then** 系统应抛出 `PermissionError` 异常
**And** 错误消息应为 `无法写入输出目录: /root/protected_dir`

#### Scenario: 记录报告生成日志

**Given** 验证完成
**When** 生成报告
**Then** 系统应记录以下日志:
- `[INFO] 开始生成验证报告...`
- `[INFO] 报告模式: detailed`
- `[INFO] 生成验证摘要表格`
- `[INFO] 生成图表: deviation_bar_chart.png`
- `[INFO] 报告已保存: validation_results/rubis/validation_report.md`

---

## 相关能力

- 依赖: `data-validation` - 提供验证结果数据
- 依赖: `configuration-management` - 获取输出目录和报告模式
