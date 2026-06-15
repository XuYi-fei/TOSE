# RQ1 Experiment Status

## Goal

RQ1 当前目标是评估：

1. 不同聚类算法在四个 subject system 上学到的辨识结果是否稳定。
2. 将这些辨识结果接入统一异常检测框架后，`fp` / `fn` 表现如何。
3. 高 `fp` 或高 `fn` 的主要原因来自哪里：辨识分布、abnormal 数据构造，还是当前评估口径。

本轮 RQ1 使用的四个 subject system：

- `rubis`
- `bsn`
- `swat`
- `wadi`

本轮 RQ1 使用的四个聚类算法：

- `hdbscan`
- `gmm`
- `affinity_propagation`
- `mean_shift`

最终目标是形成 `4 x 4 = 16` 组辨识-检测结果矩阵。

## Holdout Reconstruction

2026-06-15 起，RQ1 只保留一套唯一的 holdout 评估协议。旧的两套 RQ1 runner 已废弃，不再作为正式结果来源。

当前唯一有效的 RQ1 协议：

- 测试数据完全由已有 `identity` 段重新拼接生成。
- abnormal trace 的异常段始终位于最后一段，评估口径仍使用文件名中的 `abn1_start_time`。
- `rubis`、`swat`、`wadi` 的 holdout 单元是 identity 文件名中的 `norm1/norm2/norm3`。
- `bsn` 的 holdout 单元是 `sensor_index + norm_label`，例如 `sensor3_norm2`。
- 对某个 holdout 单元 `u`：
  - holdout abnormal 数据的最后一段只使用 `{u}`
  - abnormal 前缀由非 `{u}` 的 identity 分布段自由拼接
- `GROUP`：
  - 对每个 holdout 单元单独训练
  - 训练 identity 使用该 holdout 目录下的 `identity`
  - 测试只测该 holdout 目录下的 `abnormal`
- `SWD`、`ARD`、`PRD`、`GPD`：
  - 每个 system 只训练一次
  - 统一使用 `data/<system>/identity` 训练
  - 对该 system 下所有 holdout abnormal 逐组测试并聚合

对应标准化脚本：

- [build_rq1_lodo_dataset.py](/Users/xuyifei/NJU/repos/TOSE/scripts/build_rq1_lodo_dataset.py)
- [build_rq1_lodo_group_distributions.py](/Users/xuyifei/NJU/repos/TOSE/scripts/build_rq1_lodo_group_distributions.py)
- [run_rq1_methods_matrix.py](/Users/xuyifei/NJU/repos/TOSE/scripts/run_rq1_methods_matrix.py)
- [run_rq1_lodo_pipeline.py](/Users/xuyifei/NJU/repos/TOSE/scripts/run_rq1_lodo_pipeline.py)

相关实现：

- [rq_methods/lodo_dataset.py](/Users/xuyifei/NJU/repos/TOSE/rq_methods/lodo_dataset.py)
- [rq_methods/holdout_runner.py](/Users/xuyifei/NJU/repos/TOSE/rq_methods/holdout_runner.py)

holdout 数据与结果目录：

- `data_rq1_lodo/`
- `clustering_results_rq1_holdout/`
- `rq_results/rq1/`

本轮 holdout 数量：

- `rubis`: 3
- `bsn`: 18
- `swat`: 3
- `wadi`: 3

## Official RQ1 Protocol

2026-06-15 起，RQ1 只承认这一套协议的结果：

- holdout 数据统一来自 `data_rq1_lodo/`
- `GROUP` 对每个 `holdout_*` 单独训练，再测试该 holdout 的 abnormal 数据
- `SWD`、`ARD`、`PRD`、`GPD` 对每个 system 只训练一次，训练集固定为 `data/<system>/identity`
- baseline 训练完成后，对该 system 下全部 holdout abnormal 数据逐组测试并聚合

旧的两套结果现在都只保留作历史调试痕迹，不再作为论文或实验结论来源：

- 旧的“直接基于 `data/<system>/abnormal` 的统一五方法矩阵”
- 旧的“baseline 也跟着每个 holdout 重训”的 LODO 五方法矩阵

当前唯一正式入口：

```bash
python3 scripts/run_rq1_methods_matrix.py \
  --data-root data_rq1_lodo \
  --output-dir rq_results/rq1 \
  --learned-root clustering_results_rq1_holdout \
  --baseline-identity-root data
```

当前唯一正式汇总文件：

- [rq1_holdout_per_holdout_summary.csv](/Users/xuyifei/NJU/repos/TOSE/rq_results/rq1/summary/rq1_holdout_per_holdout_summary.csv)
- [rq1_holdout_per_holdout_summary.json](/Users/xuyifei/NJU/repos/TOSE/rq_results/rq1/summary/rq1_holdout_per_holdout_summary.json)
- [rq1_holdout_system_summary.csv](/Users/xuyifei/NJU/repos/TOSE/rq_results/rq1/summary/rq1_holdout_system_summary.csv)
- [rq1_holdout_system_summary.json](/Users/xuyifei/NJU/repos/TOSE/rq_results/rq1/summary/rq1_holdout_system_summary.json)

## Current Official Results

本轮按新协议重跑后的 system-level 汇总如下：

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

当前结论：

- `GROUP` 是四个 system 上唯一整体稳定的方法。
- `bsn` 在按 `sensor` 分区后，`GROUP` 的 `FP` 已稳定下降到 `2.97%`，不再是主失败案例。
- `wadi` 上 `GROUP` 当前最佳，`FP=0`，`FN=0.83`。
- `rubis` 和 `swat` 上 `GROUP` 也显著优于其余方法。
- 这套新协议下，`SWD/PRD/GPD` 大多表现为高 `FN`，`ARD` 大多表现为高 `FP`。

## Current Scope

当前 RQ1 已完成：

1. 统一四个 system 的聚类配置，正式支持按算法分别导出 `learned_distributions_<algorithm>.yaml`。
2. 已将辨识主链路重构为两阶段：
   `stage-1` 先对 identity 段的 `mu` 做自由聚类，`stage-2` 再对每个簇内原始样本重新选择更合适的分布族。
3. 已将检测主链路改为读取异构 learned distributions，并按 `max_p_value` 聚合各簇的边缘概率。
4. trace 级报警仍保留统一框架，但容忍次数现在改为按二项分布一侧置信上界计算。
5. 已为新语义补齐标准配置字段、YAML 导出格式以及核心回归测试。
6. 已把“上下文条件化 identity 建模”接入统一主链路：
   - 解析器可为每个 identity segment 提取 `context_key/context_features`
   - `learned_distributions_<algorithm>.yaml` 顶层可导出 `context_calibration_model`
   - 检测时先做 exact/nearest 上下文匹配，再用线性 `mu` 校准对 cluster 分布做位置平移
7. 已把 `bsn` 的 `sensor_index` 纳入统一主链路的 stage-1 分区键：
   - 辨识阶段先按 `sensor_index` 分区，再在分区内做自由聚类
   - learned distributions 会额外导出 `partition_context_key/partition_context_features`
   - 检测阶段先按 `sensor_index` 做 `partition_exact` 候选筛选，再在该 `sensor` 对应的 learned distributions 内比较尾概率
8. 已新增统一矩阵脚本：
   - [scripts/run_rq1_detection_matrix.py](/Users/xuyifei/NJU/repos/TOSE/scripts/run_rq1_detection_matrix.py)
9. 已新增论文 RQ1 五方法统一 runner：
   - [scripts/run_rq1_methods_matrix.py](/Users/xuyifei/NJU/repos/TOSE/scripts/run_rq1_methods_matrix.py)
   - 方法维度统一为 `SWD`、`ARD`、`PRD`、`GPD`、`GROUP`
   - 其中 `GROUP` 对每个 holdout 单元读取 `clustering_results_rq1_holdout/<system>/holdout_*/learned_distributions.yaml`
   - baseline 方法不再按 holdout 重训，而是每个 system 只训练一次

## Standard Pipeline

### Clustering

正式聚类入口统一为：

```bash
python3 cluster.py --config configs/<system>_clustering_config.yaml
```

当前正式配置：

- [rubis_clustering_config.yaml](/Users/xuyifei/NJU/repos/TOSE/configs/rubis_clustering_config.yaml)
- [bsn_clustering_config.yaml](/Users/xuyifei/NJU/repos/TOSE/configs/bsn_clustering_config.yaml)
- [swat_clustering_config.yaml](/Users/xuyifei/NJU/repos/TOSE/configs/swat_clustering_config.yaml)
- [wadi_clustering_config.yaml](/Users/xuyifei/NJU/repos/TOSE/configs/wadi_clustering_config.yaml)

四个正式配置现在都启用了：

- `save_learned_distributions: true`
- `save_per_algorithm_distributions: true`

同时统一声明两阶段分布建模：

- `distribution_modeling.stage1_clustering_feature: mu`
- `distribution_modeling.candidate_distributions: [norm, lognorm, gamma, weibull_min]`
- `distribution_modeling.normality_alpha: 0.05`
- `distribution_modeling.enable_context_calibration: true`
- `distribution_modeling.context_modeling_method: linear_mu`

其中 `bsn` 额外启用：

- `distribution_modeling.partition_context_features: [sensor_index]`

因此每个 system 都会导出：

- `clustering_results/<system>/learned_distributions.yaml`
- `clustering_results/<system>/learned_distributions_hdbscan.yaml`
- `clustering_results/<system>/learned_distributions_gmm.yaml`
- `clustering_results/<system>/learned_distributions_affinity_propagation.yaml`
- `clustering_results/<system>/learned_distributions_mean_shift.yaml`

### Detection

RQ1 的 16 组检测使用通用检测框架，读取每个算法单独导出的 learned distributions。

检测主入口：

```bash
python3 detect.py --config configs/<system>_detection_config.yaml
```

但 RQ1 的 16 组检测不是只读默认 `learned_distributions.yaml`，而是按算法分别读取：

- `clustering_results/<system>/learned_distributions_hdbscan.yaml`
- `clustering_results/<system>/learned_distributions_gmm.yaml`
- `clustering_results/<system>/learned_distributions_affinity_propagation.yaml`
- `clustering_results/<system>/learned_distributions_mean_shift.yaml`

输出文件落在：

- `detection_results/<system>/detection_report_<algorithm>.md`
- `detection_results/<system>/detection_results_<algorithm>.json`
- `detection_results/<system>/detection_results_<algorithm>.csv`

当前正式 detection config 统一使用：

- `detection.sigma_threshold: 3.0`
- `detection.aggregation_method: max_p_value`
- `detection.alarm_count_policy: binomial_confidence_bound`
- `detection.trace_alarm_confidence: 0.99`
- `detection.context_matching_strategy: nearest`
- `detection.apply_context_mu_shift: true`

即点级检测和 trace 级触发都围绕边缘概率工作：

1. 对每个点，先由系统解析器提取该点所属的 `context_key/context_features`。
2. 检测器先在 learned distributions 中做 exact/nearest 上下文匹配，缩小候选簇集合。
3. 对于 `bsn`，若 learned YAML 声明了 `partition_context_features: [sensor_index]`，则检测器优先按 `sensor_index` 做 `partition_exact` 路由。
4. 若 learned YAML 顶层包含 `context_calibration_model`，则先按 identity 学到的上下文-均值关系，对候选 cluster distribution 的位置参数做线性平移。
5. 对平移后的候选分布分别计算双侧边缘概率，并用 `max_p_value` 选择“最能解释该点”的簇分布。
6. 若该最大边缘概率 `< alpha`，该点记为 raw anomaly，其中默认 `alpha` 由 `sigma_threshold=3.0` 推导得到，约为 `0.0027`。
7. 在第 `n` 个已观测点时，允许累计 raw anomaly 数取 `Binomial(n, alpha)` 在置信度 `0.99` 下的一侧上界。
8. 只有当累计 raw anomaly 数 `>` 该上界时，才记为真正报警。

统一批量重跑入口：

```bash
python3 scripts/run_rq1_detection_matrix.py
```

### Unified RQ1 Method Matrix

论文 RQ1 横向对比入口统一为：

```bash
python3 scripts/run_rq1_methods_matrix.py --output-dir rq_results/rq1
```

该入口会同时运行：

- `SWD`
- `ARD`
- `PRD`
- `GPD`
- `GROUP`

输出文件：

- `rq_results/rq1/baseline_methods/<system>/<METHOD>.json`
- `rq_results/rq1/baseline_methods/<system>/detection_results_<METHOD>.json`
- `rq_results/rq1/<system>/GROUP/detection_report_GROUP.md`
- `rq_results/rq1/<system>/GROUP/detection_results_GROUP.json`
- `rq_results/rq1/<system>/GROUP/detection_results_GROUP.csv`
- `rq_results/rq1/summary/rq1_methods_summary.csv`
- `rq_results/rq1/summary/rq1_methods_summary.json`

`GROUP` 的聚类选择规则：

- 只读取 `clustering_results/<system>/learned_distributions.yaml`。
- 该文件由聚类阶段根据当前最佳聚类方法导出。
- 不读取 `learned_distributions_hdbscan.yaml`、`learned_distributions_gmm.yaml` 等算法后缀文件。
- 如果要重新比较四个聚类算法本身，仍使用 [scripts/run_rq1_detection_matrix.py](/Users/xuyifei/NJU/repos/TOSE/scripts/run_rq1_detection_matrix.py)。

### Headless Plotting

当前机器上，为了稳定生成聚类图，实际运行时使用：

```bash
MPLBACKEND=Agg MPLCONFIGDIR=tmp-test/mplconfig python3 cluster.py --config ...
```

这只是执行环境参数，不属于实验配置本身。

## Code Paths

RQ1 相关代码入口和关键落点：

- 聚类 CLI: [cluster.py](/Users/xuyifei/NJU/repos/TOSE/cluster.py)
- 聚类执行主逻辑: [cluster_analysis/cli.py](/Users/xuyifei/NJU/repos/TOSE/cluster_analysis/cli.py)
- 聚类引擎: [cluster_analysis/core/engine.py](/Users/xuyifei/NJU/repos/TOSE/cluster_analysis/core/engine.py)
- 簇内分布拟合: [cluster_analysis/core/distribution_fitting.py](/Users/xuyifei/NJU/repos/TOSE/cluster_analysis/core/distribution_fitting.py)
- 聚类结果导出: [cluster_analysis/visualization/reporter.py](/Users/xuyifei/NJU/repos/TOSE/cluster_analysis/visualization/reporter.py)
- 检测 CLI: [detect.py](/Users/xuyifei/NJU/repos/TOSE/detect.py)
- 检测器: [anomaly_detection/core/detector.py](/Users/xuyifei/NJU/repos/TOSE/anomaly_detection/core/detector.py)
- 检测评估器: [anomaly_detection/core/evaluator.py](/Users/xuyifei/NJU/repos/TOSE/anomaly_detection/core/evaluator.py)
- 检测结果导出: [anomaly_detection/visualization/reporter.py](/Users/xuyifei/NJU/repos/TOSE/anomaly_detection/visualization/reporter.py)

系统解析器：

- RUBIS: [common/adapters/rubis.py](/Users/xuyifei/NJU/repos/TOSE/common/adapters/rubis.py)
- BSN: [common/adapters/bsn.py](/Users/xuyifei/NJU/repos/TOSE/common/adapters/bsn.py)
- SWAT: [common/adapters/swat.py](/Users/xuyifei/NJU/repos/TOSE/common/adapters/swat.py)
- WADI: [common/adapters/wadi.py](/Users/xuyifei/NJU/repos/TOSE/common/adapters/wadi.py)

统一 trace 读取：

- [common/utils/trace_series.py](/Users/xuyifei/NJU/repos/TOSE/common/utils/trace_series.py)

## Current Clustering Outcomes

当前默认 `learned_distributions.yaml` 对应的最佳算法：

| System | Best Algorithm | Cluster Count | Silhouette |
|---|---|---:|---:|
| rubis | hdbscan | 3 | 0.9915 |
| bsn | hdbscan | 3 | 0.9866 |
| swat | gmm | 3 | 0.9990 |
| wadi | mean_shift | 3 | 0.7061 |

对应输出目录：

- [rubis clustering](/Users/xuyifei/NJU/repos/TOSE/clustering_results/rubis)
- [bsn clustering](/Users/xuyifei/NJU/repos/TOSE/clustering_results/bsn)
- [swat clustering](/Users/xuyifei/NJU/repos/TOSE/clustering_results/swat)
- [wadi clustering](/Users/xuyifei/NJU/repos/TOSE/clustering_results/wadi)

## RQ1 Detection Matrix

完整汇总文件：

- [detection_matrix_summary.csv](/Users/xuyifei/NJU/repos/TOSE/detection_results/summary/detection_matrix_summary.csv)
- [detection_matrix_summary.json](/Users/xuyifei/NJU/repos/TOSE/detection_results/summary/detection_matrix_summary.json)

本轮 16 组结果如下。

`fp_rate` 和 `fn_rate` 当前按 trace 级口径计算：

- `fp_rate = FP / total_traces`
- `fn_rate = FN / total_traces`

| System | Algorithm | Clusters | Total | FP | FN | FP Rate | FN Rate |
|---|---|---:|---:|---:|---:|---:|---:|
| rubis | hdbscan | 3 | 200 | 133 | 0 | 0.6650 | 0.0000 |
| rubis | gmm | 3 | 200 | 133 | 0 | 0.6650 | 0.0000 |
| rubis | affinity_propagation | 340 | 200 | 82 | 0 | 0.4100 | 0.0000 |
| rubis | mean_shift | 5 | 200 | 117 | 0 | 0.5850 | 0.0000 |
| bsn | hdbscan | 3 | 200 | 150 | 0 | 0.7500 | 0.0000 |
| bsn | gmm | 3 | 200 | 150 | 0 | 0.7500 | 0.0000 |
| bsn | affinity_propagation | 173 | 200 | 144 | 0 | 0.7200 | 0.0000 |
| bsn | mean_shift | 3 | 200 | 150 | 0 | 0.7500 | 0.0000 |
| swat | hdbscan | 48 | 200 | 26 | 0 | 0.1300 | 0.0000 |
| swat | gmm | 3 | 200 | 32 | 0 | 0.1600 | 0.0000 |
| swat | affinity_propagation | 722 | 200 | 0 | 0 | 0.0000 | 0.0000 |
| swat | mean_shift | 3 | 200 | 32 | 0 | 0.1600 | 0.0000 |
| wadi | hdbscan | 9 | 200 | 94 | 0 | 0.4700 | 0.0000 |
| wadi | gmm | 10 | 200 | 0 | 6 | 0.0000 | 0.0300 |
| wadi | affinity_propagation | 46 | 200 | 0 | 4 | 0.0000 | 0.0200 |
| wadi | mean_shift | 3 | 200 | 180 | 0 | 0.9000 | 0.0000 |

## RQ1 ASE-Style Baseline Matrix

为对齐 `分组oracle实验.xlsx` 中 RQ1 的横向 baseline 对比，已新增独立 baseline 适配层，仿照 ASE25Experiment 的实现接入当前 TOSE 数据目录。

当前迁移口径：

- `rubis`、`swat`、`wadi` 使用单 detector。
- `bsn` 使用 ASE 风格 6 detector MultiDetector，每个 `/g3t1_1` 到 `/g3t1_6` sensor 独立辨识和检测。

## LODO Method Matrix

LODO 五方法统一汇总文件：

- [rq1_lodo_per_holdout_summary.csv](/Users/xuyifei/NJU/repos/TOSE/rq_results/rq1_lodo/summary/rq1_lodo_per_holdout_summary.csv)
- [rq1_lodo_per_holdout_summary.json](/Users/xuyifei/NJU/repos/TOSE/rq_results/rq1_lodo/summary/rq1_lodo_per_holdout_summary.json)
- [rq1_lodo_system_summary.csv](/Users/xuyifei/NJU/repos/TOSE/rq_results/rq1_lodo/summary/rq1_lodo_system_summary.csv)
- [rq1_lodo_system_summary.json](/Users/xuyifei/NJU/repos/TOSE/rq_results/rq1_lodo/summary/rq1_lodo_system_summary.json)

系统级汇总结果：

| System | Method | FN | FP | MTD | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|---:|---:|
| rubis | GROUP | 0.00 | 10.83 | 3.46 | 0.8917 | 1.0000 | 0.9419 |
| rubis | SWD | 33.00 | 0.67 | 5.48 | 0.6633 | 0.6667 | 0.6650 |
| rubis | PRD | 66.67 | 0.00 | 0.33 | 0.3333 | 0.3333 | 0.3333 |
| rubis | GPD | 51.50 | 0.00 | 123.64 | 0.6667 | 0.4850 | 0.5418 |
| rubis | ARD | 0.17 | 88.33 | 8.51 | 0.1152 | 0.9848 | 0.2047 |
| bsn | GROUP | 0.00 | 92.28 | 2.57 | 0.0772 | 0.7222 | 0.1379 |
| bsn | SWD | 32.72 | 1.53 | 5.85 | 0.6575 | 0.6667 | 0.6620 |
| bsn | PRD | 33.33 | 0.00 | 5.28 | 0.6667 | 0.6667 | 0.6667 |
| bsn | GPD | 72.72 | 0.00 | 131.54 | 0.6667 | 0.2728 | 0.3856 |
| bsn | ARD | 0.00 | 100.00 | 0.00 | 0.0000 | 0.0000 | 0.0000 |
| swat | GROUP | 0.00 | 4.17 | 3.53 | 0.9583 | 1.0000 | 0.9787 |
| swat | SWD | 33.00 | 1.33 | 2.71 | 0.6567 | 0.6667 | 0.6616 |
| swat | PRD | 33.33 | 32.33 | 0.67 | 0.3433 | 0.6667 | 0.4467 |
| swat | GPD | 31.83 | 34.67 | 5.93 | 0.3350 | 0.6667 | 0.4425 |
| swat | ARD | 0.00 | 74.50 | 1.00 | 0.2550 | 1.0000 | 0.3830 |
| wadi | GROUP | 0.83 | 0.00 | 8.79 | 1.0000 | 0.9917 | 0.9958 |
| wadi | SWD | 33.00 | 1.00 | 11.15 | 0.6600 | 0.6667 | 0.6633 |
| wadi | PRD | 49.83 | 0.00 | 28.75 | 0.6667 | 0.5017 | 0.5702 |
| wadi | GPD | 31.00 | 7.33 | 17.94 | 0.6167 | 0.6667 | 0.6405 |
| wadi | ARD | 0.00 | 99.33 | 0.67 | 0.0067 | 0.6667 | 0.0132 |

当前结论：

- 在 `rubis`、`swat`、`wadi` 上，`GROUP` 在 LODO 设定下是最优或接近最优方法，尤其 `swat` 和 `wadi` 明显优于四个 baseline。
- `wadi` 的 `GROUP` 结果最稳定，`FP=0`，`FN=0.83`，F1 达到 `0.9958`。
- `rubis` 和 `swat` 的 `GROUP` 仍有少量前缀误报，但已经显著优于 `ARD`，也优于高 `FN` 的 `PRD/GPD`。
- `bsn` 仍然是当前最突出的问题系统：`GROUP` 在新的 LODO 定义下出现了结构性的高 `FP=92.28`。这说明即使 abnormal 后缀严格取自留出分布单元，BSN 的“多传感器联合 trace + 单传感器 holdout 语义”之间仍存在较强的不一致，需要继续单独定位。

一些关键 holdout 观察：

- `rubis/GROUP` 的 3 个 holdout 都选到 `gmm`，且每个 holdout 的 `cluster_count=2`。
- `swat/GROUP` 的 3 个 holdout 都选到 `gmm`，且误报稳定在 `2%`、`5%`、`5.5%` 一带。
- `wadi/GROUP` 的 3 个 holdout 最佳算法并不一致：
  - `norm1`: `gmm`, `cluster_count=4`
  - `norm2`: `mean_shift`, `cluster_count=3`
  - `norm3`: `hdbscan`, `cluster_count=19`
- `bsn/GROUP` 的 18 个 holdout 几乎都选到 `gmm`，但像 `sensor0_norm1`、`sensor0_norm2` 这类 holdout 会直接 `FP=100%`，说明问题不在少数边界 case，而是集中在 BSN 的数据语义和检测口径不匹配。
- BSN trace 的 `sensor_index` 是目标异常 sensor；首次报警必须只来自该目标 sensor 才计为 TP，否则按 FP 处理。

baseline 方法：

- `SWD`: sliding-window mean range detector
- `ARD`: autoregressive residual hypothesis detector
- `PRD`: probability-distribution detector，对应 ASE 中的 `PROB`
- `GPD`: Kalman-style probability detector

代码和入口：

- baseline 包: [baseline_methods](/Users/xuyifei/NJU/repos/TOSE/baseline_methods)
- 统一 runner: [scripts/run_rq1_baseline_matrix.py](/Users/xuyifei/NJU/repos/TOSE/scripts/run_rq1_baseline_matrix.py)
- 回归测试: [tests/test_ase_baseline_adapter.py](/Users/xuyifei/NJU/repos/TOSE/tests/test_ase_baseline_adapter.py)

运行命令：

```bash
python3 scripts/run_rq1_baseline_matrix.py --output-dir baseline_results
```

输出文件：

- `baseline_results/<system>/<METHOD>.json`: baseline 辨识配置
- `baseline_results/<system>/detection_results_<METHOD>.json`: per-trace 检测结果
- [rq1_baseline_summary.csv](/Users/xuyifei/NJU/repos/TOSE/baseline_results/summary/rq1_baseline_summary.csv)
- [rq1_baseline_summary.json](/Users/xuyifei/NJU/repos/TOSE/baseline_results/summary/rq1_baseline_summary.json)

当前 baseline 结果如下。

| System | Method | Total | TP | FP | FN | FP | FN | MTD | AR |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| rubis | SWD | 200 | 200 | 0 | 0 | 0.00 | 0.00 | 0.00 | 0.09 |
| rubis | ARD | 200 | 34 | 166 | 0 | 83.00 | 0.00 | 1.00 | 0.03 |
| rubis | PRD | 200 | 200 | 0 | 0 | 0.00 | 0.00 | 1.00 | 0.19 |
| rubis | GPD | 200 | 200 | 0 | 0 | 0.00 | 0.00 | 0.79 | 0.17 |
| bsn | SWD | 200 | 54 | 146 | 0 | 73.00 | 0.00 | 13.26 | 0.64 |
| bsn | ARD | 200 | 16 | 184 | 0 | 92.00 | 0.00 | 1.00 | 0.03 |
| bsn | PRD | 200 | 56 | 144 | 0 | 72.00 | 0.00 | 7.68 | 0.40 |
| bsn | GPD | 200 | 178 | 0 | 22 | 0.00 | 11.00 | 80.16 | 14.20 |
| swat | SWD | 200 | 199 | 1 | 0 | 0.50 | 0.00 | 6.73 | 0.43 |
| swat | ARD | 200 | 55 | 145 | 0 | 72.50 | 0.00 | 1.00 | 0.03 |
| swat | PRD | 200 | 200 | 0 | 0 | 0.00 | 0.00 | 1.00 | 0.12 |
| swat | GPD | 200 | 186 | 14 | 0 | 7.00 | 0.00 | 11.59 | 0.65 |
| wadi | SWD | 200 | 199 | 1 | 0 | 0.50 | 0.00 | 17.11 | 2.50 |
| wadi | ARD | 200 | 0 | 200 | 0 | 100.00 | 0.00 | 0.00 | 0.00 |
| wadi | PRD | 200 | 11 | 0 | 189 | 0.00 | 94.50 | 76.82 | 24.09 |
| wadi | GPD | 200 | 180 | 20 | 0 | 10.00 | 0.00 | 21.95 | 2.87 |

当前直接结论：

- `rubis`: `SWD`、`PRD`、`GPD` 表现稳定，`ARD` 高 FP。
- `bsn`: 多 detector 口径下 `SWD`、`ARD`、`PRD` 都出现高 FP，`GPD` 无 FP 但 FN 和 MTD 偏高；这比此前单 sensor 口径更接近 ASE baseline 评估方式。
- `swat`: `PRD` 当前最好，`SWD` 接近可用，`ARD` 高 FP。
- `wadi`: `SWD` 当前最好；`PRD` 高 FN，`ARD` 高 FP。

## RQ1 Unified Five-Method Matrix

本节对应论文表格的最终方法维度：`SWD`、`ARD`、`PRD`、`GPD`、`GROUP`。

运行命令：

```bash
python3 scripts/run_rq1_methods_matrix.py --output-dir rq_results/rq1
```

汇总文件：

- [rq1_methods_summary.csv](/Users/xuyifei/NJU/repos/TOSE/rq_results/rq1/summary/rq1_methods_summary.csv)
- [rq1_methods_summary.json](/Users/xuyifei/NJU/repos/TOSE/rq_results/rq1/summary/rq1_methods_summary.json)

当前 `GROUP` 行使用的最佳聚类方法：

| System | GROUP Best Algorithm | Cluster Count |
|---|---|---:|
| rubis | hdbscan | 3 |
| bsn | hdbscan | 3 |
| swat | gmm | 3 |
| wadi | mean_shift | 3 |

2026-06-08 重新聚类并重跑后的五方法矩阵结果：

| System | Method | Total | FP | FN | FP (%) | FN (%) | MTD | AR (%) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| rubis | SWD | 200 | 0 | 0 | 0.00 | 0.00 | 0.00 | 0.09 |
| rubis | ARD | 200 | 166 | 0 | 83.00 | 0.00 | 1.00 | 0.03 |
| rubis | PRD | 200 | 0 | 0 | 0.00 | 0.00 | 1.00 | 0.19 |
| rubis | GPD | 200 | 0 | 0 | 0.00 | 0.00 | 0.79 | 0.17 |
| rubis | GROUP | 200 | 25 | 0 | 12.50 | 0.00 | 3.33 | 0.00 |
| bsn | SWD | 200 | 146 | 0 | 73.00 | 0.00 | 13.26 | 0.64 |
| bsn | ARD | 200 | 184 | 0 | 92.00 | 0.00 | 1.00 | 0.03 |
| bsn | PRD | 200 | 144 | 0 | 72.00 | 0.00 | 7.68 | 0.40 |
| bsn | GPD | 200 | 0 | 22 | 0.00 | 11.00 | 80.16 | 14.20 |
| bsn | GROUP | 200 | 4 | 0 | 2.00 | 0.00 | 5.26 | 0.00 |
| swat | SWD | 200 | 1 | 0 | 0.50 | 0.00 | 6.73 | 0.43 |
| swat | ARD | 200 | 145 | 0 | 72.50 | 0.00 | 1.00 | 0.03 |
| swat | PRD | 200 | 0 | 0 | 0.00 | 0.00 | 1.00 | 0.12 |
| swat | GPD | 200 | 14 | 0 | 7.00 | 0.00 | 11.59 | 0.65 |
| swat | GROUP | 200 | 10 | 0 | 5.00 | 0.00 | 2.58 | 0.00 |
| wadi | SWD | 200 | 1 | 0 | 0.50 | 0.00 | 17.11 | 2.50 |
| wadi | ARD | 200 | 200 | 0 | 100.00 | 0.00 | 0.00 | 0.00 |
| wadi | PRD | 200 | 0 | 189 | 0.00 | 94.50 | 76.82 | 24.09 |
| wadi | GPD | 200 | 20 | 0 | 10.00 | 0.00 | 21.95 | 2.87 |
| wadi | GROUP | 200 | 0 | 6 | 0.00 | 3.00 | 17.76 | 0.00 |

说明：

- baseline 的 `AR` 沿用 ASE 风格 abnormal-rate 统计。
- 当前 `GROUP` 的统一 evaluator 尚未定义与 ASE 完全等价的 `AR`，因此统一表中暂填 `0.00`，不把它解释为 GROUP 的真实异常率。
- 若论文表需要 `GROUP` 的 `AR`，应后续在 `AnomalyEvaluator` 中按 trace 级检测时间补齐同口径统计。
- 本轮已重新运行四个 subject system 的聚类，再运行 [scripts/run_rq1_methods_matrix.py](/Users/xuyifei/NJU/repos/TOSE/scripts/run_rq1_methods_matrix.py) 生成五方法矩阵。
- `GROUP` 行使用聚类阶段按聚类质量选出的默认最佳 learned distributions：`rubis=hdbscan`、`bsn=hdbscan`、`swat=gmm`、`wadi=mean_shift`。
- 已将上述 RQ1 的 `FN/FP/MTD` 填入工作簿副本：`outputs/rq1/分组oracle实验_rq1_filled.xlsx`。
- 本轮曾尝试重跑四聚类算法的完整 GROUP detection matrix；由于 `affinity_propagation` 在 BSN/SWAT 产生数百到上千个簇，检测耗时过高，已终止该长任务，不作为本次 Excel RQ1 填表依据。

## Current Interpretation

### 2026-06-13 BSN Sensor-Partitioned Update

本轮对 `bsn` 做了统一主链路层面的进一步修正：

- clustering 侧新增 `partition_context_features`
- `configs/bsn_clustering_config.yaml` 固定使用 `sensor_index` 作为 stage-1 分区键
- detector 侧优先按 `partition_context_key` 选择候选 learned distributions

已完成的聚焦验证：

- `python3 -m unittest tests.test_sensor_partitioned_clustering tests.test_context_conditioned_detection tests.test_rq1_lodo_dataset tests.test_rq1_lodo_runner`
- `python3 -m compileall common/models/distribution.py anomaly_detection/core/distribution.py anomaly_detection/core/detector.py cluster_analysis/config/config.py cluster_analysis/cli.py cluster_analysis/core/engine.py cluster_analysis/visualization/reporter.py tests/test_sensor_partitioned_clustering.py tests/test_context_conditioned_detection.py`

对新输出结果的抽样确认：

- [detection_results_GROUP.json](/Users/xuyifei/NJU/repos/TOSE/rq_results/rq1_lodo_partitioned_bsn/bsn/holdout_sensor0_norm1/bsn/GROUP/detection_results_GROUP.json)
  - `context_match_strategy = partition_exact`
  - `matched_context_key = sensor_index=0.000000`

这说明当前 `bsn` 检测已经不是“跨 sensor 串配”问题。剩余高 `FP` 的根因已经收敛为：

- 同一 `sensor` 内部，abnormal 前缀中的正常点仍明显偏离该 `sensor` 对应的 learned distributions
- 或者同一 `sensor` 内不同 normal 分布之间仍存在训练/测试漂移，导致尾概率持续偏低

### Direct Observations

- 容错触发后，`rubis`、`bsn`、`swat` 的 `FP` 都明显下降，但 `rubis`、`bsn` 仍然偏高。
- `swat` 中 `affinity_propagation` 在当前口径下达到了 `FP=0, FN=0`，但簇数极高，属于明显碎片化结果。
- `wadi` 中 `gmm` 和 `affinity_propagation` 结果最好，`FP=0`，但分别有 `6` 和 `4` 个 `FN`。
- `wadi` 中 `mean_shift` 对当前 abnormal 数据不适合，`FP` 很高。

### Current Redesign Note

上表仍然对应重构前的一轮正式结果。当前代码已经切换到“两阶段辨识 + 异构分布检测 + 基于 alpha 的 trace 容忍触发”，因此后续重新跑 16 组实验时，应以新链路产出的结果为准。

### 2026-04-22 BSN Context-Conditioned Update

BSN 现已验证接入“上下文匹配 + `mu` 线性校准”的统一主链路。使用当前正式配置重跑后，已确认：

| System | Algorithm | Clusters | Total | TP | FP | FN | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| bsn | hdbscan | 3 | 200 | 196 | 4 | 0 | 0.9800 | 1.0000 | 0.9899 |
| bsn | gmm | 3 | 200 | 196 | 4 | 0 | 0.9800 | 1.0000 | 0.9899 |
| bsn | mean_shift | 3 | 200 | 196 | 4 | 0 | 0.9800 | 1.0000 | 0.9899 |

这说明此前 BSN 的高 `FP` 主要不是“异常前缀被分错 cluster”，而是 identity 中 `offset=0.0225` 与 abnormal 前缀中 `offset=0.025` 的连续上下文漂移没有进入统一模型。现在在标准流程中加入上下文线性校准后，`FP` 已从 `139` 级别降到 `4`。

`bsn + affinity_propagation` 与完整 16 组矩阵仍建议通过 [scripts/run_rq1_detection_matrix.py](/Users/xuyifei/NJU/repos/TOSE/scripts/run_rq1_detection_matrix.py) 统一刷新，因为超多簇结果的检测耗时明显更高。

### Why FP Is High For RUBIS, BSN, SWAT

当前 `FP` 高，不等价于“异常前正常前缀和 identity 分布完全不相似”。

更主要的原因是：

1. 当前评估器使用 trace 级分类。
2. 即使改成容错触发，`rubis` 和 `bsn` 的 abnormal 前缀里 raw anomaly 仍然累积较多，最终依旧会在 `abn1_start_time` 前越过容忍门槛。

对应逻辑见：

- [anomaly_detection/core/evaluator.py](/Users/xuyifei/NJU/repos/TOSE/anomaly_detection/core/evaluator.py)

因此即便容忍了少量 raw anomaly，只要异常前前缀足够长，或者前缀本身已经偏离 identity 分布，依旧会被累计放大成高 trace 级 `FP`。

本轮已确认：

- `rubis` 主要是 trace 级累计效应导致高 `FP`
- `swat` 也是 trace 级累计效应为主
- `bsn` 除了 trace 级累计效应，abnormal 前缀里的 `norm2` 也有明显提前漂移
- BSN 现已在统一框架中被进一步解释为“连续上下文漂移引发的 `mu` 偏移”，而不是简单的错簇问题

## Abnormal Data Sanity Check

当前 abnormal 数据检查结论：

- `rubis abnormal`
  - 最合理
  - 异常前前缀点级误报低
  - `abn1` 异常段很强
- `bsn abnormal`
  - 整体可用
  - abnormal 文件现已补齐到 `200`
  - 且部分 `norm2` 前缀已明显偏离 identity 分布
- `swat abnormal`
  - 结构合理
  - 但异常强度偏弱，很多 `abn1` 只会触发约一半点的异常
- `wadi abnormal`
  - 异常段本身很强
  - 但正常前缀误报偏高
  - 更像是当前 identity / learned distributions 本身较紧，而不只是 abnormal 构造问题

## Known Issues

### 1. Trace-level metric may still inflate FP

当前 RQ1 汇总表中的 `fp_rate` / `fn_rate` 都是 trace 级，不是点级。

如果后续论文或报告需要更细的解释，建议再补两类统计：

1. 点级 `fp_rate` / `fn_rate`
2. 只统计 `abn1` 之后窗口的检测指标

### 2. Highly fragmented clustering can game FP

像 `swat + affinity_propagation` 这类结果，虽然 `FP` 很低，但簇数极高。

这类结果说明：

- 检测边界更宽
- 更容易覆盖正常波动
- 但辨识结果解释性弱，泛化能力也需要额外审查

## Reproduction

### Step 1. Refresh clustering outputs

```bash
MPLBACKEND=Agg MPLCONFIGDIR=tmp-test/mplconfig python3 cluster.py --config configs/rubis_clustering_config.yaml
MPLBACKEND=Agg MPLCONFIGDIR=tmp-test/mplconfig python3 cluster.py --config configs/bsn_clustering_config.yaml
MPLBACKEND=Agg MPLCONFIGDIR=tmp-test/mplconfig python3 cluster.py --config configs/swat_clustering_config.yaml
MPLBACKEND=Agg MPLCONFIGDIR=tmp-test/mplconfig python3 cluster.py --config configs/wadi_clustering_config.yaml
```

### Step 2. Run all 16 detection combinations

当前没有单独的批处理脚本；本轮是通过一个本地 Python 批处理片段直接调用：

- `AnomalyDetector.from_yaml(...)`
- `AnomalyEvaluator(...)`
- `DetectionReporter(...)`

如果 RQ1 后续要反复复现，建议补一个正式脚本，例如：

- `scripts/run_rq1_detection_matrix.py`

## Recommended Next Steps

1. 为 RQ1 补一个正式批处理脚本，避免再次手工拼 16 组实验。
2. 为 RQ1 增加点级指标汇总，和 trace 级指标并行报告。
3. 检查 `swat abnormal` 的异常强度是否需要增强。
4. 检查 `wadi identity` 与 learned distributions 是否过紧，导致正常前缀误报偏高。
