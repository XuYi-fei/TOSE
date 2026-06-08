# 聚类分析框架 (Clustering Analysis Framework)

自动发现trace数据分布参数的聚类分析框架，与validation框架紧密集成。

## 目录

- [功能特点](#功能特点)
- [架构设计](#架构设计)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [算法说明](#算法说明)
- [输出结果](#输出结果)
- [与Validation框架集成](#与validation框架集成)

## 功能特点

✅ **自动参数发现**: 从trace数据中自动发现分布参数（均值、方差）

✅ **多算法支持**: 内置4种无监督聚类算法：
- HDBSCAN: 基于密度的层次聚类
- GMM+BIC: 高斯混合模型，BIC自动选择聚类数
- Affinity Propagation: 基于消息传递的聚类
- Mean Shift: 基于密度峰值的聚类

✅ **算法可插拔**: 支持自定义算法注册和参数调优

✅ **丰富的可视化**: 提供4种可视化类型：
- 散点图（每个算法）
- 算法对比图
- 特征密度曲线
- 指标对比图

✅ **详细报告**: 自动生成Markdown格式的分析报告

✅ **高性能**: <10秒完成600+数据点的聚类分析

✅ **代码复用**: 与validation框架共享数据层，避免代码重复

## 架构设计

### 三层架构

```
┌─────────────────────────────────────┐
│   CLI Layer (cluster.py)            │
│   - 命令行接口                        │
│   - 配置加载                          │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│   Business Logic Layer               │
│   ┌──────────────────────────────┐  │
│   │ cluster_analysis/            │  │
│   │  - core: 引擎、结果          │  │
│   │  - algorithms: 聚类算法      │  │
│   │  - visualization: 可视化     │  │
│   │  - config: 配置管理          │  │
│   └──────────────────────────────┘  │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│   Common Data Layer (common/)       │
│   - adapters: ParserFactory         │
│   - models: TraceMetadata, Params   │
│   - utils: statistics               │
└─────────────────────────────────────┘
```

### 模块说明

#### cluster_analysis/core
- `engine.py`: 聚类引擎，协调整个分析流程
- `result.py`: 结果数据模型（ClusteringResult, AlgorithmResult）

#### cluster_analysis/algorithms
- `base.py`: 聚类算法抽象基类
- `factory.py`: 算法工厂，支持动态注册
- `hdbscan_algo.py`, `gmm_algo.py`, `affinity_propagation_algo.py`, `mean_shift_algo.py`: 4种算法实现

#### cluster_analysis/visualization
- `plotter.py`: 可视化绘图器
- `reporter.py`: Markdown报告生成器

#### cluster_analysis/config
- `config.py`: YAML配置加载和验证

#### common/
共享数据层，被validation和clustering框架共同使用：
- `adapters/`: RUBISParser, BSNParser, SWATParser, ParserFactory
- `models/`: TraceMetadata, DistributionParameters
- `utils/`: statistics函数

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

需要的包：
- pandas
- numpy
- matplotlib
- seaborn
- scikit-learn
- hdbscan
- scipy
- pyyaml

### 2. 准备数据

将trace数据放在对应的系统目录：
- RUBIS: `data/rubis/identity/`
- BSN: `data/bsn/identity/`
- SWAT: `data/swat/identity/`

### 3. 配置聚类

使用对应系统的配置文件：
- `configs/rubis_clustering_config.yaml`
- `configs/bsn_clustering_config.yaml`
- `configs/swat_clustering_config.yaml`

示例配置（SWAT）：

```yaml
system_type: swat
data_path: data/swat/identity
algorithms:
  - hdbscan
  - gmm
  - affinity_propagation
  - mean_shift
output:
  dir: clustering_results/swat
  visualizations: true
  report: true
  save_learned_distributions: true
  learned_distributions_path: clustering_results/swat/learned_distributions.yaml
```

### 4. 运行聚类

```bash
# 基本用法
python cluster.py --config configs/rubis_clustering_config.yaml

# 指定输出目录
python cluster.py --config configs/rubis_clustering_config.yaml --output results

# 详细日志
python cluster.py --config configs/rubis_clustering_config.yaml --verbose
```

### 5. 查看结果

聚类结果保存在 `clustering_results/rubis/`：
- `clustering_report.md`: 分析报告
- `scatter_*.png`: 各算法散点图
- `algorithm_comparison.png`: 算法对比图
- `density_curves.png`: 特征密度曲线
- `metrics_comparison.png`: 指标对比图

## 配置说明

### 完整配置示例

```yaml
# 系统类型 (必填)
system_type: rubis  # 或 bsn

# 数据路径 (必填)
data_path: rubis_evaluation_data/eval_ident_traces

# 聚类算法列表 (必填，至少一个)
algorithms:
  - hdbscan
  - gmm
  - affinity_propagation
  - mean_shift

# 算法参数配置 (可选)
algorithm_params:
  hdbscan:
    min_cluster_size: 10  # 最小簇大小
    min_samples: 5        # 核心点最小邻居数

  gmm:
    min_clusters: 2       # 最小聚类数
    max_clusters: 10      # 最大聚类数
    covariance_type: full # 协方差类型

  affinity_propagation:
    damping: 0.5          # 阻尼系数 (0.5-1.0)
    max_iter: 200         # 最大迭代次数

  mean_shift:
    bandwidth: null       # 带宽 (null表示自动估计)

# 输出配置 (可选)
output:
  dir: clustering_results/rubis  # 输出目录
  visualizations: true            # 是否生成可视化
  report: true                    # 是否生成报告
```

### 配置参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| system_type | string | 是 | 系统类型: `rubis` 或 `bsn` |
| data_path | string | 是 | trace文件目录路径 |
| algorithms | list | 是 | 要使用的算法列表 |
| algorithm_params | dict | 否 | 算法特定参数 |
| output.dir | string | 否 | 输出目录，默认 `clustering_results/{system_type}` |
| output.visualizations | boolean | 否 | 是否生成可视化，默认 `true` |
| output.report | boolean | 否 | 是否生成报告，默认 `true` |

## 算法说明

### 1. HDBSCAN (推荐)

**特点**:
- 基于层次密度的聚类
- 自动确定聚类数量
- 可以识别噪声点
- 适合发现不同密度的簇

**参数**:
- `min_cluster_size`: 最小簇大小（默认10）
- `min_samples`: 核心点的最小邻居数（默认5）

**适用场景**: 数据分布未知，可能有噪声点

### 2. GMM (Gaussian Mixture Model)

**特点**:
- 基于概率模型的聚类
- 使用BIC自动选择聚类数量
- 假设数据服从高斯分布
- 软聚类（每个点有属于各簇的概率）

**参数**:
- `min_clusters`: 最小聚类数（默认2）
- `max_clusters`: 最大聚类数（默认10）
- `covariance_type`: 协方差类型（默认full）

**适用场景**: 数据近似高斯分布，需要概率解释

### 3. Affinity Propagation

**特点**:
- 基于消息传递机制
- 自动确定聚类数量
- 选择数据点作为exemplar（代表点）
- 不需要预先指定聚类中心数

**参数**:
- `damping`: 阻尼系数（默认0.5）
- `max_iter`: 最大迭代次数（默认200）

**适用场景**: 不知道聚类数量，需要选择代表样本

### 4. Mean Shift

**特点**:
- 基于密度峰值检测
- 自动确定聚类数量
- 向密度最大的方向移动
- 不需要预先指定聚类数

**参数**:
- `bandwidth`: 带宽参数（null表示自动估计）

**适用场景**: 数据有明显的密度峰值

### 算法对比

| 算法 | 聚类数自动检测 | 噪声处理 | 速度 | 适合场景 |
|------|--------------|---------|------|---------|
| HDBSCAN | ✅ | ✅ | 快 | 未知分布，可能有噪声 |
| GMM | ✅ (BIC) | ❌ | 中 | 高斯分布数据 |
| Affinity Propagation | ✅ | ❌ | 慢 | 需要代表样本 |
| Mean Shift | ✅ | ❌ | 中 | 明显的密度峰值 |

## 输出结果

### 1. Markdown报告 (`clustering_report.md`)

包含以下部分：

#### 数据概述
- 系统类型、数据点数
- 特征统计（均值、方差的分布）

#### 算法结果汇总
- 各算法的聚类数、轮廓系数、执行时间
- 标注最佳算法

#### 最佳算法推荐
- 推荐理由（基于轮廓系数）
- 聚类质量评估

#### 详细算法结果
- 每个算法的聚类统计
- Norm标签分布
- 额外评估指标

#### 可视化图表
- 嵌入所有生成的图表

#### 聚类发现的分布参数
- 基于最佳算法的聚类中心
- 可直接用于validation配置

示例：
```markdown
| Cluster | Mean (μ) | Variance (σ²) | 样本数 | 主要Norm标签 |
|---------|----------|---------------|--------|-------------|
| 0 | 0.115244 | 0.000166 | 174 | norm2 |
| 1 | 0.028450 | 0.000003 | 166 | norm3 |
| 2 | 0.052544 | 0.000006 | 164 | norm1 |
```

### 2. 可视化图表

#### 散点图 (`scatter_*.png`)
- 展示每个算法的聚类结果
- X轴: Mean (响应时间均值)
- Y轴: Variance (方差)
- 不同颜色代表不同的簇
- 红色星标表示聚类中心

#### 算法对比图 (`algorithm_comparison.png`)
- 多子图并排展示所有算法结果
- 方便直观对比不同算法的聚类效果

#### 特征密度曲线 (`density_curves.png`)
- 左图: Mean的分布直方图和KDE密度估计
- 右图: Variance的分布直方图和KDE密度估计

#### 指标对比图 (`metrics_comparison.png`)
- 4个子图：
  1. 聚类数量对比（柱状图）
  2. 轮廓系数对比（柱状图）
  3. 执行时间对比（柱状图）
  4. 综合指标表格（高亮最佳算法）

### 3. 控制台输出

```
============================================================
聚类分析结果摘要
============================================================
⭐ hdbscan: 聚类数=3, 轮廓系数=0.9915, 耗时=0.190s
   gmm: 聚类数=3, 轮廓系数=0.9915, 耗时=0.223s
   affinity_propagation: 聚类数=340, 轮廓系数=0.3207, 耗时=0.353s
   mean_shift: 聚类数=5, 轮廓系数=0.7972, 耗时=0.427s
============================================================

✅ 最佳算法: hdbscan
输出目录: clustering_results/rubis
```

## 与Validation框架集成

### 典型工作流程

1. **数据探索阶段** - 使用聚类框架发现分布参数

```bash
python cluster.py --config configs/rubis_clustering_config.yaml
```

2. **提取参数** - 从报告中获取聚类中心

```
| Cluster | Mean (μ) | Variance (σ²) | 样本数 | 主要Norm标签 |
|---------|----------|---------------|--------|-------------|
| 0 | 0.115244 | 0.000166 | 174 | norm2 |
| 1 | 0.028450 | 0.000003 | 166 | norm3 |
| 2 | 0.052544 | 0.000006 | 164 | norm1 |
```

3. **配置验证** - 将参数写入validation配置文件

编辑 `configs/rubis_config.yaml`:

```yaml
expected_distributions:
  norm1:
    mu: 0.052544        # 从聚类中心获取
    sigma: 0.000006     # 从聚类中心获取

  norm2:
    mu: 0.115244
    sigma: 0.000166

  norm3:
    mu: 0.028450
    sigma: 0.000003
```

4. **运行验证** - 验证新数据

```bash
python validate.py --config configs/rubis_config.yaml
```

### 共享数据层

两个框架通过 `common/` 包共享以下组件：

```python
from common.adapters import ParserFactory, RUBISParser, BSNParser
from common.models import TraceMetadata, DistributionParameters
from common.utils import statistics
```

**优势**:
- ✅ 避免代码重复
- ✅ 一致的数据解析逻辑
- ✅ 统一的统计计算
- ✅ 易于维护和扩展

## 扩展指南

### 添加自定义聚类算法

1. 创建算法类继承 `ClusteringAlgorithm`:

```python
from cluster_analysis.algorithms.base import ClusteringAlgorithm
from cluster_analysis.algorithms.factory import register_algorithm

@register_algorithm('my_algorithm')
class MyAlgorithm(ClusteringAlgorithm):
    def fit_predict(self, X):
        # 实现聚类逻辑
        labels = ...
        return labels

    def get_n_clusters(self, labels):
        return len(np.unique(labels))
```

2. 在配置文件中使用:

```yaml
algorithms:
  - my_algorithm

algorithm_params:
  my_algorithm:
    param1: value1
```

### 添加新系统类型

1. 在 `common/adapters/` 下创建新的Parser类
2. 继承 `TraceParser` 并实现三个抽象方法:
   - `parse_filename()`
   - `parse_trace_file()`
   - `extract_parameters()`
3. 注册到 `ParserFactory`

## 性能

在标准笔记本电脑上（MacBook Pro M1）测试：

- **数据点**: 600+
- **总执行时间**: <10秒
  - HDBSCAN: ~0.2秒
  - GMM: ~0.2秒
  - Affinity Propagation: ~0.4秒
  - Mean Shift: ~0.4秒
  - 可视化生成: ~1秒

## 常见问题

### Q: 为什么有些算法聚类数差异很大？

A: 不同算法有不同的聚类策略：
- HDBSCAN和GMM倾向于找到真实的簇
- Affinity Propagation可能产生很多小簇（exemplar过多）
- Mean Shift对bandwidth敏感

**建议**: 优先参考轮廓系数高的算法（≥0.5表示质量优秀）

### Q: 如何调整算法参数？

A: 在配置文件的 `algorithm_params` 部分调整：
- HDBSCAN: 降低 `min_cluster_size` 可能发现更多簇
- GMM: 增大 `max_clusters` 范围
- Affinity Propagation: 调整 `damping` 和 `preference`
- Mean Shift: 手动指定 `bandwidth`

### Q: 聚类结果不理想怎么办？

A: 检查以下方面：
1. 数据质量：是否有异常值？
2. 特征选择：是否需要特征标准化？
3. 算法选择：尝试不同算法
4. 参数调优：根据数据特点调整参数

### Q: 如何解释轮廓系数？

A: 轮廓系数范围 [-1, 1]：
- **0.7-1.0**: 聚类质量优秀
- **0.5-0.7**: 聚类质量良好
- **0.3-0.5**: 聚类质量一般，结构不够清晰
- **<0.3**: 聚类质量差，可能没有明显的簇结构

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
