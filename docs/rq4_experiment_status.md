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

- 检测流程完全复用当前 `GROUP` 检测矩阵。
- 辨识阶段对每个 system 分别读取对应算法的 `learned_distributions_<algorithm>.yaml`。
- `ARI` 基于 `data/<system>/identity` 的辨识数据重新计算：
  - `rubis/swat/wadi`: 真值标签为 `norm_label`
  - `bsn`: 真值标签为 `sensor_index + norm_label`

## Code Paths

- ARI helper: [rq4_ari.py](/Users/xuyifei/NJU/repos/TOSE/rq_methods/rq4_ari.py)
- Runner: [rq4_runner.py](/Users/xuyifei/NJU/repos/TOSE/rq_methods/rq4_runner.py)
- CLI: [run_rq4_group_algorithms_matrix.py](/Users/xuyifei/NJU/repos/TOSE/scripts/run_rq4_group_algorithms_matrix.py)

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

## Verification

```bash
python3 -m unittest tests.test_rq4_runner
python3 -m compileall rq_methods/rq4_ari.py rq_methods/rq4_runner.py scripts/run_rq4_group_algorithms_matrix.py tests/test_rq4_runner.py
```
