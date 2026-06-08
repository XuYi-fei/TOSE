# 聚类分析框架集成提案

## 为什么需要这个变更 (Why)

当前项目已经实现了数据验证框架 (`data_validation`)，能够验证RUBIS和BSN系统的identity数据是否符合期望的正态分布参数。然而，验证框架**假设我们已知期望的分布参数**（均值、方差），这些参数需要预先配置在YAML文件中。

在实际场景中，我们需要**从原始trace数据中自动发现和识别底层分布**的能力：

### 现有问题

1. **缺少分布发现能力**：无法从大量trace文件中自动识别出有多少种不同的分布
2. **参数依赖人工设定**：验证框架需要预先知道期望参数，缺少自动化参数提取
3. **代码重复**：归档的 `rubis_trace_clustering.py` 脚本包含聚类逻辑，但与验证框架独立，存在数据解析代码重复
4. **扩展性受限**：聚类算法硬编码在单一脚本中，难以插拔新算法
5. **系统支持单一**：现有聚类脚本只支持RUBIS，不支持BSN或其他未来系统

### 业务价值

聚类分析框架将提供以下价值：

- **自动化工作流**：identity数据 → 聚类分析 → 发现分布 → 验证配置 → 数据验证
- **未知分布识别**：在不预先知道分布数量和参数的情况下，自动识别数据中的模式
- **多算法验证**：通过多种聚类算法交叉验证，提高结果可信度
- **可扩展架构**：支持轻松添加新聚类算法和新数据源类型
- **完整工具链**：与验证框架无缝集成，形成"发现-验证"完整流程

## 变更内容 (What)

本变更将引入一个**独立但与验证框架深度集成的聚类分析模块**，具体包括：

### 1. 代码重构：提取公共层

- **新增** `common/` 包，包含：
  - `common/adapters/` - 从 `data_validation/adapters/` 提取的通用数据解析器
  - `common/models/` - 从 `data_validation/models/` 提取的通用数据模型
  - `common/utils/` - 从 `data_validation/utils/` 提取的通用工具函数

- **重构** `data_validation/` 包：
  - 依赖 `common` 包而非自己的 `adapters/` 和 `models/`
  - 保持向后兼容，验证功能不受影响

### 2. 新增聚类分析模块

- **新增** `cluster_analysis/` 独立包，包含：
  - `cluster_analysis/core/` - 聚类引擎核心
    - `clustering.py` - 聚类算法抽象基类和工厂
    - `config.py` - 聚类配置加载
    - `visualizer.py` - 结果可视化
    - `reporter.py` - 聚类报告生成

  - `cluster_analysis/algorithms/` - 聚类算法实现
    - `hdbscan_clusterer.py` - HDBSCAN算法
    - `gmm_bic_clusterer.py` - GMM+BIC算法
    - `affinity_propagation_clusterer.py` - Affinity Propagation算法
    - `mean_shift_clusterer.py` - Mean Shift算法
    - `__init__.py` - 算法注册工厂

  - `cluster_analysis/models/` - 聚类特有的数据模型
    - `clustering_result.py` - 聚类结果模型
    - `evaluation_metrics.py` - 评估指标模型

### 3. CLI和配置

- **新增** `cluster.py` - 聚类分析启动脚本（独立于 `validate.py`）
- **新增** 配置文件：
  - `configs/rubis_cluster.yaml` - RUBIS聚类配置
  - `configs/bsn_cluster.yaml` - BSN聚类配置
  - 配置项：数据路径、系统类型、算法选择、算法参数、输出设置

### 4. 可视化和报告

- **新增** 可视化输出（PNG格式）：
  - 参数空间散点图 (mean, variance) 带聚类标签
  - 每个算法的聚类结果对比（2x2子图）
  - 每个聚类中心的分布密度曲线

- **新增** Markdown报告：
  - 聚类统计摘要（聚类数、样本数、噪声点）
  - 评估指标（Silhouette Score、BIC等）
  - 每个聚类的参数表格（均值、方差、样本数）
  - 算法对比表格

### 5. 功能特性

- **可插拔算法**：通过 `ClusteringFactory.register()` 轻松注册自定义算法
- **多系统支持**：通过 `common/adapters/` 支持RUBIS、BSN及预留扩展接口
- **多算法并行**：同时运行多个算法，生成对比分析
- **配置驱动**：所有参数通过YAML配置，无需修改代码
- **快速执行**：要求所有算法在合理时间内完成（<10秒处理600个数据点）

## 影响范围 (Impact)

### 新增能力规范

本变更将新增以下能力规范（specs）：

1. **common-data-layer** - 公共数据层（adapters、models、utils）
2. **clustering-engine** - 聚类引擎核心功能
3. **clustering-algorithms** - 聚类算法插件系统
4. **clustering-visualization** - 可视化和报告生成
5. **clustering-integration** - 与验证框架的集成

### 修改的现有代码

- `data_validation/` 包将重构以依赖 `common/` 包
- 保持向后兼容：
  - `validate.py` 脚本功能不变
  - 现有配置文件 (`rubis_config.yaml`, `bsn_config.yaml`) 保持兼容
  - 现有API和导入路径保持兼容（通过re-export）

### 新增依赖

```python
# 已有依赖（验证框架已使用）
- numpy
- pandas
- pyyaml

# 新增依赖（聚类功能）
- scikit-learn >= 1.5.0  # HDBSCAN, GMM, AffinityPropagation, MeanShift
- matplotlib >= 3.8.0    # 可视化
- scipy >= 1.11.0        # 统计工具
```

### 项目结构变化

```
TOSE/
├── common/                      # 新增：公共数据层
│   ├── adapters/               # 从data_validation迁移
│   ├── models/                 # 从data_validation迁移
│   └── utils/                  # 从data_validation迁移
│
├── cluster_analysis/           # 新增：聚类分析模块
│   ├── core/
│   ├── algorithms/
│   └── models/
│
├── data_validation/            # 修改：依赖common
│   ├── core/
│   └── cli.py
│
├── cluster.py                  # 新增：聚类CLI入口
├── validate.py                 # 保持不变
│
├── configs/
│   ├── rubis_cluster.yaml      # 新增
│   └── bsn_cluster.yaml        # 新增
│
└── clustering_results/         # 新增：聚类输出目录
    ├── rubis/
    └── bsn/
```

## 成功标准 (Success Criteria)

1. **功能完整性**
   - [ ] 成功解析200个RUBIS trace文件，提取约600个分布参数点
   - [ ] 成功解析200个BSN trace文件，提取约600个分布参数点
   - [ ] 4种聚类算法全部成功运行并产生结果
   - [ ] 聚类结果理想情况下收敛到3个簇（匹配norm1/norm2/norm3）

2. **性能要求**
   - [ ] 完整聚类分析流程（数据加载+4种算法+可视化）< 10秒
   - [ ] 每个算法执行时间 < 3秒

3. **可扩展性**
   - [ ] 通过 `ClusteringFactory.register()` 可注册自定义算法
   - [ ] 通过 `ParserFactory.register()` 可注册新数据源类型
   - [ ] 添加新算法只需实现抽象基类，无需修改核心代码

4. **集成质量**
   - [ ] 验证框架功能不受影响，所有现有测试通过
   - [ ] `validate.py` 脚本行为保持不变
   - [ ] 公共层提取后，代码重复率降低 > 80%

5. **输出质量**
   - [ ] 生成4张可视化图表（参数散点图、算法对比、分布密度、评估指标）
   - [ ] 生成完整Markdown报告，包含统计、评估、对比
   - [ ] 图表清晰可读，标签中文化

6. **文档完善**
   - [ ] README.md 更新，包含聚类分析使用说明
   - [ ] 配置文件示例完整，包含注释说明
   - [ ] 代码文档（docstring）完整，中文注释清晰

## 风险和缓解

### 风险1：重构破坏现有功能

**风险**：将 `data_validation` 的代码提取到 `common/` 可能导致导入路径变化，破坏现有功能。

**缓解措施**：
- 在 `data_validation/__init__.py` 中re-export所有公共符号
- 创建兼容层，保持旧导入路径可用
- 完整回归测试验证框架功能

### 风险2：聚类算法性能问题

**风险**：某些算法（如Affinity Propagation）可能在600个数据点上运行缓慢。

**缓解措施**：
- 设置算法超时机制（单算法最大3秒）
- 提供算法选择配置，允许禁用慢算法
- 优化数据预处理，减少计算量

### 风险3：聚类结果不收敛到3簇

**风险**：算法可能识别出2个、4个或更多簇，不符合预期。

**缓解措施**：
- 这不是失败，而是数据洞察（说明数据分布可能有重叠或异常）
- 报告中明确标注期望簇数vs实际簇数
- 提供手动调整算法参数的能力

## 实施计划概览

实施分为6个阶段（详见 `tasks.md`）：

1. **Phase 1**: 提取公共层 (2-3天)
2. **Phase 2**: 实现聚类引擎核心 (2天)
3. **Phase 3**: 实现聚类算法 (2-3天)
4. **Phase 4**: 实现可视化和报告 (2天)
5. **Phase 5**: CLI和配置 (1天)
6. **Phase 6**: 集成测试和文档 (2天)

**总时间估算**：11-13天

## 相关文档

- **现有实现参考**：`rubis_trace_clustering.py`（归档脚本）
- **验证框架文档**：`openspec/changes/refactor-unified-data-validation-framework/`
- **设计细节**：`design.md`（本变更）
- **实施任务**：`tasks.md`（本变更）
