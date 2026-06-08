## MODIFIED Requirements

### Requirement: 检测参数配置
检测配置系统 SHALL 支持多种检测模式，并为 BOCPD 模式加载专用参数。

#### Scenario: 保持现有点级配置兼容
- **WHEN** 配置文件未提供 `detection.mode`
- **THEN** 系统 SHALL 默认使用 `pointwise`
- **AND** 现有配置文件无需修改即可继续运行

#### Scenario: 加载 BOCPD 配置
- **WHEN** 配置文件设置 `detection.mode: bocpd`
- **THEN** 系统 SHALL 读取 `detection.bocpd.hazard_lambda`
- **AND** 读取 `detection.bocpd.max_run_length`
- **AND** 读取 `detection.bocpd.state_prior`
- **AND** 读取 `detection.bocpd.changepoint_posterior_threshold`
- **AND** 读取 `detection.bocpd.raw_anomaly_rule`

#### Scenario: 校验非法 BOCPD 参数
- **WHEN** `detection.mode` 为 `bocpd` 且任一 BOCPD 参数非法
- **THEN** 配置加载 SHALL 失败并返回明确错误
