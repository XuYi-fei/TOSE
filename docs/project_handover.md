# TOSE 项目交接说明

> 核对日期：2026-10-01。本文依据当前仓库代码、`docs/rq1_experiment_status.md` 至 `docs/rq4_experiment_status.md`、本机已有的结果 CSV 和 Git 状态编写。结果数字是现有产物的快照，不代表今天重新跑完了全部实验。

## 1. 项目背景与目标

TOSE 是面向自适应系统实验的数据分析框架。它从系统正常运行数据中辨识分布，再检测运行 trace 中的异常，当前覆盖 RUBiS、BSN、SWaT、WaDi 四个 subject system。项目既支持配置驱动的单系统聚类和检测，也提供论文研究问题 RQ1–RQ4 的统一实验脚本。

核心研究对象是 `GROUP` 方法：先从 `identity` 数据聚类并导出 learned distributions，再用这些分布检测 `abnormal` trace。对比方法来自 ASE 风格适配层。四个研究问题分别回答：

| 研究问题 | 要回答的问题 | 当前比较范围 |
| --- | --- | --- |
| RQ1 | GROUP 相对其他检测方法的表现如何？ | 四系统 × GROUP、SWD、ARD、PRD、GPD；另保留 GROUP 四聚类算法检测矩阵 |
| RQ2 | 各方法都按相同 holdout 单元重新辨识时表现如何？ | 四系统 × GROUP、PRO、GPD |
| RQ3 | 检测异常的时长占比及其派生 utility 如何？ | 沿用 RQ1 协议，统计五方法的 AR 与 `100 - AR` |
| RQ4 | GROUP 采用不同聚类算法时，聚类质量与检测效果有何关系？ | 四系统 × HDBSCAN、GMM、Affinity Propagation、Mean Shift，追加 ARI |

`PRO` 是 RQ2 对 ASE `PRD` 辨识和检测实现的输出名称，不应把两者当作独立算法。RQ1 的五方法正式 holdout 实验与 RQ1/RQ4 的四聚类算法矩阵使用不同协议，结果不能逐行直接比较。

## 2. 一次实验如何流转

```text
data/<system>/identity ──> cluster.py ──> clustering_results/<system>/learned_distributions*.yaml
data/<system>/abnormal ──> detect.py + learned distributions ──> detection_results/<system>/

data/<system>/identity ──> RQ1 holdout 数据构建 ──> data_rq1_holdout/<system>/holdout_*/
                                                   └─> GROUP holdout 辨识产物
                                                       clustering_results_rq1_holdout/
                                                   └─> RQ1、RQ2、RQ3 的统一实验入口
                                                       rq_results/rq{1,2,3}/

原始/通用数据 + 四算法产物 ──> GROUP 检测矩阵 ──> detection_results/summary/
                                      └─> RQ4 加入 ARI ──> rq_results/rq4/summary/
```

通用数据目录为 `data/<system>/{identity,abnormal}`。正式 RQ1 holdout 测试数据由原始 `identity` 的已知分布段重组：异常段放在 trace 末尾，用 `abn1_start_time` 标记评估边界。RUBiS、SWaT、WaDi 各有 3 个 `norm` holdout；BSN 按 `sensor_index + norm_label` 分区，共 18 个 holdout。这个分区规则会影响 BSN 的误报统计。

WaDi 有两条链路。论文统一实验使用 `scripts/extract_wadi_trace_dataset.py` 和 `scripts/build_wadi_generic_dataset.py` 转出的 `data/wadi/` 通用 trace；`cluster_wadi.py`、`detect_wadi.py` 是保留的原始 CSV 状态感知链路。两条链路的输入和输出不要混用。详见 [运行知识](../RTK.md)和 [WaDi 数据说明](wadi_trace_dataset.md)。

## 3. 当前进度与已有结果

### RQ1：正式五方法 holdout 对比已产出

正式协议为：GROUP 每个 holdout 分别训练和检测；SWD、ARD、PRD、GPD 每个系统在 `data/<system>/identity` 上训练一次，再对该系统所有 holdout 的 abnormal 数据检测。主要入口是 [run_rq1_methods_matrix.py](../scripts/run_rq1_methods_matrix.py)，从头构建并重跑可用 [run_rq1_holdout_pipeline.py](../scripts/run_rq1_holdout_pipeline.py)。

当前 [系统级汇总](../rq_results/rq1/summary/rq1_holdout_system_summary.csv)中，GROUP 的结果为：

| 系统 | FP (%) | FN (%) | F1 |
| --- | ---: | ---: | ---: |
| RUBiS | 10.83 | 0.00 | 0.9419 |
| BSN | 2.97 | 0.00 | 0.9847 |
| SWaT | 4.17 | 0.00 | 0.9787 |
| WaDi | 0.00 | 0.83 | 0.9958 |

按这批结果，GROUP 是四系统中表现最稳定的方法。多数 SWD、PRD、GPD 组合的 FN 很高；ARD 常以很高的 FP 换取较低 FN。详细协议与全部方法数值见 [RQ1 进度文档](rq1_experiment_status.md)。

另有 [GROUP 四算法检测矩阵](../detection_results/summary/detection_matrix_summary.csv)，覆盖 4 × 4 共 16 组，入口为 [run_rq1_detection_matrix.py](../scripts/run_rq1_detection_matrix.py)。该矩阵使用通用检测链路，不能当作上述正式 holdout 五方法结果。当前默认最佳聚类产物分别来自 RUBiS/HDBSCAN、BSN/HDBSCAN、SWaT/GMM、WaDi/Mean Shift。

### RQ2：同一 holdout 条件下的三方法对比已产出

GROUP、PRO、GPD 都在各自 `holdout_*` 的 `identity` 上辨识，并只检测同一目录的 `abnormal`。入口为 [run_rq2_methods_matrix.py](../scripts/run_rq2_methods_matrix.py)。[系统级汇总](../rq_results/rq2/summary/rq2_holdout_system_summary.csv)显示 GROUP 的四系统 F1 仍为 0.9419、0.9847、0.9787、0.9958；PRO 的 F1 范围为 0.3333–0.6667，GPD 为 0.3856–0.6405。具体目录和产物见 [RQ2 进度文档](rq2_experiment_status.md)。

### RQ3：AR 与 utility 汇总已产出，但解释需谨慎

RQ3 从 RQ1 的 trace 级结果汇总 `AR = abnormal_time / abnormal_total_time × 100`，再导出 `utility = 100 - AR`。入口为 [run_rq3_methods_matrix.py](../scripts/run_rq3_methods_matrix.py)，现有结果见 [系统级汇总](../rq_results/rq3/summary/rq3_system_summary.csv)。

现有汇总中存在需要核查的矛盾：例如 RUBiS 的 SWD、PRD 均为 `FN=100%`，但 `AR=0`、`utility=100`。因此当前不能仅凭 utility 排序或直接将它写成综合检测效用；应先追查 trace 级时长字段及汇总逻辑，并与 FP、FN 一起报告。相关代码见 [metrics.py](../rq_methods/metrics.py)、[rq3_runner.py](../rq_methods/rq3_runner.py)。

### RQ4：四算法矩阵与 ARI 已产出

入口为 [run_rq4_group_algorithms_matrix.py](../scripts/run_rq4_group_algorithms_matrix.py)。默认复用 RQ1 四算法 GROUP 矩阵的配置和 `evaluate_system_algorithm(...)` 执行链，结果写入独立的 [RQ4 汇总](../rq_results/rq4/summary/rq4_group_algorithms_summary.csv)。ARI 真值标签在 BSN 为 `sensor_index + norm_label`，其他系统为 `norm_label`。

截至本次交接，[一致性脚本](../scripts/check_rq4_matches_rq1_matrix.py)运行通过，RQ4 与 RQ1 四算法矩阵的共享检测字段一致。结果也表明 ARI 与最终检测 F1 不总是同步：例如 SWaT 的 Affinity Propagation 当前 ARI 约 0.2934、检测 F1 为 1.0，但产生了 1012 个簇。阅读结果时需同时看簇数和聚类语义。

**文档同步问题：** [RQ4 进度文档](rq4_experiment_status.md)中若干簇数和检测值仍是旧快照。例如它把 SWaT/Affinity Propagation 写为 1492 簇，当前 CSV 为 1012 簇。引用当前实验数字时以 CSV 为准，后续应更新进度文档。

## 4. 项目结构与定位

| 路径 | 用途 |
| --- | --- |
| `cluster.py`、`detect.py`、`validate.py` | 通用配置驱动的辨识、检测与分布验证入口 |
| `cluster_wadi.py`、`detect_wadi.py` | WaDi 原始数据的专用状态感知链路 |
| `cluster_analysis/`、`anomaly_detection/` | 聚类算法、适配器、分布建模与检测实现 |
| `baseline_methods/` | ASE 风格对比方法的辨识和检测适配 |
| `rq_methods/` | holdout 数据、各 RQ runner、指标、ARI 与一致性检查 |
| `scripts/` | 数据构建、矩阵实验和检查的命令行入口 |
| `configs/` | 单系统聚类、检测配置 |
| `data/`、`data_rq1_holdout/` | 通用输入与正式 holdout 输入 |
| `clustering_results/`、`clustering_results_rq1_holdout/` | learned distributions 与聚类产物 |
| `detection_results/`、`rq_results/` | 通用检测与研究问题汇总结果 |
| `docs/`、`tests/` | 实验说明与聚焦回归测试 |
| `archived_docs/`、`archived_scripts/` | 旧材料；优先依据当前 RQ 文档和入口脚本 |

仓库规则见 [AGENTS.md](../AGENTS.md)，全局运行约定见 [RTK.md](../RTK.md)。遇到新能力、架构变更或正式提案时，再查 [OpenSpec 约定](../openspec/AGENTS.md)。

## 5. 新接手者如何复现与核对

README 声明 Python 3.8+，依赖列于 [requirements.txt](../requirements.txt)。项目没有锁定依赖版本的 lockfile；复现时应记录实际 Python 和包版本。先确认四系统的 `data/`、正式 holdout 数据与 learned distributions 都已准备好，再执行实验入口。

```bash
python3 -m pip install -r requirements.txt

# 正式 RQ1：已准备好 holdout 数据与 GROUP 辨识产物时
python3 scripts/run_rq1_methods_matrix.py \
  --data-root data_rq1_holdout \
  --output-dir rq_results/rq1 \
  --learned-root clustering_results_rq1_holdout \
  --baseline-identity-root data

# 从原始通用数据构建 holdout 并重跑 RQ1
python3 scripts/run_rq1_holdout_pipeline.py \
  --data-root data \
  --holdout-root data_rq1_holdout \
  --learned-root clustering_results_rq1_holdout \
  --output-dir rq_results/rq1

# RQ2、RQ3、RQ4 的完整参数以各自进度文档和 --help 为准
python3 scripts/check_rq4_matches_rq1_matrix.py
```

本机目前有正式 holdout 数据和辨识产物，但 `data_rq1_holdout/`（约 1.2 GB）、`clustering_results_rq1_holdout/`（约 156 MB）、`outputs/` 在 Git 状态中属于**未跟踪目录**。`.gitignore` 还排除了 `data/`、`clustering_results/`、`detection_results/`、`rq_results/` 等实验输入和产物。因此仅克隆源码不能复现本文数字：必须另行移交数据与结果文件，并记录来源、生成命令和版本。不要把本机存在的文件误认为已随 Git 提交。

## 6. 交接时优先处理的事项

1. **补齐可移交产物。** 确认四系统原始/通用数据、`data_rq1_holdout/`、`clustering_results_rq1_holdout/` 和四个 RQ 的汇总文件已交给接手者；同时记录文件校验值与生成环境。
2. **核查 RQ3 的 AR 边界情况。** 从 `FN=100%` 且 `AR=0` 的 trace 开始定位字段和分母来源，明确修正前的结果能否用于论文结论。
3. **同步 RQ4 文档。** 以当前 CSV 核对并更新旧快照数字；保留 RQ1/RQ4 一致性检查作为重跑后的验收步骤。
4. **继续分析高 FP 与数据合理性。** 尤其关注 RQ1 中 RUBiS/GROUP 的 10.83% FP、ARD 在多系统的高 FP，以及由重组 identity 生成 abnormal trace 的实验边界。不要只看总表，应回到逐 holdout 和 trace 级结果。

修改代码后按 [AGENTS.md](../AGENTS.md)执行聚焦验证、更新必要的进度文档并提交 Git；提交信息须包含 Conventional Commits 风格标题和说明改动、原因、验证的正文。
