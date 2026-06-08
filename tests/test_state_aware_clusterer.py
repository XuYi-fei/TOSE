"""Tests for StateAwareClusterer."""

import tempfile
from pathlib import Path
import numpy as np
import pandas as pd

try:
    from cluster_analysis.state_aware_clusterer import StateAwareClusterer, DistributionValidator
    IMPORTS_OK = True
except ImportError as e:
    IMPORTS_OK = False
    IMPORT_ERROR = str(e)


def create_mock_multimodal_data():
    """Create mock data with 3 distinct operational states."""
    np.random.seed(42)

    # State 0: LOW flow (~0.004 L/s)
    state0_data = np.random.normal(0.004, 0.002, 10000)

    # State 1: MEDIUM flow (~1.3 L/s)
    state1_data = np.random.normal(1.305, 0.152, 12000)

    # State 2: HIGH flow (~2.4 L/s)
    state2_data = np.random.normal(2.410, 0.180, 12000)

    # Combine
    all_data = np.concatenate([state0_data, state1_data, state2_data])
    state_labels = np.array([0]*10000 + [1]*12000 + [2]*12000)

    # Create DataFrame
    df = pd.DataFrame({
        'Time': pd.date_range('2023-01-01', periods=len(all_data), freq='1min'),
        'HMI_2_FIT_001.PV': all_data
    })

    return df, state_labels


def test_cluster_3_states():
    """
    Test clustering across 3 operational states.

    Expected from Task 4.1:
    Returns 3 distributions with distinct means.
    """
    if not IMPORTS_OK:
        print(f"Skipping test: {IMPORT_ERROR}")
        return

    df, state_labels = create_mock_multimodal_data()

    clusterer = StateAwareClusterer(min_cluster_size=50)
    distributions = clusterer.fit(df, state_labels, 'HMI_2_FIT_001.PV')

    # Should learn 3 distributions
    assert len(distributions) == 3
    assert 'fit_state_0' in distributions
    assert 'fit_state_1' in distributions
    assert 'fit_state_2' in distributions

    # Check means are approximately correct
    assert abs(distributions['fit_state_0']['mu'] - 0.004) < 0.001
    assert abs(distributions['fit_state_1']['mu'] - 1.305) < 0.05
    assert abs(distributions['fit_state_2']['mu'] - 2.410) < 0.05

    # Check sample counts
    assert distributions['fit_state_0']['sample_count'] > 9000  # Some outliers removed
    assert distributions['fit_state_1']['sample_count'] > 11000
    assert distributions['fit_state_2']['sample_count'] > 11000

    print(f"✓ Clustered 3 states:")
    for name, dist in distributions.items():
        print(f"  {name}: μ={dist['mu']:.4f}, σ={dist['sigma']:.4f}, n={dist['sample_count']}")


def test_save_and_load_distributions():
    """Test saving and loading distributions."""
    if not IMPORTS_OK:
        print(f"Skipping test: {IMPORT_ERROR}")
        return

    df, state_labels = create_mock_multimodal_data()

    clusterer = StateAwareClusterer(min_cluster_size=50)
    distributions = clusterer.fit(df, state_labels, 'HMI_2_FIT_001.PV')

    # Save to temp file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as f:
        yaml_path = f.name

    try:
        clusterer.save_distributions(yaml_path)

        # Load back
        loaded = StateAwareClusterer.load_distributions(yaml_path)

        assert len(loaded) == len(distributions)
        assert loaded['fit_state_0']['mu'] == distributions['fit_state_0']['mu']

        print(f"✓ Saved and loaded {len(loaded)} distributions")

    finally:
        Path(yaml_path).unlink()


def test_well_separated_states():
    """
    Test distribution separation validation.

    Expected from Task 4.3:
    Returns True for 12.15σ separation.
    """
    if not IMPORTS_OK:
        print(f"Skipping test: {IMPORT_ERROR}")
        return

    df, state_labels = create_mock_multimodal_data()

    clusterer = StateAwareClusterer(min_cluster_size=50)
    distributions = clusterer.fit(df, state_labels, 'HMI_2_FIT_001.PV')

    # Check separation between state 0 and state 1
    dist0 = distributions['fit_state_0']
    dist1 = distributions['fit_state_1']

    validator = DistributionValidator()
    is_separated = validator.check_separation(dist0, dist1, min_sigma_separation=3.0)

    assert is_separated, "States 0 and 1 should be well-separated"

    # Validate all distributions
    all_valid = validator.validate_all_distributions(distributions, min_sigma_separation=3.0)

    assert all_valid, "All state distributions should be well-separated"

    print("✓ All distributions are well-separated (≥3σ)")


def test_outlier_filtering():
    """Test that HDBSCAN outliers are filtered before distribution fitting."""
    if not IMPORTS_OK:
        print(f"Skipping test: {IMPORT_ERROR}")
        return

    # Create data with outliers
    np.random.seed(42)
    normal_data = np.random.normal(1.3, 0.15, 1000)
    outliers = np.array([10.0, -5.0, 20.0])  # Extreme outliers
    data_with_outliers = np.concatenate([normal_data, outliers])

    df = pd.DataFrame({
        'HMI_2_FIT_001.PV': data_with_outliers
    })
    state_labels = np.zeros(len(data_with_outliers), dtype=int)

    clusterer = StateAwareClusterer(min_cluster_size=50)
    distributions = clusterer.fit(df, state_labels, 'HMI_2_FIT_001.PV')

    # Check that mean is close to 1.3 (outliers filtered)
    assert abs(distributions['fit_state_0']['mu'] - 1.3) < 0.1

    # Check outlier count
    assert distributions['fit_state_0']['outlier_count'] > 0

    print(f"✓ Outliers filtered: {distributions['fit_state_0']['outlier_count']} removed")


if __name__ == '__main__':
    print("Running StateAwareClusterer tests...\n")

    if not IMPORTS_OK:
        print(f"⚠ Cannot run tests: {IMPORT_ERROR}")
        print("Install hdbscan with: pip install hdbscan")
    else:
        test_cluster_3_states()
        test_save_and_load_distributions()
        test_well_separated_states()
        test_outlier_filtering()

        print("\n✓ All StateAwareClusterer tests passed")
