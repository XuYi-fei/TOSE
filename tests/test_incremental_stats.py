"""Tests for IncrementalStats."""

import numpy as np

from cluster_analysis.utils import IncrementalStats


class TestIncrementalStats:
    """Test suite for IncrementalStats."""

    def test_basic_mean_computation(self):
        """Test basic mean computation."""
        stats = IncrementalStats()

        stats.update(1.0)
        stats.update(2.0)
        stats.update(3.0)

        assert abs(stats.mean - 2.0) < 0.001
        assert stats.count == 3

    def test_std_computation(self):
        """Test standard deviation computation."""
        stats = IncrementalStats()

        # Data: [1, 2, 3, 4, 5], mean=3, std≈1.414 (population)
        for value in [1.0, 2.0, 3.0, 4.0, 5.0]:
            stats.update(value)

        assert abs(stats.mean - 3.0) < 0.001
        assert abs(stats.std() - 1.414) < 0.01

    def test_batch_update(self):
        """Test batch update with array."""
        stats = IncrementalStats()

        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        stats.update_batch(values)

        assert stats.count == 5
        assert abs(stats.mean - 3.0) < 0.001
        assert abs(stats.std() - 1.414) < 0.01

    def test_match_batch_statistics(self):
        """Test that incremental stats match batch computation."""
        # Generate large dataset
        np.random.seed(42)
        data = np.random.normal(loc=100, scale=15, size=10000)

        # Compute batch statistics
        batch_mean = np.mean(data)
        batch_std = np.std(data)

        # Compute incremental statistics in chunks
        stats = IncrementalStats()
        chunk_size = 1000

        for i in range(0, len(data), chunk_size):
            chunk = data[i:i+chunk_size]
            stats.update_batch(chunk)

        # Verify match within 0.1%
        assert abs(stats.mean - batch_mean) / batch_mean < 0.001
        assert abs(stats.std() - batch_std) / batch_std < 0.001

    def test_handle_nan_values(self):
        """Test handling of NaN values."""
        stats = IncrementalStats()

        values = np.array([1.0, np.nan, 2.0, 3.0, np.nan, 4.0, 5.0])
        stats.update_batch(values)

        # Should skip NaN values, count only valid: [1, 2, 3, 4, 5]
        assert stats.count == 5
        assert abs(stats.mean - 3.0) < 0.001

    def test_variance_with_single_value(self):
        """Test variance returns 0 for single value."""
        stats = IncrementalStats()
        stats.update(5.0)

        assert stats.variance() == 0.0
        assert stats.std() == 0.0

    def test_sample_variance(self):
        """Test sample variance (Bessel's correction)."""
        stats = IncrementalStats()

        # Data: [1, 2, 3]
        stats.update_batch(np.array([1.0, 2.0, 3.0]))

        # Population variance: 0.6667
        # Sample variance: 1.0 (with Bessel's correction)
        assert abs(stats.variance() - 0.6667) < 0.01
        assert abs(stats.sample_variance() - 1.0) < 0.01

    def test_get_and_restore_state(self):
        """Test state checkpointing."""
        stats1 = IncrementalStats()
        stats1.update_batch(np.array([1.0, 2.0, 3.0]))

        # Save state
        state = stats1.get_state()

        # Create new instance and restore
        stats2 = IncrementalStats()
        stats2.restore_state(state)

        assert stats2.count == stats1.count
        assert stats2.mean == stats1.mean
        assert stats2.M2 == stats1.M2

    def test_merge_statistics(self):
        """Test merging statistics from parallel workers."""
        # Worker 1 processes [1, 2, 3]
        stats1 = IncrementalStats()
        stats1.update_batch(np.array([1.0, 2.0, 3.0]))

        # Worker 2 processes [4, 5, 6]
        stats2 = IncrementalStats()
        stats2.update_batch(np.array([4.0, 5.0, 6.0]))

        # Merge results
        stats1.merge(stats2)

        # Combined data: [1, 2, 3, 4, 5, 6], mean=3.5
        assert stats1.count == 6
        assert abs(stats1.mean - 3.5) < 0.001

    def test_incremental_matches_full_dataset(self):
        """
        Test that incremental computation across chunks matches full dataset stats.

        This is the key validation for Task 1.2: verify incremental stats
        match batch-computed statistics within 0.1%.
        """
        np.random.seed(42)

        # Simulate large dataset split into 3 chunks
        chunk1 = np.random.normal(100, 15, 3000)
        chunk2 = np.random.normal(100, 15, 3000)
        chunk3 = np.random.normal(100, 15, 3000)

        # Batch computation on full data
        full_data = np.concatenate([chunk1, chunk2, chunk3])
        batch_mean = np.mean(full_data)
        batch_std = np.std(full_data)

        # Incremental computation
        stats = IncrementalStats()
        stats.update_batch(chunk1)
        stats.update_batch(chunk2)
        stats.update_batch(chunk3)

        # Verify match within 0.1%
        assert abs(stats.mean - batch_mean) / batch_mean < 0.001
        assert abs(stats.std() - batch_std) / batch_std < 0.001

        print(f"✓ Incremental mean={stats.mean:.6f}, batch mean={batch_mean:.6f}")
        print(f"✓ Incremental std={stats.std():.6f}, batch std={batch_std:.6f}")
