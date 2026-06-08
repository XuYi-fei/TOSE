# Design Document: Data Reorganization and SWAT Support

## Architecture Overview

This change involves two major components:
1. **Data Layout Refactoring**: Structural reorganization without logic changes
2. **SWAT Parser Addition**: New adapter following existing patterns

## 1. Data Layout Design

### Directory Structure

```
data/
├── rubis/
│   ├── identity/          # Clustering/learning data (eval_ident_traces)
│   │   ├── eval_ident_trace-cnt-000-...txt
│   │   ├── eval_ident_trace-cnt-001-...txt
│   │   └── ...
│   └── abnormal/          # Detection/testing data (eval_abn_traces)
│       ├── eval_abn_trace-cnt-000-...txt
│       ├── eval_abn_trace-cnt-001-...txt
│       └── ...
├── bsn/
│   ├── identity/
│   └── abnormal/
├── swat/
│   ├── identity/
│   └── abnormal/          # May be empty initially
└── wadi/                  # Reserved for future use
    ├── identity/
    └── abnormal/
```

### Design Rationale

**Why `identity/` and `abnormal/` instead of `eval_ident_traces/` and `eval_abn_traces/`?**
- Shorter, clearer names
- Semantic meaning: "identity" = learning/clustering data, "abnormal" = testing/detection data
- Removes redundant `eval_` prefix (already implied by being in evaluation data)
- More intuitive for new users

**Why system-level directories (`rubis/`, `swat/`) instead of flat structure?**
- Scalability: Easy to add new systems (WADI, TrainTicket, etc.)
- Isolation: Each system's data is self-contained
- Consistency: Same structure for all systems

**Why `data/` at project root?**
- Single entry point for all evaluation data
- Clear separation from code (`src/`-like pattern)
- Common convention in ML/data science projects

### Migration Strategy

**Step 1**: Create new directory structure
```bash
mkdir -p data/{rubis,bsn,swat,wadi}/{identity,abnormal}
```

**Step 2**: Move existing data
```bash
# RUBIS
mv rubis_evaluation_data/eval_ident_traces/* data/rubis/identity/
mv rubis_evaluation_data/eval_abn_traces/* data/rubis/abnormal/

# BSN
mv bsn_evaluation_data/eval_ident_traces/* data/bsn/identity/

# SWAT
mv swat_evaluation_data/eval_ident_traces/* data/swat/identity/

# WADI (if exists)
mv wadi_evaluation_data/eval_ident_traces/* data/wadi/identity/
```

**Step 3**: Remove old directories (after verification)
```bash
rm -rf rubis_evaluation_data bsn_evaluation_data swat_evaluation_data wadi_evaluation_data
```

## 2. SWAT Parser Design

### File Format Analysis

**SWAT Trace Example**:
```csv
time,water_tank,noisy_B_in,noisy_B_out,u_1_in,u_1_out,y_0
2,tank301,0.3703703703703703,-0.3734551768816545,0.0,1.0,-0.3892191700865624
3,tank301,0.3703703703703703,-0.3726262663030032,0.0,1.0,-0.3060867144447456
...
```

**RUBIS Trace Example**:
```csv
simTime(s),controlServersDouble_{k-1},controlServers_{k-1},measuredArrivalRate_{k},measuredAvgRespTime_{k}
960,2,2,40.0667,0.128231
1020,1.78091,2,40.5167,0.109956
...
```

**Similarities**:
- First column is time (different names: `time` vs `simTime(s)`)
- Last column is target metric (`y_0` vs `measuredAvgRespTime_{k}`)
- Same filename pattern: `eval_(ident|abn)_trace-cnt-XXX-duration-XXX-config_num-XXX-trace_config-XXX-start_time-XXX.txt`

**Differences**:
- SWAT has intermediate columns with different semantics
- SWAT time starts at 2, RUBIS time varies
- Column count differs (SWAT: 7, RUBIS: 5)

### Class Hierarchy Options

**Option A: Inheritance from RUBISParser**
```python
class SWATParser(RUBISParser):
    TARGET_COLUMN = 'y_0'
    TIME_COLUMN = 'time'
```

**Option B: Separate implementation with shared base**
```python
class SWATParser(TraceParser):
    # Duplicate filename parsing logic
    # Custom implementation
```

**Option C: Composition with shared utilities**
```python
class SWATParser(TraceParser):
    # Reuse filename parsing via utility function
    # Custom trace parsing
```

**Decision: Option A (Inheritance)**

**Rationale**:
- Filename pattern is identical → reuse `FILENAME_PATTERN` and `parse_filename()`
- Trace parsing logic is similar → override only `TARGET_COLUMN` and minor methods
- Reduces code duplication
- Easy to maintain (bug fixes in base class apply to both)

**Trade-off**:
- Tight coupling with RUBISParser
- If RUBIS parser changes, SWAT parser may need updates
- **Mitigation**: RUBIS parser is stable, filename pattern is unlikely to change

### Implementation Details

```python
class SWATParser(RUBISParser):
    """SWAT数据适配器

    SWAT数据格式与RUBIS非常相似：
    - 文件名格式完全相同
    - 第一列是时间（time vs simTime(s)）
    - 最后一列是目标指标（y_0 vs measuredAvgRespTime_{k}）

    因此继承RUBISParser，只需覆盖列名配置
    """

    # SWAT目标列名（最后一列）
    TARGET_COLUMN = 'y_0'

    # SWAT时间列名（第一列）
    TIME_COLUMN = 'time'

    # Metadata类型使用RUBISMetadata（字段完全一致）
    # 或创建SWATMetadata别名

    def parse_trace_file(self, filepath: Path, metadata: RUBISMetadata) -> Dict[str, pd.DataFrame]:
        """解析SWAT trace文件并按norm标签分段

        覆盖父类方法以使用SWAT特定的列名
        """
        df = pd.read_csv(filepath)
        df_clean = df.dropna()

        segments = {}
        start_times = metadata.start_time
        trace_configs = metadata.trace_config

        for i, norm_label in enumerate(trace_configs):
            start = start_times[i]
            end = start_times[i + 1] if i + 1 < len(start_times) else df_clean[self.TIME_COLUMN].max() + 1

            segment_df = df_clean[
                (df_clean[self.TIME_COLUMN] >= start) &
                (df_clean[self.TIME_COLUMN] < end)
            ].copy()

            segments[norm_label] = segment_df

        return segments

    def extract_parameters(self, segments: Dict[str, pd.DataFrame], metadata: RUBISMetadata) -> List[DistributionParameters]:
        """从SWAT分段数据中提取参数

        使用TARGET_COLUMN提取目标指标
        """
        # Similar to RUBISParser but uses self.TARGET_COLUMN
        # Implementation follows same pattern
```

### Metadata Design

**Option A: Reuse RUBISMetadata**
- SWAT filename format is identical to RUBIS
- All fields are the same: `cnt`, `duration`, `config_num`, `trace_config`, `start_time`, `filename`
- **Decision**: Reuse RUBISMetadata directly

**Option B: Create SWATMetadata alias**
```python
from ..models.metadata import RUBISMetadata as SWATMetadata
```
- Provides semantic clarity
- Easy to extend if SWAT-specific fields are added later
- **Decision**: Use this approach for clarity

## 3. Configuration Design

### Configuration File Paths

**Clustering Configs**:
- `configs/rubis_clustering_config.yaml`: `data_path: data/rubis/identity`
- `configs/bsn_clustering_config.yaml`: `data_path: data/bsn/identity`
- `configs/swat_clustering_config.yaml`: `data_path: data/swat/identity` (NEW)

**Detection Configs**:
- `configs/rubis_detection_config.yaml`: `test_data_path: data/rubis/abnormal`
- `configs/bsn_detection_config.yaml`: `test_data_path: data/bsn/abnormal`
- `configs/swat_detection_config.yaml`: `test_data_path: data/swat/abnormal` (NEW)

### SWAT Configuration Template

```yaml
# SWAT聚类分析配置文件

# 系统类型
system_type: swat

# 数据路径
data_path: data/swat/identity

# 聚类算法列表
algorithms:
  - hdbscan
  - gmm
  - affinity_propagation
  - mean_shift

# 算法参数配置
algorithm_params:
  hdbscan:
    min_cluster_size: 10
    min_samples: 5
  gmm:
    min_clusters: 2
    max_clusters: 10
    covariance_type: full
  affinity_propagation:
    damping: 0.5
    max_iter: 200
  mean_shift:
    bandwidth: null

# 输出配置
output:
  dir: clustering_results/swat
  visualizations: true
  report: true
  save_learned_distributions: true
  learned_distributions_path: clustering_results/swat/learned_distributions.yaml
```

## 4. Testing Strategy

### Test Levels

**Unit Tests**:
1. `test_swat_parser_filename()`: Verify SWAT filename parsing
2. `test_swat_parser_trace_file()`: Verify trace file segmentation
3. `test_swat_parser_extract_parameters()`: Verify parameter extraction
4. `test_parser_factory_swat()`: Verify SWAT parser registration

**Integration Tests**:
1. **SWAT Clustering Workflow**:
   ```bash
   python cluster.py --config configs/swat_clustering_config.yaml
   ```
   - Verify: 200 files loaded, ~600 parameters extracted, 3 distributions found
   - Verify: `clustering_results/swat/learned_distributions.yaml` created
   - Verify: Visualizations generated with Chinese text

2. **SWAT Detection Workflow** (if abnormal data exists):
   ```bash
   python detect.py --config configs/swat_detection_config.yaml
   ```
   - Verify: Detection report generated
   - Verify: Metrics calculated correctly

3. **RUBIS Regression Test**:
   - Re-run RUBIS clustering and detection with new paths
   - Verify: Results identical to previous runs

4. **BSN Regression Test**:
   - Re-run BSN clustering with new paths
   - Verify: Results match expectations

### Validation Checklist

- [ ] SWAT parser registered in ParserFactory
- [ ] SWAT identity traces (200 files) load successfully
- [ ] Clustering generates learned_distributions.yaml for SWAT
- [ ] Visualizations render with correct Chinese labels
- [ ] RUBIS workflows unchanged (regression test)
- [ ] BSN workflows unchanged (regression test)
- [ ] All config files validate successfully
- [ ] Documentation includes SWAT examples

## 5. Documentation Plan

### README Updates

**New Section**: "Data Organization"
```markdown
## Data Organization

All evaluation data is organized under the `data/` directory:

```
data/
├── rubis/
│   ├── identity/    # Clustering/learning data
│   └── abnormal/    # Detection/testing data
├── bsn/
│   ├── identity/
│   └── abnormal/
└── swat/
    ├── identity/
    └── abnormal/
```

- **identity/**: Data for clustering analysis and distribution learning
- **abnormal/**: Data for anomaly detection and testing
```

**New Section**: "Supported Systems"
```markdown
## Supported Systems

The framework supports three system types:

### RUBIS (Rice University Bidding System)
- **Domain**: E-commerce web application
- **Metric**: Average response time (`measuredAvgRespTime_{k}`)
- **Data**: 200 identity traces, 200 abnormal traces

### BSN (Body Sensor Network)
- **Domain**: Healthcare monitoring
- **Metric**: Processing cost (`cost`)
- **Data**: 200 identity traces

### SWAT (Secure Water Treatment)
- **Domain**: Industrial control system
- **Metric**: Water tank level (`y_0`)
- **Data**: 200 identity traces
```

**Updated Usage Examples**:
```markdown
### SWAT Clustering Example

```bash
# Run clustering analysis on SWAT data
python cluster.py --config configs/swat_clustering_config.yaml

# Output:
# - clustering_results/swat/learned_distributions.yaml
# - clustering_results/swat/*.png (visualizations)
# - clustering_results/swat/clustering_report.md
```

### SWAT Detection Example (when abnormal data available)

```bash
# Run anomaly detection on SWAT data
python detect.py --config configs/swat_detection_config.yaml
```
```

### Migration Guide

**File**: `docs/data_migration_guide.md`

```markdown
# Data Migration Guide

This guide helps migrate from the old data layout to the new organized structure.

## Old Layout → New Layout

| Old Path | New Path |
|----------|----------|
| `rubis_evaluation_data/eval_ident_traces/` | `data/rubis/identity/` |
| `rubis_evaluation_data/eval_abn_traces/` | `data/rubis/abnormal/` |
| `bsn_evaluation_data/eval_ident_traces/` | `data/bsn/identity/` |
| `swat_evaluation_data/eval_ident_traces/` | `data/swat/identity/` |

## Migration Steps

1. Create new directory structure:
   ```bash
   mkdir -p data/{rubis,bsn,swat}/{identity,abnormal}
   ```

2. Move data files:
   ```bash
   # RUBIS
   mv rubis_evaluation_data/eval_ident_traces/* data/rubis/identity/
   mv rubis_evaluation_data/eval_abn_traces/* data/rubis/abnormal/

   # BSN
   mv bsn_evaluation_data/eval_ident_traces/* data/bsn/identity/

   # SWAT
   mv swat_evaluation_data/eval_ident_traces/* data/swat/identity/
   ```

3. Update configuration files (already done in new configs)

4. Verify migrations:
   ```bash
   python cluster.py --config configs/rubis_clustering_config.yaml
   python cluster.py --config configs/bsn_clustering_config.yaml
   python cluster.py --config configs/swat_clustering_config.yaml
   ```

5. Remove old directories (optional, keep as backup):
   ```bash
   # WARNING: Only run after verification
   rm -rf rubis_evaluation_data bsn_evaluation_data swat_evaluation_data
   ```
```

## 6. Implementation Phases

### Phase 1: Data Reorganization
- Create `data/` directory structure
- Move RUBIS, BSN, SWAT data to new locations
- Verify data integrity (file counts, checksums)

### Phase 2: SWAT Parser Implementation
- Create `common/adapters/swat.py`
- Implement SWATParser class
- Register in ParserFactory
- Add unit tests

### Phase 3: Configuration Updates
- Update RUBIS configs with new paths
- Update BSN configs with new paths
- Create SWAT configs
- Validate all configs load successfully

### Phase 4: Integration Testing
- Test SWAT clustering workflow end-to-end
- Test RUBIS regression (clustering + detection)
- Test BSN regression (clustering)
- Verify all visualizations and reports generate correctly

### Phase 5: Documentation
- Update README with data organization section
- Add SWAT system documentation
- Create migration guide
- Update usage examples for all three systems

## 7. Risk Analysis

### High Risk: Path References

**Risk**: Hardcoded paths in code or configs may break
**Detection**:
```bash
# Search for old path references
rg "rubis_evaluation_data" --type py
rg "bsn_evaluation_data" --type py
rg "swat_evaluation_data" --type py
```
**Mitigation**: Comprehensive search and replace, thorough testing

### Medium Risk: SWAT Data Format Variations

**Risk**: SWAT data may have edge cases not covered in initial analysis
**Detection**: Run clustering on all 200 files, check for parsing errors
**Mitigation**: Add robust error handling, validate CSV structure before processing

### Low Risk: Configuration Validation

**Risk**: New configs may have typos or invalid paths
**Detection**: Config validation in ClusteringConfig.from_yaml()
**Mitigation**: Use validation that checks file/directory existence

## Summary

This design provides a clean, scalable data organization structure and extends the framework to support SWAT data with minimal code duplication. The inheritance-based SWAT parser design leverages existing RUBIS logic while allowing easy customization. The phased implementation approach minimizes risk through incremental validation at each step.
