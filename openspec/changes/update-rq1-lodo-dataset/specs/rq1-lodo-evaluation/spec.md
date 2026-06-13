## ADDED Requirements

### Requirement: Generate Leave-One-Distribution-Out RQ1 Datasets
The system SHALL generate a new RQ1 dataset root where each holdout distribution unit has a paired identity and abnormal dataset derived from identity segments.

#### Scenario: Holdout unit generates paired datasets
- **WHEN** the user runs the RQ1 LODO dataset builder for a system with distribution units
- **THEN** the system SHALL create one holdout directory per distribution unit
- **AND** each holdout directory SHALL contain `identity/`, `abnormal/`, and `manifests/`
- **AND** the abnormal traces SHALL end with an `abn1` segment derived from the holdout unit

### Requirement: Define Distribution Units by System Semantics
The system SHALL derive holdout distribution units directly from identity segment metadata.

#### Scenario: Non-BSN systems use norm labels
- **WHEN** the system parses `rubis`, `swat`, or `wadi` identity traces
- **THEN** the distribution unit SHALL equal the segment `norm_label`

#### Scenario: BSN uses sensor plus norm label
- **WHEN** the system parses `bsn` identity traces
- **THEN** the distribution unit SHALL equal `sensor{sensor_index}_{norm_label}`

### Requirement: Preserve Trace-Level Detection Semantics
The system SHALL keep the current RQ1 evaluation semantics where the anomalous segment is always the final segment of an abnormal trace.

#### Scenario: Abnormal trace keeps final anomaly segment
- **WHEN** an abnormal trace is generated for holdout unit `u`
- **THEN** all prefix segments SHALL come from non-holdout units
- **AND** the final segment SHALL be written as `abn1`
- **AND** the generated filename SHALL encode `abn1_start_time`

### Requirement: Run RQ1 Methods Per Holdout Unit
The system SHALL run baseline and GROUP RQ1 methods against every holdout-unit dataset and aggregate the results by system and method.

#### Scenario: LODO runner aggregates method results
- **WHEN** the user runs the RQ1 LODO methods runner
- **THEN** the system SHALL evaluate `SWD`, `ARD`, `PRD`, `GPD`, and `GROUP` for every holdout unit
- **AND** it SHALL emit per-holdout summaries and aggregated per-system summaries
