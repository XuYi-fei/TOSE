"""Tests for WaDi sensor parser."""

from cluster_analysis.adapters.wadi.sensor_parser import (
    parse_sensor_type,
    is_process_value_column,
    is_status_column,
    get_pump_columns,
    group_by_zone
)


def test_parse_fit_column():
    """
    Test parsing flow indicator transmitter column.

    Expected from Task 2.1:
    'HMI_2_FIT_001.PV' → {'type': 'FIT', 'measurement': 'flow', 'zone': 'HMI_2'}
    """
    result = parse_sensor_type('HMI_2_FIT_001.PV')

    assert result is not None
    assert result['type'] == 'FIT'
    assert result['measurement'] == 'flow'
    assert result['unit'] == 'L/s'
    assert result['zone'] == 'HMI_2'
    assert result['number'] == '001'
    assert result['suffix'] == 'PV'
    assert result['full_name'] == 'Flow Indicator Transmitter'
    assert result['priority'] == 3  # FIT has high priority

    print(f"✓ Parsed FIT column: {result}")


def test_parse_pit_column():
    """Test parsing pressure indicator transmitter column."""
    result = parse_sensor_type('HMI_2_PIT_001.PV')

    assert result['type'] == 'PIT'
    assert result['measurement'] == 'pressure'
    assert result['unit'] == 'bar'
    assert result['priority'] == 2

    print(f"✓ Parsed PIT column: {result}")


def test_parse_lt_column():
    """Test parsing level transmitter column."""
    result = parse_sensor_type('HMI_2_LT_001.PV')

    assert result['type'] == 'LT'
    assert result['measurement'] == 'level'
    assert result['unit'] == 'm'
    assert result['priority'] == 1

    print(f"✓ Parsed LT column: {result}")


def test_parse_ait_column():
    """Test parsing analytical instrument transmitter column."""
    result = parse_sensor_type('HMI_3_AIT_002.PV')

    assert result['type'] == 'AIT'
    assert result['measurement'] == 'analytical'
    assert result['unit'] == 'pH/NTU'
    assert result['zone'] == 'HMI_3'

    print(f"✓ Parsed AIT column: {result}")


def test_parse_pump_status_column():
    """Test parsing pump status column."""
    result = parse_sensor_type('HMI_2_P_001_STATUS')

    assert result['type'] == 'P'
    assert result['measurement'] == 'pump_status'
    assert result['unit'] == 'ON/OFF'
    assert result['suffix'] == 'STATUS'

    print(f"✓ Parsed pump status column: {result}")


def test_parse_invalid_column():
    """Test parsing non-sensor column."""
    result = parse_sensor_type('Time')

    assert result is None

    print("✓ Correctly returned None for invalid column")


def test_is_process_value_column():
    """Test PV column identification."""
    assert is_process_value_column('HMI_2_FIT_001.PV') is True
    assert is_process_value_column('HMI_2_P_001_STATUS') is False

    print("✓ PV column identification works")


def test_is_status_column():
    """Test status column identification."""
    assert is_status_column('HMI_2_P_001_STATUS') is True
    assert is_status_column('HMI_2_FIT_001.PV') is False

    print("✓ Status column identification works")


def test_get_pump_columns():
    """Test extraction of pump status columns."""
    all_columns = [
        'Time',
        'HMI_2_P_001_STATUS',
        'HMI_2_FIT_001.PV',
        'HMI_2_P_002_STATUS',
        'HMI_1_P_001_STATUS',
        'HMI_2_PIT_001.PV'
    ]

    pump_cols = get_pump_columns(all_columns)

    assert len(pump_cols) == 3
    assert 'HMI_2_P_001_STATUS' in pump_cols
    assert 'HMI_2_P_002_STATUS' in pump_cols
    assert 'HMI_1_P_001_STATUS' in pump_cols
    assert 'HMI_2_FIT_001.PV' not in pump_cols  # Not a pump

    print(f"✓ Extracted {len(pump_cols)} pump columns: {pump_cols}")


def test_group_by_zone():
    """Test grouping columns by HMI zone."""
    columns = [
        'HMI_1_FIT_001.PV',
        'HMI_2_FIT_001.PV',
        'HMI_2_PIT_001.PV',
        'HMI_3_FIT_001.PV'
    ]

    groups = group_by_zone(columns)

    assert len(groups) == 3
    assert 'HMI_1' in groups
    assert 'HMI_2' in groups
    assert 'HMI_3' in groups
    assert len(groups['HMI_2']) == 2
    assert 'HMI_2_FIT_001.PV' in groups['HMI_2']
    assert 'HMI_2_PIT_001.PV' in groups['HMI_2']

    print(f"✓ Grouped into {len(groups)} zones: {list(groups.keys())}")


def test_sensor_priority_ranking():
    """Test that sensor types have correct priority for ranking."""
    fit_info = parse_sensor_type('HMI_2_FIT_001.PV')
    pit_info = parse_sensor_type('HMI_2_PIT_001.PV')
    lt_info = parse_sensor_type('HMI_2_LT_001.PV')

    # FIT (flow) should have highest priority
    assert fit_info['priority'] == 3
    assert pit_info['priority'] == 2
    assert lt_info['priority'] == 1

    print("✓ Sensor priority ranking: FIT=3, PIT=2, LT=1")


if __name__ == '__main__':
    print("Running sensor parser tests...\n")

    test_parse_fit_column()
    test_parse_pit_column()
    test_parse_lt_column()
    test_parse_ait_column()
    test_parse_pump_status_column()
    test_parse_invalid_column()
    test_is_process_value_column()
    test_is_status_column()
    test_get_pump_columns()
    test_group_by_zone()
    test_sensor_priority_ranking()

    print("\n✓ All sensor parser tests passed")
