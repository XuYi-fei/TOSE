# RUBIS Trace Clustering Analysis

A comprehensive Python tool for analyzing RUBIS benchmark trace files to extract and cluster Gaussian distribution parameters. This tool automatically identifies underlying performance distributions using multiple unsupervised clustering algorithms.

## Features

- **Automated trace parsing**: Extracts configuration metadata and performance metrics from RUBIS trace files
- **Gaussian distribution fitting**: Calculates mean and variance for each trace segment
- **Four clustering algorithms**: HDBSCAN, GMM+BIC, Affinity Propagation, Mean Shift
- **Comprehensive comparison**: Evaluates clustering quality with silhouette scores
- **Rich visualizations**: Generates parameter space plots and recovered distribution curves
- **Statistical reporting**: Produces detailed text reports with cluster analysis

## Requirements

### Python Version
- Python 3.8 or higher

### Dependencies

```
numpy>=1.20.0
pandas>=1.3.0
matplotlib>=3.4.0
scipy>=1.7.0
scikit-learn>=1.3.0
```

### Installation

1. Clone or download this repository
2. Install dependencies:

```bash
pip install numpy pandas matplotlib scipy scikit-learn
```

Or using conda:

```bash
conda install numpy pandas matplotlib scipy scikit-learn>=1.3.0
```

**Note**: scikit-learn 1.3.0+ is required for HDBSCAN support.

## Usage

### Basic Usage

Place your RUBIS trace files in the `rubis_evaluation_data/eval_ident_traces/` directory, then run:

```bash
python rubis_trace_clustering.py
```

### Expected Input Format

Trace files should follow this naming pattern:

```
eval_ident_trace-cnt-XXX-duration-XXXXX-config_num-N-trace_config-normA,normB,normC-start_time-T1,T2,T3.txt
```

Example:
```
eval_ident_trace-cnt-000-duration-64800-config_num-3-trace_config-norm2,norm1,norm3-start_time-960,33660,47580.txt
```

Each trace file should be a CSV with:
- First column: `simTime(s)` (timestamp)
- Last column: `measuredAvgRespTime_{k}` (response time metric)

### Output Files

All outputs are saved to the `clustering_results/` directory:

#### Visualizations (PNG format)

1. **`clustering_parameter_space.png`**
   - Side-by-side scatter plots of all four algorithms
   - Shows (mean, variance) parameter space
   - Points colored by cluster assignment
   - Resolution: 150 DPI, suitable for publications

2. **`distributions_<algorithm>.png`**
   - Dual-panel visualization (Gaussian PDFs + parameter space)
   - Generated for high-quality algorithms (silhouette > 0.7)
   - Shows recovered distribution curves with parameters
   - Displays cluster centroids as star markers

#### Statistical Report (TXT format)

**`clustering_analysis_report.txt`**
- Section 1: Data processing summary
- Section 2: Algorithm comparison table
- Section 3: Detailed cluster analysis
- Section 4: Cluster centroids and parameters
- Section 5: Best algorithm recommendation

## Algorithm Overview

### HDBSCAN (Hierarchical DBSCAN)
- **Type**: Density-based clustering
- **Strengths**: Handles noise, finds clusters of varying density
- **Parameters**: `min_samples=5`, `min_cluster_size=10`
- **Best for**: Detecting fine-grained structure and outliers

### GMM+BIC (Gaussian Mixture Model with BIC)
- **Type**: Model-based clustering
- **Strengths**: Principled model selection, handles Gaussian data
- **Parameters**: Tests k=1 to k=10, selects optimal by BIC
- **Best for**: Gaussian-distributed data (ideal for this use case)

### Affinity Propagation
- **Type**: Message-passing clustering
- **Strengths**: Automatically determines exemplars
- **Parameters**: Default preference (median similarity)
- **Best for**: Small to medium datasets

### Mean Shift
- **Type**: Density-based clustering
- **Strengths**: Non-parametric, finds cluster centers
- **Parameters**: Auto-estimated bandwidth (quantile=0.3)
- **Best for**: Validation and non-parametric analysis

## Example Output

### Console Output

```
============================================================
PHASE 1: DATA PARSING AND DISTRIBUTION FITTING
============================================================
Total trace files: 200
Successfully processed: 200
Failed to process: 0
Total distributions extracted: 600
Average distributions per file: 3.00

Distribution Parameters:
  Mean range: [0.022768, 0.117614]
  Mean average: 0.065078
  Variance range: [0.000002, 0.000222]
  Variance average: 0.000058

================================================================================
PHASE 2 & 3: CLUSTERING AND EVALUATION
================================================================================

Prepared data matrix: (600, 2)

Running all clustering algorithms...

================================================================================
CLUSTERING COMPARISON SUMMARY
================================================================================

Algorithm                 Clusters   Noise      Silhouette   Match 3?
--------------------------------------------------------------------------------
HDBSCAN                   7          19         0.8377       ✗
GMM+BIC                   4          0          0.9896       ✗
Affinity Propagation      200        0          0.6515       ✗
Mean Shift                4          0          0.9896       ✗

✓ Algorithms that found 3 clusters: 0/4

================================================================================
BEST ALGORITHM: GMM+BIC
================================================================================
  Clusters: 4
  Silhouette Score: 0.9896
  Noise Points: 0

================================================================================
PHASE 4: VISUALIZATION AND REPORTING
================================================================================

✓ Parameter space visualization saved: clustering_results/clustering_parameter_space.png
✓ Distribution visualization saved: clustering_results/distributions_hdbscan.png
✓ Distribution visualization saved: clustering_results/distributions_gmm_bic.png
✓ Distribution visualization saved: clustering_results/distributions_mean_shift.png
✓ Statistical report saved: clustering_results/clustering_analysis_report.txt

================================================================================
ANALYSIS COMPLETE
================================================================================
```

### Interpretation

**Silhouette Score**:
- **0.71 - 1.0**: Excellent - Strong structure, well-separated clusters
- **0.51 - 0.7**: Good - Reasonable structure, distinguishable clusters
- **0.26 - 0.5**: Fair - Weak structure, overlapping clusters
- **< 0.26**: Poor - No substantial structure

**Noise Points**: Points labeled as -1 by density-based algorithms (HDBSCAN), indicating outliers or insufficient density.

## Project Structure

```
.
├── rubis_trace_clustering.py          # Main implementation
├── test_rubis_trace_clustering.py     # Unit tests
├── test_clustering_synthetic.py       # Synthetic data tests
├── README_RUBIS_CLUSTERING.md         # This file
├── PHASE1_COMPLETION_SUMMARY.md       # Phase 1 documentation
├── PHASE2_COMPLETION_SUMMARY.md       # Phase 2 documentation
├── PHASE3_COMPLETION_SUMMARY.md       # Phase 3 documentation
├── PHASE4_COMPLETION_SUMMARY.md       # Phase 4 documentation
├── rubis_evaluation_data/
│   └── eval_ident_traces/             # Input trace files (200 files)
├── clustering_results/                # Output directory
│   ├── clustering_parameter_space.png
│   ├── distributions_*.png
│   └── clustering_analysis_report.txt
└── openspec/                          # OpenSpec specifications
    └── changes/add-gaussian-distribution-clustering/
```

## Code Architecture

### Main Components

1. **TraceFileParser**: Parses RUBIS trace filenames and CSV content
   - Extracts metadata (config_num, trace_config, start_time)
   - Segments data by time ranges
   - Filters segments with insufficient data

2. **GaussianFitter**: Fits Gaussian distributions to trace segments
   - Calculates sample mean and variance
   - Validates distribution parameters
   - Returns DistributionParameters objects

3. **ClusteringAlgorithms**: Runs four clustering algorithms
   - `run_hdbscan()`: HDBSCAN clustering
   - `run_gmm_bic()`: GMM with BIC selection
   - `run_affinity_propagation()`: Affinity Propagation
   - `run_mean_shift()`: Mean Shift clustering

4. **ClusteringComparison**: Orchestrates algorithm comparison
   - Runs all algorithms on same dataset
   - Calculates evaluation metrics
   - Identifies best algorithm

5. **ResultVisualizer**: Generates visualizations
   - `visualize_parameter_space()`: Multi-algorithm scatter plots
   - `visualize_distributions()`: Recovered Gaussian PDFs

6. **StatisticalReporter**: Generates text reports
   - `generate_report()`: Comprehensive 5-section report
   - Cluster centroids and statistics

## Testing

### Unit Tests

Run the unit test suite:

```bash
python test_rubis_trace_clustering.py
```

Tests cover:
- Filename parsing
- Metadata validation
- CSV parsing and segmentation
- Gaussian fitting
- Edge case handling

### Synthetic Data Tests

Validate clustering algorithms on known data:

```bash
python test_clustering_synthetic.py
```

Generates:
- 3-cluster synthetic Gaussian mixture data
- Comparison visualization
- Algorithm performance metrics

## Performance

**Typical runtime on 600 distributions:**
- Data loading and parsing: ~2.5 seconds
- HDBSCAN: ~0.01 seconds
- GMM+BIC: ~0.22 seconds
- Affinity Propagation: ~0.90 seconds
- Mean Shift: ~0.04 seconds
- Visualization and reporting: ~1.3 seconds
- **Total**: ~5 seconds

**Memory usage**: ~180 MB peak (includes matplotlib rendering)

## Troubleshooting

### Common Issues

**Q: "No module named 'sklearn.cluster.HDBSCAN'"**
- A: Upgrade scikit-learn: `pip install --upgrade scikit-learn>=1.3.0`

**Q: "No trace files found"**
- A: Ensure trace files are in `rubis_evaluation_data/eval_ident_traces/`
- A: Verify filenames match the expected pattern

**Q: "Failed to read CSV"**
- A: Check that trace files are valid CSV format
- A: Ensure files contain `simTime(s)` column

**Q: Visualizations not generated**
- A: Check `clustering_results/` directory exists and is writable
- A: Ensure matplotlib backend is properly configured

### Debug Mode

Enable debug logging by modifying the logging level:

```python
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
```

## Citation

If you use this tool in your research, please cite:

```
RUBIS Trace Clustering Analysis Tool
TOSE Project, 2026
```

## License

This project is part of the TOSE (Theory of Software Engineering) coursework.

## Contributing

This is a course project. For questions or issues, please contact the project maintainers.

## Acknowledgments

- RUBIS benchmark suite for providing the evaluation traces
- scikit-learn for clustering algorithm implementations
- OpenSpec methodology for structured development

## Version History

- **v1.0.0** (2026-01-12): Initial release
  - Phase 1: Data parsing and distribution fitting
  - Phase 2: Four clustering algorithm implementations
  - Phase 3: Clustering comparison and evaluation
  - Phase 4: Visualization and statistical reporting
  - Phase 5: Validation, cleanup, and documentation

## Contact

For questions or issues, please refer to the course materials or contact the instructors.
