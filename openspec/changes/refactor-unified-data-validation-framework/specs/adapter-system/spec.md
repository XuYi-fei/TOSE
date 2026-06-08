# 适配器系统能力规范

## ADDED Requirements

### Requirement: 支持多种数据集格式

The system MUST support different dataset file formats and data structures through the adapter pattern.

系统必须通过适配器模式支持不同数据集的文件格式和数据结构。

#### Scenario: 解析RUBIS文件名

**Given** RUBIS trace文件名为:
`eval_ident_trace-cnt-000-duration-64800-config_num-3-trace_config-norm2,norm1,norm3-start_time-960,33660,47580.txt`

**When** RUBISParser解析文件名
**Then** 应提取以下元数据:
- cnt: 0
- duration: 64800
- config_num: 3
- trace_config: ['norm2', 'norm1', 'norm3']
- start_time: [960, 33660, 47580]

#### Scenario: 解析BSN文件名

**Given** BSN trace文件名为:
`eval_ident_trace-cnt-005-duration-64800-sensor_index-2-config_num-3-trace_config-norm1,norm3,norm2-start_time-960,33660,47580.txt`

**When** BSNParser解析文件名
**Then** 应提取以下元数据:
- cnt: 5
- sensor_index: 2
- config_num: 3
- trace_config: ['norm1', 'norm3', 'norm2']
- start_time: [960, 33660, 47580]

### Requirement: 处理不同的数据列结构

The system MUST be able to extract correct response time data from CSV files with different column structures.

系统必须能够从不同结构的CSV文件中提取正确的响应时间数据。

#### Scenario: RUBIS单列数据提取

**Given** RUBIS CSV文件包含列: `simTime(s), controlServers, measuredArrivalRate, measuredAvgRespTime_{k}`
**When** 提取响应时间数据
**Then** 应选择 `measuredAvgRespTime_{k}` 列
**And** 无需考虑sensor_index

#### Scenario: BSN多维数据选择

**Given** BSN CSV文件包含多列: `simTime, gt_3_1, gt_3_2, gt_3_3, ..., gt_3_10`
**And** 文件元数据中 sensor_index=2
**When** 提取响应时间数据
**Then** 应选择 `gt_3_3` 列（sensor_index + 1）
**And** 忽略其他列

### Requirement: 按时间段分段数据

The system MUST segment trace file data based on start_time and trace_config, with each segment corresponding to a norm label.

系统必须根据start_time和trace_config将trace文件数据分段,每段对应一个norm标签。

#### Scenario: 分段RUBIS数据

**Given** trace_config=['norm2', 'norm1', 'norm3']
**And** start_time=[960, 33660, 47580]
**And** CSV数据包含simTime从960到64800
**When** 解析trace文件
**Then** 应生成3个数据段:
- norm2段: simTime ∈ [960, 33660)
- norm1段: simTime ∈ [33660, 47580)
- norm3段: simTime ∈ [47580, 最大simTime]

#### Scenario: 处理段内数据点不足

**Given** 某时间段内的数据点少于10个
**When** 提取该段的分布参数
**Then** 该段应被跳过
**And** 记录警告日志

### Requirement: 适配器工厂和注册

The system MUST provide an adapter factory that supports dynamic creation and registration of new adapters.

系统必须提供适配器工厂,支持动态创建和注册新适配器。

#### Scenario: 根据配置创建适配器

**Given** 配置中 system_type='rubis'
**When** ParserFactory.create('rubis')
**Then** 应返回RUBISParser实例

**Given** 配置中 system_type='bsn'
**When** ParserFactory.create('bsn')
**Then** 应返回BSNParser实例

#### Scenario: 注册自定义适配器

**Given** 用户定义了 MySystemParser 类
**When** 执行 `ParserFactory.register('mysystem', MySystemParser)`
**Then** 后续可通过 `ParserFactory.create('mysystem')` 创建实例

#### Scenario: 处理未知系统类型

**Given** 配置中 system_type='unknown'
**When** ParserFactory.create('unknown')
**Then** 应抛出 `ValueError` 异常
**And** 错误消息应包含支持的系统类型列表

### Requirement: 提取分布统计参数

The system MUST extract mean, variance, standard deviation, and response time range from segmented data.

系统必须从分段数据中提取均值、方差、标准差和响应时间范围。

#### Scenario: 计算段内统计参数

**Given** norm1段包含100个响应时间数据点
**When** 提取分布参数
**Then** 应计算并返回:
- mean: 数值均值
- variance: 样本方差
- std_dev: 标准差
- min_value: 最小值
- max_value: 最大值
- sample_count: 100

---

## 相关能力

- 依赖: `configuration-management` - 获取系统类型和数据路径
- 被依赖: `data-validation` - 提供解析后的分布参数
