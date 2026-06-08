# Capability: Environment State Detection

**Capability ID:** `environment_state_detection`
**Change:** `integrate-wadi-dataset-adapter`
**Status:** Proposed

## Overview

Environment State Detection identifies operational states in the WaDi system based on pump/valve configurations. It enables state-conditional clustering and anomaly detection to avoid false positives during legitimate state transitions.

## ADDED Requirements

### Requirement: Detect Operational States from Pump Status

**ID:** `WADI-STATE-001`

The system SHALL identify distinct operational states by clustering pump and valve status patterns.

#### Scenario: Detect 3 Flow States from Pump Combinations

**Given** a DataFrame with pump status columns:
```
HMI_2_P_001_STATUS: [1, 1, 0, 0, 1, 1, ...]  # Pump 1 ON/OFF
HMI_2_P_002_STATUS: [0, 1, 0, 1, 1, 0, ...]  # Pump 2 ON/OFF
```

**When** the state detector analyzes patterns with `EnvironmentStateDetector.detect_states(df)`

**Then** the system SHALL:
1. Extract binary status vectors for each row
2. Apply K-means clustering with k=3 (configurable)
3. Assign state labels: 0=LOW flow (both OFF), 1=MEDIUM flow (one ON), 2=HIGH flow (both ON)
4. Return state label array matching DataFrame row count

**Expected Output**:
```python
detector = EnvironmentStateDetector(pump_columns=['HMI_2_P_001_STATUS', 'HMI_2_P_002_STATUS'])
state_labels = detector.detect_states(df)

assert len(state_labels) == len(df)
assert set(state_labels) == {0, 1, 2}  # Three states detected
```

#### Scenario: Handle "Bad Input" in Status Columns

**Given** pump status with "Bad Input" values:
```
HMI_2_P_001_STATUS: [1, "Bad Input", 0, 1]
```

**When** state detection is performed

**Then** the system SHALL:
- Convert "Bad Input" to NaN
- Forward-fill NaN with last valid state (assume state persists)
- Log warning about imputed values

**Example**:
```python
# Before: [1, "Bad Input", 0, 1]
# After:  [1, 1, 0, 1]  (NaN filled with previous 1)
```

---

### Requirement: Fallback to Change Point Detection

**ID:** `WADI-STATE-002`

The system SHALL provide alternative state detection using metric change points when pump status data is unreliable (>20% "Bad Input").

#### Scenario: Detect States from Flow Metric Trends

**Given** a flow metric `HMI_2_FIT_001.PV` with values cycling between [0.003, 1.3, 2.4]

**When** pump status has >20% "Bad Input" AND change point detection is enabled

**Then** the system SHALL:
1. Apply PELT (Pruned Exact Linear Time) algorithm to detect distribution shifts
2. Segment data at detected change points
3. Assign state labels based on mean flow rate in each segment:
   - state_0: mean < 0.5 L/s (LOW)
   - state_1: 0.5 ≤ mean < 2.0 L/s (MEDIUM)
   - state_2: mean ≥ 2.0 L/s (HIGH)

**Example**:
```python
detector = EnvironmentStateDetector(
    pump_columns=['HMI_2_P_001_STATUS'],
    fallback_metric='HMI_2_FIT_001.PV',
    fallback_threshold=0.2  # Switch to change point if >20% bad
)

state_labels = detector.detect_states(df)
# Uses change point detection automatically if pump data poor
```

---

### Requirement: Validate State Consistency with Metrics

**ID:** `WADI-STATE-003`

The system SHALL validate that detected states correlate with expected metric distributions to ensure state detection accuracy.

#### Scenario: Verify Flow Rate Matches Pump State

**Given** detected state labels and flow metric values

**When** validation is performed with `detector.validate_states(df, state_labels, 'HMI_2_FIT_001.PV')`

**Then** the system SHALL:
1. Compute mean flow rate for each state
2. Check ordering: mean(state_0) < mean(state_1) < mean(state_2)
3. Check separation: mean(state_i+1) - mean(state_i) > 0.3 L/s (configurable threshold)
4. Raise warning if validation fails

**Expected Validation**:
```python
state_stats = {
    'state_0': {'mean_flow': 0.004, 'std_flow': 0.002},
    'state_1': {'mean_flow': 1.305, 'std_flow': 0.150},
    'state_2': {'mean_flow': 2.410, 'std_flow': 0.180},
}

# Validation checks:
assert state_stats['state_0']['mean_flow'] < state_stats['state_1']['mean_flow']  # Ordering
assert state_stats['state_1']['mean_flow'] - state_stats['state_0']['mean_flow'] > 0.3  # Separation
```

---

### Requirement: Export State Labels for Reproducibility

**ID:** `WADI-STATE-004`

The system SHALL save detected state labels to CSV for reproducible clustering and debugging.

#### Scenario: Save State Labels with Timestamps

**Given** a DataFrame with detected state labels

**When** clustering completes with `WadiAdapter.save_state_labels(df, state_labels, output_path)`

**Then** the system SHALL:
1. Create CSV with columns: `Time`, `HMI_2_P_001_STATUS`, `HMI_2_P_002_STATUS`, `detected_state`, `HMI_2_FIT_001.PV`
2. Include timestamp, pump status, detected state, and primary metric for each row
3. Save to `clustering_results/wadi/state_labels.csv`

**Example CSV Output**:
```csv
Time,HMI_2_P_001_STATUS,HMI_2_P_002_STATUS,detected_state,HMI_2_FIT_001.PV
2023-12-18 01:45:00,0,0,0,0.0037
2023-12-18 01:46:00,1,0,1,1.3020
2023-12-18 01:47:00,1,1,2,2.4050
```

---

### Requirement: Support Auto-Detection of State Count

**ID:** `WADI-STATE-005`

The system SHALL automatically determine optimal number of states using elbow method when `auto_detect_states: true` is configured.

#### Scenario: Determine Optimal K for K-Means

**Given** pump status data with unclear state count

**When** auto-detection is enabled with `EnvironmentStateDetector(auto_detect_states=True, max_states=5)`

**Then** the system SHALL:
1. Compute K-means inertia for k=2 to k=max_states
2. Apply elbow method: find k where inertia decrease rate drops below 10%
3. Use detected k for state clustering
4. Log detected state count

**Example**:
```python
# Inertia curve:
# k=2: 450.3
# k=3: 120.5 (drop 73%, significant)
# k=4: 105.2 (drop 13%, marginal)
# k=5: 98.7 (drop 6%, marginal)
# → Select k=3

detector = EnvironmentStateDetector(auto_detect_states=True, max_states=5)
state_labels = detector.detect_states(df)

assert detector.detected_state_count == 3
```

---

### Requirement: Handle State Transition Boundaries

**ID:** `WADI-STATE-006`

The system SHALL provide configurable buffer zones around state transitions to avoid artifacts from transient dynamics.

#### Scenario: Exclude Transition Periods from Clustering

**Given** a state transition from state_0 to state_1 at timestamp T

**When** configured with `transition_buffer_seconds: 30`

**Then** the system SHALL:
1. Mark rows in [T-15s, T+15s] as "transition" state (-1)
2. Exclude these rows from clustering within steady states
3. Log number of excluded transition rows

**Example**:
```python
detector = EnvironmentStateDetector(
    pump_columns=['HMI_2_P_001_STATUS', 'HMI_2_P_002_STATUS'],
    transition_buffer_seconds=30
)
state_labels = detector.detect_states(df)

# state_labels: [0, 0, 0, -1, -1, 1, 1, ...]
#                         ^  transition buffer
```

#### Scenario: Optional Transition State Clustering

**Given** configuration `cluster_transitions: true`

**When** transition buffers are collected

**Then** the system SHALL cluster transition data separately and learn "transient" distribution for anomaly detection during state changes.

---

## Implementation Notes

### K-Means on Binary Status Vectors

```python
from sklearn.cluster import KMeans

def detect_states_from_pumps(df: pd.DataFrame, pump_columns: List[str], n_states: int) -> np.ndarray:
    # Extract binary status matrix
    status_matrix = df[pump_columns].values  # Shape: (n_rows, n_pumps)

    # Handle "Bad Input"
    status_matrix = pd.DataFrame(status_matrix).replace('Bad Input', np.nan).ffill().values

    # K-means clustering
    kmeans = KMeans(n_clusters=n_states, random_state=42)
    state_labels = kmeans.fit_predict(status_matrix)

    return state_labels
```

### Change Point Detection Fallback

```python
from ruptures import Pelt

def detect_states_from_changepoints(metric_values: np.ndarray, n_states: int) -> np.ndarray:
    # Detect change points
    algo = Pelt(model='rbf').fit(metric_values)
    change_indices = algo.predict(pen=10)

    # Assign state labels by segment mean
    state_labels = np.zeros(len(metric_values), dtype=int)
    for i, (start, end) in enumerate(zip([0] + change_indices[:-1], change_indices)):
        segment_mean = metric_values[start:end].mean()
        state_labels[start:end] = assign_state_by_mean(segment_mean, n_states)

    return state_labels
```

### Configuration Schema

```yaml
environment_detection:
  method: pump_status  # or 'change_point'
  pump_columns:
    - HMI_2_P_001_STATUS
    - HMI_2_P_002_STATUS
  num_states: 3  # Manual state count
  auto_detect_states: false  # Enable auto-detection
  max_states: 5  # For auto-detection elbow method
  fallback_metric: HMI_2_FIT_001.PV  # For change point fallback
  fallback_threshold: 0.2  # Switch to change point if >20% bad
  transition_buffer_seconds: 30  # Exclude transition periods
  cluster_transitions: false  # Learn transient distributions
  validation:
    min_separation: 0.3  # Min metric difference between states
    check_ordering: true  # Verify state ordering
```

## Cross-References

- **Depends On**: `wadi_metric_adapter` (requires parsed pump status columns)
- **Enables**: `multimodal_clustering` (provides state labels for clustering)
- **Related**: `state_conditional_detection` (detection uses state context)

## Testing

### Unit Tests
- `test_kmeans_state_detection`: Mock pump status → expected state labels
- `test_handle_bad_input`: Status with "Bad Input" → forward-filled labels
- `test_change_point_fallback`: High bad input ratio → triggers fallback
- `test_elbow_method`: Mock inertia curve → correct k selection

### Integration Tests
- `test_state_validation`: Detected states → validates with flow metrics
- `test_save_state_labels`: State detection → CSV output with correct columns

### Data Tests
- `test_wadi_state_consistency`: Real WaDi data → 3 states with expected flow ranges
- `test_transition_buffer_coverage`: State transitions → <5% rows in buffer zones
