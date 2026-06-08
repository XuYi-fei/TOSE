"""Tests for WadiAdapter."""

import tempfile
from pathlib import Path
import numpy as np
import pandas as pd

from cluster_analysis.adapters.wadi.wadi_adapter import WadiAdapter


def create_mock_wadi_csv():
    """Create a temporary mock WaDi CSV file."""
    np.random.seed(42)

    df = pd.DataFrame({
        'Time': pd.date_range('2023-12-18 01:00:00', periods=1000, freq='1min'),
        'HMI_2_FIT_001.PV': np.random.normal(1.3, 0.15, 1000),
        'HMI_2_PIT_001.PV': np.random.normal(2.45, 0.10, 1000),
        'HMI_2_LT_001.PV': np.random.normal(3.5, 0.07, 1000),
        'HMI_3_AIT_001.PV': ['Bad Input' if i % 2 == 0 else np.random.normal(5, 0.5)
                             for i in range(1000)],
        'HMI_1_LT_002.PV': np.random.normal(10.0, 0.001, 1000),
        'HMI_2_P_001_STATUS': np.random.choice([0, 1], 1000),
        'HMI_2_P_002_STATUS': np.random.choice([0, 1], 1000)
    })

    # Create temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        df.to_csv(f.name, index=False)
        csv_path = f.name

    return csv_path


def test_wadi_adapter_load():
    """Test loading WaDi CSV data."""
    csv_path = create_mock_wadi_csv()

    try:
        adapter = WadiAdapter()
        df = adapter.load_identity_data(csv_path)

        assert len(df) == 1000
        assert 'Time' in df.columns
        assert df['Time'].dtype == 'datetime64[ns]'

        # Check that "Bad Input" was handled
        assert (df['HMI_3_AIT_001.PV'] == 'Bad Input').sum() == 0

        print(f"✓ Loaded {len(df)} rows with {len(df.columns)} columns")

    finally:
        Path(csv_path).unlink()


def test_load_and_rank_metrics():
    """
    Test loading WaDi CSV and ranking metrics.

    Expected from Task 2.3:
    - Loads data successfully
    - Returns top 3 metrics
    """
    csv_path = create_mock_wadi_csv()

    try:
        adapter = WadiAdapter(top_k=3)
        df = adapter.load_identity_data(csv_path)

        metrics = adapter.get_metrics()

        assert len(metrics) == 3
        assert 'HMI_2_FIT_001.PV' in metrics  # High priority + good variability
        assert 'HMI_2_PIT_001.PV' in metrics
        assert 'HMI_2_LT_001.PV' in metrics

        # Should exclude low quality metric
        assert 'HMI_3_AIT_001.PV' not in metrics

        # Should exclude too stable metric
        assert 'HMI_1_LT_002.PV' not in metrics

        print(f"✓ Selected metrics: {metrics}")

    finally:
        Path(csv_path).unlink()


def test_get_pump_columns():
    """Test extraction of pump status columns."""
    csv_path = create_mock_wadi_csv()

    try:
        adapter = WadiAdapter()
        adapter.load_identity_data(csv_path)

        pump_cols = adapter.get_pump_columns()

        assert len(pump_cols) == 2
        assert 'HMI_2_P_001_STATUS' in pump_cols
        assert 'HMI_2_P_002_STATUS' in pump_cols

        print(f"✓ Found {len(pump_cols)} pump columns: {pump_cols}")

    finally:
        Path(csv_path).unlink()


def test_group_by_zone():
    """Test grouping metrics by zone."""
    csv_path = create_mock_wadi_csv()

    try:
        adapter = WadiAdapter()
        adapter.load_identity_data(csv_path)

        groups = adapter.group_by_zone()

        # Should have metrics from HMI_2 zone
        assert 'HMI_2' in groups
        assert len(groups['HMI_2']) > 0

        print(f"✓ Grouped into zones: {list(groups.keys())}")

    finally:
        Path(csv_path).unlink()


def test_manual_override():
    """Test manual metric override."""
    csv_path = create_mock_wadi_csv()

    try:
        adapter = WadiAdapter(
            top_k=3,
            manual_include=['HMI_1_LT_002.PV'],
            manual_exclude=['HMI_2_LT_001.PV']
        )
        adapter.load_identity_data(csv_path)

        metrics = adapter.get_metrics()

        # Manual include should force inclusion even if too stable
        assert 'HMI_1_LT_002.PV' in metrics

        # Manual exclude should force exclusion
        assert 'HMI_2_LT_001.PV' not in metrics

        print(f"✓ Manual override applied: {metrics}")

    finally:
        Path(csv_path).unlink()


def test_load_identity_data_from_trace_directory():
    """Test loading a directory of trace CSV files as one identity dataset."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        trace_dir = root / 'identity'
        trace_dir.mkdir(parents=True, exist_ok=True)

        for file_idx, values in enumerate(([68.0, 68.1], [74.0, 74.1, 80.0])):
            df = pd.DataFrame({
                'time': [f'2023-12-18 00:00:0{i}' for i in range(len(values))],
                'HMI_2_LT_001.PV': values,
                'segment_label': ['norm1'] * len(values),
            })
            df.to_csv(trace_dir / f'trace_{file_idx:03d}.csv', index=False)

        adapter = WadiAdapter()
        df = adapter.load_identity_data(str(trace_dir))

        assert len(df) == 5
        assert 'HMI_2_LT_001.PV' in df.columns

        print(f"✓ Loaded trace directory with {len(df)} rows")


def test_from_config():
    """Test creating adapter from config dict."""
    config = {
        'top_k': 2,
        'quality_threshold': 0.7,
        'manual_include': ['HMI_1_LT_002.PV']
    }

    adapter = WadiAdapter.from_config(config)

    assert adapter.top_k == 2
    assert adapter.quality_threshold == 0.7
    assert 'HMI_1_LT_002.PV' in adapter.manual_include

    print("✓ Adapter created from config")


def test_parse_sensor_type():
    """Test sensor type parsing via adapter."""
    adapter = WadiAdapter()

    info = adapter.parse_sensor_type('HMI_2_FIT_001.PV')

    assert info['type'] == 'FIT'
    assert info['measurement'] == 'flow'
    assert info['zone'] == 'HMI_2'

    print(f"✓ Parsed sensor type: {info['type']} - {info['measurement']}")


if __name__ == '__main__':
    print("Running WadiAdapter tests...\n")

    test_wadi_adapter_load()
    test_load_and_rank_metrics()
    test_get_pump_columns()
    test_group_by_zone()
    test_manual_override()
    test_from_config()
    test_parse_sensor_type()

    print("\n✓ All WadiAdapter tests passed")
