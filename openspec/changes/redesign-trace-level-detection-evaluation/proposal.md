# 提案：重新设计trace级别异常检测评估逻辑

**变更ID**: `redesign-trace-level-detection-evaluation`
**状态**: 草案
**创建时间**: 2026-01-17
**类型**: 重大架构变更（breaking change）

---

## Why

当前的异常检测评估逻辑存在根本性的语义错误：系统在点级别（point-level）计算混淆矩阵，导致每个trace产生数百个TP/FP计数，200个trace的总TP达到74028。这使得precision/recall等性能指标完全失去了trace级别的解释意义。

实际检测场景中，我们需要回答的问题是"有多少个trace被正确/错误地分类"，而非"有多少个数据点被正确/错误地分类"。因此，必须将评估逻辑重构为trace级别，使每个trace恰好被分类为一个类别（TP/FP/FN/TN），混淆矩阵总和等于trace总数（200），性能指标才能正确反映检测效果。

---

## 📋 概述

当前的异常检测评估逻辑在**数据点级别**（point-level）计算混淆矩阵（TP/FP/TN/FN），这导致每个trace内部都有大量TP/FP计数。这种设计不符合实际检测场景的语义，因为：

1. **总trace数固定为200**，但当前输出显示每个trace内都有几百个TP/FP，这些数字没有意义
2. **检测目标是trace级别的分类**，而非每个数据点的分类
3. **性能指标失去解释性**：当前precision/recall是基于所有数据点计算的，无法反映trace级别的检测效果

本提案将评估逻辑从**point-level**重构为**trace-level**，使每个trace被分类为单一类别（TP/FP/FN/TN），并基于200个trace计算有意义的性能指标。

---

## 🎯 目标

### 主要目标

1. **重新定义混淆矩阵语义**：从点级别改为trace级别
   - TP：trace在abn1时间点或之后检测到异常
   - FP：trace在abn1时间点之前检测到异常（误报）
   - FN：trace全程未检测到任何异常
   - TN：正常trace未检测到异常（适用于norm-only traces，如果有）

2. **重新设计检测延迟计算**：
   - 单位从"秒"改为"循环"（loops）
   - 1个loop = 1个时间步长（如time=960→1020为1个loop）
   - 延迟 = 首次检测时间点的loop索引 - abn1时间点的loop索引
   - 平均延迟 = sum(所有TP的延迟) / TP数量

3. **调整输出格式**：
   - 聚合混淆矩阵：TP/FP/FN/TN的总和 = 200（总trace数）
   - 每个trace的分类：单一标签（TP/FP/FN/TN之一）
   - 每个trace的延迟：仅对TP和FP有效（FN无延迟）

### 非目标

- 不改变3-sigma检测算法本身
- 不改变learned_distributions.yaml格式
- 不改变trace文件解析逻辑

---

## 🔍 现状分析

### 当前实现问题

#### 1. 评估器逐点计算混淆矩阵

**文件**: `anomaly_detection/core/evaluator.py:115-158`

```python
# 当前逻辑（错误）
for idx, row in df_clean.iterrows():
    time = row['simTime(s)']
    value = row[value_column]

    # 确定当前点所属的segment
    segment_label = self._find_segment(time, metadata.start_time, metadata.trace_config)
    is_ground_truth_anomaly = self.parser.is_anomaly_segment(segment_label)

    # 执行检测
    detection_result = self.detector.detect_point(value)

    # 更新混淆矩阵（每个点都增加TP/FP/TN/FN）
    if is_ground_truth_anomaly:
        if detection_result.is_anomaly:
            metrics.tp += 1  # ❌ 错误：每个异常点都算一个TP
        else:
            metrics.fn += 1  # ❌ 错误：每个未检测的异常点都算一个FN
    else:
        if detection_result.is_anomaly:
            metrics.fp += 1  # ❌ 错误：每个误报点都算一个FP
        else:
            metrics.tn += 1  # ❌ 错误：每个正常点都算一个TN
```

**问题**：
- 每个trace有几百个数据点，导致`metrics.tp`可能高达几百
- 200个trace的`total_tp`加起来达到74028（见检测结果）
- 这使得precision/recall等指标完全失去trace级别的解释意义

#### 2. 检测延迟计算不正确

**文件**: `anomaly_detection/core/evaluator.py:145-150`

```python
# 当前延迟计算（错误）
if metrics.first_anomaly_time is None:
    metrics.first_anomaly_time = time
    # 找到异常段开始时间
    segment_idx = metadata.trace_config.index(segment_label)
    metrics.anomaly_segment_start = metadata.start_time[segment_idx]
    metrics.detection_delay = time - metrics.anomaly_segment_start
    # ❌ 问题1：使用时间戳差值，而非loop数
    # ❌ 问题2：使用segment_start而非abn1的精确时间
```

**问题**：
- 延迟单位是秒（时间戳差），应该是loop数（时间步数）
- 使用segment开始时间而非abn1的精确start_time

#### 3. 文件名解析不提取abn1时间

**文件**: `common/adapters/rubis.py:44-68`

当前解析器提取：
- `trace_config`: ['norm3', 'norm1', 'abn1']
- `start_time`: [960, 23100, 52740]

但没有显式标记哪个时间对应abn1。需要通过`trace_config.index('abn1')`来找到。

#### 4. 聚合指标语义错误

**文件**: `anomaly_detection/core/evaluator.py:206-211`

```python
# 聚合混淆矩阵（错误）
for m in trace_metrics:
    aggregated.total_tp += m.tp  # ❌ 累加点级别的TP，而非trace级别
    aggregated.total_fp += m.fp
    aggregated.total_tn += m.tn
    aggregated.total_fn += m.fn
```

**结果示例**（当前输出）：
```json
"confusion_matrix": {
    "TP": 74028,   // ❌ 应该 ≤ 200（总trace数）
    "FP": 36853,   // ❌ 应该 ≤ 200
    "TN": 102119,  // ❌ 应该 ≤ 200
    "FN": 0        // ❌ 应该 ≤ 200
}
```

**正确输出应该类似**：
```json
"confusion_matrix": {
    "TP": 180,     // ✅ 180个trace成功检测
    "FP": 10,      // ✅ 10个trace误报
    "FN": 10,      // ✅ 10个trace漏检
    "TN": 0        // ✅ 0个正常trace（因为所有trace都包含abn1）
}
// TP + FP + FN + TN = 200
```

---

## 📐 设计方案

### 新的trace级别评估逻辑

#### 分类规则

对于每个trace文件：

1. **解析文件名**，提取：
   - `trace_config`: 段标签列表（如['norm3', 'norm1', 'abn1']）
   - `start_time`: 段开始时间列表（如[960, 23100, 52740]）
   - 如果`trace_config`包含'abn1'：
     - `abn1_index = trace_config.index('abn1')`
     - `abn1_start_time = start_time[abn1_index]`（如52740）
   - 如果不包含abn1，则此trace为纯正常trace

2. **遍历trace数据**，记录所有检测到异常的时间点：
   ```python
   detected_anomaly_times = []
   for idx, row in df_clean.iterrows():
       detection_result = detector.detect_point(row[value_column])
       if detection_result.is_anomaly:
           detected_anomaly_times.append(row['simTime(s)'])
   ```

3. **trace级别分类**：
   - **如果trace包含abn1段**：
     - 如果`detected_anomaly_times`为空 → **FN**（漏检）
     - 否则：
       - `first_detection_time = min(detected_anomaly_times)`
       - 如果`first_detection_time >= abn1_start_time` → **TP**（成功检测）
       - 如果`first_detection_time < abn1_start_time` → **FP**（误报）

   - **如果trace不包含abn1段**（纯正常trace）：
     - 如果`detected_anomaly_times`为空 → **TN**（正确拒绝）
     - 否则 → **FP**（误报）

4. **计算检测延迟**（仅对TP和FP有效）：
   - 将trace的时间序列转换为loop索引：
     ```python
     time_values = df_clean['simTime(s)'].values
     abn1_loop_index = np.where(time_values >= abn1_start_time)[0][0]
     first_detection_loop_index = np.where(time_values == first_detection_time)[0][0]
     delay_in_loops = first_detection_loop_index - abn1_loop_index
     ```
   - 注意：
     - 对于TP：delay ≥ 0（在abn1时间点或之后检测）
     - 对于FP：delay < 0（在abn1时间点之前检测）

#### 数据结构变更

**修改前**（点级别）：
```python
@dataclass
class TraceEvaluationMetrics:
    filename: str
    tp: int = 0        # 点级别累加
    fp: int = 0        # 点级别累加
    tn: int = 0        # 点级别累加
    fn: int = 0        # 点级别累加
    ...
```

**修改后**（trace级别）：
```python
@dataclass
class TraceEvaluationMetrics:
    filename: str
    classification: str  # 'TP' | 'FP' | 'FN' | 'TN'
    has_abn1: bool      # 是否包含abn1段
    abn1_start_time: Optional[float]  # abn1段开始时间（如果有）
    first_detection_time: Optional[float]  # 首次检测时间（如果有）
    detection_delay_loops: Optional[int]  # 检测延迟（loop数，可为负）
    total_detection_count: int  # 检测到的异常点总数
    anomaly_points: List[AnomalyPoint]  # 所有检测到的异常点
```

**聚合指标**：
```python
@dataclass
class AggregatedMetrics:
    total_traces: int  # 200
    tp_count: int      # TP trace数
    fp_count: int      # FP trace数
    fn_count: int      # FN trace数
    tn_count: int      # TN trace数（可能为0）

    # tp_count + fp_count + fn_count + tn_count = total_traces

    precision: float   # tp_count / (tp_count + fp_count)
    recall: float      # tp_count / (tp_count + fn_count)
    f1_score: float    # 2 * P * R / (P + R)

    # 延迟统计（仅TP）
    avg_delay_loops: Optional[float]  # sum(TP延迟) / tp_count
    min_delay_loops: Optional[int]
    max_delay_loops: Optional[int]

    trace_metrics: List[TraceEvaluationMetrics]
```

---

## 🔧 实施细节

### 需要修改的文件

1. **`common/models/metadata.py`**（可选）
   - 添加辅助方法：`get_abn1_start_time()`
   - 提取abn1时间点

2. **`anomaly_detection/core/evaluator.py`** ⭐ 核心修改
   - 重写`evaluate_trace()`方法
   - 修改`TraceEvaluationMetrics`数据类
   - 修改`AggregatedMetrics`数据类
   - 重写`aggregate_results()`方法

3. **`anomaly_detection/visualization/reporter.py`**
   - 修改JSON输出格式
   - 修改CSV输出格式
   - 修改Markdown报告格式

4. **`detect.py`**（主程序）
   - 可能需要调整日志输出

---

## ❓ 待确认问题

在开始实施前，需要用户确认以下设计决策：

### 1. Loop计算方式

**问题**：如何将时间戳转换为loop索引？

**示例**：
- trace数据：`simTime(s)` = [960, 1020, 1080, 1140, ...]
- abn1_start_time = 52740

**方案A**（推荐）：使用数组索引
```python
time_values = [960, 1020, 1080, ..., 52740, 52800, ...]
abn1_loop_index = 数组中第一个 >= 52740 的索引
# 例如：abn1_loop_index = 862（第862个数据点）

first_detection_time = 53400（首次检测时间）
first_detection_loop_index = 数组中等于53400的索引
# 例如：first_detection_loop_index = 873

delay_in_loops = 873 - 862 = 11 loops
```

**方案B**：计算时间步数
```python
# 假设时间间隔固定为60秒
delay_in_loops = (first_detection_time - abn1_start_time) / 60
# = (53400 - 52740) / 60 = 11 loops
```

**请确认**：使用方案A还是方案B？

---

### 2. 多次检测的处理

**问题**：如果一个trace中多次检测到异常，应该：

**方案A**（推荐）：仅使用首次检测时间
- 延迟基于首次检测
- 理由：首次检测最能反映检测器的响应速度

**方案B**：记录所有检测时间，但仅首次用于分类
- 延迟基于首次
- 但在`anomaly_points`中保留所有检测点

**请确认**：使用方案A还是方案B？

---

### 3. FP的延迟语义

**问题**：FP（在abn1之前误报）的延迟应该：

**方案A**：记录为负值
- 例如：abn1_loop_index=862，first_detection_loop_index=850
- delay = 850 - 862 = -12 loops
- 表示提前12个loop误报

**方案B**：FP不计算延迟（设为null）
- 理由：FP是错误的检测，延迟没有意义

**请确认**：使用方案A还是方案B？

---

### 4. 纯正常trace的处理

**问题**：是否存在不含abn1段的trace？

**观察**：当前检测结果显示所有200个trace都有`traces_with_anomalies=200`

**如果存在纯正常trace**：
- TN分类才有意义
- 需要识别这些trace

**如果所有trace都含abn1**：
- TN始终为0
- TP + FP + FN = 200

**请确认**：当前200个trace是否全部包含abn1段？

---

## 📊 预期输出示例

### JSON格式（修改后）

```json
{
  "metadata": {
    "system_type": "rubis",
    "detection_time": "2026-01-17T...",
    "config_path": "configs/rubis_detection_config.yaml"
  },
  "summary": {
    "total_traces": 200,
    "tp_traces": 180,
    "fp_traces": 10,
    "fn_traces": 10,
    "tn_traces": 0
  },
  "confusion_matrix": {
    "TP": 180,
    "FP": 10,
    "FN": 10,
    "TN": 0
  },
  "performance_metrics": {
    "precision": 0.9474,   // 180 / (180+10)
    "recall": 0.9474,      // 180 / (180+10)
    "f1_score": 0.9474
  },
  "detection_delay": {
    "average_loops": 5.2,
    "minimum_loops": 0,
    "maximum_loops": 35
  },
  "trace_details": [
    {
      "filename": "eval_abn_trace-cnt-000-...",
      "classification": "TP",
      "abn1_start_time": 52740,
      "first_detection_time": 53400,
      "detection_delay_loops": 11,
      "total_detection_count": 45
    },
    {
      "filename": "eval_abn_trace-cnt-001-...",
      "classification": "FP",
      "abn1_start_time": 50340,
      "first_detection_time": 49800,
      "detection_delay_loops": -9,
      "total_detection_count": 12
    },
    {
      "filename": "eval_abn_trace-cnt-002-...",
      "classification": "FN",
      "abn1_start_time": 51540,
      "first_detection_time": null,
      "detection_delay_loops": null,
      "total_detection_count": 0
    }
  ]
}
```

### CSV格式（修改后）

| filename | classification | abn1_start_time | first_detection_time | delay_loops | total_detections |
|----------|---------------|-----------------|---------------------|-------------|------------------|
| eval_abn_trace-cnt-000-... | TP | 52740 | 53400 | 11 | 45 |
| eval_abn_trace-cnt-001-... | FP | 50340 | 49800 | -9 | 12 |
| eval_abn_trace-cnt-002-... | FN | 51540 | N/A | N/A | 0 |

---

## ✅ 验收标准

1. **混淆矩阵约束**：
   - TP + FP + FN + TN = 200（总trace数）
   - 所有值 ≥ 0且 ≤ 200

2. **延迟计算**：
   - TP的delay ≥ 0
   - FP的delay < 0（如果记录延迟）
   - FN的delay = null

3. **性能指标范围**：
   - Precision ∈ [0, 1]
   - Recall ∈ [0, 1]
   - F1 ∈ [0, 1]

4. **输出格式**：
   - JSON符合新schema
   - CSV包含所有必需列
   - Markdown报告可读性良好

---

## 🚀 下一步行动

1. **用户确认**上述4个待确认问题
2. **创建详细spec**（基于确认结果）
3. **编写tasks.md**（实施步骤）
4. **开始实施**

---

**创建者**: Claude (Sonnet 4.5)
**审核者**: 待定
