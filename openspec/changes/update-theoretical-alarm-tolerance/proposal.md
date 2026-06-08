# 提案：按 3σ 理论容忍次数触发 trace 级报警

## Why

当前 RQ1 检测口径是“任意 1 个异常点即触发整条 trace 的首次报警”。在 abnormal trace 的正常前缀较长时，这会把很低的点级误报累积放大成很高的 trace 级 FP。

现有实现已经保留了点级 3σ 判定，因此可以进一步利用 3σ 的理论尾概率，为 trace 级报警增加一个与已观测点数成比例的容忍次数门槛。

## What Changes

- 保留现有点级 `detect_point()` 的 3σ 判定
- 将 trace 级首次报警的触发条件改为：
  - 在第 `n` 个已观测点时，允许的 raw anomaly 数为 `ceil(n * p_sigma)`
  - 其中 `p_sigma = erfc(sigma_threshold / sqrt(2))`
  - 仅当累计 raw anomaly 数大于该门槛时，才认定真正报警发生
- 扩展 detection config、结果 JSON/CSV/Markdown，使新触发策略可配置、可追溯
- 用新口径直接替换 RQ1 正式检测结果与汇总表

## Impact

- Affected specs:
  - `trace-level-evaluation`
- Affected code:
  - `anomaly_detection/core/evaluator.py`
  - `anomaly_detection/config/config.py`
  - `anomaly_detection/visualization/reporter.py`
  - `detect.py`
  - `configs/*_detection_config.yaml`
  - `docs/rq1_experiment_status.md`
