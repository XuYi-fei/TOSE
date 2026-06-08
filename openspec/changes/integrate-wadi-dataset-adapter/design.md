# Design: WaDi Dataset Adapter

**Change ID:** `integrate-wadi-dataset-adapter`

## Architectural Overview

The WaDi adapter introduces a **state-aware clustering and detection** architecture to handle multi-modal distributions in industrial control systems.

### Key Design Decisions

#### 1. Chunked CSV Processing Strategy

**Problem**: 290MB CSV file (1.7M rows × 141 columns) exceeds memory limits for single-pass loading.

**Solution**: Sliding window chunk reader with 10,000-row buffers.

```python
class ChunkedCSVReader:
    def __init__(self, csv_path: str, chunk_size: int = 10000):
        self.csv_path = csv_path
        self.chunk_size = chunk_size

    def iter_chunks(self) -> Iterator[pd.DataFrame]:
        """Yield chunks without loading entire CSV"""
        for chunk in pd.read_csv(self.csv_path, chunksize=self.chunk_size):
            yield chunk
```

**Trade-offs**:
- ✅ Memory usage: O(chunk_size) instead of O(dataset_size)
- ✅ Incremental processing enables streaming workflows
- ⚠️ State transitions may span chunk boundaries (requires lookahead buffer)
- ⚠️ Statistics (mean/std) require two-pass computation for accuracy

**Mitigation**: Use Welford's online algorithm for incremental variance calculation:
```python
def update_statistics(existing_mean, existing_M2, existing_count, new_value):
    count = existing_count + 1
    delta = new_value - existing_mean
    mean = existing_mean + delta / count
    delta2 = new_value - mean
    M2 = existing_M2 + delta * delta2
    return mean, M2, count
```

#### 2. Environment State Detection Architecture

**Problem**: WaDi metrics exhibit multi-modal distributions driven by pump/valve configurations. Standard HDBSCAN will treat these as multiple clusters, but they represent different operational states, not anomalies.

**Solution**: Two-stage clustering:

```
Stage 1: Environment State Detection
  Input: Pump/valve status columns
  Output: State labels (LOW/MEDIUM/HIGH flow configurations)
  Method: K-means on binary status vector

Stage 2: State-Conditional Metric Clustering
  Input: Metric values within each state
  Output: Normal distribution per state
  Method: HDBSCAN + Gaussian fitting within state groups
```

**Example**:
```python
# Stage 1: Detect states from pump status
pump_features = df[['HMI_2_P_001_STATUS', 'HMI_2_P_002_STATUS']].values
state_labels = KMeans(n_clusters=3).fit_predict(pump_features)

# Stage 2: Cluster metrics per state
for state_id in [0, 1, 2]:
    state_mask = (state_labels == state_id)
    state_metrics = df.loc[state_mask, 'HMI_2_FIT_001.PV']
    clusters = HDBSCAN(min_cluster_size=50).fit(state_metrics.reshape(-1, 1))
    distributions[state_id] = compute_gaussian(state_metrics[clusters.labels_ != -1])
```

**Trade-offs**:
- ✅ Avoids false positives from legitimate state transitions
- ✅ Enables state-conditional anomaly detection (test within current state)
- ⚠️ Requires accurate pump/valve status data (may have "Bad Input")
- ⚠️ Assumes discrete states (may miss gradual transitions)

**Mitigation**: Fallback to time-series segmentation if status data unreliable:
```python
if status_column_has_bad_inputs():
    # Use metric change points instead
    state_labels = detect_change_points(metric_values, method='PELT')
```

#### 3. Metric Selection Strategy

**Problem**: 141 columns include redundant sensors, control signals, and noisy data. Manual selection is infeasible.

**Solution**: Automated metric ranking by **data quality × variability × domain priority**.

```python
def rank_metrics(df: pd.DataFrame) -> List[str]:
    candidates = []
    for col in df.columns:
        if not col.endswith('.PV'):  # Only process values
            continue

        # Data quality: completeness and numeric validity
        completeness = df[col].notna().mean()
        if completeness < 0.8:
            continue

        # Variability: coefficient of variation
        cv = df[col].std() / df[col].mean()
        if cv < 0.01 or cv > 2:  # Too stable or too noisy
            continue

        # Domain priority: sensor type weighting
        sensor_type = parse_sensor_type(col)  # FIT > PIT > LT > AIT
        priority = {'FIT': 3, 'PIT': 2, 'LT': 1, 'AIT': 1}.get(sensor_type, 0)

        score = completeness * min(cv, 1) * priority
        candidates.append((col, score))

    return [col for col, _ in sorted(candidates, key=lambda x: x[1], reverse=True)]
```

**Selected Metrics** (by this algorithm):
1. `HMI_2_FIT_001.PV` (flow, score=3.0 × 1.0 × 3 = 9.0)
2. `HMI_2_PIT_001.PV` (pressure, score=1.0 × 0.4 × 2 = 0.8)
3. `HMI_2_LT_001.PV` (level, score=1.0 × 0.2 × 1 = 0.2)

**Trade-offs**:
- ✅ Objective ranking removes manual bias
- ✅ Adapts to different datasets automatically
- ⚠️ May miss low-variability anomalies (e.g., sensor freezing)
- ⚠️ Requires domain knowledge for sensor type priorities

**Mitigation**: Allow manual override in config file:
```yaml
wadi_config:
  metric_selection:
    auto_rank: true
    manual_override:
      - HMI_1_LT_002.PV  # Force include even if low-ranked
    exclude:
      - HMI_3_AIT_001.PV  # Exclude noisy sensor
```

#### 4. Integration with Existing Framework

**Adapter Pattern**: WadiAdapter implements same interface as RubisAdapter/BsnAdapter.

```python
class WadiAdapter(BaseAdapter):
    """Water Distribution system adapter with state-aware clustering"""

    def load_identity_data(self, data_path: str) -> pd.DataFrame:
        """Load normal traces from WaDi CSV with chunked reading"""
        chunks = []
        for chunk in ChunkedCSVReader(data_path).iter_chunks():
            # Filter valid data points
            chunk = chunk[chunk['HMI_2_P_001_STATUS'] != 'Bad Input']
            chunks.append(chunk)
        return pd.concat(chunks, ignore_index=True)

    def cluster_by_environment(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Group data by operational state before clustering"""
        state_detector = EnvironmentStateDetector(
            pump_columns=['HMI_2_P_001_STATUS', 'HMI_2_P_002_STATUS']
        )
        state_labels = state_detector.detect_states(df)

        segments = {}
        for state_id in np.unique(state_labels):
            state_name = f"flow_state_{state_id}"  # E.g., flow_state_0 = LOW
            segments[state_name] = df[state_labels == state_id]
        return segments

    def get_metrics(self) -> List[str]:
        """Return primary metrics for clustering"""
        return ['HMI_2_FIT_001.PV', 'HMI_2_PIT_001.PV', 'HMI_2_LT_001.PV']
```

**Registration**:
```python
# cluster_analysis/adapters/__init__.py
ADAPTER_REGISTRY = {
    'rubis': RubisAdapter,
    'bsn': BsnAdapter,
    'wadi': WadiAdapter,  # New registration
}
```

**Trade-offs**:
- ✅ Minimal changes to existing code (only add adapter)
- ✅ Existing clustering/detection logic reused
- ⚠️ State-conditional detection requires updating AnomalyDetector
- ⚠️ Config files need new `environment_detection` section

#### 5. State-Conditional Anomaly Detection

**Problem**: Standard 3-sigma detection tests against all learned distributions. For WaDi, this would flag state transitions as anomalies.

**Solution**: Context-aware z-score calculation.

```python
class WadiAnomalyDetector(AnomalyDetector):
    def detect_point_anomaly(
        self,
        metric_value: float,
        current_state: str  # E.g., "flow_state_1"
    ) -> Tuple[bool, float]:
        """Test against distribution for current state only"""

        if current_state not in self.distributions:
            # Unknown state: test against all distributions (conservative)
            return super().detect_point_anomaly(metric_value)

        # State-conditional test
        dist = self.distributions[current_state]
        z_score = abs((metric_value - dist.mu) / dist.sigma)
        is_anomaly = z_score > self.sigma_threshold

        return is_anomaly, z_score
```

**State Inference During Detection**:
```python
def detect_trace(self, trace_df: pd.DataFrame) -> List[DetectionResult]:
    """Detect anomalies with online state inference"""
    results = []

    # Infer current state from pump status
    current_state = self._infer_state_from_status(
        trace_df[['HMI_2_P_001_STATUS', 'HMI_2_P_002_STATUS']]
    )

    for idx, row in trace_df.iterrows():
        metric_value = row['HMI_2_FIT_001.PV']
        is_anomaly, z_score = self.detect_point_anomaly(metric_value, current_state)
        results.append(DetectionResult(
            timestamp=row['Time'],
            is_anomaly=is_anomaly,
            z_score=z_score,
            state=current_state
        ))

    return results
```

**Trade-offs**:
- ✅ Eliminates false positives from state transitions
- ✅ Enables state-specific threshold tuning
- ⚠️ Requires real-time state inference (adds latency)
- ⚠️ May miss anomalies that span state transitions

**Mitigation**: Hybrid approach - test both state-conditional AND cross-state:
```python
is_anomaly = (
    z_score_within_state > threshold_high OR
    z_score_across_all_states > threshold_low
)
```

## Data Flow

```
1. Data Loading (Chunked)
   CSV → ChunkedCSVReader → 10k-row chunks → Filter "Bad Input" → Concatenate

2. Metric Selection
   All columns → Rank by quality/variability/domain → Top 3 metrics

3. Environment State Detection
   Pump/valve status → K-means clustering → State labels (LOW/MED/HIGH)

4. State-Conditional Clustering
   For each state:
     Metric values → HDBSCAN → Filter outliers → Gaussian fit → Distribution params

5. Detection (Online)
   Test point → Infer state from pump status → Get state distribution → Z-score test → Anomaly flag
```

## Configuration Schema

```yaml
# configs/wadi_cluster_config.yaml
system_type: wadi
data_sources:
  identity_csv: data/wadi/WaDi.A3_Dec 2023 Historian Data_original.csv

metric_selection:
  auto_rank: true
  max_metrics: 3
  quality_threshold: 0.8  # Data completeness
  variability_range: [0.01, 2.0]  # CV bounds

environment_detection:
  method: pump_status  # or 'change_point'
  pump_columns:
    - HMI_2_P_001_STATUS
    - HMI_2_P_002_STATUS
  num_states: 3  # LOW/MEDIUM/HIGH

clustering:
  method: hdbscan
  min_cluster_size: 50
  state_aware: true  # Cluster within states

processing:
  chunk_size: 10000
  memory_limit_mb: 2048
```

## Testing Strategy

### Unit Tests
- `test_chunked_csv_reader`: Verify chunk boundaries don't lose data
- `test_environment_state_detector`: Mock pump status → expected state labels
- `test_metric_selector`: Known dataset → expected ranking

### Integration Tests
- `test_wadi_adapter_end_to_end`: CSV → clustering → learned_distributions.yaml
- `test_state_conditional_detection`: Trace with state transitions → no false positives at boundaries

### Performance Tests
- `test_memory_usage`: Process full 290MB CSV, assert peak memory < 3GB
- `test_chunked_vs_full_distributions`: Compare learned distributions with/without chunking (should match within 1%)

## Open Questions

1. **State Transition Handling**: Should we flag rapid state transitions (e.g., pump ON→OFF in <30s) as anomalies?
   - **Recommendation**: No, treat as normal unless metric values deviate within the new state.

2. **Cross-Zone Dependencies**: Should HMI_1 metrics affect HMI_2 state detection?
   - **Recommendation**: Phase 2 feature. Start with independent zones.

3. **Adaptive State Count**: Should `num_states` be auto-detected via elbow method?
   - **Recommendation**: Yes, add optional `auto_detect_states: true` flag.

4. **Historical State Labels**: Should we save detected states to CSV for reproducibility?
   - **Recommendation**: Yes, output `wadi_state_labels.csv` alongside distributions.

## Future Enhancements

1. **Online State Prediction**: Use LSTM to predict next state from metric trends
2. **Cross-Metric Anomalies**: Detect inconsistent state labels between flow/pressure/level
3. **Actuator Recommendation**: Suggest valve adjustments to return to normal state
4. **Real-Time Streaming**: Adapt chunked reader to consume live SCADA data
