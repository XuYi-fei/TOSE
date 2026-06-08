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
7. 已新增统一矩阵脚本：
   - [scripts/run_rq1_detection_matrix.py](/Users/xuyifei/NJU/repos/TOSE/scripts/run_rq1_detection_matrix.py)

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
3. 若 learned YAML 顶层包含 `context_calibration_model`，则先按 identity 学到的上下文-均值关系，对候选 cluster distribution 的位置参数做线性平移。
4. 对平移后的候选分布分别计算双侧边缘概率，并用 `max_p_value` 选择“最能解释该点”的簇分布。
5. 若该最大边缘概率 `< alpha`，该点记为 raw anomaly，其中默认 `alpha` 由 `sigma_threshold=3.0` 推导得到，约为 `0.0027`。
6. 在第 `n` 个已观测点时，允许累计 raw anomaly 数取 `Binomial(n, alpha)` 在置信度 `0.99` 下的一侧上界。
7. 只有当累计 raw anomaly 数 `>` 该上界时，才记为真正报警。

统一批量重跑入口：

```bash
python3 scripts/run_rq1_detection_matrix.py
```

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
| bsn | SWD | 200 | 56 | 144 | 0 | 72.00 | 0.00 | 13.32 | 0.67 |
| bsn | ARD | 200 | 47 | 153 | 0 | 76.50 | 0.00 | 4.91 | 0.23 |
| bsn | PRD | 200 | 200 | 0 | 0 | 0.00 | 0.00 | 14.96 | 2.66 |
| bsn | GPD | 200 | 190 | 0 | 10 | 0.00 | 5.00 | 66.23 | 11.60 |
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
- `bsn`: `PRD` 当前最好；`SWD`、`ARD` 高 FP，`GPD` 有少量 FN 且 MTD 偏高。
- `swat`: `PRD` 当前最好，`SWD` 接近可用，`ARD` 高 FP。
- `wadi`: `SWD` 当前最好；`PRD` 高 FN，`ARD` 高 FP。

## Current Interpretation

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
