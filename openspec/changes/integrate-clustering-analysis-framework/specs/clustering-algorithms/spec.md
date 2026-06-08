# Capability: Clustering Algorithms

## Overview

This capability defines the pluggable clustering algorithm system, including the abstract base class, factory pattern, and implementations of four clustering algorithms (HDBSCAN, GMM+BIC, Affinity Propagation, Mean Shift).

---

## ADDED Requirements

### Requirement: Clustering Algorithm Interface
The system MUST define an abstract base class that all clustering algorithms implement.

系统必须定义一个抽象基类，供所有聚类算法实现。

#### Scenario: Define ClusteringAlgorithm ABC
**Given** I want to implement a custom clustering algorithm

**When** I create a subclass of `ClusteringAlgorithm`

**Then** the system MUST require implementing `fit_predict(data: np.ndarray) -> ClusteringResult`

**And** it MUST require implementing `get_name() -> str`

**And** it MAY provide optional methods for parameter validation

**And** the abstract class MUST enforce these requirements at instantiation time

#### Scenario: ClusteringResult data structure
**Given** an algorithm has completed clustering

**When** it returns a `ClusteringResult` object

**Then** the result MUST contain algorithm_name (str)

**And** it MUST contain labels (np.ndarray of shape (N,))

**And** it MUST contain n_clusters (int, number of clusters found)

**And** it MUST contain n_noise (int, number of noise points with label=-1)

**And** it MUST contain silhouette_score (Optional[float])

**And** it MUST contain additional_info (Dict) for algorithm-specific metadata

---

### Requirement: Algorithm Factory and Registration
The system MUST provide a factory for creating algorithm instances and support dynamic registration.

系统必须提供创建算法实例的工厂，并支持动态注册。

#### Scenario: Register built-in algorithms
**Given** the clustering_algorithms module is imported

**When** I call `ClusteringFactory.list_algorithms()`

**Then** the result MUST include ['hdbscan', 'gmm_bic', 'affinity_propagation', 'mean_shift']

**And** all algorithms MUST be automatically registered during module initialization

#### Scenario: Create algorithm instance
**Given** 'hdbscan' is registered in the factory

**When** I call `ClusteringFactory.create('hdbscan', min_samples=5, min_cluster_size=10)`

**Then** the system MUST return an instance of `HDBSCANClusterer`

**And** the instance MUST have min_samples=5 and min_cluster_size=10

**And** calling `create()` with unknown algorithm name MUST raise ValueError

#### Scenario: Register custom algorithm
**Given** I have implemented `class MyClusterer(ClusteringAlgorithm)`

**When** I call `ClusteringFactory.register('custom', MyClusterer)`

**Then** `ClusteringFactory.list_algorithms()` MUST include 'custom'

**And** I MUST be able to create instances with `ClusteringFactory.create('custom')`

**And** the custom algorithm MUST be usable in config files

#### Scenario: Prevent duplicate registration
**Given** an algorithm named 'hdbscan' is already registered

**When** I attempt to register another class with name 'hdbscan'

**Then** the system MUST raise a ValueError

**And** the error message MUST indicate duplicate registration

---

### Requirement: HDBSCAN Algorithm Implementation
The system MUST implement HDBSCAN clustering with automatic cluster detection.

系统必须实现具有自动簇检测功能的HDBSCAN聚类算法。

#### Scenario: Run HDBSCAN with default parameters
**Given** a 2D feature matrix with 600 points representing 3 Gaussian distributions

**When** I call `HDBSCANClusterer(min_samples=5, min_cluster_size=10).fit_predict(data)`

**Then** the algorithm MUST identify between 2 and 4 clusters

**And** it MUST label noise points with -1

**And** it MUST return silhouette_score > 0.5 for well-separated clusters

**And** it MUST complete within 3 seconds

#### Scenario: Handle noise points
**Given** a dataset with outliers far from main clusters

**When** HDBSCAN runs

**Then** outliers MUST be labeled as noise (label=-1)

**And** n_noise MUST count these points

**And** noise points MUST NOT affect silhouette score calculation

#### Scenario: HDBSCAN parameter tuning
**Given** min_cluster_size=20 (larger than default)

**When** HDBSCAN runs

**Then** it MUST find fewer, larger clusters

**And** it MUST merge small clusters that don't meet the minimum size

---

### Requirement: GMM with BIC Algorithm Implementation
The system MUST implement Gaussian Mixture Model with Bayesian Information Criterion for automatic model selection.

系统必须实现带有贝叶斯信息准则的高斯混合模型，用于自动模型选择。

#### Scenario: GMM+BIC automatic component selection
**Given** a 2D feature matrix with 3 underlying Gaussian distributions

**When** I call `GMMBICClusterer(max_components=10).fit_predict(data)`

**Then** the algorithm MUST test models with 1 to 10 components

**And** it MUST calculate BIC for each model

**And** it MUST select the model with lowest BIC

**And** for 3 well-separated Gaussians, it SHOULD select n_clusters=3

**And** it MUST complete within 3 seconds

#### Scenario: GMM handles overlapping clusters
**Given** two Gaussian distributions with overlapping tails

**When** GMM+BIC runs

**Then** it MUST use soft clustering (probabilistic assignments)

**And** points in overlap region MUST be assigned to cluster with higher probability

**And** it MUST return deterministic labels (not probabilities) in ClusteringResult

#### Scenario: GMM convergence monitoring
**Given** GMM is fitting a model

**When** the algorithm fails to converge within max iterations

**Then** it MUST log a warning

**And** it MUST return the best result found so far

**And** additional_info MUST contain 'converged': False

---

### Requirement: Affinity Propagation Algorithm Implementation
The system MUST implement Affinity Propagation for cluster detection without pre-specifying cluster count.

系统必须实现亲和传播算法，无需预先指定簇数即可进行簇检测。

#### Scenario: Run Affinity Propagation
**Given** a 2D feature matrix with 600 points

**When** I call `AffinityPropagationClusterer(damping=0.9).fit_predict(data)`

**Then** the algorithm MUST identify cluster exemplars automatically

**And** it MUST assign each point to the nearest exemplar

**And** it MUST return n_clusters equal to the number of exemplars

**And** it MUST handle the O(N²) complexity by completing within 3 seconds for 600 points

#### Scenario: Affinity Propagation damping parameter
**Given** damping=0.5 (low damping)

**When** the algorithm runs

**Then** it MAY oscillate and fail to converge

**And** the system MUST catch convergence failures

**And** it MUST retry with increased damping (0.9) if configured

**And** it MUST log the retry attempt

---

### Requirement: Mean Shift Algorithm Implementation
The system MUST implement Mean Shift clustering with automatic bandwidth estimation.

系统必须实现具有自动带宽估计的均值漂移聚类算法。

#### Scenario: Run Mean Shift with automatic bandwidth
**Given** a 2D feature matrix

**When** I call `MeanShiftClusterer(quantile=0.2).fit_predict(data)`

**Then** the algorithm MUST estimate bandwidth using `estimate_bandwidth(quantile=0.2)`

**And** it MUST find cluster centers iteratively

**And** it MUST assign points to nearest center

**And** it MUST return n_clusters equal to the number of centers found

**And** it MUST complete within 3 seconds

#### Scenario: Mean Shift bandwidth sensitivity
**Given** quantile=0.1 (smaller bandwidth)

**When** the algorithm runs

**Then** it MUST find more, smaller clusters

**And** given quantile=0.3 (larger bandwidth)

**Then** it MUST find fewer, larger clusters

**And** the clustering result MUST include bandwidth in additional_info

---

### Requirement: Algorithm Comparison and Benchmarking
The system MUST provide utilities to compare algorithm performance and quality.

系统必须提供比较算法性能和质量的工具。

#### Scenario: Compare silhouette scores
**Given** results from 4 algorithms with scores [0.65, 0.72, 0.58, 0.68]

**When** I generate a comparison report

**Then** the system MUST rank algorithms by silhouette score

**And** it MUST highlight the best-performing algorithm

**And** it MUST show score differences in a table

#### Scenario: Compare cluster counts
**Given** expected_clusters=3 and results with n_clusters=[3, 4, 3, 2]

**When** I compare results

**Then** the system MUST identify which algorithms matched expected count

**And** it MUST calculate consensus (how many algorithms agree on cluster count)

**And** if 3 out of 4 algorithms find 3 clusters, consensus MUST be 75%

#### Scenario: Measure algorithm execution time
**Given** I run all 4 algorithms on the same dataset

**When** the clustering engine tracks execution time

**Then** each ClusteringResult MUST include execution_time_seconds in additional_info

**And** the comparison report MUST show a time comparison table

**And** it MUST flag algorithms that exceed 3-second timeout
