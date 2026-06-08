#!/usr/bin/env python3
"""
WaDi Dataset Clustering Script

Performs state-aware clustering on WaDi sensor data to learn
operational state-specific Gaussian distributions.

Usage:
    python cluster_wadi.py --config configs/wadi_cluster_config.yaml
"""

import argparse
import logging
import sys
from pathlib import Path
import yaml
import pandas as pd

from cluster_analysis.adapters.wadi.wadi_adapter import WadiAdapter
from anomaly_detection.state.environment_detector import EnvironmentStateDetector
from cluster_analysis.state_aware_clusterer import StateAwareClusterer, DistributionValidator


logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Configure logging output.

    Args:
        verbose: Whether to output detailed logs
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='[%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def load_config(config_path: str) -> dict:
    """Load clustering configuration from YAML file.

    Args:
        config_path: Path to configuration YAML

    Returns:
        dict: Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    return config


def run_wadi_clustering(config_path: str, verbose: bool = False) -> bool:
    """Execute WaDi state-aware clustering workflow.

    Args:
        config_path: Path to clustering configuration YAML
        verbose: Whether to output detailed logs

    Returns:
        bool: True if clustering succeeded
    """
    setup_logging(verbose)

    try:
        # 1. Load configuration
        logger.info(f"Loading configuration: {config_path}")
        config = load_config(config_path)

        dataset_config = config['dataset']
        adapter_config = config.get('adapter', {})
        clustering_config = config.get('clustering', {})
        env_config = config.get('environment_detection', {})
        output_config = config.get('output', {})
        validation_config = config.get('validation', {})

        # 2. Initialize WaDi adapter
        logger.info("Initializing WaDi adapter...")
        adapter = WadiAdapter(
            manual_include=adapter_config.get('manual_include', []),
            manual_exclude=adapter_config.get('manual_exclude', [])
        )

        # 3. Load identity data
        identity_path = dataset_config['identity_data_path']
        logger.info(f"Loading identity data from: {identity_path}")

        df = adapter.load_identity_data(identity_path)
        logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")

        # 4. Rank and select metrics
        logger.info("Ranking metrics...")
        ranked_metrics = adapter.rank_metrics()

        top_n = adapter_config.get('top_k', 3)
        selected_metrics = [m['metric'] for m in ranked_metrics[:top_n]]

        logger.info(f"Selected top {top_n} metrics for clustering:")
        for i, metric_info in enumerate(ranked_metrics[:top_n], 1):
            logger.info(
                f"  {i}. {metric_info['metric']}: "
                f"quality={metric_info['quality']:.3f}, "
                f"CV={metric_info['cv']:.3f}, "
                f"score={metric_info['score']:.3f}"
            )

        # 5. Detect operational states
        logger.info("Detecting operational states...")
        pump_columns = env_config['pump_columns']
        num_states = env_config.get('num_states', 3)
        fallback_metric = env_config.get('fallback_metric')
        fallback_threshold = env_config.get('fallback_threshold', 0.2)

        state_detector = EnvironmentStateDetector(
            pump_columns=pump_columns,
            num_states=num_states,
            auto_detect_states=env_config.get('auto_detect_states', False),
            max_states=env_config.get('max_states', 5),
            fallback_metric=fallback_metric,
            fallback_threshold=fallback_threshold
        )

        state_labels = state_detector.detect_states(df)
        logger.info(f"Detected {len(set(state_labels))} operational states")

        # 6. Validate states (optional)
        env_validation = env_config.get('validation', {})
        if env_validation.get('check_ordering', True):
            logger.info("Validating state detection...")
            validation_metric = selected_metrics[0]  # Use top metric for validation
            min_separation = env_validation.get('min_separation', 0.3)

            is_valid = state_detector.validate_states(
                df, state_labels, validation_metric, min_separation=min_separation
            )

            if not is_valid:
                logger.warning("State validation failed - states may not be well-separated")
                # Continue anyway since distribution separation will be checked later

        # 7. Perform state-aware clustering for each metric
        logger.info("Starting state-aware clustering...")

        min_cluster_size = clustering_config.get('min_cluster_size', 50)
        clusterer = StateAwareClusterer(min_cluster_size=min_cluster_size)

        all_distributions = {}

        for metric in selected_metrics:
            logger.info(f"Clustering metric: {metric}")

            try:
                distributions = clusterer.fit(df, state_labels, metric)
                all_distributions.update(distributions)

                # Log learned distributions
                for state_name, dist in distributions.items():
                    logger.info(
                        f"  {state_name}: μ={dist['mu']:.4f}, σ={dist['sigma']:.4f}, "
                        f"n={dist['sample_count']}, outliers={dist['outlier_ratio']:.1%}"
                    )

            except Exception as e:
                logger.error(f"Failed to cluster {metric}: {e}")

        logger.info(f"Learned {len(all_distributions)} total distributions")

        # 8. Validate distribution separation
        if validation_config.get('check_separation', True):
            logger.info("Validating distribution separation...")

            validator = DistributionValidator()
            min_sigma_separation = validation_config.get('min_sigma_separation', 3.0)

            # Validate separation per metric
            metrics_validated = []
            for metric in selected_metrics:
                # Get distributions for this metric
                metric_base = metric.replace('.PV', '').split('_')[-2].lower()
                metric_dists = {
                    k: v for k, v in all_distributions.items()
                    if k.startswith(f'{metric_base}_state_')
                }

                if len(metric_dists) > 1:
                    is_separated = validator.validate_all_distributions(
                        metric_dists, min_sigma_separation=min_sigma_separation
                    )
                    metrics_validated.append((metric, is_separated))

                    if not is_separated:
                        logger.warning(f"{metric}: States not well-separated")

            # Summary
            separated_count = sum(1 for _, sep in metrics_validated if sep)
            logger.info(
                f"Separation validation: {separated_count}/{len(metrics_validated)} "
                f"metrics have well-separated states (≥{min_sigma_separation}σ)"
            )

        # 9. Save learned distributions
        distributions_path = Path(output_config.get('distributions_path', 'clustering_results/wadi/learned_distributions.yaml'))
        distributions_path.parent.mkdir(parents=True, exist_ok=True)

        clusterer.distributions = all_distributions  # Set all distributions
        clusterer.save_distributions(str(distributions_path))

        logger.info(f"Saved distributions to: {distributions_path}")

        # 10. Save state labels (optional)
        if 'state_labels_path' in output_config:
            state_labels_path = Path(output_config['state_labels_path'])
            state_labels_path.parent.mkdir(parents=True, exist_ok=True)
            state_detector.save_state_labels(df, state_labels, str(state_labels_path))
            logger.info(f"Saved state labels to: {state_labels_path}")

        # 11. Print summary
        print("\n" + "="*60)
        print("WaDi State-Aware Clustering Summary")
        print("="*60)
        print(f"Dataset: {identity_path}")
        print(f"Samples: {len(df)}")
        print(f"Operational states: {len(set(state_labels))}")
        print(f"Metrics clustered: {len(selected_metrics)}")
        print(f"Total distributions: {len(all_distributions)}")
        print(f"Output: {distributions_path}")
        print("="*60)

        return True

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return False
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return False
    except Exception as e:
        logger.error(f"Execution failed: {e}", exc_info=verbose)
        return False


def main():
    """CLI main entry point."""
    parser = argparse.ArgumentParser(
        description='WaDi State-Aware Clustering - Learn operational state distributions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Run clustering with WaDi configuration
  python cluster_wadi.py --config configs/wadi_cluster_config.yaml

  # Enable verbose logging
  python cluster_wadi.py --config configs/wadi_cluster_config.yaml --verbose
        """
    )

    parser.add_argument(
        '--config', '-c',
        required=True,
        help='Path to clustering configuration YAML file'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Execute clustering
    success = run_wadi_clustering(
        config_path=args.config,
        verbose=args.verbose
    )

    # Set exit code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
