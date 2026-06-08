# Capability: Common Data Layer

## Overview

The common data layer provides shared data parsing, modeling, and utility functions that are used by both the validation framework and clustering analysis module. This capability ensures code reuse and maintains consistency across different analysis workflows.

---

## ADDED Requirements

### Requirement: Common Adapter System
The system MUST provide a unified adapter interface for parsing trace files from different systems (RUBIS, BSN, and future systems).

系统必须提供统一的适配器接口，用于解析来自不同系统（RUBIS、BSN及未来系统）的trace文件。

#### Scenario: Parse RUBIS trace file using common adapter
**Given** a RUBIS trace file exists at path `rubis_evaluation_data/eval_ident_traces/eval_ident_trace-cnt-000-duration-64800-config_num-3-trace_config-norm1,norm2,norm3-start_time-960,33660,47580.txt`

**When** I create a parser using `ParserFactory.create('rubis')`

**And** I call `parser.parse_file(filepath)`

**Then** the parser MUST return a list of `DistributionParameters` objects

**And** each object MUST contain mean, variance, norm_label, and filename

**And** the number of objects MUST equal the config_num from the filename

#### Scenario: Parse BSN trace file using common adapter
**Given** a BSN trace file exists with sensor_index=2

**When** I create a parser using `ParserFactory.create('bsn')`

**And** I call `parser.parse_file(filepath)`

**Then** the parser MUST filter data for component `/g3t1_3` (sensor_index + 1)

**And** the parser MUST return distribution parameters extracted from the 'cost' column

**And** the parameters MUST be segmented according to start_time values

#### Scenario: Register custom adapter
**Given** I have implemented a custom `TraceParser` subclass for a new system type

**When** I call `ParserFactory.register('mysystem', MyCustomParser)`

**Then** the factory MUST allow creating instances with `ParserFactory.create('mysystem')`

**And** the custom parser MUST be usable by both validation and clustering modules

---

### Requirement: Common Data Models
The system MUST define shared data models that represent trace metadata and distribution parameters consistently across all modules.

系统必须定义共享的数据模型，在所有模块中一致地表示trace元数据和分布参数。

#### Scenario: Create TraceMetadata from filename
**Given** a filename string `eval_ident_trace-cnt-005-duration-600-config_num-3-trace_config-norm2,norm1,norm3-start_time-1,207,342.txt`

**When** a parser extracts metadata using `parse_filename()`

**Then** the result MUST be a `TraceMetadata` object

**And** it MUST have fields: cnt=5, duration=600, config_num=3

**And** trace_config MUST be ['norm2', 'norm1', 'norm3']

**And** start_time MUST be [1, 207, 342]

#### Scenario: Create DistributionParameters from segment
**Given** a DataFrame segment with response time values [0.052, 0.053, 0.051, ...]

**When** I extract parameters using `extract_parameters(segment, 'norm1', 'file.txt')`

**Then** the result MUST be a `DistributionParameters` object

**And** it MUST have calculated mean, variance, std_dev

**And** it MUST have min_value and max_value from the data

**And** it MUST have sample_count equal to the segment length

**And** it MUST store norm_label='norm1' and filename='file.txt'

#### Scenario: Validate data model consistency
**Given** a `DistributionParameters` object created by RUBIS parser

**When** I pass it to the clustering module

**Then** the clustering module MUST access the mean and variance fields

**And** when I pass the same object to the validation module

**Then** the validation module MUST access the same fields without conversion

---

### Requirement: Common Utility Functions
The system MUST provide reusable statistical calculation and file operation utilities.

系统必须提供可复用的统计计算和文件操作工具函数。

#### Scenario: Calculate mean and variance
**Given** a list of values [0.052, 0.053, 0.051, 0.054, 0.050]

**When** I call `statistics.calculate_mean(values)`

**Then** the result MUST be approximately 0.052

**And** when I call `statistics.calculate_variance(values)`

**Then** the result MUST match NumPy's variance calculation

**And** it MUST use ddof=1 (sample variance)

#### Scenario: Calculate deviation percentage
**Given** expected_mean=0.0526 and actual_mean=0.0525

**When** I call `statistics.calculate_deviation_percent(expected, actual)`

**Then** the result MUST be approximately 0.19% (absolute value)

**And** the formula MUST be `abs((actual - expected) / expected) * 100`

#### Scenario: Check value in range
**Given** value=0.055, min_val=0.045, max_val=0.060

**When** I call `statistics.is_in_range(value, min_val, max_val)`

**Then** the result MUST be True

**And** when value=0.070 (outside range)

**Then** the result MUST be False

---

### Requirement: Backward Compatibility with data_validation
The system MUST maintain backward compatibility so existing validation framework code continues to work without modification.

系统必须保持向后兼容性，使现有验证框架代码无需修改即可继续工作。

#### Scenario: Import adapter from old path
**Given** existing code imports `from data_validation.adapters import RUBISParser`

**When** the common layer is implemented

**Then** the import MUST still succeed through re-export in `data_validation/__init__.py`

**And** the `RUBISParser` class MUST be identical to `common.adapters.RUBISParser`

#### Scenario: Run existing validation tests
**Given** the validation framework has existing unit tests

**When** I run the test suite after common layer extraction

**Then** all tests MUST pass without modification

**And** the validation CLI `python validate.py --config configs/rubis_config.yaml` MUST produce identical results

#### Scenario: Existing configuration files remain valid
**Given** an existing `configs/rubis_config.yaml` file

**When** the common layer is implemented

**Then** the configuration MUST load successfully

**And** validation MUST run without errors

**And** the output report MUST have the same format and content
