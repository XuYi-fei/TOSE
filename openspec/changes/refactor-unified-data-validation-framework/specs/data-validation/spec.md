# 数据验证能力规范

## ADDED Requirements

### Requirement: 支持多数据集identity数据验证

The system MUST be able to validate identity data from both RUBIS and BSN adaptive systems, detecting whether data conforms to expected normal distribution parameters.

系统必须能够验证RUBIS和BSN两种自适应系统的identity数据,检测数据是否符合期望的正态分布参数。

#### Scenario: 验证RUBIS数据集

**Given** RUBIS数据集位于 `rubis_evaluation_data/eval_ident_traces/`
**And** 期望分布参数为:
- norm1: μ=0.0526, σ=0.0024
- norm2: μ=0.1154, σ=0.0127
- norm3: μ=0.0285, σ=0.0018

**When** 运行验证命令 `python validate.py --config configs/rubis_config.yaml`
**Then** 系统应成功解析所有200个trace文件
**And** 输出每个分布的验证结果（均值、偏离百分比、正常/异常判定）
**And** 生成验证报告到指定输出目录

#### Scenario: 验证BSN数据集

**Given** BSN数据集位于 `bsn_evaluation_data/eval_ident_traces/`
**And** 期望分布参数为:
- norm1: μ=0.8999, σ=0.0107
- norm2: μ=1.0349, σ=0.0108
- norm3: μ=0.9674, σ=0.0108

**When** 运行验证命令 `python validate.py --config configs/bsn_config.yaml`
**Then** 系统应正确处理BSN的sensor_index字段
**And** 根据sensor_index选择正确的数据列 `gt_3_{sensor_index+1}`
**And** 输出验证结果和报告

### Requirement: 计算分布偏离和异常检测

The system MUST be able to calculate deviation between actual and expected distributions, and identify anomalous samples based on thresholds.

系统必须能够计算实际分布与期望分布的偏离程度,并基于阈值判定异常样本。

#### Scenario: 计算均值偏离百分比

**Given** 实际均值为 0.052544
**And** 期望均值为 0.0526
**When** 计算偏离百分比
**Then** 结果应为 0.11%
**And** 判定为正常（< 10%阈值）

#### Scenario: 识别异常样本

**Given** norm标签的期望均值为 0.0378
**And** 偏离阈值为 10%
**When** 某样本实际均值为 0.028450（偏离24.74%）
**Then** 该样本应被标记为异常
**And** 异常原因应包含"均值偏离超过阈值"

#### Scenario: 检查响应时间范围约束

**Given** norm3期望响应时间范围为 [0.0231, 0.0339]
**When** 某样本的实际范围为 [0.0227, 0.0344]
**Then** 该样本应被标记为范围违规
**And** 记录实际范围与期望范围的差异

### Requirement: 按位置分组分析

The system MUST support grouping analysis by norm label position (1, 2, 3) in trace_config to detect position-dependent issues.

系统必须支持按norm标签在trace_config中的位置(1, 2, 3)分组分析,检测位置依赖性问题。

#### Scenario: 按位置统计分布参数

**Given** norm3标签在不同trace文件中出现在位置1、2、3
**When** 执行验证
**Then** 系统应分别计算每个位置的统计信息
**And** 输出格式为:
```
位置1: 样本数=51, 均值=0.028403, 偏离=24.78%
位置2: 样本数=73, 均值=0.028474, 偏离=24.64%
位置3: 样本数=42, 均值=0.028430, 偏离=24.85%
```

#### Scenario: 检测位置依赖性

**Given** 按位置分组的统计结果
**When** 不同位置的偏离差异 > 5%
**Then** 系统应报告"存在位置依赖性问题"
**And** 标注哪些位置正常、哪些位置异常

### Requirement: 支持自定义验证阈值

The system MUST allow users to customize deviation thresholds and minimum sample counts through configuration files.

系统必须允许用户通过配置文件自定义偏离阈值和最小样本数。

#### Scenario: 使用自定义偏离阈值

**Given** 配置文件中设置 `deviation_threshold: 5.0`
**When** 某分布偏离为 7%
**Then** 该分布应被判定为异常（> 5%）

#### Scenario: 应用最小样本数过滤

**Given** 配置文件中设置 `min_samples: 10`
**When** 某trace文件的某段数据点少于10个
**Then** 该段应被跳过，不参与统计
**And** 记录警告信息

---

## 相关能力

- 依赖: `configuration-management` - 加载验证参数和阈值
- 依赖: `adapter-system` - 解析不同数据集的trace文件
- 被依赖: `reporting` - 使用验证结果生成报告
