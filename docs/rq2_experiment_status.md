# RQ2 Experiment Status

## Goal

RQ2 当前正式对比三种方法：

- `GROUP`
- `PRO`
- `GPD`

覆盖四个 subject system：

- `rubis`
- `bsn`
- `swat`
- `wadi`

其中：

- `GROUP` 使用 TOSE 当前主链路。
- `PRO` 复用 ASE `PRD` 的识别与检测实现，但在 RQ2 输出中统一命名为 `PRO`。
- `GPD` 复用 ASE `GPD` 的识别与检测实现。

## Official Protocol

三种方法都使用同一套 holdout 协议：

- `data_rq1_holdout/<system>/holdout_*` 作为统一输入。
- 对每个 `holdout_*` 单元分别训练。
- 训练集固定为该 holdout 目录下的 `identity`。
- 检测集固定为该 holdout 目录下的 `abnormal`。
- `GROUP` 读取 `clustering_results_rq1_holdout/<system>/holdout_*/learned_distributions.yaml`。
- `PRO` 与 `GPD` 直接在相同 holdout 的 `identity` 上重新辨识，再在相同 holdout 的 `abnormal` 上检测。

## Code Paths

- Runner: [rq2_holdout_runner.py](/Users/xuyifei/NJU/repos/TOSE/rq_methods/rq2_holdout_runner.py)
- CLI: [run_rq2_methods_matrix.py](/Users/xuyifei/NJU/repos/TOSE/scripts/run_rq2_methods_matrix.py)
- GROUP adapter: [group_adapter.py](/Users/xuyifei/NJU/repos/TOSE/rq_methods/group_adapter.py)
- ASE baseline identifier: [identifier.py](/Users/xuyifei/NJU/repos/TOSE/baseline_methods/identifier.py)
- ASE baseline evaluator: [evaluator.py](/Users/xuyifei/NJU/repos/TOSE/baseline_methods/evaluator.py)

## Execution

```bash
python3 scripts/run_rq2_methods_matrix.py \
  --data-root data_rq1_holdout \
  --learned-root clustering_results_rq1_holdout \
  --output-dir rq_results/rq2
```

## Outputs

- `rq_results/rq2/summary/rq2_holdout_per_holdout_summary.csv`
- `rq_results/rq2/summary/rq2_holdout_per_holdout_summary.json`
- `rq_results/rq2/summary/rq2_holdout_system_summary.csv`
- `rq_results/rq2/summary/rq2_holdout_system_summary.json`
- `rq_results/rq2/baseline_methods/<system>/holdout_*/PRO.json`
- `rq_results/rq2/baseline_methods/<system>/holdout_*/GPD.json`
- `rq_results/rq2/baseline_methods/<system>/holdout_*/detection_results_PRO.json`
- `rq_results/rq2/baseline_methods/<system>/holdout_*/detection_results_GPD.json`
- `rq_results/rq2/<system>/holdout_*/<system>/GROUP/detection_results_GROUP.json`

## Verification

```bash
python3 -m unittest tests.test_rq2_holdout_runner
python3 -m compileall rq_methods/rq2_holdout_runner.py scripts/run_rq2_methods_matrix.py tests/test_rq2_holdout_runner.py rq_methods/__init__.py
```
