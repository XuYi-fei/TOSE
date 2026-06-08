# 聚类分析框架 - 架构设计

## 设计背景 (Context)

本设计旨在将归档的 `rubis_trace_clustering.py` 脚本重构为一个生产级、可扩展的聚类分析框架，同时与现有的数据验证框架深度集成。

### 核心挑战

1. **代码复用 vs 模块独立**：聚类功能需要复用验证框架的数据解析逻辑，但又要保持独立性
2. **算法可插拔性**：支持动态注册和选择不同的聚类算法
3. **多系统支持**：统一接口处理RUBIS、BSN及未来数据源的差异
4. **性能约束**：600个数据点的聚类分析需在10秒内完成
5. **向后兼容**：重构不能破坏现有验证框架功能

## 设计目标 (Goals)

### 核心目标

1. **模块化架构**：清晰分离公共层、验证层、聚类层
2. **高可扩展性**：算法和数据源均可通过注册机制扩展
3. **低耦合集成**：聚类和验证功能独立但共享数据层
4. **用户友好**：配置驱动，一键启动，图文并茂的输出

### 非目标

- 实时流式聚类（批处理即可）
- 分布式计算支持（单机性能足够）
- 交互式参数调优UI（命令行足够）
- 支持非高斯分布聚类（数据已知为高斯）

## 架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Layer                             │
│  ┌──────────────┐                    ┌──────────────┐       │
│  │  validate.py │                    │  cluster.py  │       │
│  └──────┬───────┘                    └──────┬───────┘       │
│         │                                   │                │
└─────────┼───────────────────────────────────┼────────────────┘
          │                                   │
┌─────────▼──────────────┐       ┌───────────▼──────────────┐
│  data_validation/      │       │  cluster_analysis/       │
│  ┌──────────────────┐  │       │  ┌──────────────────┐   │
│  │ Config           │  │       │  │ Config           │   │
│  │ Validator        │  │       │  │ ClusteringEngine │   │
│  │ Reporter         │  │       │  │ Visualizer       │   │
│  └──────────────────┘  │       │  │ Reporter         │   │
└────────────┬───────────┘       │  └──────────────────┘   │
             │                   │                          │
             │                   │  ┌──────────────────────┐
             │                   │  │ AlgorithmFactory     │
             │                   │  │ ├─ HDBSCAN          │
             │                   │  │ ├─ GMM+BIC          │
             │                   │  │ ├─ AffinityProp     │
             │                   │  │ └─ MeanShift        │
             │                   │  └──────────────────────┘
             │                   └────────────┬─────────────┘
             │                                │
             └────────────────┬───────────────┘
                              │
          ┌───────────────────▼───────────────────┐
          │         common/                       │
          │  ┌────────────────────────────────┐   │
          │  │ ParserFactory                  │   │
          │  │ ├─ RUBISParser                 │   │
          │  │ ├─ BSNParser                   │   │
          │  │ └─ [Extensible]                │   │
          │  └────────────────────────────────┘   │
          │                                       │
          │  ┌────────────────────────────────┐   │
          │  │ Data Models                    │   │
          │  │ ├─ TraceMetadata               │   │
          │  │ ├─ DistributionParameters      │   │
          │  │ └─ ExpectedDistribution        │   │
          │  └────────────────────────────────┘   │
          │                                       │
          │  ┌────────────────────────────────┐   │
          │  │ Utilities                      │   │
          │  │ ├─ statistics                  │   │
          │  │ └─ file_utils                  │   │
          │  └────────────────────────────────┘   │
          └───────────────────────────────────────┘
```

### 分层职责

#### Layer 1: CLI层

- **validate.py**：数据验证入口，依赖 `data_validation` 包
- **cluster.py**：聚类分析入口，依赖 `cluster_analysis` 包
- 两者独立，互不依赖

#### Layer 2: 业务逻辑层

**data_validation/** - 验证业务逻辑
- `core/config.py` - 验证配置加载
- `core/validator.py` - 验证引擎（均值偏离、范围检查）
- `core/reporter.py` - 验证报告生成
- 依赖：`common.adapters`, `common.models`, `common.utils`

**cluster_analysis/** - 聚类业务逻辑
- `core/config.py` - 聚类配置加载
- `core/clustering.py` - 聚类引擎协调器
- `core/visualizer.py` - 可视化生成
- `core/reporter.py` - 聚类报告生成
- `algorithms/*.py` - 具体算法实现
- 依赖：`common.adapters`, `common.models`, `common.utils`

#### Layer 3: 公共数据层

**common/** - 共享基础设施
- `adapters/` - 数据源适配器（从 `data_validation` 迁移）
  - `parser.py` - 抽象基类 `TraceParser`
  - `rubis.py` - `RUBISParser` 实现
  - `bsn.py` - `BSNParser` 实现
  - `factory.py` - `ParserFactory` 工厂类

- `models/` - 通用数据模型（从 `data_validation` 迁移）
  - `metadata.py` - `TraceMetadata`, `RUBISMetadata`, `BSNMetadata`
  - `distribution.py` - `DistributionParameters`, `ExpectedDistribution`

- `utils/` - 通用工具（从 `data_validation` 迁移）
  - `statistics.py` - 统计计算函数
  - `file_utils.py` - 文件操作工具

## 关键设计决策

### 决策 1: 三层架构 - 提取公共层

**选择**：创建独立的 `common/` 包，将 `data_validation` 的 adapters、models、utils 迁移过来

**理由**：
- **代码复用**：避免在 `cluster_analysis` 中重复实现数据解析逻辑
- **单一职责**：`common` 专注数据读取和模型定义，业务逻辑在上层
- **易于扩展**：新数据源只需在 `common.adapters` 中实现，两个功能自动支持
- **依赖清晰**：`data_validation` 和 `cluster_analysis` 都依赖 `common`，但彼此独立

**备选方案**：
- **方案A：cluster_analysis 直接依赖 data_validation**
  - 问题：耦合度过高，聚类功能依赖验证逻辑（不合理）

- **方案B：代码复制到 cluster_analysis**
  - 问题：违反DRY原则，维护成本翻倍

**权衡**：需要进行一次性重构迁移，但长期收益显著

---

### 决策 2: 算法可插拔 - 工厂+注册模式

**选择**：使用 `ClusteringFactory` + 注册机制实现算法可插拔

**架构**：

```python
# cluster_analysis/core/clustering.py
from abc import ABC, abstractmethod

class ClusteringAlgorithm(ABC):
    """聚类算法抽象基类"""

    @abstractmethod
    def fit_predict(self, data: np.ndarray) -> ClusteringResult:
        """执行聚类并返回结果"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """返回算法名称"""
        pass

class ClusteringFactory:
    """聚类算法工厂"""
    _registry: Dict[str, Type[ClusteringAlgorithm]] = {}

    @classmethod
    def register(cls, name: str, algorithm_class: Type[ClusteringAlgorithm]):
        """注册新算法"""
        cls._registry[name] = algorithm_class

    @classmethod
    def create(cls, name: str, **kwargs) -> ClusteringAlgorithm:
        """创建算法实例"""
        if name not in cls._registry:
            raise ValueError(f"Unknown algorithm: {name}")
        return cls._registry[name](**kwargs)

    @classmethod
    def list_algorithms(cls) -> List[str]:
        """列出所有已注册算法"""
        return list(cls._registry.keys())

# cluster_analysis/algorithms/__init__.py
from .hdbscan_clusterer import HDBSCANClusterer
from .gmm_bic_clusterer import GMMBICClusterer
from ..core.clustering import ClusteringFactory

# 自动注册内置算法
ClusteringFactory.register('hdbscan', HDBSCANClusterer)
ClusteringFactory.register('gmm_bic', GMMBICClusterer)
# ...
```

**使用方式**：

```python
# 用户可以注册自定义算法
from cluster_analysis.core.clustering import ClusteringAlgorithm, ClusteringFactory

class MyCustomClusterer(ClusteringAlgorithm):
    def fit_predict(self, data):
        # 自定义实现
        pass

    def get_name(self):
        return "My Custom Algorithm"

ClusteringFactory.register('custom', MyCustomClusterer)

# 配置文件中使用
# algorithms:
#   - name: hdbscan
#   - name: gmm_bic
#   - name: custom
```

**理由**：
- 符合开闭原则：对扩展开放，对修改封闭
- 类似 `ParserFactory` 的设计，用户熟悉
- 运行时动态注册，灵活性高

**备选方案**：
- **插件系统（基于文件扫描）**：过度工程，增加复杂度
- **配置文件指定类路径**：需要动态导入，调试困难

---

### 决策 3: 独立CLI vs 统一CLI

**选择**：创建独立的 `cluster.py` 脚本

**理由**：
- **职责清晰**：`validate.py` 专注验证，`cluster.py` 专注聚类
- **参数简洁**：各自的命令行参数更聚焦，不会互相干扰
- **独立配置**：聚类和验证的配置文件格式不同，分开更清晰
- **易于理解**：用户明确知道每个脚本的用途

**使用示例**：

```bash
# 验证工作流
python validate.py --config configs/rubis_config.yaml

# 聚类工作流
python cluster.py --config configs/rubis_cluster.yaml

# 完整工作流（手动串联）
python cluster.py --config configs/rubis_cluster.yaml  # 发现分布
# 查看聚类结果，更新rubis_config.yaml的期望参数
python validate.py --config configs/rubis_config.yaml  # 验证数据
```

**备选方案**：
- **统一CLI**：`python validate.py --mode cluster`
  - 问题：参数混杂，`--mode` 需要控制大量互斥参数
  - 问题：配置文件需要同时包含验证和聚类配置，冗长

---

### 决策 4: 特征空间 - (Mean, Variance)

**选择**：使用2D特征空间 `[mean, variance]`

**理由**：
- **领域匹配**：均值和方差是高斯分布的两个决定性参数
- **可解释性强**：可视化直观，符合统计学直觉
- **计算高效**：2D聚类算法性能最优
- **已验证**：归档脚本使用此方案，效果良好

**不使用的方案**：
- **(Mean, StdDev)**：标准差 = sqrt(方差)，信息等价但方差更稳定
- **归一化特征**：两个维度量级接近，不需要标准化
- **高维特征**（如样本数、偏度、峰度）：过度复杂，对区分分布无帮助

---

### 决策 5: 聚类算法选择

**选择**：实现4种算法 - HDBSCAN, GMM+BIC, Affinity Propagation, Mean Shift

**每种算法的特点**：

| 算法 | 优势 | 劣势 | 适用场景 |
|------|------|------|----------|
| **HDBSCAN** | 自动确定簇数，处理噪声点，鲁棒性强 | 需调整min_samples参数 | **推荐首选** |
| **GMM+BIC** | 概率模型，适合高斯数据，BIC自动选模型 | 对初始化敏感 | 验证HDBSCAN结果 |
| **Affinity Propagation** | 无需预设簇数，基于消息传递 | 计算复杂度O(N²)，可能较慢 | 小数据集 |
| **Mean Shift** | 自动确定簇数，基于密度 | 带宽参数影响大 | 密度变化明显场景 |

**理由**：
- **多样性**：覆盖密度、概率、消息传递三类方法
- **交叉验证**：多算法结果一致性高 → 结果可信
- **性能可控**：4种算法在600个点上均可在3秒内完成

**配置示例**：

```yaml
# configs/rubis_cluster.yaml
algorithms:
  - name: hdbscan
    params:
      min_samples: 5
      min_cluster_size: 10

  - name: gmm_bic
    params:
      max_components: 10

  - name: affinity_propagation
    params:
      damping: 0.9

  - name: mean_shift
    params:
      quantile: 0.2
```

---

### 决策 6: 可视化设计

**选择**：生成4类可视化图表

**图表类型**：

1. **参数空间散点图** (`clustering_parameter_space.png`)
   - X轴：mean，Y轴：variance
   - 颜色：聚类标签（噪声点用灰色）
   - 标注：每个聚类中心
   - 目的：直观展示聚类结果

2. **算法对比图** (`clustering_comparison.png`)
   - 2x2子图，每个算法一个散点图
   - 统一颜色映射（cluster0=红色，cluster1=蓝色，cluster2=绿色）
   - 标题显示算法名+簇数+silhouette分数
   - 目的：对比不同算法的聚类效果

3. **分布密度图** (`distributions_density.png`)
   - 每个聚类一条高斯曲线
   - 基于聚类中心的均值和方差绘制
   - X轴：响应时间，Y轴：概率密度
   - 目的：展示恢复出的分布形状

4. **评估指标图** (`evaluation_metrics.png`)
   - 柱状图：横轴=算法名，纵轴=Silhouette Score
   - 表格：每个算法的簇数、噪声点数、最大簇大小
   - 目的：量化评估聚类质量

**实现技术**：
- Matplotlib + Seaborn
- 中文字体支持（`plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']`）
- 高分辨率输出（300 DPI）

---

### 决策 7: 配置文件设计

**选择**：独立的聚类配置文件 `rubis_cluster.yaml`, `bsn_cluster.yaml`

**配置结构**：

```yaml
# configs/rubis_cluster.yaml

# 系统类型（与验证框架保持一致）
system_type: rubis

# 数据路径
data_path: rubis_evaluation_data/eval_ident_traces

# 输出目录
output_dir: clustering_results/rubis

# 聚类算法配置
algorithms:
  - name: hdbscan
    enabled: true
    params:
      min_samples: 5
      min_cluster_size: 10

  - name: gmm_bic
    enabled: true
    params:
      max_components: 10

  - name: affinity_propagation
    enabled: false  # 可选禁用某些算法
    params:
      damping: 0.9

  - name: mean_shift
    enabled: true
    params:
      quantile: 0.2

# 可视化配置
visualization:
  dpi: 300
  figsize: [12, 10]
  show_noise: true
  colormap: 'viridis'

# 期望簇数（用于评估，不影响聚类）
expected_clusters: 3

# 性能配置
performance:
  algorithm_timeout: 3  # 单算法最大执行时间（秒）
  max_workers: 4        # 并行执行算法数
```

**配置加载**：

```python
# cluster_analysis/core/config.py
from dataclasses import dataclass
from typing import List, Dict, Any
import yaml

@dataclass
class AlgorithmConfig:
    name: str
    enabled: bool
    params: Dict[str, Any]

@dataclass
class ClusteringConfig:
    system_type: str
    data_path: str
    output_dir: str
    algorithms: List[AlgorithmConfig]
    expected_clusters: int
    visualization: Dict[str, Any]
    performance: Dict[str, Any]

    @classmethod
    def from_yaml(cls, path: str) -> 'ClusteringConfig':
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        algorithms = [
            AlgorithmConfig(**alg) for alg in data['algorithms']
        ]

        return cls(
            system_type=data['system_type'],
            data_path=data['data_path'],
            output_dir=data['output_dir'],
            algorithms=algorithms,
            expected_clusters=data.get('expected_clusters', 3),
            visualization=data.get('visualization', {}),
            performance=data.get('performance', {})
        )
```

---

### 决策 8: 性能优化策略

**目标**：600个数据点，4种算法，总时间 < 10秒

**优化措施**：

1. **算法并行执行**
   ```python
   from concurrent.futures import ThreadPoolExecutor, TimeoutError

   def run_all_algorithms_parallel(data, algorithms):
       with ThreadPoolExecutor(max_workers=4) as executor:
           futures = {
               executor.submit(alg.fit_predict, data): alg
               for alg in algorithms
           }

           results = []
           for future in futures:
               try:
                   result = future.result(timeout=3)  # 单算法3秒超时
                   results.append(result)
               except TimeoutError:
                   logger.warning(f"{futures[future].get_name()} 超时，跳过")

           return results
   ```

2. **数据预处理缓存**
   - 文件解析结果缓存到内存，避免重复读取
   - 提取的分布参数数组缓存，多算法共享

3. **可视化延迟生成**
   - 聚类完成后才生成图表
   - 用户可选择跳过可视化（`--no-viz`标志）

4. **算法参数优化**
   - HDBSCAN: 使用合理的min_samples（5-10）
   - GMM: 限制max_components（<15）
   - Affinity Propagation: 增大damping（0.9）减少迭代

**性能测试**（预期）：

| 阶段 | 时间 | 备注 |
|------|------|------|
| 数据加载+解析 | ~2秒 | 读取200个文件 |
| 4种算法（并行） | ~3秒 | 最慢算法决定 |
| 可视化生成 | ~2秒 | 4张图表 |
| 报告生成 | ~0.5秒 | Markdown |
| **总计** | **~8秒** | ✓ 满足 <10秒要求 |

---

## 数据流设计

### 聚类分析数据流

```
┌─────────────┐
│ Trace Files │ (200个文件)
└──────┬──────┘
       │
       │ ParserFactory.create(system_type)
       ▼
┌──────────────────┐
│  RUBISParser /   │ 解析文件名 → TraceMetadata
│  BSNParser       │ 分段读取 → segments: Dict[norm_label, DataFrame]
└──────┬───────────┘
       │
       │ 提取每段的 (mean, variance)
       ▼
┌─────────────────────────┐
│ DistributionParameters  │ (约600个数据点)
│ - mean: float           │
│ - variance: float       │
│ - norm_label: str       │
│ - filename: str         │
└──────┬──────────────────┘
       │
       │ 转换为 NumPy 数组 (N, 2)
       ▼
┌──────────────────────┐
│  Feature Matrix      │  [[mean1, var1],
│  (600, 2)            │   [mean2, var2],
└──────┬───────────────┘   ...]
       │
       │ 并行执行4种算法
       ▼
┌──────────────────────────────────────────┐
│  ClusteringResult (x4)                   │
│  - algorithm_name: str                   │
│  - labels: ndarray (600,)                │
│  - n_clusters: int                       │
│  - n_noise: int                          │
│  - silhouette_score: float               │
│  - cluster_centers: ndarray (K, 2)       │
└──────┬───────────────────────────────────┘
       │
       ├───────────────┬────────────────┐
       │               │                │
       ▼               ▼                ▼
┌────────────┐  ┌────────────┐  ┌────────────┐
│ Visualizer │  │  Reporter  │  │  Console   │
│            │  │            │  │   Output   │
│ 4张PNG图   │  │ Markdown   │  │  Summary   │
└────────────┘  └────────────┘  └────────────┘
```

### 与验证框架的集成流程

```
用户工作流：

1. 发现阶段（聚类分析）
   python cluster.py --config configs/rubis_cluster.yaml
   ↓
   输出：clustering_results/rubis/
   - clustering_parameter_space.png
   - clustering_comparison.png
   - distributions_density.png
   - clustering_report.md

   查看报告，识别出3个聚类：
   - Cluster 0: mean=0.0526, variance=0.000006
   - Cluster 1: mean=0.1154, variance=0.000161
   - Cluster 2: mean=0.0285, variance=0.000003

2. 配置更新
   手动更新 configs/rubis_config.yaml：
   expected_distributions:
     norm1:
       mu: 0.0526
       sigma: 0.0024  # sqrt(variance)
     norm2:
       mu: 0.1154
       sigma: 0.0127
     norm3:
       mu: 0.0285
       sigma: 0.0018

3. 验证阶段
   python validate.py --config configs/rubis_config.yaml
   ↓
   输出：validation_results/rubis/validation_report.md
   验证数据是否符合发现的分布参数
```

**未来自动化扩展**（可选）：
```bash
# 一键工作流（未来可实现）
python auto_analyze.py --system rubis \
  --cluster-config configs/rubis_cluster.yaml \
  --validate-config configs/rubis_config.yaml \
  --auto-update-config

# 自动执行：聚类 → 更新配置 → 验证
```

---

## 向后兼容性策略

### 迁移计划

**Phase 1: 创建 common/ 包**
- 复制 `data_validation/{adapters,models,utils}` 到 `common/`
- 保持原文件不删除

**Phase 2: 更新 data_validation 导入**
```python
# data_validation/core/validator.py (旧)
from ..adapters import ParserFactory
from ..models.distribution import DistributionParameters

# data_validation/core/validator.py (新)
from common.adapters import ParserFactory
from common.models.distribution import DistributionParameters
```

**Phase 3: 兼容层 (data_validation/__init__.py)**
```python
# 重新导出，保持旧导入路径可用
from common.adapters import ParserFactory, RUBISParser, BSNParser
from common.models import TraceMetadata, DistributionParameters

__all__ = ['ParserFactory', 'RUBISParser', 'BSNParser',
           'TraceMetadata', 'DistributionParameters']
```

这样旧代码仍可使用：
```python
# 旧代码仍能工作
from data_validation.adapters import RUBISParser  # 通过re-export
```

**Phase 4: 删除旧文件**
- 删除 `data_validation/{adapters,models,utils}`
- 保留兼容层导出

---

## 测试策略

### 单元测试

```python
# tests/test_clustering_factory.py
def test_register_custom_algorithm():
    class MockClusterer(ClusteringAlgorithm):
        def fit_predict(self, data):
            return ClusteringResult(...)
        def get_name(self):
            return "Mock"

    ClusteringFactory.register('mock', MockClusterer)
    assert 'mock' in ClusteringFactory.list_algorithms()

    clusterer = ClusteringFactory.create('mock')
    assert isinstance(clusterer, MockClusterer)

# tests/test_common_adapters.py
def test_rubis_parser_compatibility():
    # 验证从 data_validation 迁移到 common 后功能不变
    from common.adapters import RUBISParser
    parser = RUBISParser()
    # ... 测试解析逻辑
```

### 集成测试

```python
# tests/test_clustering_pipeline.py
def test_full_clustering_pipeline():
    config = ClusteringConfig.from_yaml('configs/rubis_cluster.yaml')

    # 加载数据
    parser = ParserFactory.create(config.system_type)
    distributions = load_all_distributions(config.data_path, parser)

    # 聚类
    engine = ClusteringEngine(config)
    results = engine.run(distributions)

    # 断言
    assert len(results) == 4  # 4种算法
    assert all(r.n_clusters >= 2 for r in results)  # 至少2个簇
```

### 性能测试

```python
import time

def test_performance_requirement():
    start = time.time()

    # 完整聚类流程
    run_clustering_analysis('configs/rubis_cluster.yaml')

    elapsed = time.time() - start
    assert elapsed < 10, f"聚类分析耗时{elapsed:.2f}秒，超过10秒要求"
```

---

## 安全性和错误处理

### 配置验证

```python
def validate_config(config: ClusteringConfig):
    # 检查路径存在
    if not Path(config.data_path).exists():
        raise ValueError(f"数据路径不存在: {config.data_path}")

    # 检查算法名称合法
    for alg in config.algorithms:
        if alg.name not in ClusteringFactory.list_algorithms():
            raise ValueError(f"未知算法: {alg.name}")

    # 检查参数合理性
    if config.expected_clusters < 1:
        raise ValueError("expected_clusters 必须 >= 1")
```

### 异常处理策略

```python
# 单算法失败不影响其他算法
try:
    result = algorithm.fit_predict(data)
    results.append(result)
except Exception as e:
    logger.error(f"算法 {algorithm.get_name()} 失败: {e}")
    # 记录失败但继续执行其他算法

# 至少一个算法成功才生成报告
if len(results) == 0:
    raise RuntimeError("所有聚类算法均失败，无法生成报告")
```

---

## 可维护性

### 代码规范

- 所有函数和类包含中文docstring
- 类型注解覆盖率 100%
- 遵循PEP 8代码风格
- 使用dataclass简化模型定义

### 日志策略

```python
import logging

logger = logging.getLogger('cluster_analysis')

# 不同级别日志
logger.debug("加载trace文件: {filename}")  # 详细调试信息
logger.info("开始运行HDBSCAN算法")          # 关键步骤
logger.warning("算法超时，跳过Affinity Propagation")  # 警告
logger.error("数据解析失败: {error}")      # 错误
```

### 文档要求

每个模块包含：
- 模块级docstring（中文）
- 每个公共函数/类的docstring
- 复杂逻辑的行内注释
- README示例代码

---

## 总结

本设计通过**三层架构**（CLI层、业务层、公共层）实现了聚类功能与验证框架的**低耦合集成**，同时保持了**高内聚**和**可扩展性**。

**核心优势**：
1. ✅ 代码复用率高（公共层共享）
2. ✅ 模块独立性强（CLI和业务逻辑解耦）
3. ✅ 扩展性好（工厂+注册模式）
4. ✅ 性能满足要求（<10秒）
5. ✅ 向后兼容（验证框架功能不受影响）

**下一步**：
- 查看 `specs/` 目录下的详细能力规范
- 查看 `tasks.md` 了解实施步骤
