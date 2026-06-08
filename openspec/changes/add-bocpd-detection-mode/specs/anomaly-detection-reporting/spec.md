## MODIFIED Requirements

### Requirement: 保存异常点详细信息
检测结果输出 SHALL 在统一格式中包含检测模式元数据，并在 BOCPD 模式下暴露点级 BOCPD 状态。

#### Scenario: JSON 输出包含检测模式元数据
- **WHEN** 系统生成结构化 JSON 检测结果
- **THEN** metadata 和 summary SHALL 包含 `detection_mode`
- **AND** 在 BOCPD 模式下包含关键 BOCPD 配置字段

#### Scenario: BOCPD 异常点包含状态信息
- **WHEN** 系统在 BOCPD 模式下输出 anomaly points
- **THEN** 每个 anomaly point SHALL 包含 `changepoint_probability`
- **AND** 包含 `most_likely_run_length`
- **AND** 包含 `best_tail_p_value`
- **AND** 包含 `best_log_likelihood`
- **AND** 包含 `raw_anomaly_reasons`
