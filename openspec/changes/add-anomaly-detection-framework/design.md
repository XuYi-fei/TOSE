# Design: 异常检测框架架构设计

## 架构概览

异常检测框架采用三层架构，与现有validation和clustering框架保持一致：

```
┌────────────────────────────────────────────────────────┐
│              CLI Layer (detect.py)                     │
│   - 配置加载                                            │
│   - 命令行参数解析                                       │
│   - 结果输出                                            │
└─────────────────┬──────────────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────────────┐
│         Business Logic Layer                           │
│  ┌──────────────────────────────────────────────────┐ │
│  │  anomaly_detection/                              │ │
│  │   ├─ core/                                       │ │
│  │   │   ├─ detector.py    (异常检测引擎)           │ │
│  │   │   ├─ evaluator.py   (FP/FN评估器)           │ │
│  │   │   └─ distribution.py (分布模型)              │ │
│  │   ├─ config/                                     │ │
│  │   │   └─ config.py      (配置管理)              │ │
│  │   └─ visualization/                              │ │
│  │       └─ reporter.py    (报告生成)              │ │
│  └──────────────────────────────────────────────────┘ │
└─────────────────┬──────────────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────────────┐
│         Common Data Layer (common/)                    │
│   - adapters: TraceParser (扩展支持abn标签)            │
│   - models: TraceMetadata, DistributionParameters      │
│   - utils: statistics                                  │
└────────────────────────────────────────────────────────┘
```

## 核心组件设计

### 1. LearnedDistribution（已学习分布）

```python
@dataclass
class LearnedDistribution:
    """从聚类学习到的分布参数"""
    label: str          # 分布标签（如norm1, norm2）
    mu: float           # 均值
    sigma: float        # 标准差
    sample_count: int   # 样本数量

    def probability_density(self, value: float) -> float:
        """计算给定值的概率密度"""

    def z_score(self, value: float) -> float:
        """计算给定值的z分数（标准化偏离度）"""

    def is_outlier(self, value: float, sigma_threshold: float = 3.0) -> bool:
        """判断给定值是否为异常值（超过sigma_threshold倍标准差）"""
```

### 2. AnomalyDetector（异常检测器）

```python
class AnomalyDetector:
    """异常检测引擎"""

    def __init__(
        self,
        distributions: Dict[str, LearnedDistribution],
        sigma_threshold: float = 3.0
    ):
        """初始化检测器

        Args:
            distributions: 已知分布字典
            sigma_threshold: 异常判定阈值（默认3-sigma）
        """

    def detect_point(self, value: float) -> DetectionResult:
        """检测单个数据点

        Returns:
            DetectionResult包含：
            - is_anomaly: 是否异常
            - closest_distribution: 最近的分布
            - min_z_score: 最小z分数
            - all_z_scores: 所有分布的z分数
        """

    def detect_trace(
        self,
        trace_file: Path,
        metadata: TraceMetadata
    ) -> TraceDetectionResult:
        """检测整个trace文件

        Returns:
            TraceDetectionResult包含：
            - filename: 文件名
            - segments: 各段检测结果
            - anomaly_points: 异常点列表（时间、值、z分数）
            - ground_truth_labels: 真实标签（norm1/abn1等）
        """
```

### 3. AnomalyEvaluator（异常评估器）

```python
class AnomalyEvaluator:
    """FP/FN评估器"""

    def evaluate_trace(
        self,
        detection_result: TraceDetectionResult,
        metadata: TraceMetadata
    ) -> EvaluationMetrics:
        """评估单个trace的检测性能

        计算逻辑：
        - TP (True Positive): abn段检测到异常
        - FP (False Positive): norm段误判为异常
        - TN (True Negative): norm段正确识别为正常
        - FN (False Negative): abn段未检测到异常

        Returns:
            EvaluationMetrics包含：
            - tp, fp, tn, fn: 混淆矩阵
            - precision, recall, f1: 性能指标
            - detection_delay: 检测延迟（秒）
            - first_anomaly_time: 第一个异常点时间
        """

    def aggregate_results(
        self,
        trace_results: List[EvaluationMetrics]
    ) -> AggregatedMetrics:
        """聚合多个trace的评估结果"""
```

### 4. DetectionReporter（检测报告器）

```python
class DetectionReporter:
    """检测报告生成器"""

    def generate_report(
        self,
        detection_results: List[TraceDetectionResult],
        evaluation_metrics: AggregatedMetrics,
        output_dir: Path
    ) -> str:
        """生成Markdown报告

        报告内容：
        1. 检测概览（总trace数、异常检测率）
        2. 性能指标（FP率、FN率、精确率、召回率）
        3. 检测延迟统计（平均、最小、最大）
        4. 异常案例展示（前10个）
        5. 可视化图表
        """

    def plot_detection_timeline(
        self,
        trace_result: TraceDetectionResult
    ) -> str:
        """绘制检测时间线图

        展示：
        - X轴：时间
        - Y轴：响应时间值
        - 颜色：不同段（norm1/norm2/abn1）
        - 标记：异常点（红色X）
        """
```

## 数据流设计

### 阶段1：聚类结果保存

```
ClusteringEngine.run_clustering()
    ↓
ClusteringResult (内存中的聚类结果)
    ↓
ClusteringReporter.save_learned_distributions()
    ↓
learned_distributions.yaml (持久化配置)
```

**learned_distributions.yaml格式**:
```yaml
system_type: rubis
learned_at: "2024-01-15T23:44:00"
algorithm: hdbscan
silhouette_score: 0.9915
clustering_config: configs/rubis_clustering_config.yaml

distributions:
  norm1:
    mu: 0.052544
    sigma: 0.002449
    variance: 0.000006
    sample_count: 164
    cluster_id: 2

  norm2:
    mu: 0.115244
    sigma: 0.012884
    variance: 0.000166
    sample_count: 174
    cluster_id: 0

  norm3:
    mu: 0.028450
    sigma: 0.001732
    variance: 0.000003
    sample_count: 166
    cluster_id: 1
```

### 阶段2：异常检测执行

```
DetectionConfig.from_yaml()
    ↓
LearnedDistribution.load_from_yaml()
    ↓
AnomalyDetector.__init__(distributions)
    ↓
for each trace_file:
    TraceParser.parse_file()
        ↓
    AnomalyDetector.detect_trace()
        ↓ (逐点检测)
    for each data_point:
        计算z_score = (value - mu) / sigma  (对所有分布)
        if min(abs(z_score)) > threshold:
            标记为异常
    ↓
AnomalyEvaluator.evaluate_trace()
    ↓
DetectionReporter.generate_report()
```

## 异常检测算法

### 3-Sigma规则实现

```python
def detect_point(self, value: float) -> DetectionResult:
    """
    对每个已知分布计算z分数：
        z_i = (value - μ_i) / σ_i

    异常判定条件：
        对所有分布i，|z_i| > threshold（默认3）

    即：该点偏离所有已知分布至少3倍标准差
    """
    z_scores = {}
    for label, dist in self.distributions.items():
        z_scores[label] = dist.z_score(value)

    min_abs_z = min(abs(z) for z in z_scores.values())
    is_anomaly = min_abs_z > self.sigma_threshold

    # 找到最接近的分布
    closest_label = min(z_scores, key=lambda k: abs(z_scores[k]))

    return DetectionResult(
        is_anomaly=is_anomaly,
        closest_distribution=closest_label,
        min_z_score=z_scores[closest_label],
        all_z_scores=z_scores
    )
```

### FP/FN计算逻辑

```python
def evaluate_trace(self, detection_result, metadata):
    """
    根据ground truth计算混淆矩阵：

    对每个时间段segment：
        if segment_label.startswith('norm'):
            # 正常段
            for point in segment:
                if point.is_anomaly:
                    FP += 1  # 误报
                else:
                    TN += 1  # 正确

        elif segment_label.startswith('abn'):
            # 异常段
            for point in segment:
                if point.is_anomaly:
                    TP += 1  # 正确检出
                    if not first_detected:
                        detection_delay = point.time - segment.start_time
                        first_detected = True
                else:
                    FN += 1  # 漏报

    precision = TP / (TP + FP)  if TP + FP > 0 else 0
    recall = TP / (TP + FN)     if TP + FN > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0

    FP_rate = FP / (FP + TN)  if FP + TN > 0 else 0
    FN_rate = FN / (TP + FN)  if TP + FN > 0 else 0
    """
```

## TraceParser扩展

需要扩展`common/adapters/`中的parser以支持abn标签：

```python
# 在 rubis.py 和 bsn.py 中
class RUBISParser(TraceParser):
    # 文件名正则扩展，支持abn标签
    FILENAME_PATTERN = re.compile(
        r'eval_(ident|abn)_trace-cnt-(?P<cnt>\d+)'
        r'-duration-(?P<duration>\d+)'
        r'-config_num-(?P<config_num>\d+)'
        r'-trace_config-(?P<trace_config>[^-]+)'  # 可包含norm1,norm2,abn1等
        r'-start_time-(?P<start_time>[^.]+)'
    )

    def parse_filename(self, filename: str):
        """
        解析包含abn标签的文件名
        trace_config可能包含: norm1, norm2, norm3, abn1, abn2等
        """
```

## 配置文件设计

### 检测配置 (rubis_detection_config.yaml)

```yaml
# 系统类型
system_type: rubis

# 已学习的分布参数文件路径
learned_distributions: clustering_results/rubis/learned_distributions.yaml

# 测试数据路径（包含异常的trace）
test_data_path: rubis_evaluation_data/eval_abn_traces

# 异常检测参数
detection:
  sigma_threshold: 3.0      # 3-sigma规则
  min_samples_for_detection: 5  # 至少5个点才判定异常（减少噪声）

# 输出配置
output:
  dir: detection_results/rubis
  generate_visualizations: true
  generate_detailed_report: true
  save_anomaly_points: true  # 保存异常点详细信息
```

## 可扩展性设计

### 支持新系统类型

1. 在`common/adapters/`中添加新的Parser类
2. 实现`parse_filename()`支持该系统的trace命名规则
3. 在配置文件中指定`system_type`
4. 检测框架自动适配

### 支持新的检测算法

```python
# 抽象检测器基类
class AnomalyDetector(ABC):
    @abstractmethod
    def detect_point(self, value: float) -> DetectionResult:
        pass

# 3-Sigma检测器
class SigmaBasedDetector(AnomalyDetector):
    def detect_point(self, value: float):
        # 3-sigma实现

# 未来可扩展：
class IsolationForestDetector(AnomalyDetector):
    def detect_point(self, value: float):
        # Isolation Forest实现
```

## 性能考虑

1. **批处理优化**：一次性加载所有trace文件路径，并行处理
2. **内存管理**：逐文件处理，避免同时加载所有trace数据
3. **缓存机制**：已学习的分布参数只加载一次
4. **目标性能**：200个trace文件 < 10秒

## 错误处理

1. **配置文件缺失**：明确错误提示，指导用户先运行clustering
2. **trace文件解析失败**：记录错误日志，跳过该文件继续处理
3. **分布参数异常**：验证sigma > 0，mu在合理范围
4. **无异常段的trace**：正确处理只有norm段的trace（FN=0, 全部算TN）

## 测试策略

1. **单元测试**：
   - LearnedDistribution.z_score()计算正确性
   - AnomalyDetector.detect_point()边界情况
   - AnomalyEvaluator的TP/FP/TN/FN计算

2. **集成测试**：
   - 端到端：clustering → save → detection → report
   - 使用已知异常数据验证检测准确性

3. **性能测试**：
   - 200个trace文件处理时间 < 10秒
