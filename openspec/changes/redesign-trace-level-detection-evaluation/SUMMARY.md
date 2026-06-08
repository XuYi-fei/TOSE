# OpenSpec提案：Trace级别异常检测评估

**变更ID**: `redesign-trace-level-detection-evaluation`
**状态**: ✅ 已验证（Valid OpenSpec）
**类型**: Breaking Change
**创建时间**: 2026-01-17

---

## 📋 提案概要

### 核心问题

当前异常检测评估逻辑在**点级别**计算混淆矩阵，导致：
- 每个trace产生数百个TP/FP计数
- 200个trace的总TP达到74028
- Precision/Recall等指标失去trace级别语义

### 解决方案

将评估逻辑重构为**trace级别**：
- 每个trace恰好被分类为一个类别：TP | FP | FN | TN
- 混淆矩阵总和 = 200（trace总数）
- 延迟单位从"秒"改为"loops"（时间步数）

---

## 📐 设计决策

### 已确定的设计

1. **Loop计算方式**: 使用数组索引差值（方法A）
   ```python
   abn1_loop_index = 第一个 >= abn1_start_time 的时间点索引
   first_detection_loop_index = 等于 first_detection_time 的时间点索引
   delay = first_detection_loop_index - abn1_loop_index
   ```

2. **多次检测处理**: 仅使用首次检测时间（方法A）
   - 延迟基于首次检测
   - 在`anomaly_points`中保留所有检测点

3. **FP延迟语义**: 记录为负值（方法A）
   - 例如：delay = -49 loops 表示提前49个loop误报

4. **纯正常trace**: 当前200个trace均包含abn1段
   - TN始终为0
   - TP + FP + FN = 200

---

## 📊 预期输出示例

### 修改前（点级别）
```json
{
  "confusion_matrix": {
    "TP": 74028,    // ❌ 点级别累加
    "FP": 36853,
    "TN": 102119,
    "FN": 0
  }
}
```

### 修改后（trace级别）
```json
{
  "confusion_matrix": {
    "TP": 180,      // ✅ trace计数
    "FP": 10,
    "FN": 10,
    "TN": 0
  },
  "detection_delay": {
    "average_loops": 5.2,    // ✅ loop单位
    "minimum_loops": 0,
    "maximum_loops": 35
  },
  "trace_details": [
    {
      "filename": "eval_abn_trace-cnt-000-...",
      "classification": "TP",           // ✅ 单一分类
      "abn1_start_time": 52740,
      "first_detection_time": 53400,
      "detection_delay_loops": 11,      // ✅ loop延迟
      "total_detection_count": 45
    }
  ]
}
```

---

## 🔧 实施计划

### 阶段1：数据模型变更（2个任务）
- Task 1.1: 修改 `TraceEvaluationMetrics` 数据类
- Task 1.2: 修改 `AggregatedMetrics` 数据类

### 阶段2：核心算法实现（3个任务）
- Task 2.1: 实现 `calculate_delay_in_loops` 函数
- Task 2.2: 重写 `evaluate_trace` 方法 ⭐核心
- Task 2.3: 重写 `aggregate_results` 方法

### 阶段3：输出格式更新（3个任务）
- Task 3.1: 更新 JSON 输出格式
- Task 3.2: 更新 CSV 输出格式
- Task 3.3: 更新 Markdown 报告格式

### 阶段4：测试（2个任务）
- Task 4.1: 编写单元测试（TP/FP/FN/TN各一个case + loop计算 + 聚合）
- Task 4.2: 集成测试（RUBIS数据集）

### 阶段5：文档更新（2个任务）
- Task 5.1: 更新 CHANGES.md（breaking change说明）
- Task 5.2: 更新 README.md（JSON/CSV格式示例）

### 阶段6：验证与部署（2个任务）
- Task 6.1: 在RUBIS数据集上验证（200个trace）
- Task 6.2: 性能测试（<5秒处理时间）

---

## 📁 OpenSpec文档结构

```
openspec/changes/redesign-trace-level-detection-evaluation/
├── proposal.md                          # 提案文档（用户确认用）
├── design.md                            # 详细设计文档（架构、算法）
├── tasks.md                             # 实施任务清单（14个任务）
├── SUMMARY.md                           # 本文档（快速参考）
└── specs/
    └── trace-level-evaluation/
        └── spec.md                      # 规格说明（10个需求 + 场景）
```

---

## ✅ 验收标准

### 1. 混淆矩阵约束
- TP + FP + FN + TN = 200（总trace数）
- 所有值 ≥ 0且 ≤ 200

### 2. 延迟计算
- TP的delay ≥ 0
- FP的delay < 0（提前检测）
- FN的delay = null

### 3. 性能指标范围
- Precision ∈ [0, 1]
- Recall ∈ [0, 1]
- F1 ∈ [0, 1]

### 4. 输出格式
- JSON符合新schema
- CSV包含所有必需列（6列）
- Markdown报告可读性良好

---

## ⚠️ Breaking Changes

### JSON输出格式变更
```diff
- "confusion_matrix": {"TP": 74028, ...}
+ "confusion_matrix": {"TP": 180, ...}

- "trace_details": [{"tp": 202, "fp": 358, ...}]
+ "trace_details": [{"classification": "TP", ...}]

- "detection_delay": 660.0  // 秒
+ "detection_delay_loops": 11  // loops
```

### CSV输出格式变更
```diff
- filename,tp,fp,tn,fn,precision,recall,detection_delay
+ filename,classification,abn1_start_time,first_detection_time,delay_loops,total_detections
```

### 影响范围
- ❌ 不兼容旧版JSON/CSV解析脚本（需更新）
- ✅ 检测算法未变更（仍为3-sigma）
- ✅ 配置文件格式未变更
- ✅ learned_distributions.yaml格式未变更

---

## 📝 下一步行动

### 选项A：开始实施（推荐）
```bash
# 1. 修改数据模型
# 编辑 anomaly_detection/core/evaluator.py
# - 修改 TraceEvaluationMetrics
# - 修改 AggregatedMetrics

# 2. 实现核心算法
# - 添加 calculate_delay_in_loops 函数
# - 重写 evaluate_trace 方法
# - 重写 aggregate_results 方法

# 3. 更新输出格式
# 编辑 anomaly_detection/visualization/reporter.py

# 4. 编写测试
# 创建 tests/test_trace_level_evaluation.py

# 5. 运行验证
python detect.py --config configs/rubis_detection_config.yaml
```

### 选项B：查看详细文档
```bash
# 查看提案文档
cat openspec/changes/redesign-trace-level-detection-evaluation/proposal.md

# 查看设计文档（包含完整算法）
cat openspec/changes/redesign-trace-level-detection-evaluation/design.md

# 查看任务清单
cat openspec/changes/redesign-trace-level-detection-evaluation/tasks.md

# 查看规格说明
cat openspec/changes/redesign-trace-level-detection-evaluation/specs/trace-level-evaluation/spec.md
```

---

## 🎯 核心文件修改清单

| 文件 | 修改类型 | 优先级 |
|------|---------|--------|
| `anomaly_detection/core/evaluator.py` | 重写核心逻辑 | P0 |
| `anomaly_detection/visualization/reporter.py` | 更新输出格式 | P0 |
| `tests/test_trace_level_evaluation.py` | 新建测试 | P1 |
| `CHANGES.md` | 文档更新 | P1 |
| `README.md` | 文档更新 | P1 |

---

**创建者**: Claude (Sonnet 4.5)
**验证状态**: ✅ OpenSpec Validated (--strict)
**预计工时**: 3-4天（按上述6个阶段分步实施）
**最后更新**: 2026-01-17
