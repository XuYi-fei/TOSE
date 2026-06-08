## MODIFIED Requirements

### Requirement: Distribution-Aware Point Detection
The anomaly detection pipeline SHALL score each point against all learned cluster distributions and SHALL use the highest marginal probability as the point's best-match score.

#### Scenario: Heterogeneous learned distributions are loaded
- **WHEN** detection loads `learned_distributions.yaml`
- **THEN** it SHALL support cluster entries with different `distribution_type` values
- **AND** compute point scores from the corresponding fitted parameters

#### Scenario: Point anomaly is decided by probability
- **WHEN** a point is evaluated against all learned cluster distributions
- **THEN** detection SHALL compute a marginal probability for each cluster distribution
- **AND** select the cluster with `max_p_value`
- **AND** mark the point as anomalous when that maximum probability is below the configured `alpha`

#### Scenario: Trace alarm tolerance uses point anomaly probability
- **WHEN** the evaluator updates the cumulative raw anomaly count for a trace
- **THEN** the allowed anomaly count SHALL be `ceil(observed_count * alpha)`
- **AND** the trace SHALL only alarm after the cumulative raw anomaly count exceeds that bound
