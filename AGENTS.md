<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

项目结构、入口脚本、WaDi 双链路和当前数据目录约定见 `@RTK.md`。

RQ1 当前目标：
- 在 `rubis`、`bsn`、`swat`、`wadi` 四个 subject system 上，对 `hdbscan`、`gmm`、`affinity_propagation`、`mean_shift` 四种聚类算法做统一辨识与异常检测对比。
- 论文横向方法对比使用 `SWD`、`ARD`、`PRD`、`GPD`、`GROUP` 五种方法；其中 `GROUP` 使用默认最佳聚类结果 `clustering_results/<system>/learned_distributions.yaml`。
- 重点跟踪 16 组实验的 `fp` / `fn` 表现、abnormal 数据合理性，以及高 `fp` 的成因。

RQ1 详细文档：
- `@/docs/rq1_experiment_status.md`

RQ1 关键结果文件：
- `@/detection_results/summary/detection_matrix_summary.csv`
- `@/detection_results/summary/detection_matrix_summary.json`

RQ1 统一重跑脚本：
- `@/scripts/run_rq1_detection_matrix.py`
  - 默认重跑 `GROUP × 4种聚类算法` 检测矩阵。
  - 传入 `--rebuild-from-existing-results` 时，从 `detection_results/<system>/detection_results_<algorithm>.json` 重建 summary。

RQ1 五方法统一对比脚本：
- `@/scripts/run_rq1_methods_matrix.py`

RQ1 五方法统一结果：
- `@/rq_results/rq1/summary/rq1_holdout_system_summary.csv`
- `@/rq_results/rq1/summary/rq1_holdout_system_summary.json`

RQ2 当前目标：
- 在 `rubis`、`bsn`、`swat`、`wadi` 四个 subject system 上，对 `GROUP`、`PRO`、`GPD` 三种方法做统一 holdout 方式的辨识与异常检测对比。
- 三种方法都必须按同一个 `holdout_*` 单元分别训练，并只在该 holdout 的 `abnormal` 数据上检测。
- `PRO` 复用 ASE `PRD` 的识别/检测实现，但在 RQ2 输出中统一命名为 `PRO`。

RQ2 统一重跑脚本：
- `@/scripts/run_rq2_methods_matrix.py`

RQ2 统一结果：
- `@/rq_results/rq2/summary/rq2_holdout_system_summary.csv`
- `@/rq_results/rq2/summary/rq2_holdout_system_summary.json`

RQ3 当前目标：
- 在 RQ1 的正式 holdout 协议基础上，对 `GROUP`、`SWD`、`ARD`、`PRD`、`GPD` 五种方法统计 `异常率` 与 `utility`。
- `异常率` 沿用 ASE 风格 `AR` 定义。
- `utility` 当前按 `100 - AR` 统一导出，便于与 RQ1 检测效果一起回看。

RQ3 详细文档：
- `@/docs/rq3_experiment_status.md`

RQ3 统一重跑脚本：
- `@/scripts/run_rq3_methods_matrix.py`

RQ3 统一结果：
- `@/rq_results/rq3/summary/rq3_system_summary.csv`
- `@/rq_results/rq3/summary/rq3_system_summary.json`

RQ4 当前目标：
- 只使用 `GROUP` 方法，但对 `hdbscan`、`gmm`、`affinity_propagation`、`mean_shift` 四种聚类算法分别做辨识与检测。
- 对每组 `GROUP + clustering algorithm` 的检测结果追加 `ARI`，用于评估聚类质量。
- 结果需要输出为一份额外的、只包含 `GROUP × 4种聚类算法` 的独立矩阵。

RQ4 详细文档：
- `@/docs/rq4_experiment_status.md`

RQ4 统一重跑脚本：
- `@/scripts/run_rq4_group_algorithms_matrix.py`
  - 默认与 `RQ1` 四算法 GROUP 矩阵共用同一套 detection config 和同一条 `evaluate_system_algorithm(...)` 执行链路。
  - 只有显式传入 `--reuse-detection-results` 时，才复用已有 `detection_results/<system>/detection_results_<algorithm>.json`。
  - `RQ1` 与 `RQ4` 的该类标准结果文件读取逻辑统一收敛在 `@/rq_methods/detection_matrix_results.py`。
- `RQ1`/`RQ4` 共享字段一致性校验脚本：
  - `@/scripts/check_rq4_matches_rq1_matrix.py`

RQ4 统一结果：
- `@/rq_results/rq4/summary/rq4_group_algorithms_summary.csv`
- `@/rq_results/rq4/summary/rq4_group_algorithms_summary.json`

Git 提交规范：
- 每次修改代码后都要运行聚焦验证，更新必要的进度文档，然后提交 git。
- 每次提交必须使用完整的多行 commit message：首行使用 Conventional Commits 风格，正文写清楚本次提交改了什么、为什么改、验证了什么。
- 不要只写单行提交信息；若无法提交（例如当前目录不是 git 仓库），必须在最终回复中明确说明原因。
