# Capability: Clustering Integration with Validation Framework

## Overview

This capability defines how the clustering analysis module integrates with the existing validation framework, including CLI integration, workflow orchestration, and shared configuration patterns.

---

## ADDED Requirements

### Requirement: Independent CLI Entry Point
The system MUST provide a standalone command-line interface for clustering analysis.

系统必须为聚类分析提供独立的命令行接口。

#### Scenario: Run clustering analysis via CLI
**Given** a configuration file `configs/rubis_cluster.yaml`

**When** I execute `python cluster.py --config configs/rubis_cluster.yaml`

**Then** the system MUST load the clustering configuration

**And** it MUST execute the complete clustering pipeline

**And** it MUST save results to the configured output directory

**And** it MUST print a summary to the console

**And** it MUST exit with code 0 on success

#### Scenario: CLI help and options
**Given** the cluster.py script

**When** I execute `python cluster.py --help`

**Then** the system MUST display usage information in Chinese

**And** it MUST list all available options: --config, --output, --algorithms, --verbose

**And** it MUST provide examples of typical usage

#### Scenario: Override output directory via CLI
**Given** config file specifies output_dir='clustering_results/rubis'

**When** I execute `python cluster.py --config configs/rubis_cluster.yaml --output /tmp/custom_output`

**Then** the system MUST save results to /tmp/custom_output instead

**And** the config file MUST remain unchanged

#### Scenario: Select specific algorithms via CLI
**Given** config file enables 4 algorithms

**When** I execute `python cluster.py --config configs/rubis_cluster.yaml --algorithms hdbscan,gmm_bic`

**Then** the system MUST run only HDBSCAN and GMM+BIC

**And** it MUST ignore other algorithms in the config file

#### Scenario: Verbose logging mode
**Given** the default logging level is INFO

**When** I execute `python cluster.py --config configs/rubis_cluster.yaml --verbose`

**Then** the system MUST set logging level to DEBUG

**And** it MUST print detailed progress information

**And** it MUST show data loading details, algorithm parameters, and intermediate results

---

### Requirement: Configuration File Format Consistency
The system MUST use configuration patterns consistent with the validation framework.

系统必须使用与验证框架一致的配置模式。

#### Scenario: Common configuration fields
**Given** validation config has system_type, data_path, output_dir

**When** I create a clustering config

**Then** it MUST also have system_type, data_path, output_dir fields

**And** system_type values MUST be compatible ('rubis', 'bsn')

**And** data_path MUST point to the same trace directories

**And** field names and types MUST be consistent

#### Scenario: Load config with validation-compatible system_type
**Given** a clustering config with system_type='rubis'

**When** the config is loaded

**Then** the system MUST use `ParserFactory.create('rubis')`

**And** it MUST use the same RUBISParser as the validation framework

**And** data parsing logic MUST be identical

#### Scenario: Reuse expected_distributions for comparison
**Given** a validation config `configs/rubis_config.yaml` with expected_distributions

**When** I create a clustering config `configs/rubis_cluster.yaml`

**Then** I MAY copy expected_distributions to the clustering config

**And** the clustering module MUST use it only for comparison (not as constraints)

**And** it MUST report whether discovered clusters match expected parameters

---

### Requirement: Workflow Integration
The system MUST support a workflow where clustering analysis informs validation configuration.

系统必须支持聚类分析为验证配置提供信息的工作流。

#### Scenario: Discovery-then-validation workflow
**Given** I have raw trace data without known distribution parameters

**When** I first run `python cluster.py --config configs/rubis_cluster.yaml`

**Then** the system MUST discover 3 clusters with parameters

**And** I MUST manually review clustering_results/rubis/clustering_report.md

**And** I MUST update configs/rubis_config.yaml expected_distributions based on discovered parameters

**And** I MUST then run `python validate.py --config configs/rubis_config.yaml`

**And** validation MUST check if data conforms to the discovered distributions

#### Scenario: Export clustering results to validation config format
**Given** clustering results with 3 clusters

**When** the clustering report is generated

**Then** the report MUST include a section "建议的验证配置"

**And** it MUST show YAML snippet compatible with validation config format:
```yaml
expected_distributions:
  norm1:
    mu: 0.0526
    sigma: 0.0024
  norm2:
    mu: 0.1154
    sigma: 0.0127
  norm3:
    mu: 0.0285
    sigma: 0.0018
```

**And** users MUST be able to copy-paste this into their validation config

#### Scenario: Automatic config generation (optional enhancement)
**Given** clustering analysis has completed

**When** I run `python cluster.py --config configs/rubis_cluster.yaml --export-validation-config`

**Then** the system MAY generate a validation config file automatically

**And** it MUST save to configs/rubis_config_generated.yaml

**And** it MUST populate expected_distributions from clustering results

**And** it MUST include a comment "# Auto-generated from clustering analysis on {date}"

**And** it MUST NOT overwrite existing validation configs without explicit --force flag

---

### Requirement: Shared Data Layer Usage
The system MUST use the common data layer for all data parsing operations.

系统必须使用公共数据层进行所有数据解析操作。

#### Scenario: Clustering uses common adapters
**Given** a clustering config with system_type='rubis'

**When** the clustering engine loads data

**Then** it MUST import `from common.adapters import ParserFactory`

**And** it MUST use `ParserFactory.create('rubis')`

**And** it MUST NOT duplicate any parsing logic

**And** the parser MUST return `DistributionParameters` objects from common.models

#### Scenario: Validation and clustering share parsed data
**Given** I run validation followed by clustering on the same trace files

**When** both processes parse the same file

**Then** both MUST use identical `TraceMetadata` and `DistributionParameters` objects

**And** the mean and variance values MUST match exactly

**And** this ensures consistency between validation and clustering results

#### Scenario: Adding a new system type affects both modules
**Given** I implement a new `MySystemParser` and register it with `ParserFactory`

**When** I set system_type='mysystem' in clustering config

**Then** clustering MUST automatically support the new system

**And** when I set system_type='mysystem' in validation config

**Then** validation MUST also automatically support the new system

**And** I MUST NOT need to modify clustering or validation code

---

### Requirement: Output Directory Structure Compatibility
The system MUST organize output directories in a consistent manner with the validation framework.

系统必须以与验证框架一致的方式组织输出目录。

#### Scenario: Parallel output directories
**Given** validation outputs to `validation_results/rubis/`

**When** clustering outputs are saved

**Then** they MUST go to `clustering_results/rubis/` by default

**And** the directory structure MUST be parallel and consistent

**And** both MUST support per-system subdirectories

#### Scenario: Output file naming conventions
**Given** validation report is named `validation_report.md`

**When** clustering generates reports

**Then** it MUST use consistent naming: `clustering_report.md`

**And** visualizations MUST use descriptive names: `clustering_parameter_space.png`

**And** all files MUST use lowercase with underscores

**And** all files MUST avoid special characters except hyphen and underscore

#### Scenario: Timestamp-based output organization
**Given** I run clustering analysis multiple times

**When** output_dir already contains previous results

**Then** the system MAY create timestamped subdirectories: `clustering_results/rubis/2026-01-15_14-30-00/`

**And** this MUST be configurable via `visualization.use_timestamps` in config

**And** if disabled, it MUST overwrite previous results with a warning

---

### Requirement: Error Handling Consistency
The system MUST handle errors consistently with the validation framework.

系统必须以与验证框架一致的方式处理错误。

#### Scenario: Invalid configuration file
**Given** a config file with missing required fields

**When** I run `python cluster.py --config invalid_config.yaml`

**Then** the system MUST print a clear error message in Chinese

**And** it MUST indicate which field is missing

**And** it MUST exit with non-zero code

**And** the error format MUST match validation framework's error format

#### Scenario: Data path does not exist
**Given** a config with data_path='/nonexistent/path'

**When** the clustering engine attempts to load data

**Then** the system MUST raise a FileNotFoundError

**And** the error message MUST be: "数据路径不存在: /nonexistent/path"

**And** it MUST suggest checking the config file

#### Scenario: Algorithm execution failure
**Given** an algorithm raises an exception during clustering

**When** the clustering engine runs

**Then** it MUST log the error

**And** it MUST continue executing other algorithms

**And** the final report MUST indicate which algorithms failed

**And** if all algorithms fail, it MUST exit with error code 1

---

### Requirement: Performance Consistency
The system MUST maintain comparable performance characteristics to the validation framework.

系统必须保持与验证框架相当的性能特征。

#### Scenario: Data loading performance
**Given** validation framework loads 200 RUBIS files in ~2 seconds

**When** clustering framework loads the same 200 files

**Then** it MUST complete within 3 seconds

**And** both MUST use the same `RUBISParser` with identical performance

#### Scenario: Memory efficiency
**Given** validation framework processes 200 files with <500MB memory

**When** clustering framework processes the same data

**Then** peak memory usage MUST NOT exceed 1GB

**And** the system MUST release memory after each algorithm completes

#### Scenario: Parallel processing support
**Given** the system has 4 CPU cores

**When** running 4 clustering algorithms

**Then** the system MUST utilize parallel execution

**And** it MUST complete faster than sequential execution

**And** the configuration MUST allow setting max_workers

---

### Requirement: Documentation and Examples Integration
The system MUST provide documentation that integrates with validation framework documentation.

系统必须提供与验证框架文档集成的文档。

#### Scenario: README includes both workflows
**Given** the main README.md documents the validation framework

**When** clustering integration is complete

**Then** README.md MUST include a "聚类分析" section

**And** it MUST explain the discovery-validation workflow

**And** it MUST provide examples for both `validate.py` and `cluster.py`

**And** it MUST link to detailed clustering documentation

#### Scenario: Configuration examples provided
**Given** `configs/` directory exists

**When** clustering integration is complete

**Then** it MUST contain `rubis_cluster.yaml` with complete examples

**And** it MUST contain `bsn_cluster.yaml` with complete examples

**And** each config MUST include inline comments explaining all fields

**And** comments MUST be in Chinese

#### Scenario: Quick start guide
**Given** a new user wants to try clustering

**When** they read the README

**Then** they MUST find a "快速开始" section for clustering

**And** it MUST show: installation, running first analysis, interpreting results

**And** it MUST take less than 5 minutes to complete the quick start

---

### Requirement: Testing Integration
The system MUST include tests that verify integration with the validation framework.

系统必须包含验证与验证框架集成的测试。

#### Scenario: Integration test - shared parser
**Given** a test that uses `RUBISParser`

**When** the test runs in both validation and clustering test suites

**Then** both MUST import from `common.adapters.RUBISParser`

**And** both MUST produce identical parsing results

**And** the test MUST verify `DistributionParameters` objects are identical

#### Scenario: Integration test - full workflow
**Given** a test dataset with 10 trace files

**When** I run an integration test

**Then** it MUST execute: clustering → generate config → validation

**And** it MUST verify validation uses clustering-discovered parameters

**And** it MUST verify validation passes for data matching discovered distributions

**And** the test MUST complete within 10 seconds

#### Scenario: Regression test - backward compatibility
**Given** existing validation tests for data_validation module

**When** the common layer refactoring is complete

**Then** all existing validation tests MUST still pass

**And** no test code MUST need modification (except imports if necessary)

**And** test coverage MUST remain >= current level
