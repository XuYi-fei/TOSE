# Capability: Clustering Visualization and Reporting

## Overview

This capability handles generation of visual outputs (PNG charts) and textual reports (Markdown) to present clustering results in an intuitive and comprehensive manner.

---

## ADDED Requirements

### Requirement: Parameter Space Visualization
The system MUST generate a 2D scatter plot showing distribution parameters colored by cluster labels.

系统必须生成2D散点图，显示按簇标签着色的分布参数。

#### Scenario: Generate parameter space plot
**Given** 600 distribution parameters with (mean, variance) coordinates

**And** clustering labels from HDBSCAN [0, 0, 1, 2, -1, 0, 1, ...]

**When** I call `Visualizer.plot_parameter_space(data, labels, output_path)`

**Then** the system MUST create a scatter plot saved to output_path

**And** the X-axis MUST be labeled "均值 (Mean)"

**And** the Y-axis MUST be labeled "方差 (Variance)"

**And** each cluster MUST have a distinct color

**And** noise points (label=-1) MUST be colored gray

**And** the plot MUST include a legend mapping colors to cluster IDs

**And** the figure MUST be saved at 300 DPI resolution

#### Scenario: Annotate cluster centers
**Given** clustering results with cluster centers [(0.0526, 0.000006), (0.1154, 0.000161), (0.0285, 0.000003)]

**When** the parameter space plot is generated

**Then** the system MUST mark each center with a larger marker (e.g., 'X')

**And** it MUST annotate each center with text showing mean and variance values

**And** the annotation MUST use a readable font size (10pt minimum)

#### Scenario: Handle large datasets efficiently
**Given** 600+ data points to plot

**When** generating the scatter plot

**Then** the system MUST use appropriate marker size (e.g., s=20) for readability

**And** it MUST apply alpha transparency (e.g., alpha=0.7) to show overlapping points

**And** the plot MUST render within 1 second

---

### Requirement: Algorithm Comparison Visualization
The system MUST generate a multi-panel plot comparing clustering results from different algorithms.

系统必须生成多面板图表，比较不同算法的聚类结果。

#### Scenario: Generate 2x2 comparison grid
**Given** results from 4 algorithms (HDBSCAN, GMM+BIC, AffinityProp, MeanShift)

**When** I call `Visualizer.plot_algorithm_comparison(results, data, output_path)`

**Then** the system MUST create a 2x2 subplot grid

**And** each subplot MUST show a parameter space scatter plot for one algorithm

**And** each subplot title MUST show "{Algorithm Name}: {n_clusters} clusters, Silhouette={score:.2f}"

**And** all subplots MUST use the same axis limits for comparability

**And** the figure MUST be saved at 300 DPI with size 12x10 inches

#### Scenario: Consistent color mapping across algorithms
**Given** 4 algorithms that all found 3 clusters

**When** the comparison plot is generated

**Then** the system SHOULD attempt to match cluster colors across algorithms

**And** it SHOULD use a consistent color palette (e.g., cluster 0=red, cluster 1=blue, cluster 2=green)

**And** if cluster counts differ, it MUST adjust colors dynamically

#### Scenario: Highlight best algorithm
**Given** HDBSCAN has the highest silhouette score

**When** the comparison plot is generated

**Then** the system MAY add a visual indicator (e.g., bold border) around the best subplot

**And** the overall figure title MUST indicate "Best: HDBSCAN (Silhouette=0.72)"

---

### Requirement: Distribution Density Visualization
The system MUST generate plots showing the recovered Gaussian distributions.

系统必须生成图表，显示恢复出的高斯分布。

#### Scenario: Plot recovered distributions
**Given** 3 clusters with centers (mean, variance): [(0.0526, 0.000006), (0.1154, 0.000161), (0.0285, 0.000003)]

**When** I call `Visualizer.plot_distributions(cluster_centers, output_path)`

**Then** the system MUST generate Gaussian PDF curves for each cluster

**And** the X-axis MUST be labeled "响应时间 (Response Time)"

**And** the Y-axis MUST be labeled "概率密度 (Probability Density)"

**And** each curve MUST use the cluster's mean and sqrt(variance) as parameters

**And** each curve MUST be colored according to its cluster color

**And** the plot MUST include a legend with cluster IDs and parameters

#### Scenario: Overlay actual data histogram
**Given** clustering results and original distribution parameters

**When** generating distribution plots

**Then** the system MAY overlay a histogram of actual response times

**And** the histogram MUST be semi-transparent (alpha=0.3) to not obscure curves

**And** it MUST use the same X-axis range as the PDF curves

#### Scenario: Handle overlapping distributions
**Given** two clusters with similar means but different variances

**When** generating distribution plots

**Then** both curves MUST be visible

**And** the system MUST use different line styles if colors are similar (e.g., solid vs dashed)

**And** the legend MUST clearly distinguish the two distributions

---

### Requirement: Evaluation Metrics Visualization
The system MUST generate visualizations summarizing clustering quality metrics.

系统必须生成可视化图表，汇总聚类质量指标。

#### Scenario: Plot silhouette score comparison
**Given** 4 algorithms with silhouette scores [0.65, 0.72, 0.58, 0.68]

**When** I call `Visualizer.plot_metrics(results, output_path)`

**Then** the system MUST create a bar chart

**And** the X-axis MUST show algorithm names

**And** the Y-axis MUST show silhouette scores

**And** bars MUST be colored green for scores > 0.7, yellow for 0.5-0.7, red for < 0.5

**And** each bar MUST be annotated with the exact score value

#### Scenario: Plot cluster size distribution
**Given** clustering results with cluster sizes [250, 200, 150]

**When** generating metrics visualization

**Then** the system MUST create a second subplot showing cluster size bars

**And** it MUST show each cluster's sample count

**And** it MUST highlight if one cluster is significantly larger (>50% of data)

#### Scenario: Show algorithm agreement matrix
**Given** results from multiple algorithms

**When** generating metrics visualization

**Then** the system MAY create a heatmap showing cluster count agreement

**And** each cell MUST show whether two algorithms found the same number of clusters

**And** high agreement MUST be colored green, low agreement red

---

### Requirement: Markdown Report Generation
The system MUST generate a comprehensive Markdown report summarizing clustering analysis.

系统必须生成全面的Markdown报告，总结聚类分析结果。

#### Scenario: Generate clustering summary report
**Given** completed clustering analysis with 4 algorithm results

**When** I call `Reporter.generate_report(results, config, output_path)`

**Then** the system MUST create a Markdown file at output_path

**And** the report MUST include a "聚类摘要" (Clustering Summary) section

**And** it MUST show total data points, number of algorithms run, and execution time

**And** it MUST include a table comparing all algorithms

#### Scenario: Report table format
**Given** clustering results to report

**When** generating the comparison table

**Then** the table MUST have columns: [算法名称, 簇数, 噪声点数, Silhouette分数, 是否匹配期望]

**And** each row MUST show one algorithm's results

**And** the "是否匹配期望" column MUST show ✓ or ✗ based on expected_clusters

**And** the algorithm with best silhouette MUST be highlighted (e.g., with **bold**)

#### Scenario: Include cluster statistics
**Given** clustering results with 3 clusters

**When** generating the report

**Then** the system MUST include a "聚类统计" section for each algorithm

**And** for each cluster, it MUST show: 聚类ID, 样本数, 中心均值, 中心方差

**And** it MUST calculate and show the percentage of total samples in each cluster

**And** it MUST show min and max values within each cluster

#### Scenario: Embed visualization links
**Given** generated PNG charts at `clustering_results/rubis/clustering_parameter_space.png`

**When** generating the Markdown report

**Then** the report MUST include image embed syntax `![Parameter Space](clustering_parameter_space.png)`

**And** it MUST include all 4 visualization images

**And** images MUST be linked with relative paths from the report location

#### Scenario: Include algorithm details
**Given** HDBSCAN results with params {min_samples: 5, min_cluster_size: 10}

**When** generating the report

**Then** the system MUST include an "算法参数" section

**And** it MUST list all parameters used for each algorithm

**And** it MUST show execution time for each algorithm

**And** it MUST include any warnings or errors encountered

#### Scenario: Provide actionable recommendations
**Given** clustering results where all algorithms found 4 clusters but expected is 3

**When** generating the report

**Then** the system MUST include a "建议" (Recommendations) section

**And** it MUST suggest "数据可能实际包含4个分布，考虑更新期望值"

**And** if silhouette scores are low (<0.5), it MUST suggest parameter tuning

**And** if algorithms disagree on cluster count, it MUST suggest reviewing data quality

---

### Requirement: Visualization Configuration
The system MUST support customization of visualization appearance through configuration.

系统必须支持通过配置自定义可视化外观。

#### Scenario: Configure figure DPI and size
**Given** a config with visualization.dpi=300 and visualization.figsize=[12, 10]

**When** generating any plot

**Then** all figures MUST be saved at 300 DPI

**And** all figures MUST have size 12x10 inches

**And** the system MUST respect these settings consistently

#### Scenario: Configure color scheme
**Given** a config with visualization.colormap='viridis'

**When** generating cluster scatter plots

**Then** the system MUST use the viridis colormap

**And** supported colormaps MUST include: viridis, plasma, tab10, Set3

**And** invalid colormap names MUST fall back to default ('tab10')

#### Scenario: Toggle noise point display
**Given** a config with visualization.show_noise=false

**When** generating parameter space plots

**Then** the system MUST exclude noise points (label=-1) from the plot

**And** given show_noise=true

**Then** noise points MUST be included and colored gray

#### Scenario: Configure Chinese font support
**Given** the system is running on a platform with Chinese font support

**When** generating any visualization

**Then** the system MUST configure matplotlib to use Chinese fonts

**And** it MUST use a font like 'SimHei', 'Arial Unicode MS', or 'PingFang SC'

**And** Chinese characters in labels and titles MUST render correctly

**And** if Chinese fonts are unavailable, it MUST log a warning but continue with English labels
