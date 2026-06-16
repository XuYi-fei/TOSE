# RQ3 Experiment Status

## Goal

RQ3 在 RQ1 的正式 holdout 协议基础上，统计五种方法在四个 subject system 上的两项实用性指标：

- `异常率`
- `utility`

方法集合与 RQ1 完全一致：

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

## Official Protocol

RQ3 不单独定义新的训练/检测流程，而是直接复用 RQ1 的正式协议：

- `GROUP` 按 `holdout_*` 单元分别训练并检测。
- `SWD`、`ARD`、`PRD`、`GPD` 仍按 RQ1 的 system-level 一次训练、多 holdout 回归测试方式执行。
- RQ3 只在 RQ1 已完成的 trace 级检测结果之上重新汇总 `异常率` 与 `utility`。

## Metric Definition

当前实现与 ASE 中已明确落地的 `AR` 定义保持一致：

- `异常率 = AR = abnormal_time / abnormal_total_time * 100`

其中：

- `TP` trace 的 `abnormal_time` 为从 `abn1_start_time` 到首次有效报警之间的异常持续时间。
- `FN` trace 的 `abnormal_time` 为异常段全部未被发现的持续时间。
- `abnormal_total_time` 为所有含异常 trace 的异常总时长。

当前 `utility` 采用 `AR` 的互补量：

- `utility = 100 - AR`

这使得：

- 异常越早被发现，`AR` 越低，`utility` 越高。
- 若异常从未被发现，则 `AR` 趋近于 `100`，`utility` 趋近于 `0`。

## Code Paths

- Runner: [rq3_runner.py](/Users/xuyifei/NJU/repos/TOSE/rq_methods/rq3_runner.py)
- CLI: [run_rq3_methods_matrix.py](/Users/xuyifei/NJU/repos/TOSE/scripts/run_rq3_methods_matrix.py)
- Shared metric helper: [metrics.py](/Users/xuyifei/NJU/repos/TOSE/rq_methods/metrics.py)
- RQ1 official runner: [holdout_runner.py](/Users/xuyifei/NJU/repos/TOSE/rq_methods/holdout_runner.py)

## Execution

```bash
python3 scripts/run_rq3_methods_matrix.py \
  --data-root data_rq1_holdout \
  --learned-root clustering_results_rq1_holdout \
  --output-dir rq_results/rq3 \
  --baseline-identity-root data
```

## Outputs

- `rq_results/rq3/summary/rq3_per_holdout_summary.csv`
- `rq_results/rq3/summary/rq3_per_holdout_summary.json`
- `rq_results/rq3/summary/rq3_system_summary.csv`
- `rq_results/rq3/summary/rq3_system_summary.json`

## Current Status

- `RQ3` runner 已接入当前规范化流程。
- `GROUP` 链路不再把 `AR` 固定写成 `0.0`，而是基于 trace 级异常时长真实聚合。
- 已基于正式 `RQ1` 协议完成一轮 `RQ3` 汇总结果重跑。

## Current Official Results

当前 system-level 正式汇总如下：

| system | method | AR | utility | FN | FP |
|---|---:|---:|---:|---:|---:|
| bsn | ARD | 0.0000 | 100.0000 | 0.00 | 100.00 |
| bsn | GPD | 24.9062 | 75.0938 | 100.00 | 0.00 |
| bsn | GROUP | 0.5625 | 99.4375 | 0.00 | 2.97 |
| bsn | PRD | 0.0000 | 100.0000 | 0.00 | 100.00 |
| bsn | SWD | 24.8189 | 75.1811 | 99.67 | 0.33 |
| rubis | ARD | 0.6373 | 99.3627 | 0.17 | 88.33 |
| rubis | GPD | 0.0000 | 100.0000 | 94.17 | 5.83 |
| rubis | GROUP | 4.6304 | 95.3696 | 0.00 | 10.83 |
| rubis | PRD | 0.0000 | 100.0000 | 100.00 | 0.00 |
| rubis | SWD | 0.0000 | 100.0000 | 100.00 | 0.00 |
| swat | ARD | 0.0527 | 99.9473 | 0.00 | 74.50 |
| swat | GPD | 26.4104 | 73.5896 | 86.17 | 9.33 |
| swat | GROUP | 0.3946 | 99.6054 | 0.00 | 4.17 |
| swat | PRD | 32.9159 | 67.0841 | 100.00 | 0.00 |
| swat | SWD | 31.9898 | 68.0102 | 98.33 | 1.67 |
| wadi | ARD | 0.0027 | 99.9973 | 0.00 | 99.33 |
| wadi | GPD | 30.1115 | 69.8885 | 89.67 | 8.50 |
| wadi | GROUP | 2.1967 | 97.8033 | 0.83 | 0.00 |
| wadi | PRD | 33.1401 | 66.8599 | 100.00 | 0.00 |
| wadi | SWD | 33.1401 | 66.8599 | 100.00 | 0.00 |

## Interpretation

当前结果体现出两类现象：

- `GROUP` 是唯一在四个 system 上同时兼顾低 `AR` 和可接受 `FP/FN` 的方法。
- 若某个方法几乎从不报警，则 `AR` 会非常高，`utility` 会明显下降；这在 `SWD`、`PRD`、`GPD` 上尤其明显。
- `ARD` 在 `rubis`、`swat`、`wadi` 上虽然 `AR` 很低、`utility` 很高，但这是由极高 `FP` 换来的，因此不能单独用 `utility` 判断方法优劣。
- `GROUP` 在 `bsn`、`swat`、`wadi` 上同时维持了较低 `AR` 与较高 `utility`，在 `rubis` 上也明显优于多数 baseline。

## Verification

```bash
python3 -m unittest \
  tests.test_rq1_holdout_runner \
  tests.test_rq2_holdout_runner \
  tests.test_rq3_runner \
  tests.test_algorithm_specific_outputs \
  tests.test_bocpd_detection_mode

python3 -m compileall \
  rq_methods \
  anomaly_detection/core \
  scripts/run_rq3_methods_matrix.py \
  tests/test_rq1_holdout_runner.py \
  tests/test_rq2_holdout_runner.py \
  tests/test_rq3_runner.py \
  tests/test_algorithm_specific_outputs.py \
  tests/test_bocpd_detection_mode.py
```
