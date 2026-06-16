# RQ1 Experiment Status

## Goal

RQ1 当前只保留一套正式协议，用于对比五种检测方法在四个 subject system 上的异常检测效果：

- `GROUP`
- `SWD`
- `ARD`
- `PRD`
- `GPD`

subject system 为：

- `rubis`
- `bsn`
- `swat`
- `wadi`

其中：

- `GROUP` 使用 TOSE 当前主链路的聚类 + 分布辨识 + 统一检测框架。
- `SWD`、`ARD`、`PRD`、`GPD` 使用 ASE 风格 baseline 适配层。

## Official Protocol

2026-06-15 起，RQ1 只承认这一套 holdout 协议：

- 测试数据完全由 `data/<system>/identity` 中的已知分布段重组生成。
- abnormal trace 的异常段始终位于最后一段，并继续用 `abn1_start_time` 作为评估边界。
- `rubis`、`swat`、`wadi` 的 holdout 单元是 `norm1/norm2/norm3`。
- `bsn` 的 holdout 单元是 `sensor_index + norm_label`，例如 `sensor3_norm2`。
- 对某个 holdout 单元 `u`：
  - abnormal 后缀仅来自 `{u}`
  - abnormal 前缀只来自非 `{u}` 的正常分布段
- `GROUP`：
  - 对每个 `holdout_*` 单独训练
  - 使用对应 holdout 目录下的 `identity` 做训练
  - 只测试该 holdout 目录下的 `abnormal`
- `SWD`、`ARD`、`PRD`、`GPD`：
  - 每个 system 只训练一次
  - 固定使用 `data/<system>/identity` 训练
  - 然后对该 system 下全部 holdout abnormal 数据逐组测试并聚合

## Standardized Structure

当前 RQ1 相关的正式代码与数据结构如下：

- 数据集生成：
  - [build_rq1_holdout_dataset.py](/Users/xuyifei/NJU/repos/TOSE/scripts/build_rq1_holdout_dataset.py)
  - [holdout_dataset.py](/Users/xuyifei/NJU/repos/TOSE/rq_methods/holdout_dataset.py)
- GROUP holdout 聚类产物生成：
  - [build_rq1_holdout_group_distributions.py](/Users/xuyifei/NJU/repos/TOSE/scripts/build_rq1_holdout_group_distributions.py)
- 五方法统一矩阵：
  - [run_rq1_methods_matrix.py](/Users/xuyifei/NJU/repos/TOSE/scripts/run_rq1_methods_matrix.py)
  - [holdout_runner.py](/Users/xuyifei/NJU/repos/TOSE/rq_methods/holdout_runner.py)
- 端到端重跑入口：
  - [run_rq1_holdout_pipeline.py](/Users/xuyifei/NJU/repos/TOSE/scripts/run_rq1_holdout_pipeline.py)

旧版 RQ1 脚本与测试已经从源码中删除；当前仓库只保留上述最新 holdout 版本。

正式目录约定：

- holdout 数据：`data_rq1_holdout/`
- GROUP holdout learned distributions：`clustering_results_rq1_holdout/`
- RQ1 正式结果：`rq_results/rq1/`

本轮 holdout 数量：

- `rubis`: 3
- `bsn`: 18
- `swat`: 3
- `wadi`: 3

## Execution

当前唯一正式入口：

```bash
python3 scripts/run_rq1_methods_matrix.py \
  --data-root data_rq1_holdout \
  --output-dir rq_results/rq1 \
  --learned-root clustering_results_rq1_holdout \
  --baseline-identity-root data
```

如果需要从头重建 holdout 数据并重跑：

```bash
python3 scripts/run_rq1_holdout_pipeline.py \
  --data-root data \
  --holdout-root data_rq1_holdout \
  --learned-root clustering_results_rq1_holdout \
  --output-dir rq_results/rq1
```

## Official Outputs

当前唯一正式汇总文件：

- [rq1_holdout_per_holdout_summary.csv](/Users/xuyifei/NJU/repos/TOSE/rq_results/rq1/summary/rq1_holdout_per_holdout_summary.csv)
- [rq1_holdout_per_holdout_summary.json](/Users/xuyifei/NJU/repos/TOSE/rq_results/rq1/summary/rq1_holdout_per_holdout_summary.json)
- [rq1_holdout_system_summary.csv](/Users/xuyifei/NJU/repos/TOSE/rq_results/rq1/summary/rq1_holdout_system_summary.csv)
- [rq1_holdout_system_summary.json](/Users/xuyifei/NJU/repos/TOSE/rq_results/rq1/summary/rq1_holdout_system_summary.json)

说明：

- 当前 `RQ1` summary 也会一并导出派生列 `utility = 100 - AR`，便于和 `RQ3` 对齐回看，但 `RQ1` 的核心评价仍以 `FN/FP/MTD/F1` 为主。

`GROUP` 的 holdout 训练结果输出在：

- `rq_results/rq1/<system>/holdout_*/`

baseline 的统一训练和逐 holdout 检测输出在：

- `rq_results/rq1/baseline_methods/<system>/`

## Current Official Results

当前 system-level 正式汇总如下：

| system | method | FN | FP | MTD | F1 |
|---|---:|---:|---:|---:|---:|
| rubis | GROUP | 0.00 | 10.83 | 3.46 | 0.9419 |
| rubis | ARD | 0.17 | 88.33 | 8.51 | 0.2047 |
| rubis | SWD | 100.00 | 0.00 | 0.00 | 0.0000 |
| rubis | PRD | 100.00 | 0.00 | 0.00 | 0.0000 |
| rubis | GPD | 94.17 | 5.83 | 0.00 | 0.0000 |
| bsn | GROUP | 0.00 | 2.97 | 4.11 | 0.9847 |
| bsn | ARD | 0.00 | 100.00 | 0.00 | 0.0000 |
| bsn | SWD | 99.67 | 0.33 | 0.00 | 0.0000 |
| bsn | PRD | 0.00 | 100.00 | 0.00 | 0.0000 |
| bsn | GPD | 100.00 | 0.00 | 0.00 | 0.0000 |
| swat | GROUP | 0.00 | 4.17 | 3.53 | 0.9787 |
| swat | ARD | 0.00 | 74.50 | 1.00 | 0.3830 |
| swat | SWD | 98.33 | 1.67 | 0.00 | 0.0000 |
| swat | PRD | 100.00 | 0.00 | 0.00 | 0.0000 |
| swat | GPD | 86.17 | 9.33 | 144.62 | 0.0835 |
| wadi | GROUP | 0.83 | 0.00 | 8.79 | 0.9958 |
| wadi | ARD | 0.00 | 99.33 | 0.67 | 0.0132 |
| wadi | SWD | 100.00 | 0.00 | 0.00 | 0.0000 |
| wadi | PRD | 100.00 | 0.00 | 0.00 | 0.0000 |
| wadi | GPD | 89.67 | 8.50 | 74.00 | 0.0355 |

## Interpretation

当前结论：

- `GROUP` 是四个 system 上唯一整体稳定的方法。
- `bsn` 在纳入 `sensor_index` 分区后，`GROUP` 的 `FP` 已降到 `2.97%`。
- `wadi` 上 `GROUP` 最强，`FP=0`，`FN=0.83`。
- `rubis` 和 `swat` 上 `GROUP` 也明显优于其余四个 baseline。
- 当前这套协议下，`SWD`、`PRD`、`GPD` 大多体现为高 `FN`，`ARD` 大多体现为高 `FP`。

## Related Results

GROUP 四聚类算法内部对比仍保留在单独矩阵中：

- [detection_matrix_summary.csv](/Users/xuyifei/NJU/repos/TOSE/detection_results/summary/detection_matrix_summary.csv)
- [detection_matrix_summary.json](/Users/xuyifei/NJU/repos/TOSE/detection_results/summary/detection_matrix_summary.json)
- 重跑脚本：[run_rq1_detection_matrix.py](/Users/xuyifei/NJU/repos/TOSE/scripts/run_rq1_detection_matrix.py)

当前默认最佳 `learned_distributions.yaml` 对应的最佳算法为：

| System | Best Algorithm | Cluster Count | Silhouette |
|---|---|---:|---:|
| rubis | hdbscan | 3 | 0.9915 |
| bsn | hdbscan | 3 | 0.9866 |
| swat | gmm | 3 | 0.9990 |
| wadi | mean_shift | 3 | 0.7061 |

## Verification

本轮结构收敛后，RQ1 相关建议回归命令为：

```bash
python3 -m unittest \
  tests.test_rq1_holdout_dataset \
  tests.test_rq1_holdout_runner \
  tests.test_sensor_partitioned_clustering \
  tests.test_context_conditioned_detection

python3 -m compileall \
  rq_methods/holdout_dataset.py \
  rq_methods/holdout_runner.py \
  scripts/build_rq1_holdout_dataset.py \
  scripts/build_rq1_holdout_group_distributions.py \
  scripts/run_rq1_holdout_pipeline.py \
  scripts/run_rq1_methods_matrix.py \
  tests/test_rq1_holdout_dataset.py \
  tests/test_rq1_holdout_runner.py
```
