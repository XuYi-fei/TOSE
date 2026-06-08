# Capability: Multi-Modal Distribution Learning

**Capability ID:** `multimodal_clustering`
**Change:** `integrate-wadi-dataset-adapter`
**Status:** Proposed

## Overview

Multi-Modal Distribution Learning enables state-conditional clustering and anomaly detection for systems with multiple operational modes. It prevents false positives during legitimate state transitions by learning separate distributions for each operational state.

## ADDED Requirements

### Requirement: Cluster Metrics Within Each Operational State

**ID:** `WADI-CLUSTER-001`

The system SHALL perform HDBSCAN clustering separately for each detected operational state to learn state-specific distributions.

#### Scenario: Learn 3 Distributions for 3 Flow States

**Given** flow metric `HMI_2_FIT_001.PV` with 3 operational states detected:
- state_0 (LOW): 500,000 rows
- state_1 (MEDIUM): 600,000 rows
- state_2 (HIGH): 600,000 rows

**When** state-aware clustering is performed with `StateAwareClusterer.fit(df, state_labels)`

**Then** the system SHALL:
1. Filter data for state_0 → cluster with HDBSCAN → learn distribution_0
2. Filter data for state_1 → cluster with HDBSCAN → learn distribution_1
3. Filter data for state_2 → cluster with HDBSCAN → learn distribution_2
4. Save all distributions to `learned_distributions.yaml`

**Expected Output**:
```yaml
# clustering_results/wadi/learned_distributions.yaml
distributions:
  flow_state_0:
    metric: HMI_2_FIT_001.PV
    cluster_id: 0
    mu: 0.0037
    sigma: 0.0015
    sample_count: 498000  # 500k - 2k outliers
  flow_state_1:
    metric: HMI_2_FIT_001.PV
    cluster_id: 0
    mu: 1.3050
    sigma: 0.1520
    sample_count: 595000
  flow_state_2:
    metric: HMI_2_FIT_001.PV
    cluster_id: 0
    mu: 2.4100
    sigma: 0.1800
    sample_count: 598000
```

---

### Requirement: Handle Outliers Within Each State

**ID:** `WADI-CLUSTER-002`

The system SHALL identify and exclude noise points (HDBSCAN label=-1) within each state before fitting Gaussian distributions.

#### Scenario: Filter Noise Points Before Distribution Fitting

**Given** state_1 data with HDBSCAN results:
```
Cluster labels: [0, 0, -1, 0, -1, 0, 0, 0]  # -1 = noise
Values:         [1.3, 1.28, 5.2, 1.31, 0.1, 1.29, 1.32, 1.30]
```

**When** Gaussian distribution is fitted

**Then** the system SHALL:
1. Filter out noise points (labels = -1): exclude values [5.2, 0.1]
2. Fit Gaussian on clean data: [1.3, 1.28, 1.31, 1.29, 1.32, 1.30]
3. Compute mean = 1.30, sigma = 0.015
4. Log outlier ratio: 2/8 = 25%

**Example**:
```python
clusterer = HDBSCAN(min_cluster_size=50)
cluster_labels = clusterer.fit_predict(state_1_data.reshape(-1, 1))

# Filter noise
clean_data = state_1_data[cluster_labels != -1]
mu, sigma = clean_data.mean(), clean_data.std()

assert len(clean_data) == 6  # 8 - 2 noise points
```

---

### Requirement: State-Conditional Anomaly Detection

**ID:** `WADI-CLUSTER-003`

The system SHALL perform anomaly detection by testing points against the distribution for their current operational state, not all distributions.

#### Scenario: Test Point Against Current State Distribution Only

**Given** a test point with value=1.35 at timestamp T

**When** the current system state is state_1 (MEDIUM flow)

**Then** the system SHALL:
1. Infer current state from pump status at time T
2. Retrieve distribution: flow_state_1 (mu=1.305, sigma=0.152)
3. Compute z-score: |1.35 - 1.305| / 0.152 = 0.30
4. Compare to threshold (3.0): 0.30 < 3.0 → NOT anomaly

**Contrast with cross-state test**:
```python
# State-conditional (correct):
z_score_state1 = abs(1.35 - 1.305) / 0.152 = 0.30 → Normal

# Cross-state (incorrect, would cause FP):
z_score_state0 = abs(1.35 - 0.0037) / 0.0015 = 897 → Anomaly (FALSE POSITIVE)
```

**Example**:
```python
detector = WadiAnomalyDetector.from_yaml('learned_distributions.yaml')

is_anomaly, z_score = detector.detect_point_anomaly(
    metric_value=1.35,
    current_state='flow_state_1'  # Context-aware detection
)

assert is_anomaly == False
assert z_score < 3.0
```

---

### Requirement: Hybrid State-Conditional + Cross-State Detection

**ID:** `WADI-CLUSTER-004`

The system SHALL support hybrid detection mode that tests both state-conditional (high threshold) and cross-state (low threshold) to catch ambiguous anomalies.

#### Scenario: Detect Value Anomalous in Current State But Normal in Another

**Given** a test point value=0.8 during state_1 (expected ~1.3)

**When** hybrid detection is enabled with thresholds: state_threshold=3.0, cross_state_threshold=2.5

**Then** the system SHALL:
1. State-conditional test: |0.8 - 1.305| / 0.152 = 3.32 > 3.0 → **Anomaly**
2. Cross-state test: min z-score across all states:
   - flow_state_0: |0.8 - 0.0037| / 0.0015 = 531 > 2.5 → Anomaly
   - flow_state_1: 3.32 > 2.5 → Anomaly
   - flow_state_2: |0.8 - 2.41| / 0.18 = 8.94 > 2.5 → Anomaly
3. Flag as anomaly (detected by both methods)

**Example for state transition ambiguity**:
```python
# Value 0.7 during state transition: state_0→state_1
# State-conditional: |0.7 - 0.0037| / 0.0015 = 464 > 3.0 → Anomaly
# Cross-state: |0.7 - 1.305| / 0.152 = 3.98 > 2.5 → Anomaly
# → Likely state transition, not anomaly (use lower cross-state threshold)

detector = WadiAnomalyDetector(
    mode='hybrid',
    state_threshold=3.0,
    cross_state_threshold=2.5
)

is_anomaly = detector.detect_point_anomaly(value=0.7, current_state='flow_state_0')
# Logic: (z_state > 3.0) AND (min_z_cross > 2.5) → True anomaly
```

---

### Requirement: Validate Distribution Separation

**ID:** `WADI-CLUSTER-005`

The system SHALL verify that learned distributions for different states are statistically separable to ensure effective state-conditional detection.

#### Scenario: Check 3-Sigma Separation Between State Distributions

**Given** learned distributions:
- flow_state_0: mu=0.0037, sigma=0.0015
- flow_state_1: mu=1.3050, sigma=0.1520

**When** distribution validation is performed

**Then** the system SHALL:
1. Compute separation distance: |1.305 - 0.0037| = 1.301
2. Compute pooled sigma: sqrt((0.0015² + 0.152²) / 2) = 0.107
3. Check separation ratio: 1.301 / 0.107 = 12.15 > 3.0 ✓ (well-separated)
4. Log warning if separation < 3.0 (overlapping states)

**Example**:
```python
validator = DistributionValidator()
is_separable = validator.check_separation(
    dist1={'mu': 0.0037, 'sigma': 0.0015},
    dist2={'mu': 1.305, 'sigma': 0.152},
    min_sigma_separation=3.0
)

assert is_separable == True
```

#### Scenario: Warn on Overlapping Distributions

**Given** two states with overlapping distributions:
- state_A: mu=1.30, sigma=0.20
- state_B: mu=1.50, sigma=0.25

**When** validation checks separation: |1.50 - 1.30| / 0.225 = 0.89 < 3.0

**Then** the system SHALL:
- Log warning: "States A and B have overlapping distributions (0.89σ separation)"
- Suggest: "Consider merging states or using hybrid detection mode"
- Continue processing (non-fatal)

---

### Requirement: Support Multi-Metric State-Conditional Clustering

**ID:** `WADI-CLUSTER-006`

The system SHALL cluster multiple metrics simultaneously within each state to capture cross-metric correlations.

#### Scenario: Cluster Flow and Pressure Together

**Given** two correlated metrics:
- `HMI_2_FIT_001.PV` (flow)
- `HMI_2_PIT_001.PV` (pressure)

**When** multi-metric clustering is performed with `StateAwareClusterer.fit_multi_metric(df, ['FIT', 'PIT'], state_labels)`

**Then** the system SHALL:
1. For each state, extract 2D feature matrix: [flow_values, pressure_values]
2. Apply HDBSCAN on 2D data
3. Fit bivariate Gaussian: mean vector [mu_flow, mu_pressure], covariance matrix
4. Save multi-metric distribution

**Expected Output**:
```yaml
distributions:
  flow_state_1:
    metrics: [HMI_2_FIT_001.PV, HMI_2_PIT_001.PV]
    mean: [1.305, 2.450]  # [flow, pressure]
    covariance:
      - [0.023, 0.018]  # Var(flow), Cov(flow, pressure)
      - [0.018, 0.035]  # Cov(pressure, flow), Var(pressure)
    sample_count: 595000
```

**Detection with Mahalanobis Distance**:
```python
# Test point: [flow=1.4, pressure=2.3]
mean = np.array([1.305, 2.450])
cov = np.array([[0.023, 0.018], [0.018, 0.035]])

diff = np.array([1.4, 2.3]) - mean
mahal_dist = np.sqrt(diff.T @ np.linalg.inv(cov) @ diff)

is_anomaly = mahal_dist > 3.0  # Mahalanobis distance threshold
```

---

## Implementation Notes

### StateAwareClusterer Class

```python
from sklearn.cluster import HDBSCAN
from typing import Dict, List
import numpy as np

class StateAwareClusterer:
    def __init__(self, min_cluster_size: int = 50):
        self.min_cluster_size = min_cluster_size
        self.distributions = {}

    def fit(self, df: pd.DataFrame, state_labels: np.ndarray, metric: str) -> Dict[str, dict]:
        """Cluster within each state separately"""
        for state_id in np.unique(state_labels):
            state_mask = (state_labels == state_id)
            state_data = df.loc[state_mask, metric].values

            # HDBSCAN clustering
            clusterer = HDBSCAN(min_cluster_size=self.min_cluster_size)
            cluster_labels = clusterer.fit_predict(state_data.reshape(-1, 1))

            # Filter outliers
            clean_data = state_data[cluster_labels != -1]

            # Fit Gaussian
            if len(clean_data) > 0:
                self.distributions[f'flow_state_{state_id}'] = {
                    'metric': metric,
                    'mu': float(clean_data.mean()),
                    'sigma': float(clean_data.std()),
                    'sample_count': len(clean_data)
                }

        return self.distributions

    def save_distributions(self, output_path: str):
        with open(output_path, 'w') as f:
            yaml.dump({'distributions': self.distributions}, f)
```

### WadiAnomalyDetector Class

```python
class WadiAnomalyDetector(AnomalyDetector):
    def __init__(self, mode: str = 'state_conditional', state_threshold: float = 3.0, cross_state_threshold: float = 2.5):
        super().__init__()
        self.mode = mode
        self.state_threshold = state_threshold
        self.cross_state_threshold = cross_state_threshold

    def detect_point_anomaly(self, metric_value: float, current_state: str) -> Tuple[bool, float]:
        if self.mode == 'state_conditional':
            return self._state_conditional_test(metric_value, current_state)
        elif self.mode == 'hybrid':
            return self._hybrid_test(metric_value, current_state)

    def _state_conditional_test(self, value: float, state: str) -> Tuple[bool, float]:
        dist = self.distributions[state]
        z_score = abs(value - dist['mu']) / dist['sigma']
        return z_score > self.state_threshold, z_score

    def _hybrid_test(self, value: float, state: str) -> Tuple[bool, float]:
        # Test current state with high threshold
        z_state, _ = self._state_conditional_test(value, state)

        # Test all states with low threshold
        z_scores_all = [abs(value - d['mu']) / d['sigma'] for d in self.distributions.values()]
        z_min_cross = min(z_scores_all)

        # Anomaly if deviates from current state AND all other states
        is_anomaly = z_state > self.state_threshold and z_min_cross > self.cross_state_threshold
        return is_anomaly, z_state
```

### Configuration Schema

```yaml
clustering:
  method: hdbscan
  min_cluster_size: 50
  state_aware: true  # Enable state-conditional clustering
  multi_metric: false  # Cluster multiple metrics together

detection:
  mode: state_conditional  # or 'hybrid'
  state_threshold: 3.0  # Sigma for current state
  cross_state_threshold: 2.5  # Sigma for other states (hybrid mode)

validation:
  check_separation: true
  min_sigma_separation: 3.0  # Min separation for valid states
```

## Cross-References

- **Depends On**:
  - `environment_state_detection` (requires state labels)
  - `wadi_metric_adapter` (requires selected metrics)
- **Enables**: State-conditional anomaly detection in WaDi traces
- **Related**: `chunked_data_processing` (clustering on chunked data)

## Testing

### Unit Tests
- `test_state_aware_clustering`: Mock state labels → separate distributions per state
- `test_filter_outliers`: Data with noise → HDBSCAN filters outliers
- `test_state_conditional_detection`: Test point + state → correct z-score
- `test_hybrid_detection`: Ambiguous point → hybrid logic applied

### Integration Tests
- `test_wadi_full_clustering`: Real WaDi CSV → 3 distributions learned
- `test_distribution_separation_validation`: Learned dists → separation check passes

### Data Tests
- `test_wadi_state_distributions_match`: Learned dists → match expected flow ranges
- `test_no_cross_state_fps`: State transition trace → no false positives at boundaries
