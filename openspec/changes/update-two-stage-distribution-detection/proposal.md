# Change: Two-Stage Distribution Identification And Heterogeneous Detection

## Why

当前 RQ1 主链路仍以单阶段 `[mu, variance]` 聚类和高斯 `3σ` 检测为主，无法表达“先按 identity 均值聚类、再对簇内样本重新选择分布族”的新实验设计。

## What Changes

- 将通用聚类链路改为两阶段：
  - `stage-1` 对 identity 段的 `mu` 做自由聚类
  - `stage-2` 对每个聚类簇内的原始样本做分布选择与拟合
- 将 learned distributions 导出升级为异构分布格式，保留 `distribution_type`、`fitted_params`、`goodness_of_fit`
- 将通用检测链路改为边缘概率判定，并对多个 learned cluster distribution 使用 `max_p_value` 聚合
- 将 trace 级容忍次数的计算从 `p_sigma` 泛化为点级异常概率阈值 `alpha`

## Impact

- Affected specs:
  - `clustering-analysis`
  - `anomaly-detection`
- Affected code:
  - `cluster_analysis/core/engine.py`
  - `cluster_analysis/core/distribution_fitting.py`
  - `cluster_analysis/visualization/reporter.py`
  - `anomaly_detection/core/detector.py`
  - `anomaly_detection/core/distribution.py`
  - `anomaly_detection/core/evaluator.py`
  - `configs/*_clustering_config.yaml`
  - `configs/*_detection_config.yaml`
