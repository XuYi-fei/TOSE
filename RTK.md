# TOSE Runtime Knowledge

## 项目定位

本仓库是一个面向自适应系统实验的数据分析框架，当前覆盖四类 subject system：

- `rubis`
- `bsn`
- `swat`
- `wadi`

主流程已经拆成两条相对独立但可以并存的链路：

1. 通用配置驱动链路：`cluster.py` / `detect.py` / `validate.py`
2. WaDi 专用状态感知链路：`cluster_wadi.py` / `detect_wadi.py`

当前实验主线应优先使用通用链路，因为它已经支持：

- 多聚类算法统一接入
- 统一的 learned distributions 导出
- 统一的检测输出
- 后续统计 `fp`、`fn`、`precision`、`recall` 等指标

## 当前入口脚本

### 通用入口

- `cluster.py`
  - 从 `identity` trace 数据做聚类辨识
  - 读取 `configs/*_clustering_config.yaml`
- `detect.py`
  - 读取 learned distributions 对 `abnormal` trace 做检测
  - 读取 `configs/*_detection_config.yaml`
- `validate.py`
  - 用于 identity 数据分布验证
- `scripts/run_rq1_baseline_matrix.py`
  - 运行 ASE 风格 baseline 对比方法：`SWD`、`ARD`、`PRD`、`GPD`
  - 读取 `data/<system>/{identity,abnormal}`
  - 输出到 `baseline_results/`
- `scripts/run_rq1_methods_matrix.py`
  - 运行论文 RQ1 横向五方法矩阵：`SWD`、`ARD`、`PRD`、`GPD`、`GROUP`
  - `GROUP` 使用默认最佳聚类结果 `clustering_results/<system>/learned_distributions.yaml`
  - 输出到 `rq_results/rq1/`
- `scripts/run_rq2_methods_matrix.py`
  - 运行论文 RQ2 横向三方法矩阵：`GROUP`、`PRO`、`GPD`
  - 三种方法都按同一个 `holdout_*` 单元分别训练并检测
  - 输出到 `rq_results/rq2/`
- `scripts/run_rq3_methods_matrix.py`
  - 在正式 `RQ1` holdout 协议基础上汇总 `GROUP`、`SWD`、`ARD`、`PRD`、`GPD` 的 `异常率` 与 `utility`
  - 输出到 `rq_results/rq3/`
- `scripts/run_rq4_group_algorithms_matrix.py`
  - 运行 `GROUP × 4种聚类算法` 的独立对比矩阵
  - 在检测结果后追加 `ARI`
  - 输出到 `rq_results/rq4/`

### WaDi 专用入口

- `cluster_wadi.py`
  - 面向原始 WaDi CSV 的状态感知聚类
- `detect_wadi.py`
  - 面向原始 WaDi CSV / trace 的状态条件检测

## 当前 WaDi 两套数据链路

### 1. 通用实验链路

这是当前推荐的 WaDi 实验路径。

数据准备分两步：

1. 从本地原始文件提取 trace 风格数据：
   - `scripts/extract_wadi_trace_dataset.py`
   - 输入：`wadi-original/data/WaDi.A3_Dec 2023 Historian Data_original.csv`
   - 输出：`data/wadi_trace/{identity,abnormal}`
2. 将 trace 数据转换成通用框架使用的 `.txt` 数据集：
   - `scripts/build_wadi_generic_dataset.py`
   - 输出：`data/wadi/{identity,abnormal}`

对应实验命令：

```bash
python cluster.py --config configs/wadi_clustering_config.yaml
python detect.py --config configs/wadi_gmm_detection_config.yaml
```

如果要切换检测时读取的 learned distributions，也可以改用：

```bash
python detect.py --config configs/wadi_generic_detection_config.yaml
```

当前 WaDi 通用聚类已接入四种算法：

- `hdbscan`
- `gmm`
- `affinity_propagation`
- `mean_shift`

聚类阶段会输出：

- `clustering_results/wadi/learned_distributions.yaml`
- `clustering_results/wadi/learned_distributions_gmm.yaml`
- `clustering_results/wadi/learned_distributions_hdbscan.yaml`
- `clustering_results/wadi/learned_distributions_affinity_propagation.yaml`
- `clustering_results/wadi/learned_distributions_mean_shift.yaml`

检测阶段会输出：

- `detection_results/wadi/detection_results.json`
- `detection_results/wadi/detection_results_<algorithm>.json`
- `detection_results/wadi/detection_report_<algorithm>.md`

检测输出中已经包含：

- 使用的 clustering algorithm
- 辨识得到的 cluster count

### 2. WaDi 专用状态感知链路

这是保留中的专用实现，适合直接围绕原始 CSV 做状态感知分析：

```bash
python cluster_wadi.py --config configs/wadi_cluster_config.yaml
python detect_wadi.py --config configs/wadi_detection_config.yaml
```

这一套链路依赖：

- `cluster_analysis/adapters/wadi/`
- `cluster_analysis/state_aware_clusterer.py`
- `anomaly_detection/state_conditional_detector.py`
- `anomaly_detection/state/environment_detector.py`

## 当前核心目录

```text
TOSE/
├── cluster.py
├── detect.py
├── validate.py
├── cluster_wadi.py
├── detect_wadi.py
├── configs/
├── data/
├── scripts/
├── cluster_analysis/
├── anomaly_detection/
├── baseline_methods/
├── rq_methods/
├── common/
├── clustering_results/
├── detection_results/
├── baseline_results/
├── rq_results/
├── docs/
├── tests/
└── wadi-original/
```

## 当前配置文件重点

### 通用配置

- `configs/rubis_clustering_config.yaml`
- `configs/rubis_detection_config.yaml`
- `configs/bsn_clustering_config.yaml`
- `configs/bsn_detection_config.yaml`
- `configs/swat_clustering_config.yaml`
- `configs/swat_detection_config.yaml`
- `configs/wadi_clustering_config.yaml`
- `configs/wadi_generic_detection_config.yaml`
- `configs/wadi_gmm_detection_config.yaml`

### WaDi 专用配置

- `configs/wadi_cluster_config.yaml`
- `configs/wadi_detection_config.yaml`
- `configs/wadi_trace_cluster_config.yaml`
- `configs/wadi_trace_detection_config.yaml`

## 当前数据目录约定

### 通用框架输入

- `data/rubis/{identity,abnormal}`
- `data/bsn/{identity,abnormal}`
- `data/swat/{identity,abnormal}`
- `data/wadi/{identity,abnormal}`

其中 `data/wadi/` 是转换后的通用 trace `.txt` 数据，供 `cluster.py` / `detect.py` 使用。

### WaDi trace 中间产物

- `data/wadi_trace/identity`
- `data/wadi_trace/abnormal`
- `data/wadi_trace/manifests`
- `data/wadi_trace/reports`

### WaDi 原始数据

- `wadi-original/data/`
- `wadi-original/outputs/`

## 当前实现上的重要约束

- WaDi 通用链路现在保留自由聚类结果，不再强行压缩成固定 `norm1/norm2/norm3` 三簇。
- learned distributions 对多簇算法按 cluster 级别导出，避免多个 cluster 被同一主标签覆盖。
- 检测阶段直接读取聚类导出的 cluster 级 distributions，因此辨识和检测都保持自由聚类。
- 若只做单算法对比实验，优先使用算法专属配置和带后缀的输出文件，避免结果互相覆盖。
- RQ1 baseline 结果必须写入 `baseline_results/`，不要覆盖 GROUP 链路的 `detection_results/`。
- RQ1 论文五方法统一对比写入 `rq_results/rq1/`，不要覆盖旧的 `baseline_results/` 或 `detection_results/`。
- RQ2 论文三方法统一对比写入 `rq_results/rq2/`，不要覆盖 `rq_results/rq1/`。
- RQ3 实用性汇总统一写入 `rq_results/rq3/`，不要覆盖 `rq_results/rq1/` 或 `rq_results/rq2/`。
- RQ4 的 `GROUP × 聚类算法` 独立矩阵统一写入 `rq_results/rq4/`，不要覆盖 `detection_results/summary/`。
- 五方法统一对比中的 `GROUP` 固定读取 `clustering_results/<system>/learned_distributions.yaml`，即聚类阶段选择的最佳算法产物；四聚类算法内部对比仍使用 `scripts/run_rq1_detection_matrix.py`。
- 每次代码修改后应运行聚焦验证、更新进度文档并提交 git；提交信息必须是多行 message，正文写清楚改动、原因和验证。

## 相关文档

- `README.md`
- `docs/wadi_trace_dataset.md`
- `docs/wadi_architecture.md`
- `wadi-original/README.md`
