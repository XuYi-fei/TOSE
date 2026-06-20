# RQ4 Experiment Status

## Goal

RQ4 只使用 `GROUP` 方法，但在辨识阶段分别使用四种聚类算法：

- `hdbscan`
- `gmm`
- `affinity_propagation`
- `mean_shift`

在每组检测结果后额外输出：

- `ARI (Adjusted Rand Index)`

用于衡量聚类质量。

## Official Protocol

- 检测流程默认完全复用当前 `GROUP` 检测矩阵的同一套配置与同一条执行链路。
- `RQ4` 默认会重新调用 `scripts/run_rq1_detection_matrix.py` 中的 `evaluate_system_algorithm(...)`，保证共享的 `GROUP × 聚类算法` 检测统计与 `RQ1` 四算法矩阵来源一致。
- 只有在显式传入 `--reuse-detection-results` 时，才会直接复用现有 `detection_results/<system>/detection_results_<algorithm>.json`。
- 辨识阶段对每个 system 分别读取对应算法的 `learned_distributions_<algorithm>.yaml`。
- `ARI` 基于 `data/<system>/identity` 的辨识数据重新计算：
  - `rubis/swat/wadi`: 真值标签为 `norm_label`
  - `bsn`: 真值标签为 `sensor_index + norm_label`

## Code Paths

- ARI helper: [rq4_ari.py](/Users/xuyifei/NJU/repos/TOSE/rq_methods/rq4_ari.py)
- Shared detection result loader: [detection_matrix_results.py](/Users/xuyifei/NJU/repos/TOSE/rq_methods/detection_matrix_results.py)
- Consistency checker: [rq4_consistency.py](/Users/xuyifei/NJU/repos/TOSE/rq_methods/rq4_consistency.py)
- Runner: [rq4_runner.py](/Users/xuyifei/NJU/repos/TOSE/rq_methods/rq4_runner.py)
- CLI: [run_rq4_group_algorithms_matrix.py](/Users/xuyifei/NJU/repos/TOSE/scripts/run_rq4_group_algorithms_matrix.py)
- Check script: [check_rq4_matches_rq1_matrix.py](/Users/xuyifei/NJU/repos/TOSE/scripts/check_rq4_matches_rq1_matrix.py)

## Outputs

- `rq_results/rq4/summary/rq4_group_algorithms_summary.csv`
- `rq_results/rq4/summary/rq4_group_algorithms_summary.json`

## Current Official Results

当前独立 `GROUP × 4种聚类算法` 矩阵如下：

| system | algorithm | ARI | cluster_count | TP | FP | FN | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| rubis | hdbscan | 1.0000 | 3 | 175 | 25 | 0 | 0.8750 | 1.0000 | 0.9333 |
| rubis | gmm | 1.0000 | 3 | 175 | 25 | 0 | 0.8750 | 1.0000 | 0.9333 |
| rubis | affinity_propagation | 0.2993 | 504 | 198 | 2 | 0 | 0.9900 | 1.0000 | 0.9950 |
| rubis | mean_shift | 0.9051 | 6 | 187 | 13 | 0 | 0.9350 | 1.0000 | 0.9664 |
| bsn | hdbscan | 1.0000 | 3 | 196 | 4 | 0 | 0.9800 | 1.0000 | 0.9899 |
| bsn | gmm | 1.0000 | 3 | 196 | 4 | 0 | 0.9800 | 1.0000 | 0.9899 |
| bsn | affinity_propagation | 0.3669 | 511 | 197 | 3 | 0 | 0.9850 | 1.0000 | 0.9924 |
| bsn | mean_shift | 0.9881 | 3 | 196 | 4 | 0 | 0.9800 | 1.0000 | 0.9899 |
| swat | hdbscan | 0.0300 | 68 | 196 | 4 | 0 | 0.9800 | 1.0000 | 0.9899 |
| swat | gmm | 1.0000 | 3 | 190 | 10 | 0 | 0.9500 | 1.0000 | 0.9744 |
| swat | affinity_propagation | 0.2934 | 1492 | 200 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| swat | mean_shift | 1.0000 | 3 | 190 | 10 | 0 | 0.9500 | 1.0000 | 0.9744 |
| wadi | hdbscan | 0.1576 | 14 | 192 | 0 | 8 | 1.0000 | 0.9600 | 0.9796 |
| wadi | gmm | 0.6295 | 6 | 194 | 0 | 6 | 1.0000 | 0.9700 | 0.9848 |
| wadi | affinity_propagation | 0.0866 | 26 | 192 | 0 | 8 | 1.0000 | 0.9600 | 0.9796 |
| wadi | mean_shift | 1.0000 | 3 | 194 | 0 | 6 | 1.0000 | 0.9700 | 0.9848 |

## Interpretation

当前 `RQ4` 的关键现象是：

- `ARI` 与最终检测效果并不总是同向。
- `rubis`、`bsn` 上，`hdbscan/gmm` 的 `ARI=1.0`，但检测效果不一定优于 `affinity_propagation`。
- `swat` 上，`affinity_propagation` 的 `ARI` 很低，但在当前检测数据上反而达到了 `TP=200, FP=0, FN=0`。
- `wadi` 上，`mean_shift` 的 `ARI=1.0` 且检测效果最好，是当前最一致的一组。
- `cluster_count` 也很关键：`affinity_propagation` 在多个 system 上会产生极多簇，这说明它虽然能提升部分检测指标，但聚类语义本身并不稳定。

## Consistency Constraint

- `RQ4` 与 `RQ1` 正式 holdout 协议不是同一个实验，不要求数值一致。
- 但 `RQ4` 与 `detection_results/summary/detection_matrix_summary.csv` 共享的 `GROUP × 4种聚类算法` 部分，应该来自同一批检测执行结果。
- 因此当前规范是：默认重跑并对齐 `RQ1` 四算法 GROUP 矩阵；只有显式要求快速复用旧 JSON 时，才允许产生与该矩阵不一致的独立结果。
- 当 `RQ4` 走 `--reuse-detection-results` 时，会与 `RQ1 --rebuild-from-existing-results` 共享同一套标准结果读取逻辑。
- 当前也提供显式校验命令，用于检查两份 summary 的共享字段是否完全一致：

```bash
python3 scripts/check_rq4_matches_rq1_matrix.py
```

## Verification

```bash
python3 -m unittest tests.test_detection_matrix_results tests.test_rq4_runner tests.test_rq1_detection_matrix tests.test_rq4_consistency
python3 scripts/check_rq4_matches_rq1_matrix.py
python3 -m compileall rq_methods/detection_matrix_results.py rq_methods/rq4_consistency.py rq_methods/rq4_runner.py scripts/check_rq4_matches_rq1_matrix.py scripts/run_rq1_detection_matrix.py tests/test_detection_matrix_results.py tests/test_rq4_runner.py tests/test_rq1_detection_matrix.py tests/test_rq4_consistency.py
```
