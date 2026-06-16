# 自适应系统数据分析框架

一个通用的、配置驱动的数据分析系统，支持**数据验证、聚类分析和异常检测**。支持多种自适应系统：**RUBIS、BSN、SWAT、WaDi**。

---

## 🚀 快速开始

### 环境要求

- **Python版本**: 3.8+
- **依赖安装**:
  ```bash
  pip install -r requirements.txt
  ```

### 三大功能

#### 1. 聚类分析（自动发现分布参数）

从identity数据中自动学习正态分布参数，为异常检测提供基准。

```bash
# RUBIS系统
python cluster.py --config configs/rubis_clustering_config.yaml

# BSN系统
python cluster.py --config configs/bsn_clustering_config.yaml

# SWAT系统
python cluster.py --config configs/swat_clustering_config.yaml

# WaDi系统（通用多算法链路）
python cluster.py --config configs/wadi_clustering_config.yaml

# WaDi系统（专用状态感知链路，保留）
python cluster_wadi.py --config configs/wadi_cluster_config.yaml
```

**输出文件**:
- `clustering_results/{system}/clustering_report.md` - 聚类分析报告
- `clustering_results/{system}/learned_distributions.yaml` - 学习到的分布参数（用于异常检测）
- `clustering_results/wadi/learned_distributions_{algorithm}.yaml` - WaDi按算法导出的分布参数
- `clustering_results/{system}/*.png` - 可视化图表（散点图、密度曲线、算法对比等）

#### 2. 异常检测（基于3-sigma点判定 + trace级容错触发）

使用学习到的分布参数检测abnormal数据中的异常点。当前正式检测口径为：

1. 先按 3-sigma 规则判断单点是否为 raw anomaly。
2. 再按 trace 级容错规则判断是否真正报警：
   `raw_anomaly_count > ceil(n * p_sigma)`，
   其中 `p_sigma = erfc(sigma_threshold / sqrt(2))`。

```bash
# RUBIS系统
python detect.py --config configs/rubis_detection_config.yaml

# BSN系统（需要先有abnormal数据）
python detect.py --config configs/bsn_detection_config.yaml

# SWAT系统（需要先有abnormal数据）
python detect.py --config configs/swat_detection_config.yaml

# WaDi系统（通用多算法链路）
python detect.py --config configs/wadi_gmm_detection_config.yaml

# WaDi系统（读取默认learned_distributions.yaml）
python detect.py --config configs/wadi_generic_detection_config.yaml

# WaDi系统（专用状态条件检测，保留）
python detect_wadi.py --config configs/wadi_detection_config.yaml
```

**输出文件**:
- `detection_results/{system}/detection_report.md` - 可读性报告
- `detection_results/{system}/detection_results.json` - **标准化JSON格式**（推荐用于脚本分析）
- `detection_results/{system}/detection_results.csv` - **CSV格式详细结果**（推荐用于Excel分析）
- `detection_results/wadi/detection_results_{algorithm}.json` - WaDi按算法输出的检测结果

**JSON输出格式示例**:
```json
{
  "metadata": {
    "system_type": "rubis",
    "detection_time": "2026-01-16T23:52:41.719888",
    "config_path": "configs/rubis_detection_config.yaml",
    "alarm_count_policy": "theoretical_3sigma_count",
    "sigma_threshold": 3.0,
    "p_sigma": 0.002699796063260207
  },
  "summary": {
    "total_traces": 200,
    "tp_traces": 67,
    "fp_traces": 133,
    "fn_traces": 0,
    "tn_traces": 0,
    "alarm_trigger_rule": "raw_anomaly_count > ceil(observed_count * p_sigma)"
  },
  "confusion_matrix": {
    "TP": 67, "FP": 133, "TN": 0, "FN": 0
  },
  "performance_metrics": {
    "precision": 0.335, "recall": 1.0, "f1_score": 0.501873
  },
  "trace_details": [
    {
      "filename": "eval_abn_trace-cnt-000...",
      "classification": "FP",
      "abn1_start_time": 420.0,
      "first_raw_anomaly_time": 80.0,
      "first_detection_time": 97.0,
      "trigger_alarm_count": 2,
      "trigger_allowed_count": 1,
      "total_detection_count": 10
    }
  ]
}
```

#### 3. 数据验证（验证identity数据分布）

验证identity数据是否符合预期的正态分布参数。

```bash
# RUBIS系统
python validate.py --config configs/rubis_config.yaml

# BSN系统
python validate.py --config configs/bsn_config.yaml
```

#### 4. RQ2 holdout 三方法对比

当前正式 RQ2 口径对比三种方法：

- `GROUP`
- `PRO`
- `GPD`

其中：

- `GROUP` 使用当前 TOSE 主链路。
- `PRO` 复用 ASE `PRD` 的辨识/检测实现，但在 RQ2 输出中统一命名为 `PRO`。
- `GPD` 复用 ASE `GPD` 的辨识/检测实现。

三种方法都与 `GROUP` 保持同一套 holdout 评估协议：

- 对每个 `holdout_*` 单元分别训练。
- 训练集使用该 holdout 目录下的 `identity`。
- 检测集只使用该 holdout 目录下的 `abnormal`。

```bash
python scripts/run_rq2_methods_matrix.py \
  --data-root data_rq1_holdout \
  --learned-root clustering_results_rq1_holdout \
  --output-dir rq_results/rq2
```

**输出文件**:
- `rq_results/rq2/summary/rq2_holdout_per_holdout_summary.csv`
- `rq_results/rq2/summary/rq2_holdout_per_holdout_summary.json`
- `rq_results/rq2/summary/rq2_holdout_system_summary.csv`
- `rq_results/rq2/summary/rq2_holdout_system_summary.json`
- `rq_results/rq2/baseline_methods/<system>/holdout_*/PRO.json`
- `rq_results/rq2/baseline_methods/<system>/holdout_*/GPD.json`
- `rq_results/rq2/<system>/holdout_*/<system>/GROUP/detection_results_GROUP.json`

#### 5. RQ3 实用性汇总

RQ3 不重新定义训练和检测，而是直接复用正式 RQ1 协议，对五种方法汇总：

- `异常率`
- `utility`

当前口径：

- `异常率` 直接复用 ASE 风格 `AR`
- `utility = 100 - AR`

```bash
python3 scripts/run_rq3_methods_matrix.py \
  --data-root data_rq1_holdout \
  --learned-root clustering_results_rq1_holdout \
  --output-dir rq_results/rq3 \
  --baseline-identity-root data
```

**输出文件**:
- `rq_results/rq3/summary/rq3_per_holdout_summary.csv`
- `rq_results/rq3/summary/rq3_per_holdout_summary.json`
- `rq_results/rq3/summary/rq3_system_summary.csv`
- `rq_results/rq3/summary/rq3_system_summary.json`

---

## ⚙️ 配置说明

### 聚类分析配置

配置文件位置：`configs/{system}_clustering_config.yaml`

```yaml
# 系统类型: rubis, bsn, swat
system_type: rubis

# 数据路径（identity数据）
data_path: data/rubis/identity

# 聚类算法列表
algorithms:
  - hdbscan                # 基于密度的层次聚类
  - gmm                     # 高斯混合模型（BIC自动选择聚类数）
  - affinity_propagation    # 亲和传播
  - mean_shift              # 均值漂移

# 算法参数（可选）
algorithm_params:
  hdbscan:
    min_cluster_size: 10
    min_samples: 5
  gmm:
    min_clusters: 2
    max_clusters: 10
    covariance_type: full

# 输出配置
output:
  dir: clustering_results/rubis
  visualizations: true              # 是否生成可视化图表
  report: true                       # 是否生成Markdown报告
  save_learned_distributions: true  # 是否保存分布参数
  learned_distributions_path: clustering_results/rubis/learned_distributions.yaml
```

### 异常检测配置

配置文件位置：`configs/{system}_detection_config.yaml`

```yaml
# 系统类型
system_type: rubis

# 学习到的分布参数文件（由聚类分析生成）
learned_distributions: clustering_results/rubis/learned_distributions.yaml

# 测试数据路径（abnormal数据）
test_data_path: data/rubis/abnormal

# 检测参数
detection:
  sigma_threshold: 3.0              # 3-sigma规则的sigma倍数
  alarm_count_policy: theoretical_3sigma_count
  min_samples_for_detection: 1      # 兼容保留字段，当前正式流程不用于触发报警

# 输出配置
output:
  dir: detection_results/rubis
  generate_visualizations: true     # 生成可视化（未来功能）
  save_anomaly_points: true         # 保存异常点详情
```

---

## 📂 数据组织

数据按系统类型和用途组织：

```
data/
├── rubis/
│   ├── identity/       # RUBIS辨识数据 (200个trace)
│   └── abnormal/       # RUBIS异常数据 (200个trace)
├── bsn/
│   ├── identity/       # BSN辨识数据 (200个trace)
│   └── abnormal/       # BSN异常数据 (200个trace)
├── swat/
│   ├── identity/       # SWAT辨识数据 (200个trace)
│   └── abnormal/       # SWAT异常数据 (200个trace)
└── wadi/
    ├── identity/       # WADI通用框架输入数据 (.txt)
    └── abnormal/       # WADI通用检测数据 (.txt)

data/wadi_trace/
├── identity/           # WADI trace-style中间数据 (.csv)
├── abnormal/           # WADI trace-style异常数据 (.csv)
├── manifests/          # 构造清单
└── reports/            # 数据集摘要
```

**数据格式要求**:

| 系统 | 时间列 | 目标列 | 文件命名格式 |
|------|--------|--------|-------------|
| RUBIS | `simTime(s)` | `measuredAvgRespTime_{k}` | `eval_ident_trace-cnt-XXX-...txt` |
| BSN | `logicalTime(s)` | `cost` (根据sensor_index选择) | `eval_ident_trace-cnt-XXX-sensor_index-X-...txt` |
| SWAT | `time` | `y_0` | `eval_ident_trace-cnt-XXX-...txt` |
| **WaDi（通用链路）** | `t` | `value` | `eval_ident_trace-cnt-XXX-...txt` |
| **WaDi（专用链路）** | `Time` | **自动选择** (FIT/PIT/LT传感器) | 原始 `.csv` |

---

## 🌊 WaDi（水处理系统）专用功能

WaDi是工业水处理系统数据集，具有以下特点：

### 数据集特性
- **大规模数据**: 单个CSV文件290MB，1.7M行，141列
- **工业传感器**: 31个过程变量（PV），包括LT（液位）、FIT（流量）、PIT（压力）、AIT（分析仪）
- **多模态分布**: 流量指标在3个运行状态间循环（LOW ~0.004, MEDIUM ~1.3, HIGH ~2.4 L/s）
- **环境驱动**: 泵/阀门状态决定运行模式
- **三区域架构**: HMI_1（输入）、HMI_2（处理）、HMI_3（输出）

### 使用流程

#### 1. 数据准备
WaDi 原始数据放置在本地：
```bash
wadi-original/data/WaDi.A3_Dec 2023 Historian Data_original.csv
```

如果需要生成与 `swat`、`bsn` 类似的 trace-style WaDi 数据集，请先提取 trace：

```bash
python3 scripts/extract_wadi_trace_dataset.py \
  --source-csv "wadi-original/data/WaDi.A3_Dec 2023 Historian Data_original.csv" \
  --output-root data/wadi_trace \
  --identity-count 200 \
  --abnormal-count 200 \
  --segment-len 180 \
  --seed 42
```

该脚本输出 `data/wadi_trace/{identity,abnormal}`，说明见：[docs/wadi_trace_dataset.md](/Users/xuyifei/NJU/repos/TOSE/docs/wadi_trace_dataset.md)。

接着将 `wadi_trace` 转成通用框架读取的 `.txt` 数据：

```bash
python3 scripts/build_wadi_generic_dataset.py \
  --source-root data/wadi_trace \
  --output-root data/wadi
```

此时 `data/wadi/` 会和其他 subject system 一样，包含 `identity/` 与 `abnormal/` 两部分。

#### 2. 通用多算法聚类
推荐优先使用通用框架对 WaDi 做辨识：

```bash
python cluster.py --config configs/wadi_clustering_config.yaml
```

**当前特点**：
1. 使用与 `rubis`、`bsn`、`swat` 相同的通用聚类入口。
2. 支持 `hdbscan`、`gmm`、`affinity_propagation`、`mean_shift` 四种算法。
3. learned distributions 会同时保留默认输出和按算法拆分输出。
4. 多簇算法按 cluster 级别保留结果，不再强制压缩成固定三类标签。

**输出**：
- `clustering_results/wadi/learned_distributions.yaml`
- `clustering_results/wadi/learned_distributions_gmm.yaml`
- `clustering_results/wadi/learned_distributions_hdbscan.yaml`
- `clustering_results/wadi/learned_distributions_affinity_propagation.yaml`
- `clustering_results/wadi/learned_distributions_mean_shift.yaml`
- `clustering_results/wadi/clustering_report.md`

#### 3. 通用异常检测
通用检测链路与其他 subject system 保持一致：

```bash
python detect.py --config configs/wadi_gmm_detection_config.yaml
```

如果想切换为默认 `learned_distributions.yaml`，则使用：

```bash
python detect.py --config configs/wadi_generic_detection_config.yaml
```

**当前特点**：
1. 直接读取聚类阶段导出的 cluster 级 distributions。
2. 检测结果会带出所使用的聚类算法名称和辨识得到的聚类簇数。
3. 可通过配置切换不同算法导出的 learned distributions，方便统一统计 `fp`、`fn`、`precision`、`recall` 等指标。

**输出**：
- `detection_results/wadi/detection_results_gmm.json`
- `detection_results/wadi/detection_results_hdbscan.json`
- `detection_results/wadi/detection_results_affinity_propagation.json`
- `detection_results/wadi/detection_results_mean_shift.json`
- `detection_results/wadi/detection_report_<algorithm>.md`

#### 4. 专用状态感知链路（保留）
如果需要直接围绕原始 WaDi CSV 做状态感知分析，仍可使用专用脚本：

```bash
python cluster_wadi.py --config configs/wadi_cluster_config.yaml
python detect_wadi.py --config configs/wadi_detection_config.yaml
```

这一路径依然适合：

1. 直接读取原始大 CSV。
2. 依赖泵状态做环境状态识别。
3. 做状态条件异常检测而不是通用 trace 检测。

### 配置说明

#### 通用聚类配置 (`configs/wadi_clustering_config.yaml`)
- `system_type: wadi`
- `data_path: data/wadi/identity`
- `algorithms`: 四种聚类算法统一配置
- `output.save_per_algorithm_distributions: true`

#### 通用检测配置
- `configs/wadi_gmm_detection_config.yaml`
  - 读取 `clustering_results/wadi/learned_distributions_gmm.yaml`
  - 输出带 `gmm` 后缀的检测结果
- `configs/wadi_generic_detection_config.yaml`
  - 读取 `clustering_results/wadi/learned_distributions.yaml`
  - 输出默认命名的检测结果

#### 专用 WaDi 配置
- `configs/wadi_cluster_config.yaml`
- `configs/wadi_detection_config.yaml`

### 工业传感器类型参考

| 传感器代码 | 物理含义 | 测量单位 | 领域优先级 |
|------------|----------|----------|------------|
| **FIT** | 流量（Flow Indicator Transmitter） | L/s | 高（权重3） |
| **PIT** | 压力（Pressure Indicator Transmitter） | bar | 中（权重2） |
| **LT** | 液位（Level Transmitter） | m | 低（权重1） |
| **AIT** | 分析仪（Analytical Indicator Transmitter） | 各种 | 低（权重1） |
| **DPIT** | 差压（Differential Pressure） | bar | 低（权重1） |

### 内存和性能

- **峰值内存**: < 3GB（使用分块处理）
- **处理时间**: < 60秒（完整290MB CSV聚类）
- **推荐配置**: 8GB+ RAM，多核CPU

---

## 🏗️ 代码结构

```
TOSE/
├── cluster.py                   # 通用聚类分析入口
├── detect.py                    # 通用异常检测入口
├── validate.py                  # 数据验证入口
├── cluster_wadi.py              # WaDi专用状态感知聚类入口
├── detect_wadi.py               # WaDi专用状态条件检测入口
│
├── configs/                     # 配置文件目录
│   ├── rubis_clustering_config.yaml
│   ├── rubis_detection_config.yaml
│   ├── bsn_clustering_config.yaml
│   ├── bsn_detection_config.yaml
│   ├── swat_clustering_config.yaml
│   ├── swat_detection_config.yaml
│   ├── wadi_clustering_config.yaml
│   ├── wadi_generic_detection_config.yaml
│   ├── wadi_gmm_detection_config.yaml
│   ├── wadi_cluster_config.yaml
│   ├── wadi_detection_config.yaml
│   ├── wadi_trace_cluster_config.yaml
│   └── wadi_trace_detection_config.yaml
│
├── data/                        # 统一数据目录
│   ├── rubis/{identity,abnormal}/
│   ├── bsn/{identity,abnormal}/
│   ├── swat/{identity,abnormal}/
│   ├── wadi/{identity,abnormal}/
│   └── wadi_trace/
│       ├── identity/
│       ├── abnormal/
│       ├── manifests/
│       └── reports/
│
├── scripts/
│   ├── extract_wadi_trace_dataset.py   # 从原始WaDi提取trace-style数据
│   └── build_wadi_generic_dataset.py   # 将wadi_trace转成通用框架输入
│
├── cluster_analysis/            # 聚类分析框架
│   ├── core/
│   │   ├── engine.py            # 聚类引擎
│   │   └── result.py            # 结果数据模型
│   ├── adapters/
│   │   └── wadi/                # WaDi专用适配与指标选择
│   ├── algorithms/              # 聚类算法实现
│   │   ├── base.py              # 算法基类
│   │   ├── factory.py           # 算法工厂（动态注册）
│   │   ├── hdbscan_algo.py      # HDBSCAN算法
│   │   ├── gmm_algo.py          # GMM算法
│   │   ├── affinity_propagation_algo.py
│   │   └── mean_shift_algo.py
│   ├── state_aware_clusterer.py # WaDi专用状态感知聚类器
│   ├── visualization/
│   │   ├── plotter.py           # 可视化绘图
│   │   └── reporter.py          # 报告生成
│   └── config/
│       └── config.py            # 配置加载和验证
│
├── anomaly_detection/           # 异常检测框架
│   ├── core/
│   │   ├── detector.py          # 异常检测器（3-sigma）
│   │   └── evaluator.py         # 性能评估器（混淆矩阵、PR等）
│   ├── config/
│   │   └── config.py            # 配置加载和验证
│   └── visualization/
│       └── reporter.py          # 报告生成（MD/JSON/CSV）
│
├── common/                      # 共享组件层
│   ├── adapters/                # 数据适配器
│   │   ├── __init__.py          # ParserFactory（工厂模式）
│   │   ├── rubis.py             # RUBIS解析器
│   │   ├── bsn.py               # BSN解析器
│   │   ├── swat.py              # SWAT解析器
│   │   └── wadi.py              # WaDi通用trace解析器
│   ├── models/                  # 数据模型
│   │   ├── metadata.py          # TraceMetadata
│   │   └── distribution.py      # DistributionParameters
│   └── utils/
│       └── statistics.py        # 统计工具函数
│
├── clustering_results/          # 聚类分析结果
│   ├── rubis/
│   │   ├── clustering_report.md
│   │   ├── learned_distributions.yaml  # ← 供检测使用
│   │   └── *.png                # 7张可视化图表
│   ├── bsn/
│   ├── swat/
│   ├── wadi/
│   │   ├── clustering_report.md
│   │   ├── learned_distributions.yaml
│   │   └── learned_distributions_<algorithm>.yaml
│   └── wadi_trace/
│
└── detection_results/           # 异常检测结果
    ├── rubis/
    │   ├── detection_report.md
    │   ├── detection_results.json       # ← 推荐用于脚本
    │   └── detection_results.csv        # ← 推荐用于Excel
    ├── bsn/
    ├── swat/
    ├── wadi/
    │   ├── detection_results.json
    │   ├── detection_results_<algorithm>.json
    │   └── detection_report_<algorithm>.md
    └── wadi_trace/
```

**架构特点**:
- **三层架构**: CLI层 → 业务逻辑层 → 共享数据层
- **工厂模式**: ParserFactory和AlgorithmFactory支持动态注册
- **配置驱动**: YAML配置文件，零代码切换系统
- **插件化设计**: 新增系统只需实现Parser，新增算法只需继承BaseAlgorithm

---

## 🧮 聚类算法说明

框架支持4种无监督聚类算法，自动选择最佳算法（基于轮廓系数）：

### 1. HDBSCAN (层次DBSCAN)

**原理**: 基于密度的层次聚类，自动确定聚类数
- **优点**: 能识别任意形状的簇，自动过滤噪声点
- **参数**:
  - `min_cluster_size`: 最小簇大小（默认10）
  - `min_samples`: 核心点的邻域样本数（默认5）
- **适用场景**: 数据分布复杂、存在噪声点

### 2. GMM (高斯混合模型)

**原理**: 假设数据由多个高斯分布混合而成，使用BIC准则自动选择最佳聚类数
- **优点**: 提供概率分布参数（均值、协方差），适合正态分布数据
- **参数**:
  - `min_clusters`: 最小聚类数（默认2）
  - `max_clusters`: 最大聚类数（默认10）
  - `covariance_type`: 协方差类型（full/tied/diag/spherical）
- **适用场景**: 数据符合正态分布假设

### 3. Affinity Propagation (亲和传播)

**原理**: 通过消息传递机制，自动发现代表性样本点作为聚类中心
- **优点**: 不需要预先指定聚类数
- **参数**:
  - `damping`: 阻尼系数（默认0.5，范围0.5-1.0）
  - `max_iter`: 最大迭代次数（默认200）
- **适用场景**: 聚类数未知，数据规模中等

### 4. Mean Shift (均值漂移)

**原理**: 基于密度梯度上升，向数据密度最大的方向迭代
- **优点**: 不需要预先指定聚类数，能识别任意形状的簇
- **参数**:
  - `bandwidth`: 核函数带宽（null表示自动估计）
- **适用场景**: 数据有明显的密度峰值

### 算法选择策略

框架使用**轮廓系数 (Silhouette Score)** 自动选择最佳算法：
- 取值范围：[-1, 1]
- 值越高表示聚类效果越好
- > 0.7: 优秀
- 0.5 - 0.7: 良好
- 0.25 - 0.5: 一般
- < 0.25: 较差

**实际测试结果**:
- RUBIS: HDBSCAN (0.9915) ⭐
- BSN: GMM (0.9864) ⭐
- SWAT: GMM (0.9990) ⭐

---

## 📝 使用流程

### 完整工作流程

```bash
# 步骤1: 聚类分析（从identity数据学习分布）
python cluster.py --config configs/rubis_clustering_config.yaml
# ↓ 生成: clustering_results/rubis/learned_distributions.yaml

# 步骤2: 异常检测（使用学习到的分布检测abnormal数据）
python detect.py --config configs/rubis_detection_config.yaml
# ↓ 生成: detection_results/rubis/detection_results.json

# 步骤3: 分析结果（使用生成的JSON/CSV文件）
# 方法1: 使用Python脚本
import json
with open('detection_results/rubis/detection_results.json') as f:
    results = json.load(f)
    print(f"Precision: {results['performance_metrics']['precision']}")
    print(f"Recall: {results['performance_metrics']['recall']}")

# 方法2: 使用pandas分析CSV
import pandas as pd
df = pd.read_csv('detection_results/rubis/detection_results.csv')
print(df[['filename', 'tp', 'fp', 'precision']].head())
```

---

## ⚠️ 注意事项

### 1. 执行顺序

**必须先运行聚类分析，再运行异常检测**：
```bash
# ✅ 正确顺序
python cluster.py --config configs/rubis_clustering_config.yaml  # 先聚类
python detect.py --config configs/rubis_detection_config.yaml    # 后检测

# ❌ 错误顺序
python detect.py --config configs/rubis_detection_config.yaml    # 会报错！
# 错误: 分布参数文件不存在: clustering_results/rubis/learned_distributions.yaml
```

### 2. 数据准备

- **identity数据**: 必须存在，用于聚类分析
- **abnormal数据**: 检测时必须存在
  - ✅ RUBIS: 有200个abnormal traces
  - ⚠️ BSN: 目前没有abnormal数据
  - ⚠️ SWAT: 目前没有abnormal数据

### 3. 配置文件路径

- 所有配置文件中的路径均为**相对于项目根目录**
- 如果移动了数据目录，需要更新配置文件中的 `data_path` 和 `test_data_path`

### 4. 算法性能

- HDBSCAN和Mean Shift对大数据集（>5000点）可能较慢
- Affinity Propagation可能不收敛，出现警告是正常的
- GMM通常最快且效果好，推荐作为首选

### 5. 输出文件

- 每次运行会**覆盖**输出目录中的旧文件
- 如需保留历史结果，请在运行前备份或使用 `--output` 参数指定不同目录

---

## 🔧 扩展框架

### 添加新系统支持

1. **创建数据目录**:
   ```bash
   mkdir -p data/mysystem/identity
   mkdir -p data/mysystem/abnormal
   ```

2. **实现解析器** (`common/adapters/mysystem.py`):
   ```python
   from .base import TraceParser

   class MySystemParser(TraceParser):
       FILENAME_PATTERN = re.compile(r'...')
       TARGET_COLUMN = 'metric_name'
       TIME_COLUMN = 'time'

       def parse_filename(self, filename: str):
           # 实现文件名解析
           pass

       def parse_trace_file(self, filepath, metadata):
           # 实现文件读取和分段
           pass
   ```

3. **注册解析器** (`common/adapters/__init__.py`):
   ```python
   from .mysystem import MySystemParser
   PARSERS['mysystem'] = MySystemParser
   ```

4. **更新验证器** (添加'mysystem'到valid_types):
   - `cluster_analysis/config/config.py`: line 98
   - `anomaly_detection/config/config.py`: line 110

5. **创建配置文件**:
   - `configs/mysystem_clustering_config.yaml`
   - `configs/mysystem_detection_config.yaml`

---

## 📚 参考文档

- **数据迁移指南**: `MIGRATION_GUIDE.md` - 数据重组的详细说明
- **实施总结**: `IMPLEMENTATION_SUMMARY.md` - 完整的实施记录
- **OpenSpec提案**: `openspec/changes/refactor-data-layout-and-add-swat-support/`

---

## 📧 支持

如有问题，请检查：
1. Python版本是否 >= 3.8
2. 依赖是否正确安装：`pip install -r requirements.txt`
3. 配置文件路径是否正确
4. 数据文件是否存在于指定目录
5. 运行时添加 `--verbose` 参数查看详细日志

---

**版本**: 3.0.0
**最后更新**: 2026-01-16
**项目状态**: 生产就绪 ✅
