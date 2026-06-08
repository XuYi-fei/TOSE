## ADDED Requirements

### Requirement: Trace File Parsing

The system SHALL parse RUBIS trace files to extract configuration metadata and metric values.

#### Scenario: Parse filename metadata
- **GIVEN** a trace file with naming pattern `eval_ident_trace-cnt-XXX-duration-XXXXX-config_num-N-trace_config-normA,normB,normC-start_time-T1,T2,T3.txt`
- **WHEN** the parser processes the filename
- **THEN** it SHALL extract:
  - config_num: number of configurations in the trace
  - trace_config: ordered list of norm labels (e.g., ['norm2', 'norm1', 'norm3'])
  - start_time: ordered list of start timestamps for each norm segment (e.g., [960, 33660, 47580])

#### Scenario: Extract metric values by segment
- **GIVEN** a parsed trace file with known segment start times
- **WHEN** the parser processes the CSV content
- **THEN** it SHALL:
  - Skip the header row
  - Parse each row as comma-separated values
  - Extract the first column as timestamp (simTime)
  - Extract the last column as measuredAvgRespTime_{k}
  - Assign each metric value to the appropriate norm segment based on timestamp ranges

### Requirement: Gaussian Distribution Fitting

The system SHALL fit Gaussian distributions to metric values for each trace segment.

#### Scenario: Fit distribution to segment data
- **GIVEN** a sequence of measuredAvgRespTime values for a single norm segment
- **WHEN** the fitting algorithm is applied
- **THEN** it SHALL:
  - Calculate the sample mean (μ) of the metric values
  - Calculate the sample variance (σ²) of the metric values
  - Return the (μ, σ²) pair as a single distribution data point

#### Scenario: Handle insufficient data
- **GIVEN** a norm segment with fewer than 2 data points
- **WHEN** the fitting algorithm is applied
- **THEN** it SHALL skip the segment and log a warning

### Requirement: Automatic Clustering

The system SHALL cluster distribution parameters using algorithms that automatically determine cluster count.

#### Scenario: HDBSCAN clustering
- **GIVEN** a collection of (mean, variance) pairs from all trace segments
- **WHEN** HDBSCAN clustering is applied
- **THEN** it SHALL:
  - Use min_samples parameter (default: 5) as the only required hyperparameter
  - Automatically determine the optimal number of clusters
  - Handle noise points by labeling them as cluster -1
  - Return cluster labels for each distribution data point

#### Scenario: GMM with BIC selection
- **GIVEN** a collection of (mean, variance) pairs from all trace segments
- **WHEN** GMM with BIC is applied
- **THEN** it SHALL:
  - Evaluate GMM models for cluster counts ranging from 1 to 10
  - Calculate BIC score for each model
  - Select the model with the lowest BIC score
  - Return cluster labels and the optimal number of clusters

#### Scenario: Affinity Propagation clustering
- **GIVEN** a collection of (mean, variance) pairs from all trace segments
- **WHEN** Affinity Propagation is applied
- **THEN** it SHALL:
  - Automatically determine the number of clusters based on data similarity
  - Return cluster labels and exemplar points for each cluster

#### Scenario: Mean Shift clustering
- **GIVEN** a collection of (mean, variance) pairs from all trace segments
- **WHEN** Mean Shift is applied
- **THEN** it SHALL:
  - Automatically determine cluster centers based on density
  - Return cluster labels and cluster centers

### Requirement: Clustering Comparison

The system SHALL compare results from multiple clustering algorithms.

#### Scenario: Compare cluster counts
- **GIVEN** clustering results from all implemented algorithms
- **WHEN** comparison is performed
- **THEN** it SHALL report:
  - Number of clusters identified by each algorithm
  - Highlighting when the count equals 3 (expected value)

#### Scenario: Calculate clustering quality metrics
- **GIVEN** clustering results and the original distribution data
- **WHEN** quality metrics are calculated
- **THEN** it SHALL compute:
  - Silhouette score for each algorithm (range: -1 to 1, higher is better)
  - Number of noise points (for density-based algorithms)
  - Cluster size distribution

### Requirement: Result Visualization

The system SHALL visualize clustering results and recovered distributions.

#### Scenario: Visualize clusters in parameter space
- **GIVEN** clustering results with (mean, variance) coordinates
- **WHEN** visualization is generated
- **THEN** it SHALL create a scatter plot with:
  - X-axis: mean values
  - Y-axis: variance values
  - Points colored by cluster assignment
  - Legend showing cluster labels

#### Scenario: Visualize recovered distributions
- **GIVEN** cluster assignments for distribution parameters
- **WHEN** distribution visualization is generated
- **THEN** it SHALL:
  - Calculate cluster centroids (mean of means, mean of variances)
  - Plot Gaussian probability density functions for each cluster
  - Label each distribution with its parameters

### Requirement: Statistical Reporting

The system SHALL generate comprehensive statistical reports of the analysis.

#### Scenario: Generate summary report
- **GIVEN** completed clustering analysis
- **WHEN** the report is generated
- **THEN** it SHALL include:
  - Total number of trace files processed
  - Total number of distribution parameters extracted
  - Results table comparing all clustering algorithms:
    - Algorithm name
    - Number of clusters found
    - Silhouette score
    - Cluster size distribution
  - For each identified cluster:
    - Cluster centroid (mean, variance)
    - Number of data points in cluster
    - Standard deviation of cluster members
