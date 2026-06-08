"""Incremental statistics computation using Welford's online algorithm."""

import math
from typing import Optional

import numpy as np


class IncrementalStats:
    """
    Compute mean and variance incrementally across data chunks.

    Uses Welford's online algorithm to avoid two-pass reading and numerical instability.
    This enables computing statistics for datasets too large to fit in memory.

    Algorithm:
        For each new value x:
        1. count += 1
        2. delta = x - mean
        3. mean += delta / count
        4. delta2 = x - mean
        5. M2 += delta * delta2

        variance = M2 / count
        std = sqrt(variance)

    Example:
        stats = IncrementalStats()
        for chunk in reader.iter_chunks():
            for value in chunk['metric']:
                stats.update(value)
        print(f"Mean: {stats.mean}, Std: {stats.std()}")
    """

    def __init__(self):
        """Initialize incremental statistics tracker."""
        self.count = 0
        self.mean = 0.0
        self.M2 = 0.0  # Sum of squared differences from mean

    def update(self, new_value: float):
        """
        Update statistics with a single new value.

        Args:
            new_value: New data point to incorporate

        Example:
            stats = IncrementalStats()
            stats.update(1.0)
            stats.update(2.0)
            stats.update(3.0)
            assert abs(stats.mean - 2.0) < 0.001
        """
        if math.isnan(new_value):
            return  # Skip NaN values

        self.count += 1
        delta = new_value - self.mean
        self.mean += delta / self.count
        delta2 = new_value - self.mean
        self.M2 += delta * delta2

    def update_batch(self, values: np.ndarray):
        """
        Update statistics with a batch of values efficiently.

        Args:
            values: Array of values to incorporate

        Example:
            stats = IncrementalStats()
            chunk_data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
            stats.update_batch(chunk_data)
            assert abs(stats.mean - 3.0) < 0.001
        """
        # Filter out NaN values
        valid_values = values[~np.isnan(values)]

        for value in valid_values:
            self.update(value)

    def variance(self) -> float:
        """
        Compute current variance.

        Returns:
            float: Population variance (divide by count)

        Note:
            Returns 0.0 if count <= 1
        """
        if self.count <= 1:
            return 0.0
        return self.M2 / self.count

    def sample_variance(self) -> float:
        """
        Compute current sample variance (Bessel's correction).

        Returns:
            float: Sample variance (divide by count-1)

        Note:
            Returns 0.0 if count <= 1
        """
        if self.count <= 1:
            return 0.0
        return self.M2 / (self.count - 1)

    def std(self, sample: bool = False) -> float:
        """
        Compute current standard deviation.

        Args:
            sample: If True, use sample variance (Bessel's correction). Default False.

        Returns:
            float: Standard deviation

        Example:
            stats = IncrementalStats()
            stats.update_batch(np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
            assert abs(stats.std() - 1.414) < 0.01  # Population std
        """
        if sample:
            return math.sqrt(self.sample_variance())
        return math.sqrt(self.variance())

    def get_state(self) -> dict:
        """
        Get current state for checkpointing.

        Returns:
            dict: State dictionary with count, mean, M2

        Example:
            stats = IncrementalStats()
            stats.update_batch(np.array([1, 2, 3]))
            state = stats.get_state()
            # Save state to checkpoint
        """
        return {
            'count': self.count,
            'mean': self.mean,
            'M2': self.M2
        }

    def restore_state(self, state: dict):
        """
        Restore state from checkpoint.

        Args:
            state: State dictionary from get_state()

        Example:
            stats = IncrementalStats()
            stats.restore_state({'count': 1000, 'mean': 1.5, 'M2': 250.0})
            # Continue processing from checkpoint
        """
        self.count = state['count']
        self.mean = state['mean']
        self.M2 = state['M2']

    def merge(self, other: 'IncrementalStats'):
        """
        Merge statistics from another IncrementalStats instance.

        Useful for parallel processing where different workers process different chunks.

        Args:
            other: Another IncrementalStats instance to merge

        Example:
            stats1 = IncrementalStats()
            stats1.update_batch(np.array([1, 2, 3]))

            stats2 = IncrementalStats()
            stats2.update_batch(np.array([4, 5, 6]))

            stats1.merge(stats2)
            assert stats1.count == 6
            assert abs(stats1.mean - 3.5) < 0.001
        """
        if other.count == 0:
            return

        total_count = self.count + other.count
        delta = other.mean - self.mean

        # Combine means
        new_mean = (self.count * self.mean + other.count * other.mean) / total_count

        # Combine M2 using parallel algorithm
        new_M2 = self.M2 + other.M2 + delta * delta * self.count * other.count / total_count

        self.count = total_count
        self.mean = new_mean
        self.M2 = new_M2

    def __repr__(self) -> str:
        """String representation."""
        return f"IncrementalStats(count={self.count}, mean={self.mean:.6f}, std={self.std():.6f})"
