# Anomaly Detection Config Spec

## ADDED Requirements

### Requirement: YAML配置文件加载
**ID**: ADC-001
**Priority**: High

异常检测框架SHALL支持通过YAML配置文件指定检测参数，包括分布路径、测试数据、阈值等。

#### Scenario: 加载有效的RUBIS检测配置
**Given** 存在配置文件`configs/rubis_detection_config.yaml`
**And** 配置包含system_type, learned_distributions, test_data_path
**When** 使用DetectionConfig.from_yaml()加载配置
**Then** 应成功解析配置
**And** system_type应为"rubis"
**And** learned_distributions路径应存在
**And** test_data_path目录应存在

#### Scenario: 配置文件不存在
**Given** 配置文件路径不存在
**When** 尝试加载配置
**Then** 应抛出FileNotFoundError
**And** 错误信息应明确指出文件路径

#### Scenario: 必填字段缺失
**Given** 配置文件缺少system_type字段
**When** 加载并验证配置
**Then** 应抛出ValueError
**And** 错误信息应列出缺失的字段名

---

### Requirement: 配置文件结构验证
**ID**: ADC-002
**Priority**: High

系统SHALL验证配置文件的结构完整性和参数有效性。

#### Scenario: 验证system_type有效性
**Given** 配置文件system_type="invalid_system"
**When** 验证配置
**Then** 应抛出ValueError
**And** 提示支持的系统类型为：rubis, bsn

#### Scenario: 验证learned_distributions路径
**Given** 配置文件指定learned_distributions路径
**When** 验证配置
**Then** 应检查文件是否存在
**And** 文件不存在时应抛出FileNotFoundError
**And** 提示用户先运行聚类分析

#### Scenario: 验证test_data_path目录
**Given** 配置文件指定test_data_path
**When** 验证配置
**Then** 应检查目录是否存在
**And** 目录不存在时应抛出ValueError
**And** 应检查目录中是否有trace文件
**And** 无trace文件时应发出警告

---

### Requirement: 检测参数配置
**ID**: ADC-003
**Priority**: Medium

配置文件SHALL支持指定异常检测的参数。

#### Scenario: 配置sigma阈值
**Given** 配置文件包含`detection.sigma_threshold: 2.5`
**When** 加载配置
**Then** AnomalyDetector应使用阈值2.5
**And** 默认值为3.0（未指定时）

#### Scenario: 配置最小检测样本数
**Given** 配置文件包含`detection.min_samples_for_detection: 10`
**When** 检测trace
**Then** 只有连续10个点都异常才判定为真异常
**And** 用于减少噪声引起的误报
**And** 默认值为1（不使用此过滤）

---

### Requirement: 输出配置
**ID**: ADC-004
**Priority**: Medium

配置文件SHALL支持指定输出行为。

#### Scenario: 配置输出目录
**Given** 配置文件指定`output.dir: detection_results/rubis`
**When** 执行检测
**Then** 所有结果应保存在该目录
**And** 目录不存在时自动创建

#### Scenario: 控制可视化生成
**Given** 配置文件设置`output.generate_visualizations: false`
**When** 执行检测
**Then** 不应生成可视化图表
**And** 只生成Markdown报告

#### Scenario: 保存异常点详细信息
**Given** 配置文件设置`output.save_anomaly_points: true`
**When** 检测完成
**Then** 应生成`anomaly_points.csv`文件
**And** 包含字段：filename, time, value, z_scores, segment_label

---

### Requirement: 命令行参数覆盖
**ID**: ADC-005
**Priority**: Low

系统SHALL支持命令行参数覆盖配置文件中的设置。

#### Scenario: 覆盖输出目录
**Given** 配置文件指定output.dir="detection_results/rubis"
**And** 命令行参数--output="custom_results"
**When** 执行检测
**Then** 应使用custom_results作为输出目录

#### Scenario: 覆盖sigma阈值
**Given** 配置文件指定sigma_threshold=3.0
**And** 命令行参数--sigma-threshold=2.5
**When** 初始化检测器
**Then** 应使用阈值2.5

---

### Requirement: 配置模板和示例
**ID**: ADC-006
**Priority**: Low

系统SHALL提供清晰的配置模板和示例。

#### Scenario: 提供RUBIS检测配置模板
**Given** 用户首次使用异常检测
**When** 查看configs/rubis_detection_config.yaml
**Then** 应包含所有必填和可选字段
**And** 每个字段应有注释说明用途
**And** 应提供合理的默认值

#### Scenario: 提供BSN检测配置模板
**Given** 用户需要检测BSN数据
**When** 查看configs/bsn_detection_config.yaml
**Then** 应包含BSN特定的配置
**And** test_data_path应指向BSN数据目录
**And** learned_distributions应指向BSN聚类结果
