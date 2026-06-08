# Change: Add RQ2 KMeans Numeric Baseline Evaluation

## Why

论文 RQ2 需要一个与现有“分布聚类检测”并列的 baseline。该 baseline 只用于 RQ2，方法定义为：直接对全部辨识数据的原始数值点执行 1D kmeans 聚类，再用最近中心距离做异常检测。

## What Changes

- 新增独立的 RQ2 kmeans baseline 训练入口与检测入口
- 对 `k=2..10` 全量训练并逐个输出检测结果
- 新增 `best-k` 汇总文件，默认按 F1 选择
- 修正 BSN 和 SWAT 在 trace-level 评估器中的时序读取兼容性

## Impact

- Affected code: `cluster_kmeans_baseline.py`, `detect_kmeans_baseline.py`, `rq2_kmeans_baseline/`, `anomaly_detection/core/evaluator.py`
- Affected docs: `README.md`, `configs/*_kmeans_baseline_*`
