## Context

The RUBIS trace dataset contains synthetic performance data with response time metrics generated from three underlying Gaussian distributions (norm1, norm2, norm3). Each trace file contains multiple time segments, where each segment follows one of these three distributions. The challenge is to:

1. Extract distribution parameters from raw metric data
2. Identify which extracted parameters belong to which underlying distribution
3. Validate that we can recover the three known distributions through unsupervised clustering

The key technical challenge is choosing appropriate clustering algorithms that:
- Don't require pre-specifying the number of clusters
- Can handle the 2-dimensional feature space (mean, variance)
- Are robust to potential noise or outliers in the data
- Can validate whether 3 clusters is indeed optimal

## Goals / Non-Goals

### Goals
- Implement multiple clustering algorithms for comparison
- Provide clear evaluation metrics to assess clustering quality
- Enable validation that the data generation process used three distributions
- Create reusable, maintainable code for future trace analysis tasks

### Non-Goals
- Real-time or streaming analysis (batch processing is sufficient)
- Handling non-Gaussian distributions (data is known to be Gaussian)
- Distributed computing (dataset size is manageable on single machine)
- Interactive parameter tuning UI (command-line execution is sufficient)

## Decisions

### Decision 1: Primary Algorithm - HDBSCAN

**Choice**: Use HDBSCAN as the primary/recommended clustering algorithm

**Rationale**:
- Hierarchical density-based approach handles clusters of varying densities well
- Automatic cluster number determination with minimal hyperparameters (only min_samples)
- Robust to outliers (labels them as noise rather than forcing into clusters)
- Well-maintained implementation in scikit-learn 1.8.0 and hdbscan library
- Superior performance compared to DBSCAN in recent benchmarks (2025-2026)

**Alternatives considered**:
- **DBSCAN**: Requires epsilon parameter tuning, less flexible with varying densities
- **K-Means**: Requires pre-specifying k=3, doesn't validate if 3 is optimal
- **Hierarchical Agglomerative**: Requires cutting dendrogram at specific level

### Decision 2: Secondary Algorithms for Validation

**Choice**: Implement GMM+BIC, Affinity Propagation, and Mean Shift as alternative algorithms

**Rationale**:
- **GMM with BIC**: Probabilistic approach that's well-suited for Gaussian data, BIC provides principled model selection
- **Affinity Propagation**: Message-passing approach with different assumptions, good for validation
- **Mean Shift**: Density-based alternative with automatic cluster detection

This multi-algorithm approach enables:
- Cross-validation of cluster count (if all methods find 3 clusters, high confidence)
- Understanding which algorithms are sensitive to data characteristics
- Robustness against algorithm-specific biases

### Decision 3: Feature Space - (Mean, Variance)

**Choice**: Use 2D feature space with mean and variance as coordinates

**Rationale**:
- Directly represents the two parameters that define a Gaussian distribution
- Natural representation for the problem domain
- Enables intuitive visualization
- Sufficient for distinguishing three different distributions

**Alternatives considered**:
- **(Mean, StdDev)**: Variance is more theoretically justified and avoids scale issues
- **Normalized features**: Not necessary since both dimensions are on similar scales
- **Higher-dimensional features**: Overcomplicates the problem without clear benefit

### Decision 4: Implementation Language - Python

**Choice**: Implement in Python with standard data science libraries

**Rationale**:
- Excellent library support (scikit-learn, numpy, scipy, pandas)
- All required clustering algorithms have mature implementations
- Easy visualization with matplotlib/seaborn
- Suitable for research/analysis workflow

**Dependencies**:
```python
numpy>=1.24.0          # Numerical computing
scipy>=1.10.0          # Statistical functions
scikit-learn>=1.8.0    # Clustering algorithms (HDBSCAN, GMM, Mean Shift, Affinity Propagation)
pandas>=2.0.0          # Data manipulation
matplotlib>=3.7.0      # Visualization
seaborn>=0.12.0        # Statistical visualization
hdbscan>=0.8.33        # Alternative HDBSCAN implementation (optional, scikit-learn version preferred)
```

### Decision 5: Code Organization

**Choice**: Create single Python module `rubis_trace_clustering.py` with clear class structure

**Rationale**:
- Single-file implementation keeps code accessible and easy to understand
- Class-based design enables modularity and testability
- Follows simplicity-first principle (can refactor to multi-file if needed)

**Proposed structure**:
```
rubis_trace_clustering.py
├── TraceFileParser       # Handles filename and content parsing
├── GaussianFitter        # Fits distributions to segments
├── ClusteringComparison  # Runs multiple algorithms and compares
│   ├── run_hdbscan()
│   ├── run_gmm_bic()
│   ├── run_affinity_propagation()
│   └── run_mean_shift()
├── ResultVisualizer      # Generates plots and charts
└── StatisticalReporter   # Generates text reports
```

## Risks / Trade-offs

### Risk 1: Insufficient Data Per Segment
**Description**: Some trace segments may have very few data points, leading to unreliable distribution estimates

**Mitigation**:
- Set minimum threshold (e.g., 10 data points) for fitting
- Log warnings for skipped segments
- Report statistics on data sufficiency

### Risk 2: Overlapping Distributions
**Description**: If norm1, norm2, norm3 have similar parameters, clustering may fail to separate them

**Mitigation**:
- Use silhouette scores to detect poor cluster separation
- Visualize overlapping regions in parameter space
- Report uncertainty when cluster boundaries are ambiguous

### Risk 3: Algorithm Parameter Sensitivity
**Description**: Default parameters may not work well for this specific dataset

**Mitigation**:
- Start with recommended defaults from scikit-learn documentation
- Provide easy parameter override mechanism
- Document parameter tuning guidelines in code comments

### Risk 4: Scalability (Minor)
**Description**: With ~200 trace files × 3 segments = ~600 distributions, some algorithms (Affinity Propagation O(N²)) may be slow

**Mitigation**:
- This is acceptable for offline analysis
- Implementation focuses on correctness over performance
- Can optimize later if needed

## Migration Plan

N/A - This is a new capability with no existing implementation to migrate.

## Implementation Phases

### Phase 1: Data Parsing and Distribution Fitting
1. Implement TraceFileParser with filename parsing
2. Implement CSV content parsing with segment assignment
3. Implement GaussianFitter for parameter extraction
4. Test on small subset of trace files
5. Validate extracted parameters are reasonable

### Phase 2: Clustering Implementation
1. Implement HDBSCAN clustering
2. Implement GMM with BIC selection
3. Implement Affinity Propagation
4. Implement Mean Shift
5. Test each algorithm independently on synthetic 2D data

### Phase 3: Comparison and Evaluation
1. Implement ClusteringComparison orchestrator
2. Implement silhouette score calculation
3. Implement cluster count comparison
4. Test on full RUBIS dataset

### Phase 4: Visualization and Reporting
1. Implement scatter plot visualization (parameter space)
2. Implement distribution PDF visualization
3. Implement statistical text reporter
4. Generate example outputs for documentation

## Open Questions

1. **What are the expected ranges for mean and variance?**
   - Need to examine actual data to understand scale
   - May affect algorithm parameter choices (e.g., HDBSCAN min_samples)

2. **Should we normalize features before clustering?**
   - Initially no (variance and mean are both physical quantities)
   - Can add as option if clusters are not well-separated

3. **How should we handle segments with extreme outliers?**
   - Standard approach: use full dataset
   - Alternative: robust statistics (median, MAD) if outliers are problematic

4. **What validation metrics beyond silhouette score?**
   - Consider Davies-Bouldin index, Calinski-Harabasz index
   - Can add in Phase 3 if silhouette score is insufficient
