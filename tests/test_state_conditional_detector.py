"""Tests for StateConditionalDetector."""

import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

try:
    from anomaly_detection.state_conditional_detector import StateConditionalDetector
    IMPORTS_OK = True
except ImportError as e:
    IMPORTS_OK = False
    IMPORT_ERROR = str(e)


def create_mock_distributions():
    """Create mock learned distributions for testing."""
    return {
        'fit_state_0': {
            'metric': 'HMI_2_FIT_001.PV',
            'state_id': 0,
            'mu': 0.004,
            'sigma': 0.002,
            'sample_count': 1000
        },
        'fit_state_1': {
            'metric': 'HMI_2_FIT_001.PV',
            'state_id': 1,
            'mu': 1.305,
            'sigma': 0.152,
            'sample_count': 1200
        },
        'fit_state_2': {
            'metric': 'HMI_2_FIT_001.PV',
            'state_id': 2,
            'mu': 2.410,
            'sigma': 0.180,
            'sample_count': 1200
        }
    }


def test_normal_operation():
    """
    Test detection with normal (non-anomalous) data.

    Expected: No anomalies detected within 3σ.
    """
    if not IMPORTS_OK:
        print(f"Skipping test: {IMPORT_ERROR}")
        return

    distributions = create_mock_distributions()
    detector = StateConditionalDetector(distributions=distributions)

    # Create normal data
    np.random.seed(42)
    n_per_state = 100

    state_labels = np.array([0]*n_per_state + [1]*n_per_state + [2]*n_per_state)

    normal_data = np.concatenate([
        np.random.normal(0.004, 0.002, n_per_state),  # State 0
        np.random.normal(1.305, 0.152, n_per_state),  # State 1
        np.random.normal(2.410, 0.180, n_per_state)   # State 2
    ])

    df = pd.DataFrame({'HMI_2_FIT_001.PV': normal_data})

    # Detect anomalies
    anomalies = detector.detect(df, state_labels, threshold=3.0)

    # Should have few/no anomalies
    anomaly_count = anomalies['is_anomaly'].sum()
    anomaly_rate = anomaly_count / len(anomalies)

    assert anomaly_rate < 0.01, f"Too many false positives: {anomaly_rate:.1%}"

    print(f"✓ Normal operation: {anomaly_count}/{len(anomalies)} anomalies ({anomaly_rate:.1%})")


def test_detect_anomalies():
    """Test detection of injected anomalies."""
    if not IMPORTS_OK:
        print(f"Skipping test: {IMPORT_ERROR}")
        return

    distributions = create_mock_distributions()
    detector = StateConditionalDetector(distributions=distributions)

    # Create data with anomalies
    np.random.seed(42)

    # State 0: normal + 1 anomaly
    state0_normal = np.random.normal(0.004, 0.002, 99)
    state0_anomaly = np.array([0.100])  # 48σ deviation

    # State 1: normal + 1 anomaly
    state1_normal = np.random.normal(1.305, 0.152, 99)
    state1_anomaly = np.array([2.000])  # 4.6σ deviation

    # State 2: all normal
    state2_normal = np.random.normal(2.410, 0.180, 100)

    state_labels = np.array([0]*100 + [1]*100 + [2]*100)

    data = np.concatenate([
        state0_normal, state0_anomaly,
        state1_normal, state1_anomaly,
        state2_normal
    ])

    df = pd.DataFrame({'HMI_2_FIT_001.PV': data})

    # Detect anomalies
    anomalies = detector.detect(df, state_labels, threshold=3.0)

    # Should detect the 2 injected anomalies
    anomaly_indices = np.where(anomalies['is_anomaly'])[0]

    assert len(anomaly_indices) >= 2, f"Failed to detect anomalies: {len(anomaly_indices)}/2"

    # Check that known anomalous points are detected
    state0_anomaly_idx = 99
    state1_anomaly_idx = 199

    assert state0_anomaly_idx in anomaly_indices, "State 0 anomaly not detected"
    assert state1_anomaly_idx in anomaly_indices, "State 1 anomaly not detected"

    print(f"✓ Detected {len(anomaly_indices)} anomalies (expected ≥2)")


def test_state_transition_false_positives():
    """
    Test that state transitions don't trigger false positives.

    When system transitions from state 0 → state 1, values should be
    checked against BOTH distributions.
    """
    if not IMPORTS_OK:
        print(f"Skipping test: {IMPORT_ERROR}")
        return

    distributions = create_mock_distributions()

    # Mode: state_conditional (strict)
    detector_strict = StateConditionalDetector(
        distributions=distributions,
        mode='state_conditional'
    )

    # Mode: hybrid (tolerant to state transitions)
    detector_hybrid = StateConditionalDetector(
        distributions=distributions,
        mode='hybrid',
        cross_state_threshold=2.5
    )

    # Create transition scenario: state labels say state 0, but value is from state 1
    state_labels = np.array([0, 0, 0, 0, 0])
    values = np.array([0.004, 0.005, 1.305, 0.004, 0.005])  # 3rd value is state 1 mean

    df = pd.DataFrame({'HMI_2_FIT_001.PV': values})

    # Strict mode: should flag transition as anomaly
    anomalies_strict = detector_strict.detect(df, state_labels, threshold=3.0)
    assert anomalies_strict.iloc[2]['is_anomaly'], "Strict mode should flag transition"

    # Hybrid mode: should NOT flag transition (value is normal for state 1)
    anomalies_hybrid = detector_hybrid.detect(df, state_labels, threshold=3.0)
    assert not anomalies_hybrid.iloc[2]['is_anomaly'], "Hybrid mode should allow transition"

    print("✓ Hybrid mode reduces false positives during state transitions")


def test_get_anomaly_scores():
    """Test getting anomaly scores for a single metric."""
    if not IMPORTS_OK:
        print(f"Skipping test: {IMPORT_ERROR}")
        return

    distributions = create_mock_distributions()
    detector = StateConditionalDetector(distributions=distributions)

    # Create test data
    state_labels = np.array([0, 1, 2])
    data = np.array([0.004, 1.305, 2.410])  # Exactly at distribution means

    df = pd.DataFrame({'HMI_2_FIT_001.PV': data})

    # Get scores
    scores = detector.get_anomaly_scores(df, state_labels, 'HMI_2_FIT_001.PV')

    # Should be ~0σ deviation (at mean)
    assert np.allclose(scores, 0.0, atol=0.01), f"Expected ~0σ, got {scores}"

    print(f"✓ Anomaly scores: {scores}")


def test_get_expected_distribution():
    """Test retrieving expected distributions."""
    if not IMPORTS_OK:
        print(f"Skipping test: {IMPORT_ERROR}")
        return

    distributions = create_mock_distributions()
    detector = StateConditionalDetector(distributions=distributions)

    # Get state 1 distribution
    dist = detector.get_expected_distribution('HMI_2_FIT_001.PV', state_id=1)

    assert dist is not None
    assert dist['mu'] == 1.305
    assert dist['sigma'] == 0.152

    print(f"✓ Retrieved distribution: μ={dist['mu']}, σ={dist['sigma']}")


def test_load_from_yaml():
    """Test loading distributions from YAML file."""
    if not IMPORTS_OK:
        print(f"Skipping test: {IMPORT_ERROR}")
        return

    distributions = create_mock_distributions()

    # Save to temp YAML
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml')
    yaml.dump({'distributions': distributions}, temp_file)
    temp_file.close()

    try:
        # Load detector from YAML
        detector = StateConditionalDetector(distributions_path=temp_file.name)

        assert len(detector.distributions) == 3
        assert 'HMI_2_FIT_001.PV' in detector.metric_index

        print("✓ Loaded distributions from YAML")

    finally:
        Path(temp_file.name).unlink()


if __name__ == '__main__':
    print("Running StateConditionalDetector tests...\n")

    if not IMPORTS_OK:
        print(f"⚠ Cannot run tests: {IMPORT_ERROR}")
    else:
        test_normal_operation()
        test_detect_anomalies()
        test_state_transition_false_positives()
        test_get_anomaly_scores()
        test_get_expected_distribution()
        test_load_from_yaml()

        print("\n✓ All StateConditionalDetector tests passed")
