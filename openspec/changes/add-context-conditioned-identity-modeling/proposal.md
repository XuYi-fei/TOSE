# Change: Add Context-Conditioned Identity Modeling

## Why

BSN 的 abnormal 前缀出现了明显的连续上下文漂移：identity 主要覆盖 `offset=0.0225`，而 abnormal 前缀常落在 `offset=0.025`。如果统一检测流程只使用无条件 learned distribution，就会把这类上下文漂移误判为异常，导致高 `FP`。

## What Changes

- 为统一解析器链路补充 `context_key/context_features` 提取能力
- 在 learned distributions YAML 顶层导出 `context_calibration_model`
- 检测时先做 exact/nearest 上下文匹配，再按 identity 学到的上下文-均值关系对位置参数做线性校准
- 提供统一的 RQ1 16 组矩阵重跑脚本

## Impact

- Affected specs:
  - `clustering-analysis`
  - `anomaly-detection`
- Affected code:
  - `common/models/*`
  - `common/adapters/*`
  - `cluster_analysis/core/engine.py`
  - `cluster_analysis/visualization/reporter.py`
  - `anomaly_detection/core/detector.py`
  - `anomaly_detection/core/evaluator.py`
  - `scripts/run_rq1_detection_matrix.py`
