# 实施任务清单：Trace级别异常检测评估

**变更ID**: `redesign-trace-level-detection-evaluation`

---

## 阶段1：数据模型变更（P0）

### Task 1.1: 修改 TraceEvaluationMetrics 数据类

**文件**: `anomaly_detection/core/evaluator.py`

**变更内容**:
```python
# 修改前（点级别）
@dataclass
class TraceEvaluationMetrics:
    filename: str
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    fp_rate: float = 0.0
    fn_rate: float = 0.0
    detection_delay: Optional[float] = None
    first_anomaly_time: Optional[float] = None
    anomaly_segment_start: Optional[float] = None
    total_points: int = 0
    anomaly_points: List[AnomalyPoint] = field(default_factory=list)

# 修改后（trace级别）
@dataclass
class TraceEvaluationMetrics:
    filename: str
    classification: str                    # 'TP' | 'FP' | 'FN' | 'TN'
    has_abn1: bool                        # 是否包含abn1段
    abn1_start_time: Optional[float]      # abn1段开始时间（如果有）
    first_detection_time: Optional[float] # 首次检测时间（如果有）
    detection_delay_loops: Optional[int]  # 检测延迟（loop数）
    total_detection_count: int            # 检测到的异常点总数
    anomaly_points: List[AnomalyPoint]    # 所有检测到的异常点详情
```

**验收标准**:
- [ ] 数据类定义正确
- [ ] 所有字段有明确的类型注解
- [ ] docstring说明了每个字段的含义

---

### Task 1.2: 修改 AggregatedMetrics 数据类

**文件**: `anomaly_detection/core/evaluator.py`

**变更内容**:
```python
# 修改前（点级别聚合）
@dataclass
class AggregatedMetrics:
    total_traces: int
    traces_with_anomalies: int
    total_tp: int = 0
    total_fp: int = 0
    total_tn: int = 0
    total_fn: int = 0
    overall_precision: float = 0.0
    overall_recall: float = 0.0
    overall_f1: float = 0.0
    overall_fp_rate: float = 0.0
    overall_fn_rate: float = 0.0
    avg_detection_delay: Optional[float] = None
    min_detection_delay: Optional[float] = None
    max_detection_delay: Optional[float] = None
    detection_success_rate: float = 0.0
    trace_metrics: List[TraceEvaluationMetrics] = field(default_factory=list)

# 修改后（trace级别聚合）
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

**验收标准**:
- [ ] 数据类定义正确
- [ ] 移除了所有点级别的字段
- [ ] 约束条件在注释中明确说明

---

## 阶段2：核心算法实现（P0）

### Task 2.1: 实现 calculate_delay_in_loops 函数

**文件**: `anomaly_detection/core/evaluator.py`

**新增函数**:
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
    abn1_indices = np.where(time_values >= abn1_start_time)[0]
    if len(abn1_indices) == 0:
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

**验收标准**:
- [ ] 函数实现正确
- [ ] 处理边界情况（时间不在数组中）
- [ ] 支持负延迟（FP情况）
- [ ] 单元测试通过

---

### Task 2.2: 重写 evaluate_trace 方法（核心修改）

**文件**: `anomaly_detection/core/evaluator.py`

**修改方法**: `AnomalyEvaluator.evaluate_trace()`

**新实现逻辑**:
```python
def evaluate_trace(self, trace_file: Path) -> TraceEvaluationMetrics:
    """
    评估单个trace文件（trace级别分类）

    返回:
        TraceEvaluationMetrics: 包含单一分类标签的评估结果
    """
    # Step 1: 解析文件名
    metadata = self.parser.parse_filename(trace_file.name)
    if not metadata:
        raise ValueError(f"无法解析文件名: {trace_file.name}")

    trace_config = metadata.trace_config
    start_time = metadata.start_time

    # 提取abn1信息
    has_abn1 = 'abn1' in trace_config
    if has_abn1:
        abn1_index = trace_config.index('abn1')
        abn1_start_time = start_time[abn1_index]
    else:
        abn1_start_time = None

    # Step 2: 读取trace数据
    segments = self.parser.parse_trace_file(trace_file, metadata)
    df = pd.concat(segments, ignore_index=True)

    time_values = df['simTime(s)'].values
    response_times = df[self.parser.TARGET_COLUMN].values

    # Step 3: 逐点检测，收集所有异常时间
    detected_times = []
    anomaly_points = []

    for i, (time, value) in enumerate(zip(time_values, response_times)):
        detection_result = self.detector.detect_point(value)
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

**验收标准**:
- [ ] 方法实现正确
- [ ] 每个trace返回单一分类标签
- [ ] 延迟计算正确（loop数）
- [ ] 处理FN情况（delay=None）
- [ ] 单元测试通过（TP/FP/FN/TN各一个case）

---

### Task 2.3: 重写 aggregate_results 方法

**文件**: `anomaly_detection/core/evaluator.py`

**修改方法**: `AnomalyEvaluator.aggregate_results()`

**新实现逻辑**:
```python
def aggregate_results(
    self, trace_metrics: List[TraceEvaluationMetrics]
) -> AggregatedMetrics:
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
    assert tp_count + fp_count + fn_count + tn_count == total_traces, \
        f"分类总和 {tp_count + fp_count + fn_count + tn_count} != {total_traces}"

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

**验收标准**:
- [ ] 方法实现正确
- [ ] 混淆矩阵总和 = total_traces
- [ ] 性能指标计算正确
- [ ] 延迟统计仅包含TP
- [ ] 单元测试通过

---

## 阶段3：输出格式更新（P0）

### Task 3.1: 更新 JSON 输出格式

**文件**: `anomaly_detection/visualization/reporter.py`

**修改方法**: `AnomalyReporter.generate_json_report()`

**新格式**:
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
      "filename": "eval_abn_trace-cnt-000-...",
      "classification": "TP",
      "abn1_start_time": 52740,
      "first_detection_time": 53400,
      "detection_delay_loops": 11,
      "total_detection_count": 45
    }
  ]
}
```

**验收标准**:
- [ ] JSON schema正确
- [ ] 所有字段类型正确
- [ ] TP+FP+FN+TN = total_traces
- [ ] 延迟单位为loops

---

### Task 3.2: 更新 CSV 输出格式

**文件**: `anomaly_detection/visualization/reporter.py`

**修改方法**: `AnomalyReporter.generate_csv_report()`

**新CSV列**:
```
filename,classification,abn1_start_time,first_detection_time,delay_loops,total_detections
eval_abn_trace-cnt-000-...,TP,52740,53400,11,45
eval_abn_trace-cnt-001-...,FP,50340,49800,-9,12
eval_abn_trace-cnt-002-...,FN,51540,N/A,N/A,0
```

**验收标准**:
- [ ] CSV列定义正确
- [ ] 数据类型正确（int, float, str）
- [ ] null值用"N/A"表示
- [ ] 可被pandas正常读取

---

### Task 3.3: 更新 Markdown 报告格式

**文件**: `anomaly_detection/visualization/reporter.py`

**修改方法**: `AnomalyReporter.generate_markdown_report()`

**新格式要点**:
- 混淆矩阵显示trace计数（≤200）
- 延迟统计单位为loops
- 移除点级别的统计信息

**验收标准**:
- [ ] Markdown格式正确
- [ ] 表格清晰易读
- [ ] 数值语义正确

---

## 阶段4：测试（P1）

### Task 4.1: 编写单元测试

**文件**: `tests/test_trace_level_evaluation.py`（新建）

**测试用例**:
```python
def test_tp_classification():
    """测试TP分类：abn1=52740, first_detection=53400"""
    # 预期：classification='TP', delay=11 loops
    pass

def test_fp_classification():
    """测试FP分类：abn1=52740, first_detection=49800"""
    # 预期：classification='FP', delay=-49 loops
    pass

def test_fn_classification():
    """测试FN分类：abn1=52740, detected_times=[]"""
    # 预期：classification='FN', delay=None
    pass

def test_tn_classification():
    """测试TN分类：no abn1, detected_times=[]"""
    # 预期：classification='TN', delay=None
    pass

def test_loop_calculation():
    """测试loop计算"""
    time_values = np.array([960, 1020, 1080, ..., 52740, 52800, ..., 53400, ...])
    abn1 = 52740
    detection = 53400
    expected_delay = 11
    assert calculate_delay_in_loops(time_values, abn1, detection) == expected_delay

def test_aggregation_sum():
    """测试聚合总和"""
    # 给定：200个trace的评估结果
    # 预期：tp_count + fp_count + fn_count + tn_count = 200
    pass
```

**验收标准**:
- [ ] 所有测试通过
- [ ] 代码覆盖率 > 90%
- [ ] 边界情况测试完整

---

### Task 4.2: 集成测试

**测试内容**:
1. 在RUBIS数据集上运行完整检测
2. 验证输出JSON/CSV格式正确
3. 验证混淆矩阵总和 = 200
4. 验证延迟计算合理（TP delay ≥ 0）

**测试命令**:
```bash
python detect.py --config configs/rubis_detection_config.yaml
```

**验收标准**:
- [ ] 检测成功完成
- [ ] JSON文件格式正确
- [ ] CSV文件格式正确
- [ ] TP+FP+FN+TN = 200
- [ ] precision, recall, f1 ∈ [0, 1]
- [ ] avg_delay_loops合理

---

## 阶段5：文档更新（P1）

### Task 5.1: 更新 CHANGES.md

**文件**: `CHANGES.md`

**新增内容**:
```markdown
# 更新说明 - 2026-01-17

## 🎯 Breaking Change: Trace级别异常检测评估

重新设计了异常检测评估逻辑，从点级别改为trace级别。

### 重大变更

**混淆矩阵语义变更**：
- **修改前**：每个数据点计入TP/FP/TN/FN，总和可达数万
- **修改后**：每个trace分类为单一类别（TP/FP/FN/TN），总和=总trace数（200）

**延迟单位变更**：
- **修改前**：秒（时间戳差）
- **修改后**：loops（时间步数）

**输出格式变更**：
- JSON schema修改
- CSV列定义修改
- 混淆矩阵数值范围变化

### 迁移指南

**JSON输出**：
- `confusion_matrix.TP` 从74028降至~180
- `trace_details[].classification` 从4个数值变为单一标签
- `detection_delay` 从秒改为 `detection_delay_loops`

**CSV输出**：
- 列 `tp/fp/tn/fn` 合并为 `classification`
- 列 `detection_delay` 改为 `delay_loops`

### 影响范围

- ❌ 不兼容旧版JSON/CSV解析脚本
- ✅ 检测算法未变更
- ✅ 配置文件格式未变更
```

**验收标准**:
- [ ] 变更说明清晰
- [ ] 迁移指南完整
- [ ] 影响范围明确

---

### Task 5.2: 更新 README.md

**文件**: `README.md`

**修改内容**:
- 更新JSON输出示例（使用新格式）
- 更新CSV格式说明
- 更新字段说明表格

**验收标准**:
- [ ] 示例代码正确
- [ ] 字段说明准确
- [ ] 与实际输出一致

---

## 阶段6：验证与部署（P1）

### Task 6.1: 在RUBIS数据集上验证

**验证步骤**:
1. 删除旧的detection_results输出
2. 运行聚类分析（确保learned_distributions.yaml存在）
3. 运行异常检测
4. 检查输出文件格式
5. 手工验证几个trace的分类结果

**验收标准**:
- [ ] 所有200个trace都有分类结果
- [ ] TP+FP+FN+TN = 200
- [ ] 延迟统计合理
- [ ] 无错误或警告

---

### Task 6.2: 性能测试

**测试内容**:
- 运行时间是否在可接受范围（<5秒）
- 内存使用是否正常

**验收标准**:
- [ ] 处理200个trace < 5秒
- [ ] 内存使用 < 1GB

---

## 实施顺序建议

**第一天**:
- Task 1.1, 1.2（数据模型变更）
- Task 2.1（loop计算函数）

**第二天**:
- Task 2.2（evaluate_trace重写）
- Task 2.3（aggregate_results重写）
- Task 4.1（单元测试）

**第三天**:
- Task 3.1, 3.2, 3.3（输出格式更新）
- Task 4.2（集成测试）

**第四天**:
- Task 5.1, 5.2（文档更新）
- Task 6.1, 6.2（验证与部署）

---

## 风险与依赖

**依赖**:
- 无外部依赖变更
- numpy已在requirements.txt中

**风险**:
- 旧脚本需要更新（已在CHANGES.md中说明）
- 混淆矩阵数值大幅下降可能让用户惊讶（需在文档中解释）

---

**创建者**: Claude (Sonnet 4.5)
**版本**: 1.0
**最后更新**: 2026-01-17
