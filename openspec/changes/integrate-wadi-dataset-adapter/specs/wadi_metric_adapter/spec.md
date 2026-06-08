# Capability: WaDi Metric Adapter

**Capability ID:** `wadi_metric_adapter`
**Change:** `integrate-wadi-dataset-adapter`
**Status:** Proposed

## Overview

The WaDi Metric Adapter enables parsing and interpretation of the WaDi industrial control system dataset, which contains 141 sensor and actuator columns using industrial nomenclature. This capability provides automated metric selection based on data quality, domain relevance, and statistical properties.

## ADDED Requirements

### Requirement: Parse WaDi CSV with Industrial Sensor Nomenclature

**ID:** `WADI-PARSE-001`

The system SHALL parse WaDi CSV files containing timestamp-indexed sensor readings with industrial nomenclature (LT, FIT, PIT, AIT, etc.).

#### Scenario: Load Multi-Column CSV with Sensor Types

**Given** a WaDi CSV file with 141 columns including:
- Timestamp column in format `2023-12-18 HH:MM:SS`
- Process Value columns ending in `.PV` (e.g., `HMI_2_FIT_001.PV`)
- Status columns (e.g., `HMI_2_P_001_STATUS`)

**When** the adapter loads the CSV with `WadiAdapter.load_identity_data(csv_path)`

**Then** the system SHALL:
- Parse timestamps into datetime objects
- Identify 31 PV columns as metric candidates
- Identify 50+ status/control columns as environment indicators
- Filter rows with "Bad Input" status values
- Return a DataFrame with parsed data types

**Example**:
```python
adapter = WadiAdapter()
df = adapter.load_identity_data('data/wadi/WaDi.A3_Dec 2023 Historian Data_original.csv')

assert df['Time'].dtype == 'datetime64[ns]'
assert 'HMI_2_FIT_001.PV' in df.columns
assert (df['HMI_2_P_001_STATUS'] != 'Bad Input').all()
```

---

### Requirement: Interpret Sensor Type Meanings

**ID:** `WADI-PARSE-002`

The system SHALL map industrial sensor codes to physical measurement types for domain-aware metric selection.

#### Scenario: Map Sensor Codes to Measurement Types

**Given** a column name `HMI_2_FIT_001.PV`

**When** the adapter parses the sensor type with `parse_sensor_type(column_name)`

**Then** the system SHALL return:
- Sensor type: `FIT` (Flow Indicator Transmitter)
- Measurement type: `flow`
- Physical unit: `L/s` (liters per second)
- Zone: `HMI_2` (processing stage)

**Mapping Table**:
| Code | Full Name | Measurement | Unit |
|------|-----------|-------------|------|
| LT | Level Transmitter | Liquid level | m |
| FIT | Flow Indicator Transmitter | Flow rate | L/s |
| PIT | Pressure Indicator Transmitter | Pressure | bar |
| AIT | Analytical Instrument Transmitter | Water quality | pH/NTU |
| DPIT | Differential Pressure | Pressure delta | mbar |

**Example**:
```python
sensor_info = adapter.parse_sensor_type('HMI_2_FIT_001.PV')
assert sensor_info['type'] == 'FIT'
assert sensor_info['measurement'] == 'flow'
assert sensor_info['zone'] == 'HMI_2'
```

---

### Requirement: Rank Metrics by Quality and Relevance

**ID:** `WADI-PARSE-003`

The system SHALL automatically rank metrics by data quality (completeness), variability (coefficient of variation), and domain priority (sensor type importance).

#### Scenario: Select Top 3 Metrics from 31 Candidates

**Given** a WaDi DataFrame with 31 PV columns

**When** the adapter ranks metrics with `WadiAdapter.rank_metrics(df, top_k=3)`

**Then** the system SHALL:
1. Filter columns with <80% data completeness
2. Filter columns with CV < 0.01 (too stable) or CV > 2.0 (too noisy)
3. Apply domain priority weights: FIT (flow) = 3, PIT (pressure) = 2, LT (level) = 1, AIT (analytical) = 1
4. Compute score = completeness × min(cv, 1.0) × priority
5. Return top 3 highest-scoring metrics

**Expected Output**:
```python
ranked_metrics = adapter.rank_metrics(df, top_k=3)
assert ranked_metrics == [
    'HMI_2_FIT_001.PV',  # Flow, high variability
    'HMI_2_PIT_001.PV',  # Pressure, medium variability
    'HMI_2_LT_001.PV'    # Level, low variability
]
```

#### Scenario: Exclude Low-Quality Metrics

**Given** a metric `HMI_3_AIT_002.PV` with 45% completeness

**When** the adapter ranks metrics

**Then** the system SHALL exclude this metric from candidates because completeness < 80%

---

### Requirement: Support Manual Metric Override

**ID:** `WADI-PARSE-004`

The system SHALL allow manual metric selection via configuration to override automatic ranking.

#### Scenario: Force Include Low-Ranked Metric

**Given** a configuration file:
```yaml
wadi_config:
  metric_selection:
    auto_rank: true
    manual_override:
      - HMI_1_LT_002.PV  # Force include
    exclude:
      - HMI_3_AIT_001.PV  # Force exclude
```

**When** the adapter loads metrics

**Then** the system SHALL:
- Include `HMI_1_LT_002.PV` even if ranked below top 3
- Exclude `HMI_3_AIT_001.PV` even if ranked in top 3
- Apply auto-ranking to remaining candidates

**Example**:
```python
adapter = WadiAdapter.from_config('configs/wadi_cluster_config.yaml')
metrics = adapter.get_metrics()

assert 'HMI_1_LT_002.PV' in metrics  # Forced inclusion
assert 'HMI_3_AIT_001.PV' not in metrics  # Forced exclusion
```

---

### Requirement: Handle Multi-Zone Architecture

**ID:** `WADI-PARSE-005`

The system SHALL recognize the three-zone architecture (HMI_1, HMI_2, HMI_3) representing input, processing, and output stages.

#### Scenario: Group Metrics by Zone

**Given** metrics from all three zones

**When** the adapter groups metrics with `WadiAdapter.group_by_zone(metrics)`

**Then** the system SHALL return:
```python
{
    'HMI_1': ['HMI_1_FIT_001.PV', 'HMI_1_LT_001.PV'],  # Input stage
    'HMI_2': ['HMI_2_FIT_001.PV', 'HMI_2_PIT_001.PV'],  # Processing stage
    'HMI_3': ['HMI_3_FIT_001.PV']  # Output stage
}
```

#### Scenario: Enable Zone-Independent Clustering

**Given** a configuration with `zone_independent: true`

**When** clustering is performed

**Then** the system SHALL cluster metrics within each zone separately, not mixing data from different zones.

---

## Implementation Notes

### Sensor Nomenclature Reference

Based on ISA-5.1 standard for instrumentation symbols:
- **First Letter**: Measured variable (F=Flow, L=Level, P=Pressure, A=Analytical, T=Temperature)
- **Subsequent Letters**: Modifiers (I=Indicator, T=Transmitter, C=Controller)

### Data Quality Checks

Implemented in `WadiDataQualityChecker`:
```python
def check_column_quality(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    return {
        'completeness': df[column].notna().mean(),
        'bad_input_ratio': (df[column] == 'Bad Input').mean(),
        'coefficient_of_variation': df[column].std() / df[column].mean(),
        'has_outliers': detect_outliers(df[column]),
    }
```

### Configuration Schema

```yaml
wadi_config:
  metric_selection:
    auto_rank: true  # Enable automatic ranking
    max_metrics: 3  # Top K to select
    quality_threshold: 0.8  # Min completeness
    variability_range: [0.01, 2.0]  # CV bounds
    domain_priorities:  # Sensor type weights
      FIT: 3
      PIT: 2
      LT: 1
      AIT: 1
    manual_override:
      - HMI_1_LT_002.PV
    exclude:
      - HMI_3_AIT_001.PV
  zone_independent: true  # Cluster zones separately
```

## Cross-References

- **Depends On**: None (foundational capability)
- **Enables**:
  - `environment_state_detection` (requires parsed metrics)
  - `multimodal_clustering` (requires selected metrics)
- **Related**: `chunked_data_processing` (memory-efficient loading)

## Testing

### Unit Tests
- `test_parse_sensor_type`: All sensor codes → correct mappings
- `test_rank_metrics`: Mock DataFrame → expected ordering
- `test_filter_bad_input`: CSV with "Bad Input" → filtered DataFrame

### Integration Tests
- `test_load_wadi_csv_end_to_end`: Real CSV → parsed DataFrame with correct types
- `test_metric_selection_with_config`: Config file → expected metrics list

### Data Tests
- `test_wadi_csv_column_count`: Verify 141 columns present
- `test_all_zones_represented`: Ensure HMI_1, HMI_2, HMI_3 metrics exist
