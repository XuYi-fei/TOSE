"""
WaDi sensor nomenclature parser.

Maps industrial sensor codes (ISA-5.1 standard) to physical measurements.
"""

from typing import Dict, Optional
import re


# Sensor type mapping based on ISA-5.1 standard
SENSOR_TYPE_MAPPING = {
    'LT': {
        'full_name': 'Level Transmitter',
        'measurement': 'level',
        'unit': 'm',
        'priority': 1
    },
    'FIT': {
        'full_name': 'Flow Indicator Transmitter',
        'measurement': 'flow',
        'unit': 'L/s',
        'priority': 3
    },
    'PIT': {
        'full_name': 'Pressure Indicator Transmitter',
        'measurement': 'pressure',
        'unit': 'bar',
        'priority': 2
    },
    'AIT': {
        'full_name': 'Analytical Instrument Transmitter',
        'measurement': 'analytical',
        'unit': 'pH/NTU',
        'priority': 1
    },
    'DPIT': {
        'full_name': 'Differential Pressure Indicator Transmitter',
        'measurement': 'pressure_delta',
        'unit': 'mbar',
        'priority': 1
    },
    'MV': {
        'full_name': 'Motorized Valve',
        'measurement': 'valve_position',
        'unit': '%',
        'priority': 0
    },
    'P': {
        'full_name': 'Pump',
        'measurement': 'pump_status',
        'unit': 'ON/OFF',
        'priority': 0
    }
}


def parse_sensor_type(column_name: str) -> Optional[Dict[str, str]]:
    """
    Parse WaDi column name to extract sensor information.

    WaDi column naming convention:
    - Format: HMI_<zone>_<sensor_type>_<number>.<suffix>
    - Example: HMI_2_FIT_001.PV
    - Zones: HMI_1 (input), HMI_2 (processing), HMI_3 (output)
    - Suffixes: .PV (process value), _STATUS (status), _CMD (command)

    Args:
        column_name: Column name from WaDi CSV (e.g., 'HMI_2_FIT_001.PV')

    Returns:
        dict: Sensor information with keys:
            - type: Sensor type code (e.g., 'FIT')
            - full_name: Full sensor name
            - measurement: Physical measurement type
            - unit: Measurement unit
            - zone: HMI zone (e.g., 'HMI_2')
            - number: Sensor instance number (e.g., '001')
            - suffix: Column suffix (e.g., 'PV' or 'STATUS')
            - priority: Domain priority for ranking (higher = more important)
        None: If column name doesn't match expected pattern

    Example:
        >>> info = parse_sensor_type('HMI_2_FIT_001.PV')
        >>> info['type']
        'FIT'
        >>> info['measurement']
        'flow'
        >>> info['zone']
        'HMI_2'
    """
    # Pattern: HMI_<zone>_<type>_<number>.<suffix> or HMI_<zone>_<type>_<number>_<suffix>
    pattern = r'HMI_(\d+)_([A-Z]+)_(\d+)[._](\w+)'
    match = re.match(pattern, column_name)

    if not match:
        return None

    zone_num, sensor_type, sensor_num, suffix = match.groups()

    # Get sensor type info from mapping
    sensor_info = SENSOR_TYPE_MAPPING.get(sensor_type)

    if not sensor_info:
        # Unknown sensor type
        return {
            'type': sensor_type,
            'full_name': f'Unknown Sensor {sensor_type}',
            'measurement': 'unknown',
            'unit': 'unknown',
            'zone': f'HMI_{zone_num}',
            'number': sensor_num,
            'suffix': suffix,
            'priority': 0
        }

    return {
        'type': sensor_type,
        'full_name': sensor_info['full_name'],
        'measurement': sensor_info['measurement'],
        'unit': sensor_info['unit'],
        'zone': f'HMI_{zone_num}',
        'number': sensor_num,
        'suffix': suffix,
        'priority': sensor_info['priority']
    }


def is_process_value_column(column_name: str) -> bool:
    """
    Check if column is a process value (PV) measurement.

    Args:
        column_name: Column name from WaDi CSV

    Returns:
        bool: True if column ends with .PV

    Example:
        >>> is_process_value_column('HMI_2_FIT_001.PV')
        True
        >>> is_process_value_column('HMI_2_P_001_STATUS')
        False
    """
    return column_name.endswith('.PV')


def is_status_column(column_name: str) -> bool:
    """
    Check if column is a status indicator.

    Args:
        column_name: Column name from WaDi CSV

    Returns:
        bool: True if column contains _STATUS

    Example:
        >>> is_status_column('HMI_2_P_001_STATUS')
        True
        >>> is_status_column('HMI_2_FIT_001.PV')
        False
    """
    return '_STATUS' in column_name


def get_pump_columns(all_columns: list) -> list:
    """
    Extract all pump status columns from column list.

    Args:
        all_columns: List of all column names in WaDi CSV

    Returns:
        list: Column names for pump status sensors

    Example:
        >>> cols = ['HMI_2_P_001_STATUS', 'HMI_2_FIT_001.PV', 'HMI_2_P_002_STATUS']
        >>> get_pump_columns(cols)
        ['HMI_2_P_001_STATUS', 'HMI_2_P_002_STATUS']
    """
    pump_columns = []

    for col in all_columns:
        sensor_info = parse_sensor_type(col)
        if sensor_info and sensor_info['type'] == 'P' and is_status_column(col):
            pump_columns.append(col)

    return sorted(pump_columns)


def group_by_zone(column_names: list) -> Dict[str, list]:
    """
    Group column names by HMI zone.

    Args:
        column_names: List of column names

    Returns:
        dict: Column names grouped by zone {'HMI_1': [...], 'HMI_2': [...], 'HMI_3': [...]}

    Example:
        >>> cols = ['HMI_1_FIT_001.PV', 'HMI_2_FIT_001.PV', 'HMI_2_PIT_001.PV']
        >>> groups = group_by_zone(cols)
        >>> groups['HMI_2']
        ['HMI_2_FIT_001.PV', 'HMI_2_PIT_001.PV']
    """
    zones = {}

    for col in column_names:
        sensor_info = parse_sensor_type(col)
        if sensor_info:
            zone = sensor_info['zone']
            if zone not in zones:
                zones[zone] = []
            zones[zone].append(col)

    return zones
