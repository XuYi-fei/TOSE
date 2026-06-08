# Proposal: Integrate WaDi Dataset Adapter

**Change ID:** `integrate-wadi-dataset-adapter`
**Status:** Proposed
**Created:** 2026-01-18

## Executive Summary

This proposal extends the anomaly detection framework to support the **WaDi (Water Distribution)** industrial control system dataset. The WaDi dataset represents a three-stage water treatment/distribution system with 141 sensor and actuator columns, requiring specialized metric selection, environment-aware state identification, and memory-efficient processing for the 290MB CSV data file.

## Problem Statement

Currently, the framework supports RUBIS and BSN datasets with pre-defined metrics. The WaDi dataset introduces:

1. **Sensor Nomenclature Complexity**: 31 process value (PV) columns using industrial sensor codes (LT, FIT, PIT, AIT, etc.) that require domain expertise to interpret
2. **Multi-Modal Distributions**: Metrics exhibit distinct operational states (e.g., flow rates cycling between 0.003, 1.3, 2.4 L/s) driven by pump/valve configurations
3. **Environment-Driven Distribution Shifts**: ~50 status/control columns affect metric distributions, requiring identification of which switches cause distribution changes
4. **Memory Constraints**: 290MB CSV file cannot be loaded entirely into memory for analysis
5. **Three-Zone Architecture**: HMI_1 (input), HMI_2 (processing), HMI_3 (output) zones with interdependent metrics

## Discovery Findings

### Metric Analysis
Through reconnaissance on a 20,000-row sample, I identified:

**Primary Metric Candidates** (by coefficient of variation):
- `HMI_2_FIT_001.PV` (Flow): CV=1.13, exhibits 3 distinct states (0.003, 1.3, 2.4 L/s)
- `HMI_3_FIT_001.PV` (Flow): CV=0.75, correlates with HMI_2 output
- `HMI_1_FIT_001.PV` (Flow): CV=0.65, upstream variability

**Environment Switches**:
- Pump status columns: `HMI_2_P_001_STATUS`, `HMI_2_P_002_STATUS`
- Motor valve status: `HMI_2_MV_*.Status` (14 valves in HMI_2 zone)
- Flow switches: `HMI_2_FS_*` indicators

**Operational Pattern**:
- Cyclic operation with ~3000-row (25-minute) periods
- State transitions: LOW → MEDIUM → HIGH → LOW flow states
- Correlates with pump ON/OFF cycles and valve position changes

### Data Quality
- **PV Columns**: 100% valid numeric data, no missing values
- **Status Columns**: Contains "Bad Input" strings requiring filtering
- **Timestamp Column**: `2023-12-18 HH:MM:SS` format, parseable

## Proposed Solution

### Architecture

```
WadiAdapter (new)
├── WadiDataLoader: Chunk-based CSV reader with 10,000-row windows
├── WadiMetricSelector: Domain-driven metric identification
├── EnvironmentStateDetector: Pump/valve status pattern recognition
├── StateAwareClustering: HDBSCAN within each operational state
└── MultiModalDistribution: Per-state distribution learning
```

### Capabilities

1. **WaDi Metric Adapter** (`specs/wadi_metric_adapter/`)
   - Parse 141-column CSV with sensor nomenclature awareness
   - Select metrics based on data completeness (>80%) and variability (0.01 < CV < 2)
   - Map sensor types to physical meanings (LT=level, FIT=flow, PIT=pressure)

2. **Environment State Detection** (`specs/environment_state_detection/`)
   - Identify pump/valve status columns affecting distributions
   - Detect operational state transitions in flow metrics
   - Group data segments by system configuration

3. **Memory-Efficient Processing** (`specs/chunked_data_processing/`)
   - Read CSV in 10,000-row chunks to avoid memory overflow
   - Incrementally build distribution statistics
   - Maintain rolling window for state transition detection

4. **Multi-Modal Distribution Learning** (`specs/multimodal_clustering/`)
   - Cluster within each operational state separately
   - Learn distinct distributions for LOW/MEDIUM/HIGH flow states
   - Handle state-conditional anomaly detection

## User Requirements Mapping

| User Requirement | Proposed Capability |
|------------------|---------------------|
| 1. 新增数据源wadi数据集 | WaDi Metric Adapter |
| 2. 理解LT/FIT/PIT等传感器含义 | Sensor nomenclature mapping in adapter |
| 3. 找到用作metric的列及含义 | Metric selector with domain interpretation |
| 4. 识别环境变化导致的分布变化 | Environment State Detection capability |
| 5. 处理大数据集内存问题 | Chunked Data Processing capability |
| 6. 使框架支持wadi辨识/检测 | Multi-Modal Distribution Learning |

## Implementation Scope

### In-Scope
- WadiAdapter class with chunked CSV reading
- Metric selection for 3 primary flow indicators
- Pump status-based state detection
- State-conditional clustering and distribution learning
- Integration tests on 100,000-row WaDi sample

### Out-of-Scope
- Real-time streaming data processing (CSV batch only)
- Advanced state prediction (only reactive state detection)
- Cross-zone dependency modeling (treat zones independently initially)
- Actuator control signal generation (detection-only, no control)

## Dependencies

- **External**: Existing HDBSCAN clustering, 3-sigma detection logic
- **Data**: `WaDi.A3_Dec 2023 Historian Data_original.csv` in `data/wadi/`
- **Blocked By**: None (parallel to existing adapters)

## Success Criteria

1. **Functional**: WadiAdapter processes entire 290MB CSV without memory errors
2. **Accuracy**: Correctly identifies 3 operational states in HMI_2_FIT_001.PV
3. **Integration**: `python cluster_data.py --config configs/wadi_cluster_config.yaml` succeeds
4. **Detection**: `python detect.py --config configs/wadi_detection_config.yaml` runs on test traces

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| State transition detection fails | Medium | Start with manual state labeling for validation |
| Memory usage exceeds limits | Medium | Reduce chunk size from 10,000 to 5,000 rows |
| Multi-modal distributions cause FP | High | Use state-conditional z-score (test within current state) |
| Sensor nomenclature misinterpretation | Low | Cross-reference with industrial standards documentation |

## Related Changes

- None (initial WaDi integration)

## Validation

Run `openspec validate integrate-wadi-dataset-adapter --strict` before approval.
