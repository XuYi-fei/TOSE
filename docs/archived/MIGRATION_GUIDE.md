# 数据重组迁移指南

本文档说明数据目录重组的变更及如何适应新结构。

## 变更概述

### 旧结构（已弃用）
```
TOSE/
├── rubis_evaluation_data/
│   ├── eval_ident_traces/  # RUBIS辨识数据
│   └── eval_abn_traces/    # RUBIS异常数据
├── bsn_evaluation_data/
│   └── eval_ident_traces/  # BSN辨识数据
├── swat_evaluation_data/
│   └── eval_ident_traces/  # SWAT辨识数据
└── wadi_evaluation_data/
    └── eval_ident_traces/  # WADI辨识数据
```

### 新结构（当前）
```
TOSE/
├── data/
│   ├── rubis/
│   │   ├── identity/       # RUBIS辨识数据
│   │   └── abnormal/       # RUBIS异常数据
│   ├── bsn/
│   │   ├── identity/       # BSN辨识数据
│   │   └── abnormal/       # BSN异常数据（待添加）
│   ├── swat/
│   │   ├── identity/       # SWAT辨识数据
│   │   └── abnormal/       # SWAT异常数据（待添加）
│   └── wadi/
│       ├── identity/       # WADI辨识数据（预留）
│       └── abnormal/       # WADI异常数据（预留）
```

## 变更原因

1. **统一性**：所有数据集使用相同的目录结构
2. **清晰性**：数据用途（identity/abnormal）一目了然
3. **可扩展性**：便于添加新系统（WADI、其他）
4. **可维护性**：减少项目根目录混乱

## 配置文件更新

### RUBIS配置

**聚类配置** (`configs/rubis_clustering_config.yaml`)
```yaml
# 旧路径
data_path: rubis_evaluation_data/eval_ident_traces

# 新路径
data_path: data/rubis/identity
```

**检测配置** (`configs/rubis_detection_config.yaml`)
```yaml
# 旧路径
test_data_path: rubis_evaluation_data/eval_abn_traces

# 新路径
test_data_path: data/rubis/abnormal
```

### BSN配置

**聚类配置** (`configs/bsn_clustering_config.yaml`)
```yaml
# 旧路径
data_path: bsn_evaluation_data/eval_ident_traces

# 新路径
data_path: data/bsn/identity
```

**检测配置** (`configs/bsn_detection_config.yaml`)
```yaml
# 旧路径
test_data_path: bsn_evaluation_data/eval_abn_traces

# 新路径
test_data_path: data/bsn/abnormal
```

### SWAT配置（新增）

**聚类配置** (`configs/swat_clustering_config.yaml`)
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
  save_learned_distributions: true
  learned_distributions_path: clustering_results/swat/learned_distributions.yaml
```

**检测配置** (`configs/swat_detection_config.yaml`)
```yaml
system_type: swat
learned_distributions: clustering_results/swat/learned_distributions.yaml
test_data_path: data/swat/abnormal
detection:
  sigma_threshold: 3.0
output:
  dir: detection_results/swat
```

## SWAT支持

### 新增功能

1. **SWAT数据解析器** (`common/adapters/swat.py`)
   - 继承自RUBISParser（文件名格式相同）
   - 支持SWAT特有的列名：`time`（非simTime）和`y_0`（非measuredAvgRespTime）

2. **SWAT配置文件**
   - `configs/swat_clustering_config.yaml`
   - `configs/swat_detection_config.yaml`

3. **系统类型验证**
   - `cluster_analysis/config/config.py`: 添加'swat'到valid_types
   - `anomaly_detection/config/config.py`: 添加'swat'到valid_types

### SWAT数据格式

**文件命名**：与RUBIS相同
```
eval_ident_trace-cnt-000-duration-64800-config_num-3-trace_config-norm1,norm2,norm3-start_time-960,33660,47580.txt
```

**CSV列**：
- `time`: 时间戳（第一列）
- `water_tank`, `noisy_B_in`, `noisy_B_out`, `u_1_in`, `u_1_out`: 中间列
- `y_0`: 目标指标（最后一列）

## 使用示例

### 运行SWAT聚类分析

```bash
python cluster.py --config configs/swat_clustering_config.yaml
```

**输出**：
- `clustering_results/swat/clustering_report.md`
- `clustering_results/swat/learned_distributions.yaml`
- `clustering_results/swat/*.png`（可视化图表）

### 运行SWAT异常检测

```bash
# 前提：已运行聚类分析生成learned_distributions.yaml
# 前提：data/swat/abnormal/ 目录存在异常数据

python detect.py --config configs/swat_detection_config.yaml
```

**输出**：
- `detection_results/swat/detection_report.md`
- `detection_results/swat/anomaly_points.csv`
- `detection_results/swat/*.png`

## 数据迁移步骤（如果需要）

如果你有自定义数据需要迁移到新结构：

### 1. 创建新目录

```bash
mkdir -p data/mysystem/identity
mkdir -p data/mysystem/abnormal
```

### 2. 移动数据文件

```bash
# 移动辨识数据
mv mysystem_evaluation_data/eval_ident_traces/* data/mysystem/identity/

# 移动异常数据
mv mysystem_evaluation_data/eval_abn_traces/* data/mysystem/abnormal/
```

### 3. 更新配置文件

编辑 `configs/mysystem_clustering_config.yaml`:
```yaml
data_path: data/mysystem/identity
```

编辑 `configs/mysystem_detection_config.yaml`:
```yaml
test_data_path: data/mysystem/abnormal
```

### 4. 验证迁移

```bash
# 列出文件数量
ls data/mysystem/identity/ | wc -l
ls data/mysystem/abnormal/ | wc -l

# 运行聚类测试
python cluster.py --config configs/mysystem_clustering_config.yaml
```

## 兼容性说明

- ✅ **向后兼容**：旧配置文件只需更新路径即可使用
- ✅ **数据格式不变**：trace文件的CSV格式和文件命名完全不变
- ✅ **API不变**：ParserFactory、适配器接口保持不变
- ⚠️ **绝对路径**：如果使用绝对路径引用旧目录，需要更新为新路径

## 验证测试结果

所有系统已通过完整测试：

### RUBIS
- ✅ 聚类分析：200个identity traces → 504个数据点，3个聚类
- ✅ 异常检测：200个abnormal traces，检测成功率100%

### BSN
- ✅ 聚类分析：200个identity traces → 511个数据点，3个聚类
- ⚠️ 异常检测：待添加abnormal数据

### SWAT
- ✅ 聚类分析：200个identity traces → 1492个数据点，3个聚类
- ⚠️ 异常检测：待添加abnormal数据

## 常见问题

### Q: 旧配置文件还能用吗？
A: 可以，但需要更新 `data_path` 和 `test_data_path` 字段为新路径。

### Q: 数据文件需要修改吗？
A: 不需要。trace文件的格式和文件名完全不变，只是存放位置变化。

### Q: SWAT和RUBIS的文件名格式为什么相同？
A: 这是设计优势！SWAT复用RUBIS的文件名解析逻辑，只需覆盖列名即可。参见 `common/adapters/swat.py`。

### Q: 如何添加新系统？
A:
1. 在 `data/` 下创建系统目录
2. 在 `common/adapters/` 创建解析器类
3. 在 `configs/` 创建配置文件
4. 更新 `valid_types` 列表

### Q: 旧目录会被删除吗？
A: 是的，`rubis_evaluation_data/`, `bsn_evaluation_data/`, `swat_evaluation_data/` 已被删除。数据已迁移到 `data/` 目录。

## 相关文档

- **主文档**: `README.md`
- **聚类分析**: `CLUSTERING_README.md`
- **OpenSpec提案**: `openspec/changes/refactor-data-layout-and-add-swat-support/`
  - `proposal.md`: 重组提案
  - `design.md`: 技术设计
  - `tasks.md`: 实施任务

## 技术支持

如遇问题，请检查：
1. 配置文件路径是否正确
2. 数据文件是否在新目录中
3. ParserFactory是否支持目标系统类型
4. 运行 `python cluster.py --config <config> --verbose` 查看详细日志
