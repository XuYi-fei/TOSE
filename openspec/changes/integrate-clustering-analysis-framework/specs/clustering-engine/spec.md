# Capability: Clustering Engine

## Overview

The clustering engine is the core orchestration component that coordinates data loading, algorithm execution, result collection, and output generation. It provides a high-level API for running clustering analysis workflows.

---

## ADDED Requirements

### Requirement: Clustering Configuration Management
The system MUST load and validate clustering-specific configurations from YAML files.

系统必须从YAML文件加载和验证聚类专用配置。

#### Scenario: Load valid clustering configuration
**Given** a file `configs/rubis_cluster.yaml` with system_type, data_path, algorithms, and output_dir

**When** I call `ClusteringConfig.from_yaml('configs/rubis_cluster.yaml')`

**Then** the config MUST parse successfully

**And** it MUST contain a list of algorithm configurations

**And** each algorithm config MUST have name, enabled flag, and params dict

**And** it MUST have visualization and performance settings

#### Scenario: Validate configuration paths
**Given** a configuration with data_path='nonexistent_directory'

**When** I call `validate_config(config)`

**Then** the system MUST raise a ValueError

**And** the error message MUST indicate the path does not exist

#### Scenario: Validate algorithm names
**Given** a configuration with algorithm name='unknown_algorithm'

**When** I call `validate_config(config)`

**Then** the system MUST raise a ValueError

**And** the error message MUST list available algorithms

---

### Requirement: Data Loading and Preprocessing
The system MUST load trace files using the common adapter layer and prepare feature matrices for clustering.

系统必须使用公共适配器层加载trace文件，并为聚类准备特征矩阵。

#### Scenario: Load all distributions from directory
**Given** a directory with 200 RUBIS trace files

**When** I call `ClusteringEngine.load_data(config)`

**Then** the system MUST parse all files using `RUBISParser`

**And** it MUST extract distribution parameters from each segment

**And** it MUST return approximately 600 `DistributionParameters` objects (200 files × 3 segments)

**And** the process MUST complete within 3 seconds

#### Scenario: Prepare feature matrix
**Given** a list of 600 `DistributionParameters` objects

**When** I call `ClusteringEngine.prepare_features(distributions)`

**Then** the system MUST create a NumPy array of shape (600, 2)

**And** the first column MUST contain mean values

**And** the second column MUST contain variance values

**And** all values MUST be finite (no NaN or inf)

#### Scenario: Handle empty or invalid data
**Given** a directory with no trace files

**When** I call `ClusteringEngine.load_data(config)`

**Then** the system MUST raise an exception

**And** the error message MUST indicate no valid files were found

---

### Requirement: Multi-Algorithm Execution
The system MUST execute multiple clustering algorithms in parallel or sequentially based on configuration.

系统必须根据配置并行或顺序执行多个聚类算法。

#### Scenario: Run multiple algorithms in parallel
**Given** a configuration with 4 enabled algorithms (HDBSCAN, GMM+BIC, AffinityProp, MeanShift)

**When** I call `ClusteringEngine.run_clustering(data, config)`

**Then** the system MUST execute all 4 algorithms

**And** it MUST use ThreadPoolExecutor with max_workers from config.performance

**And** it MUST return 4 `ClusteringResult` objects

**And** the total execution time MUST be less than 10 seconds

#### Scenario: Skip disabled algorithms
**Given** a configuration where Affinity Propagation has enabled=false

**When** I call `ClusteringEngine.run_clustering(data, config)`

**Then** the system MUST execute only enabled algorithms

**And** the result list MUST NOT contain Affinity Propagation results

#### Scenario: Handle algorithm timeout
**Given** a configuration with algorithm_timeout=3 seconds

**And** an algorithm takes longer than 3 seconds

**When** the clustering engine executes algorithms

**Then** the system MUST terminate the slow algorithm

**And** it MUST log a warning

**And** it MUST continue executing other algorithms

**And** it MUST exclude the timed-out algorithm from results

#### Scenario: Handle algorithm failure gracefully
**Given** one algorithm raises an exception during execution

**When** the clustering engine runs all algorithms

**Then** the system MUST catch the exception

**And** it MUST log the error

**And** it MUST continue executing remaining algorithms

**And** it MUST NOT include failed algorithm in results

**And** if at least one algorithm succeeds, the engine MUST NOT raise an exception

---

### Requirement: Result Aggregation and Evaluation
The system MUST collect clustering results, calculate evaluation metrics, and compare algorithms.

系统必须收集聚类结果、计算评估指标并比较算法。

#### Scenario: Calculate silhouette scores
**Given** clustering results with labels and data

**When** I call `ClusteringEngine.evaluate_results(results, data)`

**Then** the system MUST calculate silhouette score for each result

**And** it MUST handle noise points (label=-1) by excluding them

**And** it MUST store the score in the result object

#### Scenario: Identify best algorithm
**Given** 4 clustering results with different silhouette scores [0.65, 0.72, 0.58, 0.68]

**When** I call `ClusteringEngine.find_best_result(results)`

**Then** the system MUST return the result with highest silhouette score (0.72)

**And** it MUST consider only results with n_clusters >= 2

#### Scenario: Compare against expected clusters
**Given** config with expected_clusters=3

**And** results with n_clusters=[3, 4, 3, 2]

**When** I call `ClusteringEngine.evaluate_results(results, data)`

**Then** the system MUST flag which results match expected count

**And** it MUST store matches_expected=True for results with 3 clusters

**And** it MUST calculate deviation from expected for all results

---

### Requirement: Logging and Progress Reporting
The system MUST provide informative logging and progress feedback during execution.

系统必须在执行过程中提供信息性日志和进度反馈。

#### Scenario: Log clustering pipeline stages
**Given** a clustering analysis run

**When** the engine processes the workflow

**Then** it MUST log "Loading data from {path}" at INFO level

**And** it MUST log "Loaded {N} distribution parameters" after data loading

**And** it MUST log "Running {algorithm_name}" before each algorithm

**And** it MUST log "{algorithm_name} found {n_clusters} clusters" after each algorithm

**And** it MUST log "Clustering complete, generating outputs" at the end

#### Scenario: Report progress for large datasets
**Given** a dataset with 200 files to process

**When** the engine loads data

**Then** it MUST log progress every 50 files

**And** the log MUST show "Processed 50/200 files"

**And** it MUST show estimated time remaining if available

#### Scenario: Log warnings for anomalies
**Given** a clustering result with 0 clusters

**When** the engine evaluates results

**Then** it MUST log a WARNING "Algorithm {name} found 0 clusters, this may indicate parameter tuning needed"

**And** given all 600 points are labeled as noise

**Then** it MUST log a WARNING "All points labeled as noise, consider adjusting parameters"
