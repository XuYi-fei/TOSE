"""
State-aware clustering for multi-modal distributions.

Clusters metrics within each operational state separately to learn
state-specific Gaussian distributions.
"""

import logging
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import yaml

try:
    from hdbscan import HDBSCAN
    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False


logger = logging.getLogger(__name__)


class StateAwareClusterer:
    """
    Cluster metrics within each operational state separately.

    For systems with multiple operational modes (e.g., LOW/MEDIUM/HIGH flow),
    this clusterer learns separate distributions for each state to avoid
    false positives during state transitions.

    Example:
        >>> clusterer = StateAwareClusterer(min_cluster_size=50)
        >>> distributions = clusterer.fit(df, state_labels, 'HMI_2_FIT_001.PV')
        >>> print(distributions.keys())
        dict_keys(['flow_state_0', 'flow_state_1', 'flow_state_2'])
    """

    def __init__(self, min_cluster_size: int = 50):
        """
        Initialize state-aware clusterer.

        Args:
            min_cluster_size: HDBSCAN min_cluster_size parameter (default 50)
        """
        if not HDBSCAN_AVAILABLE:
            raise ImportError(
                "hdbscan is required for clustering. "
                "Install with: pip install hdbscan"
            )

        self.min_cluster_size = min_cluster_size
        self.distributions: Dict[str, dict] = {}

    def fit(
        self,
        df: pd.DataFrame,
        state_labels: np.ndarray,
        metric: str
    ) -> Dict[str, dict]:
        """
        Cluster metric within each state separately.

        Args:
            df: DataFrame with metric column
            state_labels: State labels for each row (from EnvironmentStateDetector)
            metric: Metric column name to cluster

        Returns:
            dict: Distributions keyed by state name
                  {'flow_state_0': {'mu': 0.004, 'sigma': 0.002, ...}, ...}

        Example:
            >>> distributions = clusterer.fit(df, state_labels, 'HMI_2_FIT_001.PV')
            >>> distributions['flow_state_0']['mu']
            0.0037
        """
        if metric not in df.columns:
            raise ValueError(f"Metric '{metric}' not in DataFrame")

        if len(state_labels) != len(df):
            raise ValueError(f"state_labels length {len(state_labels)} != df length {len(df)}")

        # Get metric base name (remove .PV suffix for naming)
        metric_base = metric.replace('.PV', '').split('_')[-2]  # e.g., FIT from HMI_2_FIT_001.PV

        unique_states = sorted(np.unique(state_labels))
        logger.info(f"Clustering {metric} across {len(unique_states)} states")

        for state_id in unique_states:
            # Filter data for this state
            state_mask = (state_labels == state_id)
            state_data = np.array(
                pd.to_numeric(df.loc[state_mask, metric], errors='coerce').dropna().to_numpy(),
                dtype=float,
                copy=True,
            )

            if len(state_data) < self.min_cluster_size:
                logger.warning(
                    f"State {state_id} has only {len(state_data)} samples, "
                    f"skipping (min_cluster_size={self.min_cluster_size})"
                )
                continue

            # HDBSCAN clustering
            try:
                clusterer = HDBSCAN(min_cluster_size=self.min_cluster_size)
                cluster_labels = clusterer.fit_predict(state_data.reshape(-1, 1))

                # Filter outliers (labels = -1)
                clean_mask = (cluster_labels != -1)
                clean_data = state_data[clean_mask]

                outlier_count = (cluster_labels == -1).sum()
                outlier_ratio = outlier_count / len(cluster_labels)
            except Exception as exc:
                logger.warning(
                    f"{metric} state_{state_id}: HDBSCAN failed ({exc}), "
                    "falling back to raw state distribution"
                )
                clean_data = state_data
                outlier_count = 0
                outlier_ratio = 0.0

            if len(clean_data) == 0:
                logger.warning(f"State {state_id}: All points classified as outliers")
                continue

            # Fit Gaussian distribution
            mu = float(clean_data.mean())
            sigma = float(clean_data.std())

            # Store distribution
            state_name = f'{metric_base.lower()}_state_{state_id}'
            self.distributions[state_name] = {
                'metric': metric,
                'state_id': int(state_id),
                'cluster_id': 0,  # Assuming single cluster per state after outlier removal
                'mu': mu,
                'sigma': sigma,
                'sample_count': len(clean_data),
                'outlier_count': int(outlier_count),
                'outlier_ratio': float(outlier_ratio)
            }

            logger.info(
                f"{state_name}: μ={mu:.4f}, σ={sigma:.4f}, "
                f"n={len(clean_data)}, outliers={outlier_ratio:.1%}"
            )

        return self.distributions

    def save_distributions(self, output_path: str):
        """
        Save learned distributions to YAML file.

        Args:
            output_path: Output file path (e.g., 'learned_distributions.yaml')

        Example:
            >>> clusterer.save_distributions('clustering_results/wadi/learned_distributions.yaml')
        """
        output_data = {'distributions': self.distributions}

        with open(output_path, 'w') as f:
            yaml.dump(output_data, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Saved {len(self.distributions)} distributions to {output_path}")

    @classmethod
    def load_distributions(cls, yaml_path: str) -> Dict[str, dict]:
        """
        Load distributions from YAML file.

        Args:
            yaml_path: Path to learned_distributions.yaml

        Returns:
            dict: Loaded distributions

        Example:
            >>> distributions = StateAwareClusterer.load_distributions('learned_distributions.yaml')
            >>> distributions['flow_state_0']['mu']
            0.0037
        """
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        return data.get('distributions', {})


class DistributionValidator:
    """
    Validate that learned distributions are statistically separable.

    Ensures state-specific distributions have sufficient separation for
    effective state-conditional anomaly detection.
    """

    @staticmethod
    def check_separation(
        dist1: dict,
        dist2: dict,
        min_sigma_separation: float = 3.0
    ) -> bool:
        """
        Check if two distributions are well-separated.

        Separation metric: |μ1 - μ2| / pooled_σ

        Args:
            dist1: First distribution {'mu': ..., 'sigma': ...}
            dist2: Second distribution
            min_sigma_separation: Minimum separation in standard deviations (default 3.0)

        Returns:
            bool: True if distributions are well-separated

        Example:
            >>> validator = DistributionValidator()
            >>> is_sep = validator.check_separation(
            ...     {'mu': 0.004, 'sigma': 0.002},
            ...     {'mu': 1.305, 'sigma': 0.152},
            ...     min_sigma_separation=3.0
            ... )
            >>> is_sep
            True  # 12.15σ separation
        """
        mu1, sigma1 = dist1['mu'], dist1['sigma']
        mu2, sigma2 = dist2['mu'], dist2['sigma']

        # Compute separation distance
        distance = abs(mu1 - mu2)

        # Compute pooled sigma
        pooled_sigma = np.sqrt((sigma1**2 + sigma2**2) / 2)

        # Check separation ratio
        separation_ratio = distance / pooled_sigma if pooled_sigma > 0 else 0

        is_separated = separation_ratio >= min_sigma_separation

        if not is_separated:
            logger.warning(
                f"Distributions overlap: {separation_ratio:.2f}σ separation "
                f"(threshold: {min_sigma_separation}σ)"
            )

        return is_separated

    @staticmethod
    def validate_all_distributions(
        distributions: Dict[str, dict],
        min_sigma_separation: float = 3.0
    ) -> bool:
        """
        Validate separation for all distribution pairs.

        Args:
            distributions: All learned distributions
            min_sigma_separation: Minimum separation threshold

        Returns:
            bool: True if all pairs are well-separated

        Example:
            >>> all_valid = DistributionValidator.validate_all_distributions(distributions)
            >>> print(f"All distributions well-separated: {all_valid}")
        """
        dist_list = list(distributions.values())
        all_separated = True

        for i in range(len(dist_list)):
            for j in range(i + 1, len(dist_list)):
                is_sep = DistributionValidator.check_separation(
                    dist_list[i],
                    dist_list[j],
                    min_sigma_separation
                )

                if not is_sep:
                    all_separated = False
                    logger.warning(
                        f"Insufficient separation between "
                        f"{list(distributions.keys())[i]} and {list(distributions.keys())[j]}"
                    )

        if all_separated:
            logger.info(f"✓ All {len(dist_list)} distributions are well-separated (≥{min_sigma_separation}σ)")

        return all_separated
