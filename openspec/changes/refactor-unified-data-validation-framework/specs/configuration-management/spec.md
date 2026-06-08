# 配置管理能力规范

## ADDED Requirements

### Requirement: 从YAML文件加载配置

The system MUST support loading all validation parameters from YAML format configuration files.

系统必须支持从YAML格式的配置文件加载所有验证参数。

#### Scenario: 加载完整配置文件

**Given** 配置文件 `configs/rubis_config.yaml` 包含:
```yaml
system_type: rubis
data_path: rubis_evaluation_data/eval_ident_traces
output_dir: validation_results/rubis
report_mode: detailed

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
  deviation_threshold: 10.0
  min_samples: 10
```

**When** 执行 `ValidationConfig.from_yaml('configs/rubis_config.yaml')`
**Then** 系统应成功解析所有字段
**And** 返回 `ValidationConfig` 对象
**And** 所有参数可通过属性访问

#### Scenario: 处理配置文件缺失

**Given** 配置文件路径不存在
**When** 尝试加载配置
**Then** 系统应抛出 `FileNotFoundError` 异常
**And** 错误消息应包含缺失的文件路径

### Requirement: 验证配置完整性

The system MUST validate required fields and data types in configuration files to ensure validity.

系统必须验证配置文件的必填项和数据类型,确保配置有效。

#### Scenario: 验证必填字段

**Given** 配置文件缺少 `system_type` 字段
**When** 调用 `config.validate()`
**Then** 系统应抛出 `ValueError` 异常
**And** 错误消息应为 "缺少必填字段: system_type"

#### Scenario: 验证system_type有效性

**Given** 配置文件中 `system_type: unknown`
**When** 验证配置
**Then** 系统应抛出 `ValueError` 异常
**And** 错误消息应包含支持的类型列表 ['rubis', 'bsn']

#### Scenario: 验证数据路径存在性

**Given** 配置文件中 `data_path: /nonexistent/path`
**When** 验证配置
**Then** 系统应抛出 `ValueError` 异常
**And** 错误消息应为 "数据路径不存在: /nonexistent/path"

#### Scenario: 验证期望分布参数

**Given** 配置文件中norm1缺少 `mu` 参数
**When** 验证配置
**Then** 系统应抛出 `ValueError` 异常
**And** 错误消息应为 "norm1缺少必需参数: mu"

### Requirement: 提供默认值

The system SHALL provide reasonable default values for optional configuration items.

系统应为可选配置项提供合理的默认值。

#### Scenario: 使用默认输出目录

**Given** 配置文件未指定 `output_dir`
**When** 加载配置
**Then** `output_dir` 应默认为 `validation_results/{system_type}`

#### Scenario: 使用默认报告模式

**Given** 配置文件未指定 `report_mode`
**When** 加载配置
**Then** `report_mode` 应默认为 `simple`

#### Scenario: 使用默认验证参数

**Given** 配置文件未指定 `validation` 部分
**When** 加载配置
**Then** `deviation_threshold` 应默认为 10.0
**And** `min_samples` 应默认为 10

### Requirement: 支持配置覆盖

The system MUST support overriding configuration file settings through command-line parameters.

系统必须支持通过命令行参数覆盖配置文件中的设置。

#### Scenario: 通过CLI覆盖输出目录

**Given** 配置文件中 `output_dir: validation_results/rubis`
**When** 命令行指定 `--output custom_output`
**Then** 实际使用的输出目录应为 `custom_output`

#### Scenario: 通过CLI覆盖报告模式

**Given** 配置文件中 `report_mode: simple`
**When** 命令行指定 `--mode detailed`
**Then** 实际使用的报告模式应为 `detailed`

---

## 相关能力

- 被依赖: `data-validation` - 提供验证参数
- 被依赖: `adapter-system` - 提供系统类型和数据路径
- 被依赖: `reporting` - 提供输出目录和报告模式
