## MODIFIED Requirements

### Requirement: Distribution-Aware Point Detection
The anomaly detection pipeline SHALL support multiple detection modes over learned distributions and SHALL preserve a unified trace-level evaluation interface.

#### Scenario: Pointwise mode remains available
- **WHEN** detection config sets `detection.mode` to `pointwise` or omits the field
- **THEN** the system SHALL use the existing pointwise detector behavior
- **AND** score each point against learned cluster distributions by marginal probability

#### Scenario: BOCPD mode is selected
- **WHEN** detection config sets `detection.mode` to `bocpd`
- **THEN** the system SHALL use an online BOCPD detector over learned distributions
- **AND** maintain run-length posterior state independently for each trace

#### Scenario: BOCPD uses learned distributions as emission models
- **WHEN** the BOCPD detector evaluates a point
- **THEN** it SHALL first select candidate learned distributions using the configured context matching strategy
- **AND** use the candidate distributions' fitted likelihoods to update BOCPD growth and changepoint probabilities

#### Scenario: Default BOCPD anomaly rule requires both change and low fit
- **WHEN** `raw_anomaly_rule` is `cp_and_tail`
- **THEN** a point SHALL be marked as a raw anomaly only if its changepoint posterior exceeds the configured threshold
- **AND** its best-match tail probability remains below the configured anomaly threshold
