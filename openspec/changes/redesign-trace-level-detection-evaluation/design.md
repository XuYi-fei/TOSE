# 设计文档：Trace级别异常检测评估

**变更ID**: `redesign-trace-level-detection-evaluation`

---

## 架构概述

### 当前架构（点级别评估）

```
┌─────────────────────────────────────────────────────────────────┐
│                         Evaluator                                │
│                                                                   │
│  evaluate_trace(trace_file)                                      │
│  ├─ 逐点遍历trace数据                                              │
│  │  ├─ detector.detect_point(value) → is_anomaly                │
│  │  ├─ 判断点是否在异常段（is_ground_truth_anomaly）                 │
│  │  └─ 更新混淆矩阵（每个点都计入TP/FP/TN/FN）                       │
│  │                                                               │
│  └─ 返回TraceEvaluationMetrics                                  │
│      ├─ tp: int（点级别累加，可达数百）                            │
│      ├─ fp: int（点级别累加）                                     │
│      ├─ tn: int（点级别累加）                                     │
│      └─ fn: int（点级别累加）                                     │
│                                                                   │
│  aggregate_results(trace_metrics)                                │
│  └─ 累加所有trace的tp/fp/tn/fn                                   │
│      → total_tp = 74028（点级别总和，无意义）                      │
└─────────────────────────────────────────────────────────────────┘
```

**问题**：
- 每个trace的TP可能有几百个，失去trace级别的语义
- 总TP达到74028，远超trace总数200

---

### 新架构（trace级别评估）

```
┌─────────────────────────────────────────────────────────────────┐
│                         Evaluator                                │
│                                                                   │
│  evaluate_trace(trace_file)                                      │
│  ├─ 1. 解析文件名                                                 │
│  │   ├─ trace_config = ['norm3', 'norm1', 'abn1']              │
│  │   ├─ start_time = [960, 23100, 52740]                       │
│  │   └─ 提取abn1_start_time（如果存在）                          │
│  │                                                               │
│  ├─ 2. 遍历所有数据点，收集检测结果                                │
│  │   ├─ detector.detect_point(value) → is_anomaly              │
│  │   └─ 如果异常，记录时间戳到detected_times[]                    │
│  │                                                               │
│  ├─ 3. Trace级别分类                                             │
│  │   ├─ 如果detected_times为空 → FN                             │
│  │   ├─ first_detection = min(detected_times)                  │
│  │   └─ 比较first_detection与abn1_start_time                   │
│  │       ├─ first_detection >= abn1_start_time → TP           │
│  │       └─ first_detection < abn1_start_time → FP            │
│  │                                                               │
│  ├─ 4. 计算延迟（仅TP/FP）                                        │
│  │   ├─ 找到abn1_start_time在时间序列中的索引                     │
│  │   ├─ 找到first_detection在时间序列中的索引                     │
│  │   └─ delay = detection_index - abn1_index                   │
│  │                                                               │
│  └─ 返回TraceEvaluationMetrics                                  │
│      ├─ classification: 'TP' | 'FP' | 'FN' | 'TN'              │
│      ├─ detection_delay_loops: int（可为负，FN时为null）          │
│      └─ anomaly_points: List[AnomalyPoint]（所有检测点）          │
│                                                                   │
│  aggregate_results(trace_metrics)                                │
│  └─ 计数各分类                                                    │
│      ├─ tp_count = count(classification == 'TP')               │
│      ├─ fp_count = count(classification == 'FP')               │
│      ├─ fn_count = count(classification == 'FN')               │
│      ├─ tn_count = count(classification == 'TN')               │
│      └─ tp + fp + fn + tn = 200 ✅                              │
└─────────────────────────────────────────────────────────────────┘
```

**优势**：
- 每个trace恰好属于一个分类（TP/FP/FN/TN）
- 混淆矩阵总和 = 200（trace总数）
- Precision/Recall有明确的trace级别语义

---

## 核心算法

### 算法1：Trace分类逻辑

**输入**：
- `trace_file`: trace文件路径
- `detector`: 异常检测器
- `parser`: 文件名解析器

**输出**：
- `TraceEvaluationMetrics`（包含分类和延迟）

**伪代码**：
```python
def evaluate_trace(trace_file: Path) -> TraceEvaluationMetrics:
    # Step 1: 解析文件名
    metadata = parser.parse_filename(trace_file.name)
    trace_config = metadata.trace_config  # e.g., ['norm3', 'norm1', 'abn1']
    start_time = metadata.start_time      # e.g., [960, 23100, 52740]

    # 提取abn1信息
    has_abn1 = 'abn1' in trace_config
    if has_abn1:
        abn1_index = trace_config.index('abn1')
        abn1_start_time = start_time[abn1_index]
    else:
        abn1_start_time = None

    # Step 2: 读取trace数据
    df = pd.read_csv(trace_file)
    time_values = df['simTime(s)'].values
    response_times = df[value_column].values

    # Step 3: 逐点检测，收集所有异常时间
    detected_times = []
    anomaly_points = []

    for i, (time, value) in enumerate(zip(time_values, response_times)):
        detection_result = detector.detect_point(value)
        if detection_result.is_anomaly:
            detected_times.append(time)
            anomaly_points.append(AnomalyPoint(
                time=time,
                value=value,
                is_detected=True,
                z_scores=detection_result.all_z_scores,
                closest_distribution=detection_result.closest_distribution
            ))

    # Step 4: Trace级别分类
    if has_abn1:
        if len(detected_times) == 0:
            # 全程未检测到异常
            classification = 'FN'
            first_detection_time = None
            delay_loops = None
        else:
            # 有检测结果
            first_detection_time = min(detected_times)

            if first_detection_time >= abn1_start_time:
                # 在abn1时间点或之后检测到
                classification = 'TP'
            else:
                # 在abn1时间点之前检测到（误报）
                classification = 'FP'

            # 计算延迟（loop数）
            delay_loops = calculate_delay_in_loops(
                time_values, abn1_start_time, first_detection_time
            )
    else:
        # 纯正常trace（如果存在）
        if len(detected_times) == 0:
            classification = 'TN'
        else:
            classification = 'FP'
        first_detection_time = None if len(detected_times) == 0 else min(detected_times)
        delay_loops = None

    # Step 5: 构造返回结果
    return TraceEvaluationMetrics(
        filename=trace_file.name,
        classification=classification,
        has_abn1=has_abn1,
        abn1_start_time=abn1_start_time,
        first_detection_time=first_detection_time,
        detection_delay_loops=delay_loops,
        total_detection_count=len(detected_times),
        anomaly_points=anomaly_points
    )
```

---

### 算法2：Loop延迟计算

**方法A：基于数组索引**（推荐）

```python
def calculate_delay_in_loops(
    time_values: np.ndarray,
    abn1_start_time: float,
    first_detection_time: float
) -> int:
    """
    计算检测延迟（loop数）

    Args:
        time_values: trace的时间序列数组
        abn1_start_time: abn1段开始时间
        first_detection_time: 首次检测时间

    Returns:
        延迟loop数（可为负）
    """
    # 找到abn1开始时间在数组中的索引
    # abn1可能恰好等于某个时间点，或位于两个时间点之间
    abn1_indices = np.where(time_values >= abn1_start_time)[0]
    if len(abn1_indices) == 0:
        # abn1在trace结束之后（不应该发生）
        raise ValueError(f"abn1_start_time {abn1_start_time} 超出trace时间范围")

    abn1_loop_index = abn1_indices[0]

    # 找到首次检测时间的索引
    detection_indices = np.where(time_values == first_detection_time)[0]
    if len(detection_indices) == 0:
        raise ValueError(f"first_detection_time {first_detection_time} 不在trace中")

    first_detection_loop_index = detection_indices[0]

    # 计算延迟
    delay = first_detection_loop_index - abn1_loop_index

    return delay
```

**示例**：
```python
time_values = [960, 1020, 1080, ..., 52740, 52800, 52860, 52920, ..., 53400, ...]
             # 索引0  1    2          862    863    864    865         873

abn1_start_time = 52740
first_detection_time = 53400

abn1_loop_index = 862（第一个 >= 52740 的索引）
first_detection_loop_index = 873（等于 53400 的索引）

delay = 873 - 862 = 11 loops
```

**方法B：基于时间间隔计算**

```python
def calculate_delay_in_loops_v2(
    abn1_start_time: float,
    first_detection_time: float,
    time_interval: float = 60.0
) -> int:
    """
    基于固定时间间隔计算延迟

    假设：trace的时间间隔固定（RUBIS为60秒）
    """
    time_diff = first_detection_time - abn1_start_time
    delay_loops = int(time_diff / time_interval)
    return delay_loops
```

**方法对比**：

| 方法 | 优点 | 缺点 | 适用场景 |
|-----|------|------|---------|
| A: 数组索引 | 精确，不依赖时间间隔假设 | 需要查找数组 | 通用，推荐 |
| B: 时间间隔 | 计算简单 | 依赖固定间隔假设 | 时间间隔严格固定时 |

**建议**：使用方法A，因为更通用且精确。

---

### 算法3：聚合统计

```python
def aggregate_results(trace_metrics: List[TraceEvaluationMetrics]) -> AggregatedMetrics:
    """
    聚合trace级别的评估结果

    Args:
        trace_metrics: 所有trace的评估指标列表

    Returns:
        聚合指标
    """
    total_traces = len(trace_metrics)

    # 计数各分类
    tp_count = sum(1 for m in trace_metrics if m.classification == 'TP')
    fp_count = sum(1 for m in trace_metrics if m.classification == 'FP')
    fn_count = sum(1 for m in trace_metrics if m.classification == 'FN')
    tn_count = sum(1 for m in trace_metrics if m.classification == 'TN')

    # 验证总和
    assert tp_count + fp_count + fn_count + tn_count == total_traces

    # 计算性能指标
    if tp_count + fp_count > 0:
        precision = tp_count / (tp_count + fp_count)
    else:
        precision = 0.0

    if tp_count + fn_count > 0:
        recall = tp_count / (tp_count + fn_count)
    else:
        recall = 0.0

    if precision + recall > 0:
        f1_score = 2 * precision * recall / (precision + recall)
    else:
        f1_score = 0.0

    # 计算延迟统计（仅TP）
    tp_delays = [m.detection_delay_loops for m in trace_metrics
                 if m.classification == 'TP' and m.detection_delay_loops is not None]

    if tp_delays:
        avg_delay = sum(tp_delays) / len(tp_delays)
        min_delay = min(tp_delays)
        max_delay = max(tp_delays)
    else:
        avg_delay = None
        min_delay = None
        max_delay = None

    return AggregatedMetrics(
        total_traces=total_traces,
        tp_count=tp_count,
        fp_count=fp_count,
        fn_count=fn_count,
        tn_count=tn_count,
        precision=precision,
        recall=recall,
        f1_score=f1_score,
        avg_delay_loops=avg_delay,
        min_delay_loops=min_delay,
        max_delay_loops=max_delay,
        trace_metrics=trace_metrics
    )
```

---

## 数据模型变更

### TraceEvaluationMetrics（修改前后对比）

**修改前**（点级别）：
```python
@dataclass
class TraceEvaluationMetrics:
    filename: str
    tp: int = 0                     # 点级别TP数
    fp: int = 0                     # 点级别FP数
    tn: int = 0                     # 点级别TN数
    fn: int = 0                     # 点级别FN数
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    fp_rate: float = 0.0
    fn_rate: float = 0.0
    detection_delay: Optional[float] = None  # 秒
    first_anomaly_time: Optional[float] = None
    anomaly_segment_start: Optional[float] = None
    total_points: int = 0
    anomaly_points: List[AnomalyPoint] = field(default_factory=list)
```

**修改后**（trace级别）：
```python
@dataclass
class TraceEvaluationMetrics:
    filename: str                          # 文件名
    classification: str                    # 'TP' | 'FP' | 'FN' | 'TN'
    has_abn1: bool                        # 是否包含abn1段
    abn1_start_time: Optional[float]      # abn1段开始时间（如果有）
    first_detection_time: Optional[float] # 首次检测时间（如果有）
    detection_delay_loops: Optional[int]  # 检测延迟（loop数，可为负或null）
    total_detection_count: int            # 检测到的异常点总数
    anomaly_points: List[AnomalyPoint]    # 所有检测到的异常点详情
```

**字段变更说明**：

| 旧字段 | 新字段 | 变更原因 |
|--------|--------|---------|
| `tp/fp/tn/fn` | `classification` | 从4个数值变为单一分类标签 |
| `precision/recall/f1/fp_rate/fn_rate` | 移除 | 这些指标在聚合层计算，单个trace不需要 |
| `detection_delay`（秒） | `detection_delay_loops`（loops） | 单位从秒改为loop数 |
| `first_anomaly_time` | `first_detection_time` | 重命名，语义更清晰 |
| `anomaly_segment_start` | `abn1_start_time` | 重命名，明确指abn1的开始时间 |
| `total_points` | 移除 | 不再需要点级别统计 |
| 新增 | `has_abn1` | 标记是否包含abn1段 |
| 新增 | `total_detection_count` | 检测到的异常点总数（辅助调试） |

---

### AggregatedMetrics（修改前后对比）

**修改前**（点级别聚合）：
```python
@dataclass
class AggregatedMetrics:
    total_traces: int
    traces_with_anomalies: int
    total_tp: int = 0               # 所有trace的tp累加（点级别）
    total_fp: int = 0               # 所有trace的fp累加（点级别）
    total_tn: int = 0               # 所有trace的tn累加（点级别）
    total_fn: int = 0               # 所有trace的fn累加（点级别）
    overall_precision: float = 0.0
    overall_recall: float = 0.0
    overall_f1: float = 0.0
    overall_fp_rate: float = 0.0
    overall_fn_rate: float = 0.0
    avg_detection_delay: Optional[float] = None  # 秒
    min_detection_delay: Optional[float] = None
    max_detection_delay: Optional[float] = None
    detection_success_rate: float = 0.0
    trace_metrics: List[TraceEvaluationMetrics] = field(default_factory=list)
```

**修改后**（trace级别聚合）：
```python
@dataclass
class AggregatedMetrics:
    total_traces: int               # 总trace数（200）
    tp_count: int                   # TP trace数
    fp_count: int                   # FP trace数
    fn_count: int                   # FN trace数
    tn_count: int                   # TN trace数
    # 约束：tp_count + fp_count + fn_count + tn_count = total_traces

    precision: float                # tp_count / (tp_count + fp_count)
    recall: float                   # tp_count / (tp_count + fn_count)
    f1_score: float                 # 2 * P * R / (P + R)

    # 延迟统计（仅TP，单位：loops）
    avg_delay_loops: Optional[float]
    min_delay_loops: Optional[int]
    max_delay_loops: Optional[int]

    trace_metrics: List[TraceEvaluationMetrics]
```

**字段变更说明**：

| 旧字段 | 新字段 | 变更原因 |
|--------|--------|---------|
| `total_tp/fp/tn/fn` | `tp_count/fp_count/fn_count/tn_count` | 从点级别累加改为trace计数 |
| `overall_precision` | `precision` | 重命名，去掉"overall"前缀 |
| `avg_detection_delay`（秒） | `avg_delay_loops` | 单位从秒改为loop |
| `traces_with_anomalies` | 移除 | 可从`tp_count + fp_count + fn_count`推导 |
| `detection_success_rate` | 移除 | 即为`recall`，冗余 |
| `overall_fp_rate/fn_rate` | 移除 | 可从混淆矩阵推导 |

---

## 兼容性影响

### Breaking Changes

此变更会破坏：
1. **JSON输出格式**
   - `confusion_matrix`字段的值域变化（从上万降至200以内）
   - `trace_details`数组中每个元素的结构变化
   - 移除部分字段（`precision/recall/f1`从trace级别）

2. **CSV输出格式**
   - 列名变更（`tp/fp/tn/fn` → `classification`）
   - 列数减少（移除per-trace precision/recall等）

3. **Python API**
   - `TraceEvaluationMetrics`数据类变更
   - `AggregatedMetrics`数据类变更

### 迁移路径

**对于已有脚本**：
- 如果依赖JSON格式：需要更新脚本以适配新schema
- 如果依赖CSV格式：需要更新列名映射

**建议**：
- 保留一个版本号字段在JSON输出中
- 在CHANGES.md中明确标注breaking change

---

## 测试策略

### 单元测试

1. **Trace分类逻辑测试**
   ```python
   def test_tp_classification():
       # 给定：abn1_start_time = 52740, first_detection = 53400
       # 预期：classification = 'TP', delay = 11 loops
       pass

   def test_fp_classification():
       # 给定：abn1_start_time = 52740, first_detection = 49800
       # 预期：classification = 'FP', delay = -49 loops
       pass

   def test_fn_classification():
       # 给定：abn1_start_time = 52740, detected_times = []
       # 预期：classification = 'FN', delay = None
       pass
   ```

2. **Loop计算测试**
   ```python
   def test_loop_calculation():
       time_values = [960, 1020, 1080, ..., 52740, 52800, ..., 53400, ...]
       abn1 = 52740
       detection = 53400
       expected_delay = 11
       assert calculate_delay_in_loops(time_values, abn1, detection) == expected_delay
   ```

3. **聚合统计测试**
   ```python
   def test_aggregation_sum_equals_total_traces():
       # 给定：200个trace的评估结果
       metrics = aggregate_results(trace_metrics)
       assert metrics.tp_count + metrics.fp_count + metrics.fn_count + metrics.tn_count == 200
   ```

### 集成测试

1. **端到端检测**：
   - 在RUBIS数据集上运行完整检测
   - 验证输出JSON/CSV格式正确
   - 验证混淆矩阵总和 = 200

2. **边界情况**：
   - Trace完全无异常检测（FN）
   - Trace在首个数据点就检测到异常
   - abn1恰好在trace末尾

---

## 实施风险与缓解

### 风险1：现有脚本依赖旧格式

**影响**：用户可能有脚本依赖当前JSON/CSV格式

**缓解**：
- 在CHANGES.md中明确标注breaking change
- 提供迁移示例脚本
- 考虑保留旧格式输出作为临时选项（通过配置标志）

### 风险2：Loop计算边界情况

**影响**：abn1时间点可能不在数据点上

**缓解**：
- 使用"第一个≥abn1_start_time的时间点"作为基准
- 添加详细日志，记录abn1和检测时间的对应关系
- 添加单元测试覆盖边界情况

### 风险3：性能影响

**影响**：需要遍历时间数组查找索引

**缓解**：
- 使用numpy向量化操作（np.where）
- 时间复杂度O(n)，n为单个trace的数据点数（几百），可接受

---

## 实施优先级

### P0（必须）
- 修改`evaluator.py`的核心分类逻辑
- 更新数据类定义
- 修改JSON/CSV输出格式

### P1（重要）
- 添加单元测试
- 更新文档（README.md, CHANGES.md）
- 验证RUBIS数据集输出正确

### P2（可选）
- 考虑向后兼容选项
- 提供迁移脚本示例

---

**创建者**: Claude (Sonnet 4.5)
**版本**: 1.0
**最后更新**: 2026-01-17
