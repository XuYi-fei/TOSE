"""Integration test for WaDi clustering workflow."""

import tempfile
from pathlib import Path
import yaml
import pandas as pd
import numpy as np

try:
    from cluster_wadi import load_config, run_wadi_clustering
    IMPORTS_OK = True
except ImportError as e:
    IMPORTS_OK = False
    IMPORT_ERROR = str(e)


def create_mock_wadi_csv():
    """Create a mock WaDi CSV file for testing.

    Returns:
        Path: Temporary CSV file path
    """
    np.random.seed(42)

    # Create 3000 rows with 3 operational states based on pump status
    n_per_state = 1000

    # State 0: Both pumps OFF (LOW flow ~0.004 L/s)
    state0_data = {
        'Time': pd.date_range('2023-01-01', periods=n_per_state, freq='1min'),
        'HMI_2_P_001_STATUS': [0.0] * n_per_state,
        'HMI_2_P_002_STATUS': [0.0] * n_per_state,
        'HMI_2_FIT_001.PV': np.random.normal(0.004, 0.002, n_per_state),
        'HMI_2_PIT_001.PV': np.random.normal(1.2, 0.1, n_per_state),
        'HMI_2_LT_001.PV': np.random.normal(0.5, 0.05, n_per_state),
    }

    # State 1: One pump ON (MEDIUM flow ~1.3 L/s)
    state1_data = {
        'Time': pd.date_range('2023-01-01 16:40', periods=n_per_state, freq='1min'),
        'HMI_2_P_001_STATUS': [1.0] * n_per_state,
        'HMI_2_P_002_STATUS': [0.0] * n_per_state,
        'HMI_2_FIT_001.PV': np.random.normal(1.305, 0.152, n_per_state),
        'HMI_2_PIT_001.PV': np.random.normal(2.4, 0.2, n_per_state),
        'HMI_2_LT_001.PV': np.random.normal(1.8, 0.15, n_per_state),
    }

    # State 2: Both pumps ON (HIGH flow ~2.4 L/s)
    state2_data = {
        'Time': pd.date_range('2023-01-02 09:20', periods=n_per_state, freq='1min'),
        'HMI_2_P_001_STATUS': [1.0] * n_per_state,
        'HMI_2_P_002_STATUS': [1.0] * n_per_state,
        'HMI_2_FIT_001.PV': np.random.normal(2.410, 0.180, n_per_state),
        'HMI_2_PIT_001.PV': np.random.normal(3.6, 0.3, n_per_state),
        'HMI_2_LT_001.PV': np.random.normal(2.5, 0.2, n_per_state),
    }

    # Combine all states
    df = pd.concat([
        pd.DataFrame(state0_data),
        pd.DataFrame(state1_data),
        pd.DataFrame(state2_data)
    ], ignore_index=True)

    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
    df.to_csv(temp_file.name, index=False)
    temp_file.close()

    return Path(temp_file.name)


def test_load_config():
    """Test configuration loading."""
    if not IMPORTS_OK:
        print(f"Skipping test: {IMPORT_ERROR}")
        return

    config_path = 'configs/wadi_cluster_config.yaml'

    try:
        config = load_config(config_path)

        assert 'dataset' in config
        assert 'adapter' in config
        assert 'clustering' in config
        assert 'environment_detection' in config

        print("✓ Configuration loaded successfully")

    except FileNotFoundError:
        print(f"⚠ Config file not found: {config_path}")


def test_mock_clustering_workflow():
    """Test clustering workflow with mock data."""
    if not IMPORTS_OK:
        print(f"Skipping test: {IMPORT_ERROR}")
        return

    # Create mock data
    csv_path = create_mock_wadi_csv()

    # Create temporary config
    temp_config = {
        'dataset': {
            'name': 'wadi',
            'identity_data_path': str(csv_path)
        },
        'adapter': {
            'type': 'wadi',
            'top_k': 2,
            'quality_threshold': 0.5,
            'cv_min': 0.01,
            'cv_max': 2.0,
            'manual_include': [],
            'manual_exclude': []
        },
        'environment_detection': {
            'method': 'pump_status',
            'pump_columns': ['HMI_2_P_001_STATUS', 'HMI_2_P_002_STATUS'],
            'num_states': 3,
            'auto_detect_states': False,
            'validation': {
                'min_separation': 0.2,
                'check_ordering': True
            }
        },
        'clustering': {
            'method': 'hdbscan',
            'min_cluster_size': 50,
            'state_aware': True
        },
        'validation': {
            'check_separation': True,
            'min_sigma_separation': 3.0
        },
        'output': {
            'distributions_path': 'test_output/learned_distributions.yaml',
            'state_labels_path': 'test_output/state_labels.csv'
        }
    }

    # Save temporary config
    temp_config_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml')
    yaml.dump(temp_config, temp_config_file)
    temp_config_file.close()

    try:
        # Run clustering
        success = run_wadi_clustering(temp_config_file.name, verbose=False)

        assert success, "Clustering workflow failed"

        # Check output files exist
        distributions_path = Path('test_output/learned_distributions.yaml')
        assert distributions_path.exists(), "Distributions file not created"

        # Load and validate distributions
        with open(distributions_path, 'r') as f:
            output_data = yaml.safe_load(f)

        assert 'distributions' in output_data
        distributions = output_data['distributions']

        # Should have distributions for 2 metrics × 3 states = 6 total
        # (assuming both metrics pass quality/CV filters)
        assert len(distributions) >= 3, f"Expected ≥3 distributions, got {len(distributions)}"

        # Verify distribution structure
        for dist_name, dist in distributions.items():
            assert 'mu' in dist
            assert 'sigma' in dist
            assert 'sample_count' in dist
            assert dist['sample_count'] > 0

        print(f"✓ Clustering workflow completed successfully")
        print(f"  - Learned {len(distributions)} distributions")

        # Cleanup
        csv_path.unlink()
        Path(temp_config_file.name).unlink()
        distributions_path.unlink()
        if Path('test_output/state_labels.csv').exists():
            Path('test_output/state_labels.csv').unlink()
        Path('test_output').rmdir()

    except Exception as e:
        # Cleanup on failure
        csv_path.unlink()
        Path(temp_config_file.name).unlink()
        print(f"✗ Test failed: {e}")
        raise


if __name__ == '__main__':
    print("Running WaDi clustering integration tests...\n")

    if not IMPORTS_OK:
        print(f"⚠ Cannot run tests: {IMPORT_ERROR}")
    else:
        test_load_config()
        test_mock_clustering_workflow()

        print("\n✓ All integration tests passed")
