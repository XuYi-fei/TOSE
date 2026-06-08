"""
RUBIS Trace Clustering Analysis

This module provides tools for analyzing RUBIS trace files to:
1. Parse trace files and extract Gaussian distribution parameters
2. Cluster distribution parameters to recover underlying distributions
3. Visualize and report clustering results

Author: Generated for TOSE Project
Date: 2026-01-12
"""

import re
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm
from sklearn.cluster import HDBSCAN, AffinityPropagation, MeanShift, estimate_bandwidth
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class TraceMetadata:
    """Metadata extracted from trace filename."""
    filename: str
    cnt: int
    duration: int
    config_num: int
    trace_config: List[str]
    start_time: List[int]

    def __post_init__(self):
        if self.config_num != len(self.trace_config):
            raise ValueError(
                f"config_num ({self.config_num}) doesn't match "
                f"trace_config length ({len(self.trace_config)})"
            )
        if self.config_num != len(self.start_time):
            raise ValueError(
                f"config_num ({self.config_num}) doesn't match "
                f"start_time length ({len(self.start_time)})"
            )


@dataclass
class DistributionParameters:
    """Gaussian distribution parameters extracted from a trace segment."""
    mean: float
    variance: float
    norm_label: str
    trace_filename: str
    sample_size: int


class TraceFileParser:
    """Parser for RUBIS trace files."""

    FILENAME_PATTERN = re.compile(
        r'eval_ident_trace-'
        r'cnt-(?P<cnt>\d+)-'
        r'duration-(?P<duration>\d+)-'
        r'config_num-(?P<config_num>\d+)-'
        r'trace_config-(?P<trace_config>[^-]+)-'
        r'start_time-(?P<start_time>[\d,]+)\.txt'
    )

    def __init__(self, min_data_points: int = 10):
        """
        Initialize TraceFileParser.

        Args:
            min_data_points: Minimum number of data points required for distribution fitting
        """
        self.min_data_points = min_data_points

    def parse_filename(self, filename: str) -> TraceMetadata:
        """
        Parse trace filename to extract metadata.

        Args:
            filename: Name of trace file (e.g., 'eval_ident_trace-cnt-000-...')

        Returns:
            TraceMetadata object with extracted information

        Raises:
            ValueError: If filename doesn't match expected pattern
        """
        match = self.FILENAME_PATTERN.match(filename)
        if not match:
            raise ValueError(f"Filename doesn't match expected pattern: {filename}")

        groups = match.groupdict()

        trace_config = groups['trace_config'].split(',')
        start_time = [int(t) for t in groups['start_time'].split(',')]

        metadata = TraceMetadata(
            filename=filename,
            cnt=int(groups['cnt']),
            duration=int(groups['duration']),
            config_num=int(groups['config_num']),
            trace_config=trace_config,
            start_time=start_time
        )

        logger.debug(f"Parsed {filename}: {metadata.config_num} configs, "
                    f"norms={metadata.trace_config}, times={metadata.start_time}")

        return metadata

    def parse_trace_file(self, filepath: Path) -> Dict[str, pd.DataFrame]:
        """
        Parse CSV content of trace file and segment by norm configuration.

        Args:
            filepath: Path to trace file

        Returns:
            Dictionary mapping norm_label to DataFrame with columns [simTime, measuredAvgRespTime]
        """
        filename = filepath.name
        metadata = self.parse_filename(filename)

        try:
            df = pd.read_csv(filepath)
        except Exception as e:
            logger.error(f"Failed to read CSV {filepath}: {e}")
            raise

        if df.empty:
            logger.warning(f"Empty CSV file: {filepath}")
            return {}

        required_cols = ['simTime(s)']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"Missing required columns in {filepath}. Found: {df.columns.tolist()}")

        timestamp_col = 'simTime(s)'
        metric_col = df.columns[-1]

        logger.debug(f"Using timestamp column: {timestamp_col}, metric column: {metric_col}")

        df_clean = df[[timestamp_col, metric_col]].copy()
        df_clean.columns = ['simTime', 'measuredAvgRespTime']

        df_clean = df_clean.dropna()

        segments = {}
        start_times = metadata.start_time + [float('inf')]

        for i, norm_label in enumerate(metadata.trace_config):
            start = start_times[i]
            end = start_times[i + 1]

            segment_mask = (df_clean['simTime'] >= start) & (df_clean['simTime'] < end)
            segment_df = df_clean[segment_mask].copy()

            if len(segment_df) < self.min_data_points:
                logger.warning(
                    f"Segment {norm_label} in {filename} has only {len(segment_df)} points "
                    f"(min: {self.min_data_points}). Skipping."
                )
                continue

            segments[norm_label] = segment_df
            logger.debug(f"Extracted segment {norm_label}: {len(segment_df)} data points")

        return segments


class GaussianFitter:
    """Fits Gaussian distributions to trace segments."""

    def __init__(self):
        """Initialize GaussianFitter."""
        pass

    def fit_segment(
        self,
        segment_df: pd.DataFrame,
        norm_label: str,
        trace_filename: str
    ) -> Optional[DistributionParameters]:
        """
        Fit Gaussian distribution to a single segment.

        Args:
            segment_df: DataFrame with measuredAvgRespTime column
            norm_label: Label for this segment (e.g., 'norm1')
            trace_filename: Source trace filename

        Returns:
            DistributionParameters object or None if fitting fails
        """
        if 'measuredAvgRespTime' not in segment_df.columns:
            logger.error(f"Missing 'measuredAvgRespTime' column in segment {norm_label}")
            return None

        values = segment_df['measuredAvgRespTime'].values

        if len(values) < 2:
            logger.warning(f"Insufficient data ({len(values)} points) for {norm_label} in {trace_filename}")
            return None

        mean = float(np.mean(values))
        variance = float(np.var(values, ddof=1))

        if variance < 0 or not np.isfinite(mean) or not np.isfinite(variance):
            logger.warning(
                f"Invalid parameters for {norm_label} in {trace_filename}: "
                f"mean={mean}, variance={variance}"
            )
            return None

        logger.debug(f"Fitted {norm_label}: mean={mean:.6f}, variance={variance:.6f}, n={len(values)}")

        return DistributionParameters(
            mean=mean,
            variance=variance,
            norm_label=norm_label,
            trace_filename=trace_filename,
            sample_size=len(values)
        )

    def fit_trace_file(
        self,
        filepath: Path,
        parser: TraceFileParser
    ) -> List[DistributionParameters]:
        """
        Parse and fit all segments in a trace file.

        Args:
            filepath: Path to trace file
            parser: TraceFileParser instance

        Returns:
            List of DistributionParameters for successfully fitted segments
        """
        segments = parser.parse_trace_file(filepath)

        distributions = []
        for norm_label, segment_df in segments.items():
            dist_params = self.fit_segment(segment_df, norm_label, filepath.name)
            if dist_params is not None:
                distributions.append(dist_params)

        logger.info(f"Fitted {len(distributions)} distributions from {filepath.name}")
        return distributions


@dataclass
class ClusteringResult:
    """Results from a clustering algorithm."""
    algorithm_name: str
    labels: np.ndarray
    n_clusters: int
    n_noise: int
    silhouette: Optional[float]
    additional_info: Dict


class ClusteringAlgorithms:
    """Collection of clustering algorithms for distribution parameter analysis."""

    @staticmethod
    def prepare_data(distributions: List[DistributionParameters]) -> np.ndarray:
        """
        Prepare distribution parameters as 2D feature array.

        Args:
            distributions: List of DistributionParameters

        Returns:
            2D array of shape (n_samples, 2) with columns [mean, variance]
        """
        data = np.array([[d.mean, d.variance] for d in distributions])
        logger.debug(f"Prepared data matrix with shape {data.shape}")
        return data

    @staticmethod
    def run_hdbscan(
        data: np.ndarray,
        min_samples: int = 5,
        min_cluster_size: int = 5
    ) -> ClusteringResult:
        """
        Run HDBSCAN clustering algorithm.

        Args:
            data: 2D array of features (mean, variance)
            min_samples: Minimum samples in neighborhood (default: 5)
            min_cluster_size: Minimum cluster size (default: 5)

        Returns:
            ClusteringResult object
        """
        logger.info(f"Running HDBSCAN with min_samples={min_samples}, min_cluster_size={min_cluster_size}")

        clusterer = HDBSCAN(min_samples=min_samples, min_cluster_size=min_cluster_size)
        labels = clusterer.fit_predict(data)

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = np.sum(labels == -1)

        silhouette = None
        if n_clusters > 1:
            valid_mask = labels != -1
            if np.sum(valid_mask) > 0:
                try:
                    silhouette = silhouette_score(data[valid_mask], labels[valid_mask])
                except Exception as e:
                    logger.warning(f"Failed to calculate silhouette score for HDBSCAN: {e}")

        logger.info(f"HDBSCAN found {n_clusters} clusters, {n_noise} noise points, silhouette={silhouette}")

        return ClusteringResult(
            algorithm_name='HDBSCAN',
            labels=labels,
            n_clusters=n_clusters,
            n_noise=n_noise,
            silhouette=silhouette,
            additional_info={
                'min_samples': min_samples,
                'min_cluster_size': min_cluster_size
            }
        )

    @staticmethod
    def run_gmm_bic(
        data: np.ndarray,
        max_components: int = 10
    ) -> ClusteringResult:
        """
        Run Gaussian Mixture Model with BIC selection.

        Args:
            data: 2D array of features (mean, variance)
            max_components: Maximum number of components to test (default: 10)

        Returns:
            ClusteringResult object
        """
        logger.info(f"Running GMM with BIC selection (max_components={max_components})")

        bic_scores = []
        models = []

        for n_components in range(1, max_components + 1):
            gmm = GaussianMixture(
                n_components=n_components,
                covariance_type='full',
                random_state=42
            )
            gmm.fit(data)
            bic = gmm.bic(data)
            bic_scores.append(bic)
            models.append(gmm)

        optimal_idx = np.argmin(bic_scores)
        optimal_n = optimal_idx + 1
        best_model = models[optimal_idx]

        labels = best_model.predict(data)
        n_clusters = optimal_n
        n_noise = 0

        silhouette = None
        if n_clusters > 1:
            try:
                silhouette = silhouette_score(data, labels)
            except Exception as e:
                logger.warning(f"Failed to calculate silhouette score for GMM: {e}")

        logger.info(f"GMM selected {n_clusters} clusters (BIC={bic_scores[optimal_idx]:.2f}), silhouette={silhouette}")

        return ClusteringResult(
            algorithm_name='GMM+BIC',
            labels=labels,
            n_clusters=n_clusters,
            n_noise=n_noise,
            silhouette=silhouette,
            additional_info={
                'bic_scores': bic_scores,
                'optimal_bic': bic_scores[optimal_idx],
                'converged': best_model.converged_
            }
        )

    @staticmethod
    def run_affinity_propagation(
        data: np.ndarray,
        preference: Optional[float] = None
    ) -> ClusteringResult:
        """
        Run Affinity Propagation clustering.

        Args:
            data: 2D array of features (mean, variance)
            preference: Preference parameter (default: median similarity)

        Returns:
            ClusteringResult object
        """
        logger.info(f"Running Affinity Propagation (preference={preference})")

        clusterer = AffinityPropagation(
            preference=preference,
            random_state=42,
            max_iter=500
        )

        try:
            labels = clusterer.fit_predict(data)
        except Exception as e:
            logger.error(f"Affinity Propagation failed: {e}")
            return ClusteringResult(
                algorithm_name='Affinity Propagation',
                labels=np.zeros(len(data), dtype=int),
                n_clusters=0,
                n_noise=0,
                silhouette=None,
                additional_info={'error': str(e)}
            )

        n_clusters = len(clusterer.cluster_centers_indices_)
        n_noise = 0

        silhouette = None
        if n_clusters > 1:
            try:
                silhouette = silhouette_score(data, labels)
            except Exception as e:
                logger.warning(f"Failed to calculate silhouette score for Affinity Propagation: {e}")

        logger.info(f"Affinity Propagation found {n_clusters} clusters, silhouette={silhouette}")

        return ClusteringResult(
            algorithm_name='Affinity Propagation',
            labels=labels,
            n_clusters=n_clusters,
            n_noise=n_noise,
            silhouette=silhouette,
            additional_info={
                'n_iter': clusterer.n_iter_,
                'exemplar_indices': clusterer.cluster_centers_indices_.tolist()
            }
        )

    @staticmethod
    def run_mean_shift(
        data: np.ndarray,
        bandwidth: Optional[float] = None
    ) -> ClusteringResult:
        """
        Run Mean Shift clustering.

        Args:
            data: 2D array of features (mean, variance)
            bandwidth: Bandwidth parameter (default: auto-estimate)

        Returns:
            ClusteringResult object
        """
        if bandwidth is None:
            bandwidth = estimate_bandwidth(data, quantile=0.3, n_samples=min(500, len(data)))
            logger.info(f"Estimated bandwidth: {bandwidth}")

        logger.info(f"Running Mean Shift (bandwidth={bandwidth})")

        clusterer = MeanShift(bandwidth=bandwidth, bin_seeding=True)

        try:
            labels = clusterer.fit_predict(data)
        except Exception as e:
            logger.error(f"Mean Shift failed: {e}")
            return ClusteringResult(
                algorithm_name='Mean Shift',
                labels=np.zeros(len(data), dtype=int),
                n_clusters=0,
                n_noise=0,
                silhouette=None,
                additional_info={'error': str(e)}
            )

        n_clusters = len(clusterer.cluster_centers_)
        n_noise = 0

        silhouette = None
        if n_clusters > 1:
            try:
                silhouette = silhouette_score(data, labels)
            except Exception as e:
                logger.warning(f"Failed to calculate silhouette score for Mean Shift: {e}")

        logger.info(f"Mean Shift found {n_clusters} clusters, silhouette={silhouette}")

        return ClusteringResult(
            algorithm_name='Mean Shift',
            labels=labels,
            n_clusters=n_clusters,
            n_noise=n_noise,
            silhouette=silhouette,
            additional_info={
                'bandwidth': bandwidth,
                'n_cluster_centers': len(clusterer.cluster_centers_)
            }
        )


@dataclass
class ClusterEvaluationMetrics:
    """Detailed evaluation metrics for clustering results."""
    algorithm_name: str
    n_clusters: int
    n_noise: int
    silhouette_score: Optional[float]
    cluster_sizes: Dict[int, int]
    largest_cluster_size: int
    smallest_cluster_size: int
    avg_cluster_size: float
    matches_expected: bool


class ClusteringComparison:
    """Orchestrates comparison of multiple clustering algorithms."""

    def __init__(self, expected_clusters: int = 3):
        """
        Initialize ClusteringComparison.

        Args:
            expected_clusters: Expected number of clusters (default: 3 for RUBIS)
        """
        self.expected_clusters = expected_clusters
        self.results = []

    def run_all_algorithms(
        self,
        data: np.ndarray,
        hdbscan_params: Optional[Dict] = None,
        gmm_params: Optional[Dict] = None,
        ap_params: Optional[Dict] = None,
        ms_params: Optional[Dict] = None
    ) -> List[ClusteringResult]:
        """
        Run all four clustering algorithms on the same dataset.

        Args:
            data: 2D numpy array of features
            hdbscan_params: Parameters for HDBSCAN (optional)
            gmm_params: Parameters for GMM (optional)
            ap_params: Parameters for Affinity Propagation (optional)
            ms_params: Parameters for Mean Shift (optional)

        Returns:
            List of ClusteringResult objects
        """
        logger.info("="*60)
        logger.info("Running clustering comparison on all algorithms")
        logger.info("="*60)

        self.results = []

        hdbscan_params = hdbscan_params or {'min_samples': 5, 'min_cluster_size': 10}
        gmm_params = gmm_params or {'max_components': 10}
        ap_params = ap_params or {}
        ms_params = ms_params or {}

        algorithms = [
            ('HDBSCAN', ClusteringAlgorithms.run_hdbscan, hdbscan_params),
            ('GMM+BIC', ClusteringAlgorithms.run_gmm_bic, gmm_params),
            ('Affinity Propagation', ClusteringAlgorithms.run_affinity_propagation, ap_params),
            ('Mean Shift', ClusteringAlgorithms.run_mean_shift, ms_params)
        ]

        for name, func, params in algorithms:
            try:
                logger.info(f"\n[{name}] Starting...")
                result = func(data, **params)
                self.results.append(result)
                logger.info(f"[{name}] Completed: {result.n_clusters} clusters, silhouette={result.silhouette}")
            except Exception as e:
                logger.error(f"[{name}] Failed: {e}")
                self.results.append(ClusteringResult(
                    algorithm_name=name,
                    labels=np.zeros(len(data), dtype=int),
                    n_clusters=0,
                    n_noise=0,
                    silhouette=None,
                    additional_info={'error': str(e)}
                ))

        logger.info("\nAll algorithms completed")
        return self.results

    def evaluate_results(self) -> List[ClusterEvaluationMetrics]:
        """
        Calculate detailed evaluation metrics for all clustering results.

        Returns:
            List of ClusterEvaluationMetrics objects
        """
        evaluations = []

        for result in self.results:
            cluster_sizes = self._calculate_cluster_sizes(result.labels)

            valid_cluster_sizes = [size for cluster_id, size in cluster_sizes.items() if cluster_id != -1]

            if valid_cluster_sizes:
                largest = max(valid_cluster_sizes)
                smallest = min(valid_cluster_sizes)
                avg = np.mean(valid_cluster_sizes)
            else:
                largest = smallest = avg = 0

            metrics = ClusterEvaluationMetrics(
                algorithm_name=result.algorithm_name,
                n_clusters=result.n_clusters,
                n_noise=result.n_noise,
                silhouette_score=result.silhouette,
                cluster_sizes=cluster_sizes,
                largest_cluster_size=largest,
                smallest_cluster_size=smallest,
                avg_cluster_size=avg,
                matches_expected=(result.n_clusters == self.expected_clusters)
            )

            evaluations.append(metrics)

        return evaluations

    def _calculate_cluster_sizes(self, labels: np.ndarray) -> Dict[int, int]:
        """
        Calculate size of each cluster.

        Args:
            labels: Cluster labels

        Returns:
            Dictionary mapping cluster_id to size
        """
        unique_labels, counts = np.unique(labels, return_counts=True)
        return dict(zip(unique_labels.tolist(), counts.tolist()))

    def print_comparison_table(self):
        """Print formatted comparison table of all clustering results."""
        print("\n" + "="*80)
        print("CLUSTERING COMPARISON SUMMARY")
        print("="*80)

        print(f"\n{'Algorithm':<25} {'Clusters':<10} {'Noise':<10} {'Silhouette':<12} {'Match {self.expected_clusters}?':<10}")
        print("-"*80)

        for result in self.results:
            match = '✓' if result.n_clusters == self.expected_clusters else '✗'
            sil_str = f"{result.silhouette:.4f}" if result.silhouette is not None else "N/A"
            print(f"{result.algorithm_name:<25} {result.n_clusters:<10} {result.n_noise:<10} {sil_str:<12} {match:<10}")

        algorithms_found = sum(1 for r in self.results if r.n_clusters == self.expected_clusters)
        print(f"\n✓ Algorithms that found {self.expected_clusters} clusters: {algorithms_found}/{len(self.results)}")

        if algorithms_found > 0:
            print(f"\n✓ SUCCESS: {algorithms_found} algorithm(s) identified {self.expected_clusters} clusters!")
        else:
            print(f"\n⚠ WARNING: No algorithm found exactly {self.expected_clusters} clusters.")

    def print_detailed_metrics(self):
        """Print detailed evaluation metrics for each algorithm."""
        evaluations = self.evaluate_results()

        print("\n" + "="*80)
        print("DETAILED EVALUATION METRICS")
        print("="*80)

        for eval_metrics in evaluations:
            print(f"\n{eval_metrics.algorithm_name}")
            print("-"*80)
            print(f"  Number of clusters: {eval_metrics.n_clusters}")
            print(f"  Noise points: {eval_metrics.n_noise}")
            print(f"  Silhouette score: {eval_metrics.silhouette_score:.4f}" if eval_metrics.silhouette_score else "  Silhouette score: N/A")
            print(f"  Matches expected ({self.expected_clusters}): {'✓ Yes' if eval_metrics.matches_expected else '✗ No'}")

            if eval_metrics.n_clusters > 0:
                print(f"\n  Cluster size statistics:")
                print(f"    Largest cluster: {eval_metrics.largest_cluster_size}")
                print(f"    Smallest cluster: {eval_metrics.smallest_cluster_size}")
                print(f"    Average cluster size: {eval_metrics.avg_cluster_size:.1f}")

                print(f"\n  Cluster size distribution:")
                valid_clusters = {k: v for k, v in eval_metrics.cluster_sizes.items() if k != -1}
                for cluster_id in sorted(valid_clusters.keys()):
                    size = valid_clusters[cluster_id]
                    print(f"    Cluster {cluster_id}: {size} samples")

    def get_best_algorithm(self) -> Optional[ClusteringResult]:
        """
        Identify the best clustering algorithm based on silhouette score.

        Returns:
            ClusteringResult with highest silhouette score, or None if all failed
        """
        valid_results = [r for r in self.results if r.silhouette is not None and r.n_clusters > 1]

        if not valid_results:
            return None

        return max(valid_results, key=lambda r: r.silhouette)


class ResultVisualizer:
    """Visualizes clustering results and distribution parameters."""

    def __init__(self, output_dir: Path = Path('clustering_results')):
        """
        Initialize ResultVisualizer.

        Args:
            output_dir: Directory to save visualization outputs
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)

    def visualize_parameter_space(
        self,
        data: np.ndarray,
        results: List[ClusteringResult],
        distributions: List[DistributionParameters],
        save: bool = True
    ) -> Optional[Path]:
        """
        Create scatter plots of clustering results in parameter space.

        Args:
            data: 2D array of (mean, variance) features
            results: List of ClusteringResult objects
            distributions: Original distribution parameters for reference
            save: Whether to save the figure

        Returns:
            Path to saved figure if save=True, otherwise None
        """
        n_algorithms = len(results)
        fig, axes = plt.subplots(1, n_algorithms, figsize=(6 * n_algorithms, 5))

        if n_algorithms == 1:
            axes = [axes]

        for idx, result in enumerate(results):
            ax = axes[idx]

            noise_mask = result.labels == -1
            valid_mask = ~noise_mask

            if np.any(valid_mask):
                scatter = ax.scatter(
                    data[valid_mask, 0],
                    data[valid_mask, 1],
                    c=result.labels[valid_mask],
                    cmap='viridis',
                    alpha=0.6,
                    s=20,
                    edgecolors='k',
                    linewidths=0.5
                )
                plt.colorbar(scatter, ax=ax, label='Cluster ID')

            if np.any(noise_mask):
                ax.scatter(
                    data[noise_mask, 0],
                    data[noise_mask, 1],
                    c='gray',
                    marker='x',
                    alpha=0.4,
                    s=30,
                    label='Noise'
                )
                ax.legend()

            sil_str = f", Silhouette={result.silhouette:.4f}" if result.silhouette else ""
            ax.set_title(f"{result.algorithm_name}\n({result.n_clusters} clusters{sil_str})")
            ax.set_xlabel('Mean (μ)')
            ax.set_ylabel('Variance (σ²)')
            ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save:
            output_path = self.output_dir / 'clustering_parameter_space.png'
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved parameter space visualization to {output_path}")
            plt.close()
            return output_path
        else:
            plt.show()
            return None

    def visualize_distributions(
        self,
        data: np.ndarray,
        result: ClusteringResult,
        save: bool = True
    ) -> Optional[Path]:
        """
        Visualize recovered Gaussian distributions for each cluster.

        Args:
            data: 2D array of (mean, variance) features
            result: ClusteringResult to visualize
            save: Whether to save the figure

        Returns:
            Path to saved figure if save=True, otherwise None
        """
        unique_labels = [label for label in np.unique(result.labels) if label != -1]

        if not unique_labels:
            logger.warning("No valid clusters to visualize distributions")
            return None

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        colors = plt.cm.viridis(np.linspace(0, 1, len(unique_labels)))

        for cluster_id, color in zip(unique_labels, colors):
            cluster_mask = result.labels == cluster_id
            cluster_points = data[cluster_mask]

            centroid_mean = np.mean(cluster_points[:, 0])
            centroid_variance = np.mean(cluster_points[:, 1])
            cluster_size = np.sum(cluster_mask)

            std_dev = np.sqrt(centroid_variance)
            x_range = np.linspace(
                max(0, centroid_mean - 4 * std_dev),
                centroid_mean + 4 * std_dev,
                1000
            )
            y_values = norm.pdf(x_range, loc=centroid_mean, scale=std_dev)

            ax1.plot(
                x_range,
                y_values,
                color=color,
                linewidth=2,
                label=f"Cluster {cluster_id}: μ={centroid_mean:.4f}, σ²={centroid_variance:.6f} (n={cluster_size})"
            )

            ax2.scatter(
                cluster_points[:, 0],
                cluster_points[:, 1],
                c=[color],
                alpha=0.6,
                s=20,
                edgecolors='k',
                linewidths=0.5,
                label=f"Cluster {cluster_id} (n={cluster_size})"
            )
            ax2.scatter(
                centroid_mean,
                centroid_variance,
                c=[color],
                marker='*',
                s=300,
                edgecolors='black',
                linewidths=2
            )

        ax1.set_title(f"Recovered Gaussian Distributions\n{result.algorithm_name}")
        ax1.set_xlabel('Response Time')
        ax1.set_ylabel('Probability Density')
        ax1.legend(fontsize=8)
        ax1.grid(True, alpha=0.3)

        ax2.set_title(f"Cluster Centroids in Parameter Space\n{result.algorithm_name}")
        ax2.set_xlabel('Mean (μ)')
        ax2.set_ylabel('Variance (σ²)')
        ax2.legend(fontsize=8)
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        if save:
            safe_name = result.algorithm_name.replace('+', '_').replace(' ', '_').lower()
            output_path = self.output_dir / f'distributions_{safe_name}.png'
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved distribution visualization to {output_path}")
            plt.close()
            return output_path
        else:
            plt.show()
            return None


class StatisticalReporter:
    """Generates statistical reports for clustering analysis."""

    def __init__(self, output_dir: Path = Path('clustering_results')):
        """
        Initialize StatisticalReporter.

        Args:
            output_dir: Directory to save report outputs
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)

    def generate_report(
        self,
        distributions: List[DistributionParameters],
        stats: Dict[str, int],
        comparison: ClusteringComparison,
        data: np.ndarray,
        save: bool = True
    ) -> Optional[Path]:
        """
        Generate comprehensive statistical report.

        Args:
            distributions: List of extracted distribution parameters
            stats: Statistics from data processing
            comparison: ClusteringComparison object with results
            data: 2D array of (mean, variance) features
            save: Whether to save report to file

        Returns:
            Path to saved report if save=True, otherwise None
        """
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("RUBIS TRACE CLUSTERING ANALYSIS - STATISTICAL REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")

        report_lines.append("=" * 80)
        report_lines.append("1. DATA PROCESSING SUMMARY")
        report_lines.append("=" * 80)
        report_lines.append(f"Total trace files found: {stats['total_files']}")
        report_lines.append(f"Successfully processed: {stats['processed_files']}")
        report_lines.append(f"Failed to process: {stats['failed_files']}")
        report_lines.append(f"Total distributions extracted: {stats['total_distributions']}")
        report_lines.append(f"Average distributions per file: {stats['distributions_per_file']:.2f}")
        report_lines.append("")

        means = [d.mean for d in distributions]
        variances = [d.variance for d in distributions]

        report_lines.append("Distribution Parameters Statistics:")
        report_lines.append(f"  Mean range: [{min(means):.6f}, {max(means):.6f}]")
        report_lines.append(f"  Mean average: {np.mean(means):.6f}")
        report_lines.append(f"  Mean std dev: {np.std(means):.6f}")
        report_lines.append(f"  Variance range: [{min(variances):.6f}, {max(variances):.6f}]")
        report_lines.append(f"  Variance average: {np.mean(variances):.6f}")
        report_lines.append(f"  Variance std dev: {np.std(variances):.6f}")
        report_lines.append("")

        norm_counts = {}
        for d in distributions:
            norm_counts[d.norm_label] = norm_counts.get(d.norm_label, 0) + 1

        report_lines.append("Distributions by norm label:")
        for norm_label, count in sorted(norm_counts.items()):
            report_lines.append(f"  {norm_label}: {count} ({100*count/len(distributions):.1f}%)")
        report_lines.append("")

        report_lines.append("=" * 80)
        report_lines.append("2. CLUSTERING ALGORITHM COMPARISON")
        report_lines.append("=" * 80)
        report_lines.append("")
        report_lines.append(f"{'Algorithm':<25} {'Clusters':<10} {'Noise':<10} {'Silhouette':<12} {'Match 3?':<10}")
        report_lines.append("-" * 80)

        for result in comparison.results:
            match = '✓' if result.n_clusters == comparison.expected_clusters else '✗'
            sil_str = f"{result.silhouette:.4f}" if result.silhouette is not None else "N/A"
            report_lines.append(f"{result.algorithm_name:<25} {result.n_clusters:<10} {result.n_noise:<10} {sil_str:<12} {match:<10}")

        algorithms_found = sum(1 for r in comparison.results if r.n_clusters == comparison.expected_clusters)
        report_lines.append("")
        report_lines.append(f"Algorithms that found {comparison.expected_clusters} clusters: {algorithms_found}/{len(comparison.results)}")
        report_lines.append("")

        report_lines.append("=" * 80)
        report_lines.append("3. DETAILED CLUSTER ANALYSIS")
        report_lines.append("=" * 80)

        evaluations = comparison.evaluate_results()

        for eval_metrics in evaluations:
            report_lines.append("")
            report_lines.append(f"Algorithm: {eval_metrics.algorithm_name}")
            report_lines.append("-" * 80)
            report_lines.append(f"  Number of clusters: {eval_metrics.n_clusters}")
            report_lines.append(f"  Noise points: {eval_metrics.n_noise}")
            sil_str = f"{eval_metrics.silhouette_score:.4f}" if eval_metrics.silhouette_score else "N/A"
            report_lines.append(f"  Silhouette score: {sil_str}")
            report_lines.append(f"  Matches expected ({comparison.expected_clusters}): {'✓ Yes' if eval_metrics.matches_expected else '✗ No'}")

            if eval_metrics.n_clusters > 0:
                report_lines.append("")
                report_lines.append("  Cluster size statistics:")
                report_lines.append(f"    Largest cluster: {eval_metrics.largest_cluster_size}")
                report_lines.append(f"    Smallest cluster: {eval_metrics.smallest_cluster_size}")
                report_lines.append(f"    Average cluster size: {eval_metrics.avg_cluster_size:.1f}")

                report_lines.append("")
                report_lines.append("  Cluster size distribution:")
                valid_clusters = {k: v for k, v in eval_metrics.cluster_sizes.items() if k != -1}
                for cluster_id in sorted(valid_clusters.keys()):
                    size = valid_clusters[cluster_id]
                    percentage = 100 * size / stats['total_distributions']
                    report_lines.append(f"    Cluster {cluster_id}: {size} samples ({percentage:.1f}%)")

        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("4. CLUSTER CENTROIDS AND PARAMETERS")
        report_lines.append("=" * 80)

        for result in comparison.results:
            report_lines.append("")
            report_lines.append(f"Algorithm: {result.algorithm_name}")
            report_lines.append("-" * 80)

            unique_labels = [label for label in np.unique(result.labels) if label != -1]

            if unique_labels:
                for cluster_id in sorted(unique_labels):
                    cluster_mask = result.labels == cluster_id
                    cluster_points = data[cluster_mask]

                    centroid_mean = np.mean(cluster_points[:, 0])
                    centroid_variance = np.mean(cluster_points[:, 1])
                    std_mean = np.std(cluster_points[:, 0])
                    std_variance = np.std(cluster_points[:, 1])
                    cluster_size = np.sum(cluster_mask)

                    report_lines.append(f"  Cluster {cluster_id} (n={cluster_size}):")
                    report_lines.append(f"    Centroid: μ={centroid_mean:.6f}, σ²={centroid_variance:.8f}")
                    report_lines.append(f"    Std dev:  μ_std={std_mean:.6f}, σ²_std={std_variance:.8f}")
            else:
                report_lines.append("  No valid clusters found")

        best = comparison.get_best_algorithm()
        if best:
            report_lines.append("")
            report_lines.append("=" * 80)
            report_lines.append("5. BEST ALGORITHM RECOMMENDATION")
            report_lines.append("=" * 80)
            report_lines.append(f"Algorithm: {best.algorithm_name}")
            report_lines.append(f"  Clusters identified: {best.n_clusters}")
            report_lines.append(f"  Silhouette score: {best.silhouette:.4f}")
            report_lines.append(f"  Noise points: {best.n_noise}")
            report_lines.append("")
            report_lines.append("Recommendation rationale:")
            report_lines.append(f"  - Highest silhouette score among all algorithms")
            report_lines.append(f"  - Silhouette interpretation: {self._interpret_silhouette(best.silhouette)}")

        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 80)

        report_text = "\n".join(report_lines)

        if save:
            output_path = self.output_dir / 'clustering_analysis_report.txt'
            output_path.write_text(report_text)
            logger.info(f"Saved statistical report to {output_path}")
            return output_path
        else:
            print(report_text)
            return None

    def _interpret_silhouette(self, score: float) -> str:
        """Interpret silhouette score."""
        if score >= 0.71:
            return "Excellent - Strong structure, well-separated clusters"
        elif score >= 0.51:
            return "Good - Reasonable structure, distinguishable clusters"
        elif score >= 0.26:
            return "Fair - Weak structure, overlapping clusters"
        else:
            return "Poor - No substantial structure"


def process_all_traces(
    trace_dir: Path,
    min_data_points: int = 10
) -> Tuple[List[DistributionParameters], Dict[str, int]]:
    """
    Process all trace files in a directory.

    Args:
        trace_dir: Directory containing trace files
        min_data_points: Minimum data points required per segment

    Returns:
        Tuple of (list of DistributionParameters, statistics dict)
    """
    parser = TraceFileParser(min_data_points=min_data_points)
    fitter = GaussianFitter()

    trace_files = sorted(trace_dir.glob('eval_ident_trace-*.txt'))

    if not trace_files:
        logger.error(f"No trace files found in {trace_dir}")
        return [], {}

    logger.info(f"Found {len(trace_files)} trace files in {trace_dir}")

    all_distributions = []
    skipped_segments = 0
    processed_files = 0

    for filepath in trace_files:
        try:
            distributions = fitter.fit_trace_file(filepath, parser)
            all_distributions.extend(distributions)
            processed_files += 1
        except Exception as e:
            logger.error(f"Failed to process {filepath.name}: {e}")
            continue

    stats = {
        'total_files': len(trace_files),
        'processed_files': processed_files,
        'failed_files': len(trace_files) - processed_files,
        'total_distributions': len(all_distributions),
        'distributions_per_file': len(all_distributions) / processed_files if processed_files > 0 else 0
    }

    logger.info(f"Processed {processed_files}/{len(trace_files)} files, "
               f"extracted {len(all_distributions)} distributions")

    return all_distributions, stats


if __name__ == '__main__':
    trace_dir = Path('rubis_evaluation_data/eval_ident_traces')

    logger.info("Starting RUBIS trace analysis")
    logger.info("Phase 1: Data Parsing and Distribution Fitting")

    distributions, stats = process_all_traces(trace_dir, min_data_points=10)

    print("\n" + "="*60)
    print("PHASE 1: DATA PARSING AND DISTRIBUTION FITTING")
    print("="*60)
    print(f"Total trace files: {stats['total_files']}")
    print(f"Successfully processed: {stats['processed_files']}")
    print(f"Failed to process: {stats['failed_files']}")
    print(f"Total distributions extracted: {stats['total_distributions']}")
    print(f"Average distributions per file: {stats['distributions_per_file']:.2f}")

    if distributions:
        means = [d.mean for d in distributions]
        variances = [d.variance for d in distributions]

        print(f"\nDistribution Parameters:")
        print(f"  Mean range: [{min(means):.6f}, {max(means):.6f}]")
        print(f"  Mean average: {np.mean(means):.6f}")
        print(f"  Variance range: [{min(variances):.6f}, {max(variances):.6f}]")
        print(f"  Variance average: {np.mean(variances):.6f}")

        norm_counts = {}
        for d in distributions:
            norm_counts[d.norm_label] = norm_counts.get(d.norm_label, 0) + 1

        print(f"\nDistributions by norm label:")
        for norm_label, count in sorted(norm_counts.items()):
            print(f"  {norm_label}: {count}")

    if not distributions:
        print("\nNo distributions extracted. Exiting.")
    else:
        print("\n" + "="*80)
        print("PHASE 2 & 3: CLUSTERING AND EVALUATION")
        print("="*80)

        logger.info("Phase 2: Running clustering algorithms")
        logger.info("Phase 3: Evaluating and comparing results")

        data = ClusteringAlgorithms.prepare_data(distributions)
        print(f"\nPrepared data matrix: {data.shape}")

        comparison = ClusteringComparison(expected_clusters=3)

        print("\nRunning all clustering algorithms...")
        results = comparison.run_all_algorithms(data)

        comparison.print_comparison_table()
        comparison.print_detailed_metrics()

        best = comparison.get_best_algorithm()
        if best:
            print(f"\n" + "="*80)
            print(f"BEST ALGORITHM: {best.algorithm_name}")
            print("="*80)
            print(f"  Clusters: {best.n_clusters}")
            print(f"  Silhouette Score: {best.silhouette:.4f}")
            print(f"  Noise Points: {best.n_noise}")

        print("\n" + "="*80)
        print("PHASE 4: VISUALIZATION AND REPORTING")
        print("="*80)

        logger.info("Phase 4: Generating visualizations and reports")

        visualizer = ResultVisualizer(output_dir=Path('clustering_results'))
        reporter = StatisticalReporter(output_dir=Path('clustering_results'))

        print("\nGenerating parameter space visualization...")
        param_space_path = visualizer.visualize_parameter_space(
            data=data,
            results=results,
            distributions=distributions,
            save=True
        )
        print(f"✓ Parameter space visualization saved: {param_space_path}")

        print("\nGenerating distribution visualizations for best algorithms...")
        for result in results:
            if result.silhouette and result.silhouette > 0.7:
                dist_path = visualizer.visualize_distributions(
                    data=data,
                    result=result,
                    save=True
                )
                print(f"✓ Distribution visualization saved: {dist_path}")

        print("\nGenerating statistical report...")
        report_path = reporter.generate_report(
            distributions=distributions,
            stats=stats,
            comparison=comparison,
            data=data,
            save=True
        )
        print(f"✓ Statistical report saved: {report_path}")

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print("\nAll outputs saved to: clustering_results/")
    print("  - clustering_parameter_space.png")
    print("  - distributions_<algorithm>.png (for best algorithms)")
    print("  - clustering_analysis_report.txt")
