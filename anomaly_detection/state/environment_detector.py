"""
Environment state detection from pump/valve configurations.

Identifies operational states (LOW/MEDIUM/HIGH flow) by clustering
pump status patterns using K-means.
"""

import logging
from typing import List, Optional, Dict
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans


logger = logging.getLogger(__name__)


class EnvironmentStateDetector:
    """
    Detect operational states from pump/valve status patterns.

    Uses K-means clustering on binary status vectors to identify distinct
    operational modes (e.g., LOW/MEDIUM/HIGH flow based on pump combinations).

    Example:
        >>> detector = EnvironmentStateDetector(
        ...     pump_columns=['HMI_2_P_001_STATUS', 'HMI_2_P_002_STATUS'],
        ...     num_states=3
        ... )
        >>> state_labels = detector.detect_states(df)
        >>> print(f"Detected {len(np.unique(state_labels))} states")
    """

    def __init__(
        self,
        pump_columns: List[str],
        num_states: int = 3,
        auto_detect_states: bool = False,
        max_states: int = 5,
        fallback_metric: Optional[str] = None,
        fallback_threshold: float = 0.2
    ):
        """
        Initialize environment state detector.

        Args:
            pump_columns: List of pump status column names
            num_states: Number of operational states (default 3)
            auto_detect_states: Use elbow method to auto-detect K (default False)
            max_states: Max states for auto-detection (default 5)
            fallback_metric: Metric for change point fallback (default None)
            fallback_threshold: Bad input ratio to trigger fallback (default 0.2)
        """
        self.pump_columns = pump_columns
        self.num_states = num_states
        self.auto_detect_states = auto_detect_states
        self.max_states = max_states
        self.fallback_metric = fallback_metric
        self.fallback_threshold = fallback_threshold

        self.detected_state_count: Optional[int] = None
        self.kmeans_model: Optional[KMeans] = None
        self.state_centroids: Optional[np.ndarray] = None

    def detect_states(self, df: pd.DataFrame) -> np.ndarray:
        """
        Detect operational states from pump status.

        Args:
            df: DataFrame with pump status columns

        Returns:
            np.ndarray: State labels (0, 1, 2, ...) for each row

        Example:
            >>> state_labels = detector.detect_states(df)
            >>> state_labels.shape
            (1000,)
            >>> set(state_labels)
            {0, 1, 2}
        """
        missing_pump_columns = [col for col in self.pump_columns if col not in df.columns]
        if missing_pump_columns:
            if self.fallback_metric:
                logger.warning(
                    "Missing pump status columns %s, using metric fallback on %s",
                    missing_pump_columns,
                    self.fallback_metric,
                )
                return self._detect_states_from_metric(df)
            raise ValueError(f"Missing required pump status columns: {missing_pump_columns}")

        # Extract status matrix
        status_matrix = self._extract_status_matrix(df)

        # Check data quality
        bad_input_ratio = self._check_bad_input_ratio(df)

        if bad_input_ratio > self.fallback_threshold and self.fallback_metric:
            logger.warning(
                f"High bad input ratio ({bad_input_ratio:.1%}), "
                f"using metric fallback on {self.fallback_metric}"
            )
            return self._detect_states_from_metric(df)

        # Auto-detect K if configured
        if self.auto_detect_states:
            self.num_states = self._auto_detect_num_states(status_matrix)
            logger.info(f"Auto-detected {self.num_states} operational states")

        # K-means clustering
        kmeans = KMeans(n_clusters=self.num_states, random_state=42, n_init=10)
        state_labels = kmeans.fit_predict(status_matrix)

        # Store model and centroids
        self.kmeans_model = kmeans
        self.state_centroids = kmeans.cluster_centers_
        self.detected_state_count = self.num_states

        # Log state distribution
        self._log_state_distribution(state_labels)

        return state_labels

    def _extract_status_matrix(self, df: pd.DataFrame) -> np.ndarray:
        """
        Extract binary status matrix from pump columns.

        Handles "Bad Input" by forward-filling with last valid state.

        Args:
            df: DataFrame with pump status columns

        Returns:
            np.ndarray: Binary status matrix (n_rows, n_pumps)
        """
        status_data = df[self.pump_columns].copy()

        # Replace "Bad Input" with NaN
        for col in self.pump_columns:
            status_data[col] = status_data[col].replace('Bad Input', np.nan)

        # Forward-fill NaN (assume state persists)
        status_data = status_data.ffill()

        # Backward-fill for any leading NaN
        status_data = status_data.bfill()

        # Convert to numeric
        status_matrix = status_data.astype(float).values

        return status_matrix

    def _check_bad_input_ratio(self, df: pd.DataFrame) -> float:
        """
        Compute ratio of "Bad Input" in pump status columns.

        Args:
            df: DataFrame with pump status columns

        Returns:
            float: Ratio of "Bad Input" values (0.0 to 1.0)
        """
        total_values = len(df) * len(self.pump_columns)
        bad_count = 0

        for col in self.pump_columns:
            bad_count += (df[col] == 'Bad Input').sum()

        return bad_count / total_values if total_values > 0 else 0.0

    def _auto_detect_num_states(self, status_matrix: np.ndarray) -> int:
        """
        Auto-detect optimal number of states using elbow method.

        Args:
            status_matrix: Binary status matrix

        Returns:
            int: Optimal number of states (2 to max_states)
        """
        inertias = []

        for k in range(2, self.max_states + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(status_matrix)
            inertias.append(kmeans.inertia_)

        # Find elbow: where inertia decrease rate drops below 10%
        for i in range(1, len(inertias)):
            decrease_rate = (inertias[i-1] - inertias[i]) / inertias[i-1]

            if decrease_rate < 0.10:
                return i + 1  # k = i + 2 (since range starts at 2)

        # Default to max if no elbow found
        return self.max_states

    def _detect_states_from_metric(self, df: pd.DataFrame) -> np.ndarray:
        """
        Fallback: detect states directly from a metric when pump states are unusable.

        Args:
            df: DataFrame with fallback metric

        Returns:
            np.ndarray: State labels
        """
        if self.fallback_metric not in df.columns:
            raise ValueError(f"Fallback metric '{self.fallback_metric}' not in DataFrame")

        metric_series = pd.to_numeric(df[self.fallback_metric], errors='coerce').ffill().bfill()
        metric_values = metric_series.to_numpy(dtype=float).reshape(-1, 1)

        if len(metric_values) == 0:
            raise ValueError(f"Fallback metric '{self.fallback_metric}' contains no valid samples")

        kmeans = KMeans(n_clusters=self.num_states, random_state=42, n_init=10)
        raw_labels = kmeans.fit_predict(metric_values)

        # Re-map clusters so state ids increase with metric centroid.
        centroid_order = np.argsort(kmeans.cluster_centers_.reshape(-1))
        label_map = {old_label: new_label for new_label, old_label in enumerate(centroid_order)}
        state_labels = np.array([label_map[label] for label in raw_labels], dtype=int)

        self.kmeans_model = kmeans
        self.state_centroids = kmeans.cluster_centers_[centroid_order]
        self.detected_state_count = self.num_states

        self._log_state_distribution(state_labels)
        logger.info(
            "Metric fallback on %s produced centroids: %s",
            self.fallback_metric,
            [f"{value:.4f}" for value in self.state_centroids.reshape(-1)],
        )

        return state_labels

    def _log_state_distribution(self, state_labels: np.ndarray):
        """
        Log distribution of detected states.

        Args:
            state_labels: State label array
        """
        unique_states, counts = np.unique(state_labels, return_counts=True)
        total = len(state_labels)

        for state, count in zip(unique_states, counts):
            percentage = (count / total) * 100
            logger.info(f"state_{state}: {count} samples ({percentage:.1f}%)")

    def validate_states(
        self,
        df: pd.DataFrame,
        state_labels: np.ndarray,
        metric: str,
        min_separation: float = 0.3
    ) -> bool:
        """
        Validate that detected states correlate with metric distributions.

        Checks:
        1. Ordering: mean(state_i) < mean(state_i+1)
        2. Separation: mean(state_i+1) - mean(state_i) > min_separation

        Args:
            df: DataFrame with metric column
            state_labels: Detected state labels
            metric: Metric column to validate against
            min_separation: Minimum metric difference between states

        Returns:
            bool: True if validation passes

        Example:
            >>> is_valid = detector.validate_states(df, state_labels, 'HMI_2_FIT_001.PV')
            >>> print(f"States valid: {is_valid}")
        """
        unique_states = sorted(np.unique(state_labels))
        state_means = []

        for state in unique_states:
            state_mask = (state_labels == state)
            state_data = pd.to_numeric(df.loc[state_mask, metric], errors='coerce').dropna()

            if len(state_data) == 0:
                logger.warning(f"State {state} has no valid data for {metric}")
                return False

            state_means.append(state_data.mean())

        # Check ordering
        is_ordered = all(state_means[i] < state_means[i+1] for i in range(len(state_means)-1))

        if not is_ordered:
            logger.warning(f"States not ordered by {metric} mean: {state_means}")
            return False

        # Check separation
        for i in range(len(state_means) - 1):
            separation = state_means[i+1] - state_means[i]

            if separation < min_separation:
                logger.warning(
                    f"Insufficient separation between state_{i} and state_{i+1}: "
                    f"{separation:.3f} < {min_separation}"
                )
                return False

        logger.info(f"✓ States validated with {metric}: {[f'{m:.3f}' for m in state_means]}")
        return True

    def save_state_labels(
        self,
        df: pd.DataFrame,
        state_labels: np.ndarray,
        output_path: str
    ):
        """
        Save detected state labels to CSV.

        Args:
            df: Original DataFrame
            state_labels: Detected state labels
            output_path: Output CSV path

        Example:
            >>> detector.save_state_labels(df, state_labels, 'state_labels.csv')
        """
        # Create output DataFrame
        output_df = pd.DataFrame({
            'Time': df['Time'] if 'Time' in df.columns else range(len(df))
        })

        # Add pump status columns
        for col in self.pump_columns:
            if col in df.columns:
                output_df[col] = df[col]

        # Add detected state
        output_df['detected_state'] = state_labels

        # Save
        output_df.to_csv(output_path, index=False)
        logger.info(f"Saved state labels to {output_path}")
