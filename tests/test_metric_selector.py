"""Tests for WaDi metric selector."""

import numpy as np
import pandas as pd

from cluster_analysis.adapters.wadi.metric_selector import (
    compute_data_quality,
    compute_coefficient_of_variation,
    rank_metrics,
    rank_metrics_with_details,
    apply_manual_override
)


def test_compute_data_quality():
    """Test data quality computation."""
    data = pd.Series([1.0, 2.0, "Bad Input", 3.0, np.nan, 4.0, 5.0])

    quality = compute_data_quality(data)

    # Valid values: [1, 2, 3, 4, 5] = 5 out of 7
    assert quality['completeness'] == 5.0 / 7.0
    assert quality['bad_input_ratio'] == 1.0 / 7.0
    assert quality['nan_ratio'] == 1.0 / 7.0
    assert quality['valid_count'] == 5

    print(f"✓ Data quality: completeness={quality['completeness']:.2f}, bad_input={quality['bad_input_ratio']:.2f}")


def test_compute_cv():
    """Test coefficient of variation computation."""
    # Data: mean=3, std≈1.58 (sample std), CV≈0.53
    data = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])

    cv = compute_coefficient_of_variation(data)

    assert 0.5 < cv < 0.6
    print(f"✓ Coefficient of variation: {cv:.3f}")


def test_cv_with_bad_input():
    """Test CV computation with Bad Input values."""
    data = pd.Series([1.0, "Bad Input", 2.0, 3.0, "Bad Input", 4.0, 5.0])

    cv = compute_coefficient_of_variation(data)

    # Should compute CV only on valid values [1, 2, 3, 4, 5]
    assert 0.5 < cv < 0.6
    print(f"✓ CV with Bad Input handled: {cv:.3f}")


def create_mock_wadi_dataframe():
    """Create mock WaDi DataFrame for testing."""
    np.random.seed(42)

    df = pd.DataFrame({
        'Time': pd.date_range('2023-01-01', periods=1000, freq='1min'),

        # High priority FIT (flow) - high variability, good quality
        'HMI_2_FIT_001.PV': np.random.normal(1.3, 0.15, 1000),

        # Medium priority PIT (pressure) - medium variability, good quality
        'HMI_2_PIT_001.PV': np.random.normal(2.45, 0.10, 1000),

        # Low priority LT (level) - low variability, good quality
        'HMI_2_LT_001.PV': np.random.normal(3.5, 0.07, 1000),

        # Low quality metric (50% bad input)
        'HMI_3_AIT_001.PV': ['Bad Input' if i % 2 == 0 else np.random.normal(5, 0.5)
                              for i in range(1000)],

        # Too stable (CV < 0.01)
        'HMI_1_LT_002.PV': np.random.normal(10.0, 0.001, 1000),

        # Status column (should be excluded from ranking)
        'HMI_2_P_001_STATUS': np.random.choice([0, 1], 1000)
    })

    return df


def test_rank_wadi_metrics():
    """
    Test automatic metric ranking on mock WaDi data.

    Expected from Task 2.2:
    Returns ['HMI_2_FIT_001.PV', 'HMI_2_PIT_001.PV', 'HMI_2_LT_001.PV']
    """
    df = create_mock_wadi_dataframe()

    ranked = rank_metrics(df, top_k=3)

    # Should rank by score: completeness × min(cv, 1) × priority
    # FIT: 1.0 × 0.12 × 3 = 0.36
    # PIT: 1.0 × 0.04 × 2 = 0.08
    # LT:  1.0 × 0.02 × 1 = 0.02

    assert len(ranked) == 3
    assert 'HMI_2_FIT_001.PV' in ranked
    assert 'HMI_2_PIT_001.PV' in ranked
    assert 'HMI_2_LT_001.PV' in ranked

    # FIT should be first (highest score)
    assert ranked[0] == 'HMI_2_FIT_001.PV'

    # Status columns should not be included
    assert 'HMI_2_P_001_STATUS' not in ranked

    # Low quality metric should be excluded
    assert 'HMI_3_AIT_001.PV' not in ranked

    # Too stable metric should be excluded
    assert 'HMI_1_LT_002.PV' not in ranked

    print(f"✓ Ranked metrics: {ranked}")


def test_rank_metrics_with_details():
    """Test metric ranking with detailed scoring info."""
    df = create_mock_wadi_dataframe()

    details = rank_metrics_with_details(df, top_k=3)

    assert len(details) == 3

    # First metric should be FIT with highest score
    assert details[0]['column'] == 'HMI_2_FIT_001.PV'
    assert details[0]['sensor_type'] == 'FIT'
    assert details[0]['priority'] == 3
    assert details[0]['completeness'] >= 0.99

    print(f"✓ Top metric: {details[0]['column']}, score={details[0]['score']:.3f}, CV={details[0]['cv']:.3f}")


def test_filter_by_quality_threshold():
    """Test that low-quality metrics are filtered out."""
    df = create_mock_wadi_dataframe()

    # HMI_3_AIT_001.PV has 50% bad input, should be excluded
    ranked = rank_metrics(df, top_k=5, quality_threshold=0.8)

    assert 'HMI_3_AIT_001.PV' not in ranked

    print(f"✓ Low quality metric correctly excluded")


def test_filter_by_cv_range():
    """Test that metrics outside CV range are filtered."""
    df = create_mock_wadi_dataframe()

    # HMI_1_LT_002.PV has CV < 0.01 (too stable)
    ranked = rank_metrics(df, top_k=5, cv_min=0.01, cv_max=2.0)

    assert 'HMI_1_LT_002.PV' not in ranked

    print(f"✓ Too-stable metric correctly excluded")


def test_apply_manual_override():
    """Test manual metric override."""
    auto_ranked = ['HMI_2_FIT_001.PV', 'HMI_2_PIT_001.PV', 'HMI_2_LT_001.PV']

    # Force include and exclude
    result = apply_manual_override(
        auto_ranked,
        manual_include=['HMI_1_LT_002.PV'],
        manual_exclude=['HMI_2_LT_001.PV'],
        max_metrics=3
    )

    assert 'HMI_1_LT_002.PV' in result  # Forced inclusion
    assert 'HMI_2_LT_001.PV' not in result  # Forced exclusion
    assert len(result) == 3

    print(f"✓ Manual override applied: {result}")


def test_domain_priority_weighting():
    """Test that domain priority affects ranking."""
    df = create_mock_wadi_dataframe()

    details = rank_metrics_with_details(df, top_k=3)

    # FIT (priority=3) should score higher than PIT (priority=2) and LT (priority=1)
    fit_score = next(d['score'] for d in details if d['sensor_type'] == 'FIT')
    pit_score = next(d['score'] for d in details if d['sensor_type'] == 'PIT')
    lt_score = next(d['score'] for d in details if d['sensor_type'] == 'LT')

    assert fit_score > pit_score > lt_score

    print(f"✓ Priority weighting: FIT={fit_score:.3f} > PIT={pit_score:.3f} > LT={lt_score:.3f}")


if __name__ == '__main__':
    print("Running metric selector tests...\n")

    test_compute_data_quality()
    test_compute_cv()
    test_cv_with_bad_input()
    test_rank_wadi_metrics()
    test_rank_metrics_with_details()
    test_filter_by_quality_threshold()
    test_filter_by_cv_range()
    test_apply_manual_override()
    test_domain_priority_weighting()

    print("\n✓ All metric selector tests passed")
