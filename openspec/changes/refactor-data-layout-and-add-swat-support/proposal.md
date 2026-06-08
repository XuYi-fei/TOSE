# Proposal: Refactor Data Layout and Add SWAT Support

## Overview

This proposal addresses data organization issues and extends the framework to support the SWAT (Secure Water Treatment) dataset. As new system types are added (RUBIS, BSN, SWAT, WADI), the project root directory is becoming cluttered with evaluation data folders. This proposal reorganizes all evaluation data into a structured `data/` directory and adds full support for SWAT data processing.

## Problem Statement

### Current Issues
1. **Disorganized Data Layout**: Evaluation data directories (`rubis_evaluation_data/`, `bsn_evaluation_data/`, `swat_evaluation_data/`, etc.) are scattered in the project root, making the project structure increasingly messy
2. **No Semantic Separation**: Identity traces and abnormal traces are mixed in the same subdirectory, requiring users to distinguish by filename patterns
3. **Missing SWAT Support**: SWAT data exists but lacks parser implementation, configuration templates, and integration tests
4. **Scalability**: As more system types are added, the current flat structure will become unmanageable

### Current Data Layout
```
TOSE/
├── rubis_evaluation_data/
│   ├── eval_ident_traces/
│   └── eval_abn_traces/
├── bsn_evaluation_data/
│   └── eval_ident_traces/
├── swat_evaluation_data/
│   └── eval_ident_traces/
└── wadi_evaluation_data/
    └── eval_ident_traces/
```

## Proposed Solution

### 1. Data Reorganization

Consolidate all evaluation data under a unified `data/` directory with clear hierarchical structure:

```
data/
├── rubis/
│   ├── identity/       # eval_ident_traces
│   └── abnormal/       # eval_abn_traces
├── bsn/
│   ├── identity/
│   └── abnormal/
├── swat/
│   ├── identity/
│   └── abnormal/
└── wadi/
    ├── identity/
    └── abnormal/
```

**Benefits**:
- Clear separation between system types (rubis, bsn, swat, wadi)
- Semantic distinction between identity (clustering/learning) and abnormal (detection/testing) data
- Consistent structure across all system types
- Single top-level `data/` directory keeps project root clean

### 2. SWAT Parser Implementation

Based on the SWAT trace file format analysis:
- **Filename Pattern**: Same as RUBIS - `eval_(ident|abn)_trace-cnt-XXX-duration-XXX-config_num-XXX-trace_config-XXX-start_time-XXX.txt`
- **CSV Structure**:
  - Column 1: `time` (simulation time)
  - Columns 2-6: Various metrics (water_tank, noisy_B_in, noisy_B_out, u_1_in, u_1_out)
  - Column 7: `y_0` (target metric - final column like RUBIS)
- **Data Format**: Very similar to RUBIS (first column = time, last column = target metric)

The SWAT parser will:
- Reuse RUBIS filename parsing logic (identical format)
- Extract the last column (`y_0`) as the target metric
- Use `time` column for temporal segmentation
- Share most code with RUBISParser through inheritance or composition

### 3. Configuration Updates

Update all configuration files to reference new data paths:
- `configs/rubis_clustering_config.yaml`: `data_path: data/rubis/identity`
- `configs/rubis_detection_config.yaml`: `test_data_path: data/rubis/abnormal`
- `configs/bsn_clustering_config.yaml`: `data_path: data/bsn/identity`
- Add new `configs/swat_clustering_config.yaml` and `configs/swat_detection_config.yaml`

### 4. Documentation

Provide comprehensive documentation covering:
- Data directory structure and organization principles
- SWAT system characteristics and data format
- Migration guide for moving data from old layout to new layout
- Updated usage examples for all three system types (RUBIS, BSN, SWAT)
- Configuration file reference

## Implementation Scope

### In Scope
1. Create new `data/` directory structure
2. Move existing evaluation data to new locations
3. Implement `SWATParser` class in `common/adapters/swat.py`
4. Register SWAT parser in `ParserFactory`
5. Create SWAT configuration templates
6. Update all existing config files with new paths
7. Update clustering and detection workflows to use new paths
8. Comprehensive end-to-end testing (clustering → detection) for SWAT
9. Documentation updates

### Out of Scope
- WADI parser implementation (data exists but not requested)
- Automated data migration scripts (manual move is sufficient)
- Changes to core clustering/detection algorithms
- Performance optimizations

## Success Criteria

1. ✅ **Data Organization**: All evaluation data moved to `data/{system}/identity|abnormal/` structure
2. ✅ **SWAT Clustering**: Successfully run clustering on SWAT identity traces, generate learned_distributions.yaml
3. ✅ **SWAT Detection**: Successfully run anomaly detection on SWAT abnormal traces (when available), generate detection reports
4. ✅ **Backward Compatibility**: All existing RUBIS and BSN workflows continue to work with new paths
5. ✅ **Configuration Validation**: All config files load successfully and reference correct data paths
6. ✅ **Documentation Complete**: README updated with new structure, SWAT usage examples, and migration guide
7. ✅ **Zero Regressions**: All previous test cases pass with new data layout

## Timeline Estimate

- **Phase 1 (Data Reorganization)**: 1-2 hours
- **Phase 2 (SWAT Parser)**: 2-3 hours
- **Phase 3 (Configuration Updates)**: 1 hour
- **Phase 4 (Testing & Validation)**: 2-3 hours
- **Phase 5 (Documentation)**: 2-3 hours

**Total**: 8-12 hours of implementation work

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing workflows during data move | High | Keep backup of original data, update configs atomically, test each system type |
| SWAT data format differs from expected | Medium | Inspect sample files carefully, add format validation in parser |
| Missing SWAT abnormal traces | Low | Document limitation, proceed with clustering-only workflow |
| Path references hardcoded in scripts | Medium | Search codebase for all path references, update systematically |

## Dependencies

- Existing clustering framework (Phase 1-7 from integrate-clustering-analysis-framework)
- Existing anomaly detection framework (Phase 1-7 from add-anomaly-detection-framework)
- SWAT evaluation data already present in `swat_evaluation_data/`

## Open Questions

1. ✅ **SWAT Abnormal Traces**: Do SWAT abnormal traces exist? If not, we'll only implement clustering workflow
   - **Answer**: Only identity traces currently available, abnormal trace support will be ready for future use

2. ✅ **WADI Support**: Should WADI parser be implemented in this proposal?
   - **Answer**: No, out of scope. WADI can be added in a future proposal if needed

3. ✅ **Data Migration**: Should we provide an automated migration script?
   - **Answer**: No, manual move is sufficient for one-time reorganization

## Approval Required

This proposal requires approval before implementation to ensure:
1. The proposed data layout meets project structure guidelines
2. SWAT parser design aligns with existing adapter patterns
3. Documentation scope is sufficient for users to migrate smoothly
