## ADDED Requirements

### Requirement: RQ2 KMeans Numeric Baseline Training
系统 SHALL 提供一条独立于现有分布聚类主链路的 RQ2 baseline 训练流程，对指定系统的全部 identity 原始数值点执行 1D kmeans 聚类。

#### Scenario: Train all configured k values
- **WHEN** 用户运行 RQ2 baseline 训练入口并提供 `k_values`
- **THEN** 系统为每个 `k` 分别训练一个 kmeans 模型
- **AND** 为每个 `k` 输出一个 `baseline_model_k<k>.yaml`

### Requirement: RQ2 KMeans Numeric Baseline Detection
系统 SHALL 使用最近中心距离对 abnormal trace 执行异常检测，并复用现有 trace-level 评估口径。

#### Scenario: Detect anomalies for each saved kmeans model
- **WHEN** 用户运行 RQ2 baseline 检测入口
- **THEN** 系统加载目录中的每个 `baseline_model_k<k>.yaml`
- **AND** 分别生成该 `k` 的 Markdown、JSON、CSV 检测结果
- **AND** 输出包含 best-k 的汇总结果

### Requirement: Cross-system Trace Series Compatibility
系统 SHALL 正确读取 RUBIS、BSN、SWAT、WADI 四类 trace 的时间列和目标数值列。

#### Scenario: Evaluate BSN and SWAT traces with trace-level metrics
- **WHEN** 评估器处理 BSN 或 SWAT abnormal trace
- **THEN** BSN 使用 `logicalTime(s)` 并按 `sensor_index` 过滤目标 component
- **AND** SWAT 使用 `time` 作为时间列
