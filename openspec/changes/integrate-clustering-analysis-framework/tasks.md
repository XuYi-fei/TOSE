# 任务清单 - 聚类分析框架集成

## Phase 1: 公共层提取和重构 (Common Layer Extraction)

### 1.1 创建common包结构
- [ ] 创建 `common/` 目录及子目录结构
- [ ] 创建 `common/{adapters,models,utils}` 子包
- [ ] 创建所有 `__init__.py` 文件
- [ ] 验证：目录结构完整，包可导入

### 1.2 迁移adapters模块
- [ ] 复制 `data_validation/adapters/` 到 `common/adapters/`
- [ ] 保留原文件，暂不删除（确保向后兼容）
- [ ] 更新 `common/adapters/__init__.py`，导出ParserFactory
- [ ] 更新 `common/adapters/parser.py` 导入路径（如有需要）
- [ ] 验证：`from common.adapters import ParserFactory` 成功

### 1.3 迁移models模块
- [ ] 复制 `data_validation/models/` 到 `common/models/`
- [ ] 保留原文件
- [ ] 更新 `common/models/__init__.py`，导出所有模型类
- [ ] 验证：`from common.models import TraceMetadata, DistributionParameters` 成功

### 1.4 迁移utils模块
- [ ] 复制 `data_validation/utils/` 到 `common/utils/`
- [ ] 保留原文件
- [ ] 更新 `common/utils/__init__.py`，导出工具函数
- [ ] 验证：`from common.utils import statistics` 成功

### 1.5 更新data_validation导入
- [ ] 更新 `data_validation/core/validator.py` 导入路径
- [ ] 更新 `data_validation/core/reporter.py` 导入路径
- [ ] 更新 `data_validation/cli.py` 导入路径
- [ ] 验证：运行 `python validate.py --config configs/rubis_config.yaml`，功能正常

### 1.6 创建兼容层
- [ ] 在 `data_validation/__init__.py` 中re-export common模块
- [ ] 测试旧导入路径：`from data_validation.adapters import RUBISParser`
- [ ] 确保所有旧导入路径仍可用
- [ ] 验证：现有代码无需修改即可运行

### 1.7 删除冗余文件
- [ ] 删除 `data_validation/adapters/` 目录（保留__init__.py作为re-export）
- [ ] 删除 `data_validation/models/` 目录（保留__init__.py作为re-export）
- [ ] 删除 `data_validation/utils/` 目录（保留__init__.py作为re-export）
- [ ] 验证：验证框架功能不受影响

---

## Phase 2: 聚类引擎核心实现 (Clustering Engine Core)

### 2.1 创建cluster_analysis包结构
- [ ] 创建 `cluster_analysis/` 目录
- [ ] 创建 `cluster_analysis/{core,algorithms,models}` 子包
- [ ] 创建所有 `__init__.py` 文件
- [ ] 验证：包结构清晰

### 2.2 实现配置模块
- [ ] 创建 `cluster_analysis/core/config.py`
- [ ] 定义 `AlgorithmConfig` dataclass
- [ ] 定义 `ClusteringConfig` dataclass
- [ ] 实现 `ClusteringConfig.from_yaml()` 方法
- [ ] 实现 `validate_config()` 函数
- [ ] 验证：可加载 `configs/rubis_cluster.yaml`（待创建）

### 2.3 实现聚类抽象基类
- [ ] 创建 `cluster_analysis/core/clustering.py`
- [ ] 定义 `ClusteringAlgorithm` ABC
- [ ] 定义必需方法：`fit_predict()`, `get_name()`
- [ ] 定义 `ClusteringResult` dataclass
- [ ] 添加中文docstring
- [ ] 验证：基类可被继承

### 2.4 实现聚类工厂
- [ ] 在 `clustering.py` 中实现 `ClusteringFactory` 类
- [ ] 实现 `register()` 类方法
- [ ] 实现 `create()` 类方法
- [ ] 实现 `list_algorithms()` 类方法
- [ ] 添加单元测试验证工厂模式
- [ ] 验证：可注册和创建算法实例

### 2.5 实现聚类引擎协调器
- [ ] 创建 `ClusteringEngine` 类
- [ ] 实现 `load_data()` 方法（使用common.adapters）
- [ ] 实现 `prepare_features()` 方法（转换为NumPy数组）
- [ ] 实现 `run_clustering()` 方法（并行执行算法）
- [ ] 实现 `evaluate_results()` 方法（计算silhouette等指标）
- [ ] 实现超时和异常处理
- [ ] 验证：可协调完整聚类流程

### 2.6 实现数据模型
- [ ] 创建 `cluster_analysis/models/clustering_result.py`
- [ ] 定义 `ClusteringResult` dataclass（如未在core中定义）
- [ ] 创建 `cluster_analysis/models/evaluation_metrics.py`
- [ ] 定义 `ClusterEvaluationMetrics` dataclass
- [ ] 验证：模型可实例化

---

## Phase 3: 聚类算法实现 (Clustering Algorithms)

### 3.1 实现HDBSCAN算法
- [ ] 创建 `cluster_analysis/algorithms/hdbscan_clusterer.py`
- [ ] 实现 `HDBSCANClusterer(ClusteringAlgorithm)`
- [ ] 实现 `fit_predict()` 方法
- [ ] 实现 `get_name()` 方法
- [ ] 处理噪声点（label=-1）
- [ ] 计算silhouette score（排除噪声点）
- [ ] 验证：在合成数据上测试，识别3个簇

### 3.2 实现GMM+BIC算法
- [ ] 创建 `cluster_analysis/algorithms/gmm_bic_clusterer.py`
- [ ] 实现 `GMMBICClusterer(ClusteringAlgorithm)`
- [ ] 实现 `fit_predict()` 方法（遍历1到max_components）
- [ ] 计算每个模型的BIC
- [ ] 选择最小BIC的模型
- [ ] 验证：在高斯数据上测试，自动选择正确component数

### 3.3 实现Affinity Propagation算法
- [ ] 创建 `cluster_analysis/algorithms/affinity_propagation_clusterer.py`
- [ ] 实现 `AffinityPropagationClusterer(ClusteringAlgorithm)`
- [ ] 实现 `fit_predict()` 方法
- [ ] 配置damping参数（默认0.9）
- [ ] 处理收敛失败情况
- [ ] 验证：在600个点上测试，< 3秒完成

### 3.4 实现Mean Shift算法
- [ ] 创建 `cluster_analysis/algorithms/mean_shift_clusterer.py`
- [ ] 实现 `MeanShiftClusterer(ClusteringAlgorithm)`
- [ ] 实现 `fit_predict()` 方法
- [ ] 实现自动带宽估计（`estimate_bandwidth()`）
- [ ] 验证：在不同密度数据上测试

### 3.5 注册所有算法
- [ ] 在 `cluster_analysis/algorithms/__init__.py` 中导入所有算法
- [ ] 自动注册所有算法到 `ClusteringFactory`
- [ ] 验证：`ClusteringFactory.list_algorithms()` 返回4个算法

### 3.6 算法单元测试
- [ ] 为每个算法编写单元测试
- [ ] 测试合成数据（3个高斯分布）
- [ ] 测试性能（< 3秒）
- [ ] 测试异常处理
- [ ] 验证：所有算法测试通过

---

## Phase 4: 可视化和报告 (Visualization & Reporting)

### 4.1 实现可视化模块基础
- [ ] 创建 `cluster_analysis/core/visualizer.py`
- [ ] 实现 `Visualizer` 类
- [ ] 配置matplotlib中文字体支持
- [ ] 实现 `_setup_chinese_fonts()` 私有方法
- [ ] 验证：中文标签正常显示

### 4.2 实现参数空间散点图
- [ ] 实现 `plot_parameter_space()` 方法
- [ ] X轴：mean，Y轴：variance
- [ ] 颜色映射：按簇标签
- [ ] 标注聚类中心
- [ ] 噪声点灰色显示
- [ ] 验证：生成清晰可读的PNG图表

### 4.3 实现算法对比图
- [ ] 实现 `plot_algorithm_comparison()` 方法
- [ ] 2x2子图网格
- [ ] 每个算法一个散点图
- [ ] 统一轴范围和颜色映射
- [ ] 标题显示算法名+簇数+silhouette
- [ ] 验证：4个算法对比清晰

### 4.4 实现分布密度图
- [ ] 实现 `plot_distributions()` 方法
- [ ] 为每个簇绘制高斯PDF曲线
- [ ] 使用簇中心的均值和方差
- [ ] 颜色与散点图一致
- [ ] 验证：曲线形状正确

### 4.5 实现评估指标图
- [ ] 实现 `plot_metrics()` 方法
- [ ] 柱状图：silhouette scores
- [ ] 簇大小分布图
- [ ] 算法一致性矩阵（可选）
- [ ] 验证：指标可视化清晰

### 4.6 实现报告生成器
- [ ] 创建 `cluster_analysis/core/reporter.py`
- [ ] 实现 `Reporter` 类
- [ ] 实现 `generate_report()` 方法
- [ ] 生成Markdown格式报告
- [ ] 包含：摘要表格、统计、算法对比、建议
- [ ] 嵌入可视化图表链接
- [ ] 生成建议的验证配置YAML片段
- [ ] 验证：报告完整、格式正确

---

## Phase 5: CLI和配置 (CLI & Configuration)

### 5.1 创建配置文件
- [ ] 创建 `configs/rubis_cluster.yaml`
- [ ] 定义system_type, data_path, output_dir
- [ ] 定义algorithms列表（4个算法）
- [ ] 定义visualization配置
- [ ] 定义performance配置
- [ ] 添加中文注释说明
- [ ] 创建 `configs/bsn_cluster.yaml`（类似结构）
- [ ] 验证：配置文件可正常加载

### 5.2 实现CLI模块
- [ ] 创建 `cluster_analysis/cli.py`
- [ ] 使用argparse解析命令行参数
- [ ] 支持参数：`--config`, `--output`, `--algorithms`, `--verbose`
- [ ] 实现 `run_clustering_analysis()` 函数
- [ ] 实现进度显示
- [ ] 实现错误处理和友好提示
- [ ] 验证：命令行参数解析正确

### 5.3 创建启动脚本
- [ ] 创建 `cluster.py` 脚本（项目根目录）
- [ ] 简单包装调用 `cluster_analysis.cli.main()`
- [ ] 添加使用帮助信息（中文）
- [ ] 测试：`python cluster.py --help` 输出清晰
- [ ] 测试：`python cluster.py --config configs/rubis_cluster.yaml` 正常运行

### 5.4 集成测试 - 端到端
- [ ] 运行 `python cluster.py --config configs/rubis_cluster.yaml`
- [ ] 验证：加载200个RUBIS文件
- [ ] 验证：提取约600个分布参数
- [ ] 验证：4种算法全部成功执行
- [ ] 验证：总时间 < 10秒
- [ ] 验证：生成4张PNG图表
- [ ] 验证：生成Markdown报告
- [ ] 验证：报告包含建议的验证配置

### 5.5 集成测试 - BSN数据
- [ ] 运行 `python cluster.py --config configs/bsn_cluster.yaml`
- [ ] 验证：加载200个BSN文件
- [ ] 验证：聚类结果合理
- [ ] 验证：输出格式与RUBIS一致

---

## Phase 6: 文档和测试完善 (Documentation & Testing)

### 6.1 单元测试覆盖
- [ ] 为配置模块编写测试
- [ ] 为聚类引擎编写测试
- [ ] 为每个算法编写测试
- [ ] 为可视化模块编写测试（使用mock）
- [ ] 为工厂模式编写测试
- [ ] 运行测试，确保覆盖率>80%

### 6.2 集成测试
- [ ] 测试公共层共享：验证和聚类使用相同parser
- [ ] 测试向后兼容：现有验证测试仍通过
- [ ] 测试discovery-validation工作流
- [ ] 测试自定义算法注册
- [ ] 测试自定义数据源注册
- [ ] 验证：所有集成测试通过

### 6.3 性能测试
- [ ] 测试200个RUBIS文件聚类时间
- [ ] 测试200个BSN文件聚类时间
- [ ] 确保总时间 < 10秒
- [ ] 测试单算法时间 < 3秒
- [ ] 如有性能问题，优化瓶颈
- [ ] 验证：性能达标

### 6.4 更新主README
- [ ] 在README.md添加"聚类分析"章节
- [ ] 说明聚类分析功能和用途
- [ ] 提供快速开始示例
- [ ] 说明配置文件格式
- [ ] 说明discovery-validation工作流
- [ ] 添加可视化输出示例
- [ ] 验证：文档清晰易懂

### 6.5 创建专门文档（可选）
- [ ] 创建 `docs/clustering_analysis.md`（可选）
- [ ] 详细说明每个算法的特点和参数
- [ ] 提供高级使用示例
- [ ] 说明如何添加自定义算法
- [ ] 说明如何添加自定义数据源
- [ ] 验证：文档完整

### 6.6 代码质量
- [ ] 所有函数添加中文docstring
- [ ] 所有关键逻辑添加中文注释
- [ ] 运行类型检查（mypy可选）
- [ ] 代码格式化（black/autopep8）
- [ ] 删除调试代码和无用注释
- [ ] 验证：代码整洁，注释清晰

### 6.7 更新归档文件
- [ ] 将 `rubis_trace_clustering.py` 移动到 `archived_scripts/`
- [ ] 更新 `archived_scripts/README.md`
- [ ] 说明新框架与归档脚本的关系
- [ ] 说明迁移指南
- [ ] 验证：项目结构清晰

---

## Phase 7: 可选增强 (Optional Enhancements)

### 7.1 自动配置生成（可选）
- [ ] 实现 `--export-validation-config` CLI选项
- [ ] 自动生成验证配置YAML文件
- [ ] 包含从聚类结果提取的参数
- [ ] 添加时间戳和来源注释
- [ ] 验证：生成的配置可被validate.py使用

### 7.2 配置文件模板（可选）
- [ ] 创建 `configs/cluster_template.yaml`
- [ ] 包含所有可配置选项和说明
- [ ] 提供多种场景的配置示例
- [ ] 验证：用户可基于模板创建自定义配置

### 7.3 性能优化（可选）
- [ ] 实现数据加载缓存
- [ ] 优化特征矩阵准备
- [ ] 优化可视化生成
- [ ] 实现增量报告生成
- [ ] 验证：性能进一步提升

### 7.4 交互式报告（可选）
- [ ] 生成HTML报告（除Markdown外）
- [ ] 嵌入交互式Plotly图表
- [ ] 添加参数调整滑块
- [ ] 验证：HTML报告可在浏览器中查看

---

## 任务依赖关系

```
Phase 1 (公共层提取)
  └── Phase 2 (聚类引擎核心) - 依赖Phase 1完成
       ├── Phase 3 (算法实现) - 依赖Phase 2完成
       ├── Phase 4 (可视化) - 依赖Phase 2完成，可与Phase 3并行
       └── Phase 5 (CLI) - 依赖Phase 2-4完成
            └── Phase 6 (文档测试) - 依赖Phase 5完成
                 └── Phase 7 (可选增强) - 独立
```

## 里程碑

- **M1 (Day 1-2)**: Phase 1完成，公共层提取，验证框架功能不受影响
- **M2 (Day 3-4)**: Phase 2完成，聚类引擎核心可用
- **M3 (Day 5-7)**: Phase 3-4完成，算法和可视化实现
- **M4 (Day 8-9)**: Phase 5完成，CLI可用，端到端测试通过
- **M5 (Day 10-11)**: Phase 6完成，测试和文档完善
- **M6 (Day 12+)**: Phase 7完成（可选），增强功能

## 验收标准

每个阶段完成后需满足：
1. 所有checkbox勾选完成
2. 验证步骤全部通过
3. 代码有中文注释和docstring
4. 相关文档已更新
5. 相关测试已编写并通过

## 总体验收标准

项目完成时需满足：
- [ ] 所有功能需求实现
- [ ] 所有性能要求达标（< 10秒）
- [ ] 验证框架功能不受影响
- [ ] 4种聚类算法全部可用
- [ ] 可视化输出清晰完整
- [ ] Markdown报告信息完整
- [ ] 配置文件示例完整
- [ ] README文档更新完整
- [ ] 单元测试覆盖率>80%
- [ ] 集成测试全部通过
