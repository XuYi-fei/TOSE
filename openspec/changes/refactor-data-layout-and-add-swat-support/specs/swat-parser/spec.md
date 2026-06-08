# Spec Delta: SWAT Parser Support (SWP)

## ADDED Requirements

### Requirement: SWAT Data Format Support
**ID**: SWP-001
**Priority**: High
**Status**: Proposed

The framework SHALL support parsing SWAT (Secure Water Treatment) trace files. The parser MUST correctly identify `time` as the time column and `y_0` as the target metric column in SWAT CSV files.

#### Scenario: Parse SWAT trace file with correct columns
**Given** a SWAT trace file with columns: `time, water_tank, noisy_B_in, noisy_B_out, u_1_in, u_1_out, y_0`
**When** the SWAT parser reads the file
**Then** it should identify `time` as the time column
**And** it should identify `y_0` as the target metric column
**And** it should successfully parse all rows into a DataFrame

### Requirement: SWAT Filename Pattern Support
**ID**: SWP-002
**Priority**: High
**Status**: Proposed

The SWAT parser SHALL correctly parse SWAT trace filenames which follow the same pattern as RUBIS: `eval_(ident|abn)_trace-cnt-XXX-duration-XXX-config_num-XXX-trace_config-XXX-start_time-XXX.txt`.

#### Scenario: Parse SWAT identity trace filename
**Given** a filename `eval_ident_trace-cnt-000-duration-1800-config_num-4-trace_config-norm3,norm1,norm3,norm1-start_time-2,182,244,469.txt`
**When** the SWAT parser parses this filename
**Then** it should extract cnt=0, duration=1800, config_num=4
**And** it should extract trace_config as list of segments
**And** it should extract start_time as list of integers
**And** it should return a metadata object with these fields

### Requirement: SWAT Parser Registration
**ID**: SWP-003
**Priority**: High
**Status**: Proposed

The SWAT parser MUST be registered in ParserFactory and SHALL be accessible via system type 'swat'.

#### Scenario: Create SWAT parser via factory
**Given** the ParserFactory is initialized
**When** `ParserFactory.create('swat')` is called
**Then** it should return a SWATParser instance
**And** the parser should be fully functional

### Requirement: SWAT Parser Implementation via Inheritance
**ID**: SWP-004
**Priority**: Medium
**Status**: Proposed

The SWAT parser SHALL leverage code reuse by inheriting from RUBISParser due to identical filename patterns. The parser MUST override `TARGET_COLUMN` to specify `'y_0'` as the target metric.

#### Scenario: SWAT parser reuses RUBIS filename parsing
**Given** a SWAT trace filename
**When** the SWATParser parses it
**Then** it should use the inherited FILENAME_PATTERN regex from RUBISParser
**And** should use the inherited parse_filename() method
**And** should return metadata with correct fields

### Requirement: SWAT Clustering Workflow Support
**ID**: SWP-005
**Priority**: High
**Status**: Proposed

The clustering framework SHALL support end-to-end SWAT clustering workflow. The framework MUST load SWAT identity traces, extract parameters, and generate learned_distributions.yaml for SWAT.

#### Scenario: Load SWAT identity traces for clustering
**Given** SWAT identity trace files in `data/swat/identity/`
**When** clustering workflow is run with SWAT config
**Then** all trace files should be loaded successfully
**And** parameters should be extracted from each file
**And** approximately 600 distribution parameters should be collected

### Requirement: SWAT Detection Workflow Support
**ID**: SWP-006
**Priority**: Medium
**Status**: Proposed

The detection framework SHALL support SWAT anomaly detection when abnormal traces are available. The framework MUST handle the case where SWAT abnormal data does not yet exist with a clear error message.

#### Scenario: Load SWAT learned distributions for detection
**Given** a SWAT learned_distributions.yaml file exists
**When** the detection workflow initializes
**Then** it should load the SWAT distributions successfully
**And** should create an AnomalyDetector with SWAT distributions
**And** should be ready to process SWAT abnormal traces

## MODIFIED Requirements

### Requirement: ParserFactory System Type Support
**ID**: COM-PF-001 (Modified)
**Priority**: High
**Status**: Proposed

ParserFactory SHALL support 'rubis', 'bsn', and 'swat' system types. Each system type MUST return a different, appropriate parser class.

**Previous Behavior**: Supports 'rubis' and 'bsn' system types
**New Behavior**: Supports 'rubis', 'bsn', and 'swat' system types

#### Scenario: All three system types supported
**Given** the ParserFactory is initialized
**When** checking supported system types
**Then** 'rubis', 'bsn', and 'swat' should all be valid
**And** each should return a different parser class

## REMOVED Requirements

None. This change is purely additive.
