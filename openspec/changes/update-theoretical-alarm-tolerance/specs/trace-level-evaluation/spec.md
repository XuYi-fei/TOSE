## MODIFIED Requirements

### Requirement: Trace-level alarm classification SHALL use a trigger rule, not a raw point hit

The system SHALL classify a trace using the first triggered alarm time rather than the first raw anomaly point time.

#### Scenario: Single raw anomaly remains tolerated

- **GIVEN** the detector uses `sigma_threshold = 3.0`
- **AND** the current trace has observed enough points that `ceil(n * p_sigma) = 1`
- **WHEN** exactly one raw anomaly point has appeared so far
- **THEN** the trace SHALL remain in a non-triggered state
- **AND** no `first_detection_time` SHALL be recorded yet

#### Scenario: Trigger occurs only after cumulative anomalies exceed the tolerance

- **GIVEN** the detector uses the theoretical 3-sigma alarm count policy
- **AND** the current trace has observed `n` points
- **WHEN** the cumulative raw anomaly count becomes greater than `ceil(n * p_sigma)`
- **THEN** the current point time SHALL become the `first_detection_time`
- **AND** the trace classification SHALL use that triggered time for TP/FP/FN/TN evaluation

#### Scenario: Abnormal trace avoids FP when the tolerated anomaly occurs before abn1

- **GIVEN** an abnormal trace contains one tolerated raw anomaly before `abn1_start_time`
- **AND** the cumulative raw anomaly count does not exceed the tolerance until after `abn1_start_time`
- **WHEN** the evaluator classifies the trace
- **THEN** the trace SHALL be classified as `TP`
- **AND** it SHALL NOT be classified as `FP` solely because of the tolerated pre-abn raw anomaly
