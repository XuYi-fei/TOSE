# Spec Delta: Configuration Updates (CFG)

## ADDED Requirements

### Requirement: SWAT Clustering Configuration Template
**ID**: CFG-SWP-001
**Priority**: High
**Status**: Proposed

A SWAT clustering configuration file SHALL be provided at `configs/swat_clustering_config.yaml`. The configuration MUST set `system_type: swat` and MUST point `data_path` to `data/swat/identity/`.

#### Scenario: SWAT clustering config defines system type
**Given** the file `configs/swat_clustering_config.yaml`
**When** the configuration is loaded
**Then** system_type should be set to 'swat'
**And** this should trigger use of SWATParser

### Requirement: SWAT Detection Configuration Template
**ID**: CFG-SWP-002
**Priority**: High
**Status**: Proposed

A SWAT detection configuration file SHALL be provided at `configs/swat_detection_config.yaml`. The configuration MUST set `system_type: swat`, MUST reference SWAT learned distributions, and MUST point `test_data_path` to `data/swat/abnormal/`.

#### Scenario: SWAT detection config defines system type
**Given** the file `configs/swat_detection_config.yaml`
**When** the configuration is loaded
**Then** system_type should be set to 'swat'

### Requirement: Chinese Comments in Configuration Files
**ID**: CFG-I18N-001
**Priority**: Medium
**Status**: Proposed

All configuration files SHALL include Chinese comments explaining settings and options. SWAT configuration files MUST include comments describing SWAT-specific considerations.

#### Scenario: SWAT clustering config has Chinese comments
**Given** the SWAT clustering configuration file
**When** a user reads the file
**Then** they should see Chinese comments explaining each section
**And** comments should describe SWAT-specific considerations

## MODIFIED Requirements

### Requirement: RUBIS Configuration File Paths
**ID**: CFG-RUBIS-001 (Modified)
**Priority**: High
**Status**: Proposed

RUBIS configuration files SHALL use new data layout paths. Clustering configs MUST use `data_path: data/rubis/identity` and detection configs MUST use `test_data_path: data/rubis/abnormal`.

**Previous Behavior**: `data_path: rubis_evaluation_data/eval_ident_traces`, `test_data_path: rubis_evaluation_data/eval_abn_traces`
**New Behavior**: `data_path: data/rubis/identity`, `test_data_path: data/rubis/abnormal`

#### Scenario: RUBIS clustering config uses new identity path
**Given** the updated `configs/rubis_clustering_config.yaml`
**When** the configuration is loaded
**Then** data_path should be `data/rubis/identity`
**And** loading trace files from this path should succeed

### Requirement: BSN Configuration File Paths
**ID**: CFG-BSN-001 (Modified)
**Priority**: High
**Status**: Proposed

BSN configuration files SHALL use new data layout paths. Clustering configs MUST use `data_path: data/bsn/identity`.

**Previous Behavior**: `data_path: bsn_evaluation_data/eval_ident_traces`
**New Behavior**: `data_path: data/bsn/identity`

#### Scenario: BSN clustering config uses new identity path
**Given** the updated `configs/bsn_clustering_config.yaml`
**When** the configuration is loaded
**Then** data_path should be `data/bsn/identity`
**And** loading trace files from this path should succeed

### Requirement: Configuration File Reference Documentation
**ID**: CFG-DOC-001 (Modified)
**Priority**: Medium
**Status**: Proposed

Configuration documentation SHALL show examples using the new `data/{system}/{identity|abnormal}` path format. No examples SHALL reference old `{system}_evaluation_data/eval_{type}_traces` paths.

**Previous Behavior**: Documentation shows old path formats
**New Behavior**: Documentation shows new data layout paths

#### Scenario: Configuration examples show new paths
**Given** documentation with configuration examples
**When** a user reads configuration examples
**Then** all examples should use `data/{system}/{identity|abnormal}` format
**And** no examples should reference old paths

## REMOVED Requirements

None. This is purely an update to existing configurations and addition of new SWAT configurations.
