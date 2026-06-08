"""
Test clustering algorithms on synthetic data

This script generates synthetic 2D Gaussian mixture data with 3 known clusters
and tests all four clustering algorithms.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from rubis_trace_clustering import ClusteringAlgorithms, ClusteringResult


def generate_synthetic_data(n_samples_per_cluster=100, random_state=42):
    """
    Generate synthetic 2D data with 3 Gaussian clusters.

    Returns:
        data: 2D array of shape (n_samples, 2)
        true_labels: True cluster labels
    """
    np.random.seed(random_state)

    cluster1 = np.random.multivariate_normal(
        mean=[0.05, 0.00002],
        cov=[[0.0001, 0], [0, 0.000001]],
        size=n_samples_per_cluster
    )

    cluster2 = np.random.multivariate_normal(
        mean=[0.08, 0.00008],
        cov=[[0.0001, 0], [0, 0.000001]],
        size=n_samples_per_cluster
    )

    cluster3 = np.random.multivariate_normal(
        mean=[0.11, 0.00015],
        cov=[[0.0001, 0], [0, 0.000001]],
        size=n_samples_per_cluster
    )

    data = np.vstack([cluster1, cluster2, cluster3])
    true_labels = np.concatenate([
        np.zeros(n_samples_per_cluster),
        np.ones(n_samples_per_cluster),
        np.full(n_samples_per_cluster, 2)
    ])

    return data, true_labels.astype(int)


def print_result_summary(result: ClusteringResult, true_n_clusters: int = 3):
    """Print summary of clustering result."""
    print(f"\n{'='*60}")
    print(f"Algorithm: {result.algorithm_name}")
    print(f"{'='*60}")
    print(f"Number of clusters found: {result.n_clusters}")
    print(f"Expected number of clusters: {true_n_clusters}")
    print(f"Match: {'✓ YES' if result.n_clusters == true_n_clusters else '✗ NO'}")
    print(f"Number of noise points: {result.n_noise}")
    print(f"Silhouette score: {result.silhouette:.4f}" if result.silhouette is not None else "Silhouette score: N/A")

    if result.additional_info:
        print(f"\nAdditional info:")
        for key, value in result.additional_info.items():
            if key != 'bic_scores' and key != 'exemplar_indices':
                print(f"  {key}: {value}")


def visualize_results(data, results, true_labels, output_dir='clustering_test_results'):
    """
    Visualize clustering results.

    Args:
        data: 2D data array
        results: List of ClusteringResult objects
        true_labels: True cluster labels
        output_dir: Directory to save plots
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    n_algorithms = len(results) + 1
    fig, axes = plt.subplots(1, n_algorithms, figsize=(5 * n_algorithms, 4))

    axes[0].scatter(data[:, 0], data[:, 1], c=true_labels, cmap='viridis', alpha=0.6)
    axes[0].set_title('True Labels (3 clusters)')
    axes[0].set_xlabel('Mean')
    axes[0].set_ylabel('Variance')

    for idx, result in enumerate(results):
        ax = axes[idx + 1]

        noise_mask = result.labels == -1
        valid_mask = ~noise_mask

        if np.any(valid_mask):
            ax.scatter(
                data[valid_mask, 0],
                data[valid_mask, 1],
                c=result.labels[valid_mask],
                cmap='viridis',
                alpha=0.6,
                label='Clustered'
            )

        if np.any(noise_mask):
            ax.scatter(
                data[noise_mask, 0],
                data[noise_mask, 1],
                c='gray',
                marker='x',
                alpha=0.3,
                label='Noise'
            )

        ax.set_title(f"{result.algorithm_name}\n({result.n_clusters} clusters)")
        ax.set_xlabel('Mean')
        ax.set_ylabel('Variance')
        if np.any(noise_mask):
            ax.legend()

    plt.tight_layout()
    output_file = output_path / 'synthetic_clustering_comparison.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\nVisualization saved to: {output_file}")
    plt.close()


def main():
    """Main test function."""
    print("="*60)
    print("Testing Clustering Algorithms on Synthetic Data")
    print("="*60)

    print("\nGenerating synthetic data (3 Gaussian clusters, 100 samples each)...")
    data, true_labels = generate_synthetic_data(n_samples_per_cluster=100)
    print(f"Data shape: {data.shape}")
    print(f"Feature ranges:")
    print(f"  Mean: [{data[:, 0].min():.6f}, {data[:, 0].max():.6f}]")
    print(f"  Variance: [{data[:, 1].min():.8f}, {data[:, 1].max():.8f}]")

    results = []

    print("\n" + "="*60)
    print("Running Clustering Algorithms")
    print("="*60)

    print("\n[1/4] Testing HDBSCAN...")
    result_hdbscan = ClusteringAlgorithms.run_hdbscan(data, min_samples=5, min_cluster_size=5)
    results.append(result_hdbscan)
    print_result_summary(result_hdbscan)

    print("\n[2/4] Testing GMM with BIC...")
    result_gmm = ClusteringAlgorithms.run_gmm_bic(data, max_components=10)
    results.append(result_gmm)
    print_result_summary(result_gmm)

    print("\n[3/4] Testing Affinity Propagation...")
    result_ap = ClusteringAlgorithms.run_affinity_propagation(data)
    results.append(result_ap)
    print_result_summary(result_ap)

    print("\n[4/4] Testing Mean Shift...")
    result_ms = ClusteringAlgorithms.run_mean_shift(data)
    results.append(result_ms)
    print_result_summary(result_ms)

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"\n{'Algorithm':<25} {'Clusters':<10} {'Match?':<10} {'Silhouette':<12}")
    print("-"*60)
    for result in results:
        match = '✓' if result.n_clusters == 3 else '✗'
        sil_str = f"{result.silhouette:.4f}" if result.silhouette is not None else "N/A"
        print(f"{result.algorithm_name:<25} {result.n_clusters:<10} {match:<10} {sil_str:<12}")

    algorithms_found_3 = sum(1 for r in results if r.n_clusters == 3)
    print(f"\nAlgorithms that found 3 clusters: {algorithms_found_3}/{len(results)}")

    print("\nGenerating visualization...")
    visualize_results(data, results, true_labels)

    print("\n" + "="*60)
    print("Test completed successfully!")
    print("="*60)


if __name__ == '__main__':
    main()
