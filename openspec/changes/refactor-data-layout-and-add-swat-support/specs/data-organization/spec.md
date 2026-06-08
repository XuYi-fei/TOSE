# Spec Delta: Data Organization (DRG)

## ADDED Requirements

### Requirement: Unified Data Directory Structure
**ID**: DRG-001
**Priority**: High
**Status**: Proposed

The framework SHALL organize all evaluation data under a single `data/` directory at the project root. The structure MUST separate system types into subdirectories (`rubis/`, `bsn/`, `swat/`) and MUST further separate data by purpose (`identity/`, `abnormal/`) within each system subdirectory.

#### Scenario: Project contains multiple system datasets
**Given** the project supports multiple system types (RUBIS, BSN, SWAT)
**When** a user navigates to the project root directory
**Then** they should see a single `data/` directory containing all evaluation data
**And** each system type should have its own subdirectory (`rubis/`, `bsn/`, `swat/`)
**And** each system subdirectory should contain `identity/` and `abnormal/` subdirectories

#### Scenario: User needs identity traces for clustering
**Given** the user wants to perform clustering analysis on RUBIS data
**When** they configure the clustering tool
**Then** they should reference `data/rubis/identity/` as the data path
**And** this directory should contain all eval_ident_trace files for RUBIS

### Requirement: Semantic Directory Naming
**ID**: DRG-002
**Priority**: Medium
**Status**: Proposed

Subdirectories within each system type MUST use semantic names `identity/` and `abnormal/` that clearly indicate the purpose of the data. The `identity/` subdirectory SHALL contain normal operational data for distribution learning, and the `abnormal/` subdirectory SHALL contain traces with injected anomalies for testing detection.

#### Scenario: Directory names indicate data purpose
**Given** a user is exploring the data directory structure
**When** they see `identity/` and `abnormal/` subdirectories
**Then** they should understand that identity/ contains normal operational data for distribution learning
**And** abnormal/ contains traces with injected anomalies for testing detection

### Requirement: Data Integrity During Migration
**ID**: DRG-003
**Priority**: High
**Status**: Proposed

When migrating data from old locations to the new structure, all files MUST be moved without corruption or loss. File contents SHALL remain byte-for-byte identical to originals.

#### Scenario: RUBIS data migrated completely
**Given** RUBIS data originally in `rubis_evaluation_data/`
**When** data is migrated to `data/rubis/`
**Then** all 200 identity trace files must be in `data/rubis/identity/`
**And** all 200 abnormal trace files must be in `data/rubis/abnormal/`
**And** no files should be missing or duplicated
**And** file contents should be byte-for-byte identical to originals

## MODIFIED Requirements

### Requirement: Configuration File Data Paths
**ID**: CFG-PATH-001 (Modified)
**Priority**: High
**Status**: Proposed

Configuration files SHALL reference data paths using the new `data/{system}/{identity|abnormal}/` structure instead of the old `{system}_evaluation_data/eval_{type}_traces/` format. The configuration loaders MUST validate that these paths exist.

**Previous Behavior**: Config files referenced `{system}_evaluation_data/eval_{type}_traces/`
**New Behavior**: Config files reference `data/{system}/{identity|abnormal}/`

#### Scenario: RUBIS clustering config uses new path
**Given** a RUBIS clustering configuration file
**When** the `data_path` field is evaluated
**Then** it should point to `data/rubis/identity/`
**And** loading this config should succeed
**And** the path should resolve to existing trace files

## REMOVED Requirements

None. This change is additive and refactoring-focused, with no feature removal.
