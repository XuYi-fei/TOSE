"""
State-conditional anomaly detector.

Detects anomalies using state-specific Gaussian distributions learned
during training. Avoids false positives during operational state transitions.
"""

import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats

from cluster_analysis.state_aware_clusterer import StateAwareClusterer


logger = logging.getLogger(__name__)


class StateConditionalDetector:
    """
    Detect anomalies using state-conditional Gaussian distributions.

    For multi-modal systems with distinct operational states, this detector:
    1. Infers current operational state from system context
    2. Selects state-specific distribution for each metric
    3. Computes anomaly score based on Gaussian likelihood

    Example:
        >>> detector = StateConditionalDetector(distributions_path='learned_distributions.yaml')
        >>> state_labels = np.array([0, 0, 1, 1, 2, 2])
        >>> df = pd.DataFrame({'HMI_2_FIT_001.PV': [0.004, 0.005, 1.3, 1.4, 2.4, 2.5]})
        >>> anomalies = detector.detect(df, state_labels, threshold=3.0)
        >>> anomalies['is_anomaly'].sum()
        0  # All values are within 3σ of their state distributions
    """

    def __init__(
        self,
        distributions_path: Optional[str] = None,
        distributions: Optional[Dict[str, dict]] = None,
        mode: str = 'state_conditional',
        cross_state_threshold: float = 2.5
    ):
        """
        Initialize state-conditional detector.

        Args:
            distributions_path: Path to learned_distributions.yaml (optional)
            distributions: Pre-loaded distributions dict (optional)
            mode: Detection mode - 'state_conditional' or 'hybrid'
                  - state_conditional: Only check current state distribution
                  - hybrid: Check current state + all other states (cross-state anomalies)
            cross_state_threshold: Sigma threshold for cross-state checks (hybrid mode)

        Raises:
            ValueError: If neither distributions_path nor distributions provided
        """
        if distributions_path:
            self.distributions = StateAwareClusterer.load_distributions(distributions_path)
        elif distributions:
            self.distributions = distributions
        else:
            raise ValueError("Must provide either distributions_path or distributions")

        self.mode = mode
        self.cross_state_threshold = cross_state_threshold

        # Build metric -> state -> distribution mapping
        self._build_metric_index()

        logger.info(f"Loaded {len(self.distributions)} state-specific distributions")
        logger.info(f"Detection mode: {self.mode}")

    def _build_metric_index(self):
        """Build index: metric -> state_id -> distribution for fast lookup."""
        self.metric_index: Dict[str, Dict[int, dict]] = {}

        for dist_name, dist in self.distributions.items():
            metric = dist['metric']
            state_id = dist['state_id']

            if metric not in self.metric_index:
                self.metric_index[metric] = {}

            self.metric_index[metric][state_id] = dist

        logger.debug(f"Indexed {len(self.metric_index)} metrics across distributions")

    def detect(
        self,
        df: pd.DataFrame,
        state_labels: np.ndarray,
        threshold: float = 3.0,
        metrics: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Detect anomalies using state-conditional distributions.

        Args:
            df: DataFrame with metric columns
            state_labels: Operational state label for each row (from EnvironmentStateDetector)
            threshold: Sigma threshold for anomaly detection (default 3.0)
            metrics: Metrics to check (default: all metrics in distributions)

        Returns:
            pd.DataFrame: Anomaly detection results with columns:
                - Time: Timestamp (if available)
                - state: Operational state label
                - {metric}_value: Raw metric value
                - {metric}_sigma: Sigma deviation from state distribution
                - {metric}_anomaly: Boolean anomaly flag
                - is_anomaly: Overall anomaly flag (any metric anomalous)
                - anomaly_count: Number of anomalous metrics per row

        Example:
            >>> anomalies = detector.detect(df, state_labels, threshold=3.0)
            >>> anomaly_rows = anomalies[anomalies['is_anomaly']]
            >>> print(f"Found {len(anomaly_rows)} anomalous timestamps")
        """
        if len(state_labels) != len(df):
            raise ValueError(f"state_labels length {len(state_labels)} != df length {len(df)}")

        # Determine metrics to check
        if metrics is None:
            metrics = list(self.metric_index.keys())

        # Initialize result DataFrame
        result = pd.DataFrame()

        if 'Time' in df.columns:
            result['Time'] = df['Time']

        result['state'] = state_labels

        # Detect anomalies per metric
        anomaly_flags = []

        for metric in metrics:
            if metric not in self.metric_index:
                logger.warning(f"Metric {metric} not in learned distributions, skipping")
                continue

            if metric not in df.columns:
                logger.warning(f"Metric {metric} not in DataFrame, skipping")
                continue

            # Get metric values
            metric_values = pd.to_numeric(df[metric], errors='coerce').values

            # Compute sigma deviations
            sigma_deviations = self._compute_sigma_deviations(
                metric_values, state_labels, metric
            )

            # Anomaly detection
            is_anomaly = np.abs(sigma_deviations) > threshold

            # Store results
            result[f'{metric}_value'] = metric_values
            result[f'{metric}_sigma'] = sigma_deviations
            result[f'{metric}_anomaly'] = is_anomaly

            anomaly_flags.append(is_anomaly)

        # Overall anomaly: any metric anomalous
        if len(anomaly_flags) > 0:
            result['is_anomaly'] = np.any(anomaly_flags, axis=0)
            result['anomaly_count'] = np.sum(anomaly_flags, axis=0)
        else:
            result['is_anomaly'] = False
            result['anomaly_count'] = 0

        # Log summary
        total_anomalies = result['is_anomaly'].sum()
        anomaly_rate = total_anomalies / len(result) if len(result) > 0 else 0.0

        logger.info(
            f"Detected {total_anomalies}/{len(result)} anomalous samples "
            f"({anomaly_rate:.1%}) using {threshold}σ threshold"
        )

        return result

    def _compute_sigma_deviations(
        self,
        values: np.ndarray,
        state_labels: np.ndarray,
        metric: str
    ) -> np.ndarray:
        """
        Compute sigma deviations from state-specific distributions.

        Args:
            values: Metric values
            state_labels: State labels for each value
            metric: Metric name

        Returns:
            np.ndarray: Sigma deviations (z-scores)
        """
        sigma_deviations = np.full(len(values), np.nan)

        state_distributions = self.metric_index[metric]

        for state_id, dist in state_distributions.items():
            # Find rows in this state
            state_mask = (state_labels == state_id)

            if not np.any(state_mask):
                continue

            # Get state-specific distribution parameters
            mu = dist['mu']
            sigma = dist['sigma']

            if sigma == 0:
                logger.warning(f"{metric} state_{state_id}: sigma=0, using 0.01 as fallback")
                sigma = 0.01

            # Compute z-score: (value - mu) / sigma
            state_values = values[state_mask]
            z_scores = (state_values - mu) / sigma

            sigma_deviations[state_mask] = z_scores

        # Handle hybrid mode: check cross-state anomalies
        if self.mode == 'hybrid':
            sigma_deviations = self._check_cross_state_anomalies(
                values, state_labels, metric, sigma_deviations
            )

        return sigma_deviations

    def _check_cross_state_anomalies(
        self,
        values: np.ndarray,
        state_labels: np.ndarray,
        metric: str,
        state_sigma: np.ndarray
    ) -> np.ndarray:
        """
        Check if values are anomalous across ALL states (hybrid mode).

        A value is only marked non-anomalous if it's within threshold of
        at least one state's distribution (current or other).

        Args:
            values: Metric values
            state_labels: State labels
            metric: Metric name
            state_sigma: Sigma deviations from current state

        Returns:
            np.ndarray: Updated sigma deviations (min across all states)
        """
        state_distributions = self.metric_index[metric]

        for i, (value, current_state) in enumerate(zip(values, state_labels)):
            if np.isnan(value):
                continue

            # Check all state distributions
            min_abs_sigma = abs(state_sigma[i])

            for state_id, dist in state_distributions.items():
                if state_id == current_state:
                    continue  # Already checked

                mu = dist['mu']
                sigma = dist['sigma'] if dist['sigma'] > 0 else 0.01

                cross_sigma = abs((value - mu) / sigma)

                if cross_sigma < min_abs_sigma:
                    min_abs_sigma = cross_sigma

            # If value is within cross_state_threshold of ANY state, reduce severity
            if min_abs_sigma < self.cross_state_threshold:
                # Value is likely from a different operational state (state transition)
                state_sigma[i] = min_abs_sigma if state_sigma[i] >= 0 else -min_abs_sigma

        return state_sigma

    def get_anomaly_scores(
        self,
        df: pd.DataFrame,
        state_labels: np.ndarray,
        metric: str
    ) -> np.ndarray:
        """
        Get anomaly scores (sigma deviations) for a single metric.

        Args:
            df: DataFrame with metric column
            state_labels: State labels
            metric: Metric column name

        Returns:
            np.ndarray: Sigma deviations

        Example:
            >>> scores = detector.get_anomaly_scores(df, state_labels, 'HMI_2_FIT_001.PV')
            >>> max_deviation = np.nanmax(np.abs(scores))
            >>> print(f"Max deviation: {max_deviation:.2f}σ")
        """
        if metric not in df.columns:
            raise ValueError(f"Metric {metric} not in DataFrame")

        if metric not in self.metric_index:
            raise ValueError(f"Metric {metric} not in learned distributions")

        values = pd.to_numeric(df[metric], errors='coerce').values
        return self._compute_sigma_deviations(values, state_labels, metric)

    def get_expected_distribution(
        self,
        metric: str,
        state_id: int
    ) -> Optional[dict]:
        """
        Get expected distribution for a metric in a specific state.

        Args:
            metric: Metric name
            state_id: Operational state ID

        Returns:
            dict: Distribution parameters (mu, sigma, sample_count, ...)
            None: If distribution not found

        Example:
            >>> dist = detector.get_expected_distribution('HMI_2_FIT_001.PV', state_id=1)
            >>> print(f"Expected: μ={dist['mu']:.4f}, σ={dist['sigma']:.4f}")
        """
        if metric not in self.metric_index:
            return None

        return self.metric_index[metric].get(state_id)
