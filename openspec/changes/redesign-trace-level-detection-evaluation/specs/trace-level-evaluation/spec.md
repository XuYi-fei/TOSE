# Spec: Trace级别异常检测评估

**变更ID**: `redesign-trace-level-detection-evaluation`
**能力**: trace-level-evaluation

---

## MODIFIED Requirements

### Requirement: 异常检测评估应在trace级别而非点级别进行分类

**ID**: `REQ-TRACE-001`

系统**必须**对每个trace文件进行单一分类（TP/FP/FN/TN），而非对trace内的每个数据点进行分类。混淆矩阵的TP、FP、FN、TN值**应**分别表示被分类为该类别的trace数量，其总和**必须**等于总trace数。

**当前行为**（点级别）:
- 系统对trace中的每个数据点进行TP/FP/TN/FN分类
- 单个trace的混淆矩阵计数可达数百
- 200个trace的TP总和达到74028（点级别累加）
- 性能指标基于所有数据点计算，失去trace级别语义

**新行为**（trace级别）:
- 系统对每个trace文件进行单一分类：TP | FP | FN | TN
- 每个trace贡献1个计数到混淆矩阵
- 200个trace的TP+FP+FN+TN=200
- 性能指标基于trace计数，具有明确语义

#### Scenario: 检测到异常且时间正确（True Positive）

**Given**:
- trace文件包含abn1段，开始时间为52740
- 检测器在时间53400首次检测到异常

**When**: 评估器处理该trace

**Then**:
- trace被分类为 'TP'
- 检测延迟为11 loops（时间步数）
- 该trace在聚合时贡献1到TP计数

---

#### Scenario: 检测到异常但时间过早（False Positive）

**Given**:
- trace文件包含abn1段，开始时间为52740
- 检测器在时间49800首次检测到异常（早于abn1）

**When**: 评估器处理该trace

**Then**:
- trace被分类为 'FP'
- 检测延迟为-49 loops（负值表示提前）
- 该trace在聚合时贡献1到FP计数

---

#### Scenario: 未检测到异常（False Negative）

**Given**:
- trace文件包含abn1段，开始时间为51540
- 检测器未在任何时间点检测到异常

**When**: 评估器处理该trace

**Then**:
- trace被分类为 'FN'
- 检测延迟为null（无延迟）
- 该trace在聚合时贡献1到FN计数

---

#### Scenario: 正常trace未检测到异常（True Negative）

**Given**:
- trace文件不包含abn1段（纯正常trace）
- 检测器未在任何时间点检测到异常

**When**: 评估器处理该trace

**Then**:
- trace被分类为 'TN'
- 检测延迟为null
- 该trace在聚合时贡献1到TN计数

---

### Requirement: 检测延迟应以时间步数（loops）而非秒为单位

**ID**: `REQ-DELAY-001`

系统**必须**以时间步数（loops）为单位计算检测延迟，而非使用时间戳差值（秒）。延迟**应**通过计算首次检测时间点的数组索引与abn1开始时间点的数组索引之差得出。

**当前行为**:
- 延迟 = first_detection_time - abn1_start_time（秒）
- 示例：53400 - 52740 = 660秒

**新行为**:
- 延迟 = first_detection_loop_index - abn1_loop_index（loops）
- 示例：873 - 862 = 11 loops

#### Scenario: 计算loop级别延迟

**Given**:
- trace的时间序列为 [960, 1020, 1080, ..., 52740, 52800, ..., 53400, ...]
- abn1_start_time = 52740（对应索引862）
- first_detection_time = 53400（对应索引873）

**When**: 计算检测延迟

**Then**:
- 延迟 = 873 - 862 = 11 loops
- 延迟以整数形式存储（不是浮点数）

---

#### Scenario: 处理提前检测（负延迟）

**Given**:
- abn1_start_time = 52740（对应索引862）
- first_detection_time = 49800（对应索引813）

**When**: 计算检测延迟

**Then**:
- 延迟 = 813 - 862 = -49 loops
- 系统支持并正确记录负延迟

---

### Requirement: 聚合统计应基于trace计数而非点计数

**ID**: `REQ-AGG-001`

系统**必须**基于trace计数计算Precision、Recall和F1分数，而非基于点计数。聚合混淆矩阵的TP、FP、FN、TN值**必须**等于对应分类的trace数量，其总和**必须**等于总trace数。

**当前行为**:
- Precision = sum(all_trace.tp) / (sum(all_trace.tp) + sum(all_trace.fp))
- 分母可达数万（点级别）

**新行为**:
- Precision = tp_count / (tp_count + fp_count)
- 分母最大为total_traces（200）

#### Scenario: 聚合200个trace的评估结果

**Given**:
- 200个trace已完成评估
- 分类结果：180个TP，10个FP，10个FN，0个TN

**When**: 执行聚合统计

**Then**:
- tp_count = 180
- fp_count = 10
- fn_count = 10
- tn_count = 0
- tp_count + fp_count + fn_count + tn_count = 200
- precision = 180 / (180+10) = 0.9474
- recall = 180 / (180+10) = 0.9474
- f1_score = 2 * 0.9474 * 0.9474 / (0.9474 + 0.9474) = 0.9474

---

#### Scenario: 验证混淆矩阵约束

**Given**: 任意一组trace评估结果

**When**: 执行聚合统计

**Then**:
- tp_count ≥ 0
- fp_count ≥ 0
- fn_count ≥ 0
- tn_count ≥ 0
- tp_count + fp_count + fn_count + tn_count = total_traces
- 如果约束不满足，系统抛出断言错误

---

## MODIFIED Requirements

### Requirement: TraceEvaluationMetrics数据模型应反映trace级别分类

**ID**: `REQ-MODEL-001`

TraceEvaluationMetrics数据类**必须**包含classification字段（值为'TP'/'FP'/'FN'/'TN'之一），而非包含tp/fp/tn/fn四个整数字段。该数据类**应**包含has_abn1、abn1_start_time、first_detection_time和detection_delay_loops字段以支持trace级别评估。

**当前数据模型**:
```python
@dataclass
class TraceEvaluationMetrics:
    filename: str
    tp: int = 0              # 点级别TP数
    fp: int = 0              # 点级别FP数
    tn: int = 0              # 点级别TN数
    fn: int = 0              # 点级别FN数
    precision: float = 0.0   # per-trace precision
    recall: float = 0.0      # per-trace recall
    ...
```

**新数据模型**:
```python
@dataclass
class TraceEvaluationMetrics:
    filename: str
    classification: str                    # 'TP' | 'FP' | 'FN' | 'TN'
    has_abn1: bool                        # 是否包含abn1段
    abn1_start_time: Optional[float]      # abn1段开始时间
    first_detection_time: Optional[float] # 首次检测时间
    detection_delay_loops: Optional[int]  # 检测延迟（loops）
    total_detection_count: int            # 检测到的异常点总数
    anomaly_points: List[AnomalyPoint]    # 所有检测点详情
```

#### Scenario: 创建TP trace的评估指标

**Given**: trace被分类为TP

**When**: 创建TraceEvaluationMetrics实例

**Then**:
- classification = 'TP'
- has_abn1 = True
- abn1_start_time = 52740（具体值）
- first_detection_time = 53400（具体值）
- detection_delay_loops = 11（非负整数）
- total_detection_count > 0

---

#### Scenario: 创建FN trace的评估指标

**Given**: trace被分类为FN

**When**: 创建TraceEvaluationMetrics实例

**Then**:
- classification = 'FN'
- has_abn1 = True
- abn1_start_time = 51540（具体值）
- first_detection_time = None
- detection_delay_loops = None
- total_detection_count = 0

---

## MODIFIED Requirements

### Requirement: AggregatedMetrics数据模型应反映trace级别聚合

**ID**: `REQ-MODEL-002`

AggregatedMetrics数据类**必须**包含tp_count、fp_count、fn_count、tn_count字段表示trace计数，而非total_tp/total_fp/total_tn/total_fn字段表示点计数。延迟统计字段**必须**以loops为单位（avg_delay_loops、min_delay_loops、max_delay_loops）。

**当前数据模型**:
```python
@dataclass
class AggregatedMetrics:
    total_traces: int
    total_tp: int = 0        # 所有trace的tp累加（点级别）
    total_fp: int = 0        # 所有trace的fp累加（点级别）
    ...
```

**新数据模型**:
```python
@dataclass
class AggregatedMetrics:
    total_traces: int
    tp_count: int            # TP trace数
    fp_count: int            # FP trace数
    fn_count: int            # FN trace数
    tn_count: int            # TN trace数
    precision: float         # trace级别precision
    recall: float            # trace级别recall
    f1_score: float
    avg_delay_loops: Optional[float]  # 平均延迟（loops）
    min_delay_loops: Optional[int]
    max_delay_loops: Optional[int]
    trace_metrics: List[TraceEvaluationMetrics]
```

#### Scenario: 聚合指标包含trace计数而非点计数

**Given**: 200个trace的评估结果

**When**: 创建AggregatedMetrics实例

**Then**:
- total_traces = 200
- tp_count ∈ [0, 200]
- fp_count ∈ [0, 200]
- fn_count ∈ [0, 200]
- tn_count ∈ [0, 200]
- tp_count + fp_count + fn_count + tn_count = 200

---

## MODIFIED Requirements

### Requirement: JSON输出格式应反映trace级别语义

**ID**: `REQ-OUTPUT-001`

JSON输出**必须**在confusion_matrix字段中显示trace计数（值≤总trace数），而非点计数（值可达数万）。trace_details数组中的每个对象**必须**包含classification字段，**应**包含detection_delay_loops字段表示loop级别延迟。

**当前JSON格式**:
```json
{
  "confusion_matrix": {
    "TP": 74028,
    "FP": 36853,
    "TN": 102119,
    "FN": 0
  },
  "trace_details": [
    {
      "filename": "...",
      "tp": 202,
      "fp": 358,
      "precision": 0.3607
    }
  ]
}
```

**新JSON格式**:
```json
{
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
    "precision": 0.9474,
    "recall": 0.9474,
    "f1_score": 0.9474
  },
  "detection_delay": {
    "average_loops": 5.2,
    "minimum_loops": 0,
    "maximum_loops": 35
  },
  "trace_details": [
    {
      "filename": "...",
      "classification": "TP",
      "abn1_start_time": 52740,
      "first_detection_time": 53400,
      "detection_delay_loops": 11,
      "total_detection_count": 45
    }
  ]
}
```

#### Scenario: 生成JSON报告包含trace级别混淆矩阵

**Given**: 聚合指标已计算完成

**When**: 生成JSON报告

**Then**:
- `confusion_matrix.TP` 的值等于 `tp_count`
- `confusion_matrix.FP` 的值等于 `fp_count`
- `confusion_matrix.FN` 的值等于 `fn_count`
- `confusion_matrix.TN` 的值等于 `tn_count`
- 四个值之和等于 `total_traces`

---

#### Scenario: 生成JSON报告包含trace详情

**Given**: 每个trace已完成分类

**When**: 生成JSON报告

**Then**:
- `trace_details` 数组长度 = `total_traces`
- 每个trace对象包含 `classification` 字段（值为'TP'/'FP'/'FN'/'TN'之一）
- 每个trace对象包含 `detection_delay_loops` 字段（int或null）
- TP/FP trace的 `detection_delay_loops` 为非null整数
- FN/TN trace的 `detection_delay_loops` 为null

---

## MODIFIED Requirements

### Requirement: CSV输出格式 MUST 反映trace级别分类

**ID**: `REQ-OUTPUT-002`

CSV输出 MUST 包含classification列（值为'TP'/'FP'/'FN'/'TN'之一），SHALL 包含delay_loops列表示loop级别延迟。CSV MUST 有与总trace数相等的数据行数（不含表头）。

**当前CSV格式**:
```
filename,tp,fp,tn,fn,precision,recall,f1_score,detection_delay
"trace-000...",202,358,505,0,0.3607,1.0000,0.5302,N/A
```

**新CSV格式**:
```
filename,classification,abn1_start_time,first_detection_time,delay_loops,total_detections
"trace-000...",TP,52740,53400,11,45
```

#### Scenario: 生成CSV报告每行一个trace分类

**Given**: 所有trace已完成评估

**When**: 生成CSV报告

**Then**:
- CSV有200行数据（不含表头）
- 每行包含6列：filename, classification, abn1_start_time, first_detection_time, delay_loops, total_detections
- `classification` 列值仅为 'TP', 'FP', 'FN', 'TN' 之一
- `delay_loops` 列为整数或 'N/A'
- CSV可被pandas正常读取

---

## REMOVED Requirements

### Requirement: [REMOVED] 点级别混淆矩阵计算

**ID**: `REQ-POINT-001`

**移除原因**: 点级别评估语义不正确，应改为trace级别评估

**原行为**:
- 系统遍历trace中每个数据点
- 判断点是否在异常段内（is_ground_truth_anomaly）
- 判断点是否被检测为异常（detection_result.is_anomaly）
- 根据2x2矩阵更新TP/FP/TN/FN计数

**影响**:
- `evaluator.py:115-158` 的逐点循环需要重写
- 移除 `_find_segment()` 方法（不再需要）
- 移除 `is_anomaly_segment()` 调用

---

### Requirement: [REMOVED] 每个trace计算独立的precision/recall

**ID**: `REQ-POINT-002`

**移除原因**: 单个trace的precision/recall没有意义，应仅在聚合层计算

**原行为**:
- 每个trace返回自己的precision/recall/f1值
- 基于该trace内的点级别TP/FP/TN/FN计算

**影响**:
- TraceEvaluationMetrics移除precision/recall/f1字段
- 这些指标仅在AggregatedMetrics中计算

---

## ADDED Requirements

### Requirement: 提供loop延迟计算辅助函数

**ID**: `REQ-UTIL-001`

系统**必须**提供calculate_delay_in_loops函数，该函数接受时间序列数组、abn1开始时间和首次检测时间作为参数，返回以loops为单位的延迟。函数**应**使用数组索引查找而非时间间隔计算来确保精确性。

#### Scenario: 计算abn1和检测时间的loop差值

**Given**:
- 时间序列数组 time_values = [960, 1020, ..., 52740, ..., 53400, ...]
- abn1_start_time = 52740
- first_detection_time = 53400

**When**: 调用 `calculate_delay_in_loops(time_values, abn1_start_time, first_detection_time)`

**Then**:
- 函数找到第一个 ≥ abn1_start_time 的时间点索引（862）
- 函数找到等于 first_detection_time 的时间点索引（873）
- 返回值 = 873 - 862 = 11

---

#### Scenario: 处理abn1时间不在数组中的情况

**Given**:
- abn1_start_time = 99999（超出trace时间范围）

**When**: 调用 `calculate_delay_in_loops(...)`

**Then**:
- 函数抛出 ValueError，消息包含 "超出trace时间范围"

---

## ADDED Requirements

### Requirement: 系统 MUST 提供abn1时间提取逻辑

**ID**: `REQ-PARSE-001`

评估器 MUST 能够从trace metadata中提取abn1段的开始时间。系统 SHALL 通过在trace_config列表中查找'abn1'的索引，然后从start_time列表中获取对应位置的时间值来实现此功能。

#### Scenario: 从metadata提取abn1时间

**Given**:
- metadata.trace_config = ['norm3', 'norm1', 'abn1']
- metadata.start_time = [960, 23100, 52740]

**When**: 提取abn1开始时间

**Then**:
- 系统找到 'abn1' 在 trace_config 中的索引（2）
- 系统提取 start_time[2] = 52740
- 返回 abn1_start_time = 52740

---

#### Scenario: 处理不含abn1的trace

**Given**:
- metadata.trace_config = ['norm1', 'norm2']
- metadata.start_time = [960, 23100]

**When**: 提取abn1开始时间

**Then**:
- 系统检测到 'abn1' 不在 trace_config 中
- 返回 has_abn1 = False
- 返回 abn1_start_time = None

---

**创建者**: Claude (Sonnet 4.5)
**版本**: 1.0
**最后更新**: 2026-01-17
