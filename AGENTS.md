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

RQ1 五方法统一对比脚本：
- `@/scripts/run_rq1_methods_matrix.py`

RQ1 五方法统一结果：
- `@/rq_results/rq1/summary/rq1_holdout_system_summary.csv`
- `@/rq_results/rq1/summary/rq1_holdout_system_summary.json`

Git 提交规范：
- 每次修改代码后都要运行聚焦验证，更新必要的进度文档，然后提交 git。
- 每次提交必须使用完整的多行 commit message：首行使用 Conventional Commits 风格，正文写清楚本次提交改了什么、为什么改、验证了什么。
- 不要只写单行提交信息；若无法提交（例如当前目录不是 git 仓库），必须在最终回复中明确说明原因。
