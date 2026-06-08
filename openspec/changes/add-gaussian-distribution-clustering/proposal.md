# Change: Add Gaussian Distribution Clustering for RUBIS Trace Analysis

## Why

The RUBIS evaluation dataset contains trace files with response time metrics following three underlying Gaussian distributions (norm1, norm2, norm3). To understand and validate the data generation process, we need to:

1. Identify the Gaussian distribution parameters (mean, variance) for each segment within individual trace files
2. Cluster all extracted distribution parameters to recover the three underlying distributions
3. Validate that the clustering successfully identifies the three known distributions used in data generation

This capability is essential for:
- Validating the data generation process
- Understanding the statistical properties of different system configurations
- Enabling future workload characterization and performance modeling

## What Changes

This change introduces a new capability for RUBIS trace data analysis:

- **NEW**: Gaussian distribution parameter extraction from trace segments
  - Parse trace filenames to extract configuration metadata (config_num, norm labels, start times)
  - Extract measuredAvgRespTime_{k} metric values for each time segment
  - Fit Gaussian distributions to each segment and extract (mean, variance) pairs

- **NEW**: Automatic clustering of distribution parameters
  - Implement multiple clustering algorithms that don't require pre-specified cluster counts:
    1. **HDBSCAN** (Hierarchical DBSCAN) - Primary recommendation
    2. **GMM with BIC** (Gaussian Mixture Model with Bayesian Information Criterion)
    3. **Affinity Propagation** - Alternative approach
    4. **Mean Shift** - Density-based alternative
  - Compare clustering results across algorithms
  - Evaluate clustering quality (silhouette score, number of clusters identified)

- **NEW**: Result visualization and validation
  - Visualize identified cluster distributions
  - Compare recovered distributions against expected three distributions
  - Generate statistical summary reports

## Impact

- **Affected specs**: New capability `rubis-trace-analysis` (no existing specs affected)
- **Affected code**: New Python module for trace analysis (to be implemented in project root or appropriate subdirectory)
- **Dependencies**:
  - Python 3.8+
  - NumPy, SciPy (statistical analysis)
  - scikit-learn (clustering algorithms)
  - pandas (data manipulation)
  - matplotlib/seaborn (visualization)
  - hdbscan (optional, for HDBSCAN implementation)

## Success Criteria

- Successfully parse all trace files in `rubis_evaluation_data/eval_ident_traces/`
- Extract Gaussian parameters for each norm segment across all traces
- Clustering algorithms identify 3 clusters (matching the known three distributions)
- Recovered distribution parameters closely match the original norm1, norm2, norm3 distributions
