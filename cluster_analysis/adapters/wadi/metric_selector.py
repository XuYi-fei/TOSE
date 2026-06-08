"""
WaDi metric selection and ranking algorithm.

Automatically selects top K metrics from 31 candidates based on:
1. Data quality (completeness)
2. Variability (coefficient of variation)
3. Domain priority (sensor type importance)
"""

from typing import List, Dict, Optional
import numpy as np
import pandas as pd

from .sensor_parser import parse_sensor_type, is_process_value_column


def compute_data_quality(series: pd.Series) -> Dict[str, float]:
    """
    Compute data quality metrics for a column.

    Args:
        series: Data column from WaDi CSV

    Returns:
        dict: Quality metrics with keys:
            - completeness: Fraction of valid (non-NaN, non-"Bad Input") values
            - bad_input_ratio: Fraction of "Bad Input" strings
            - nan_ratio: Fraction of NaN values
            - valid_count: Number of valid numeric values

    Example:
        >>> data = pd.Series([1.0, 2.0, "Bad Input", 3.0, np.nan])
        >>> quality = compute_data_quality(data)
        >>> quality['completeness']  # 3/5 = 0.6
        0.6
    """
    total_count = len(series)

    if total_count == 0:
        return {
            'completeness': 0.0,
            'bad_input_ratio': 0.0,
            'nan_ratio': 0.0,
            'valid_count': 0
        }

    # Count "Bad Input" strings
    bad_input_mask = (series == 'Bad Input')
    bad_input_count = bad_input_mask.sum()

    # Convert to numeric, coercing errors to NaN
    numeric_series = pd.to_numeric(series, errors='coerce')

    # Count NaN values (excluding those that were "Bad Input")
    nan_mask = numeric_series.isna() & ~bad_input_mask
    nan_count = nan_mask.sum()

    valid_count = total_count - bad_input_count - nan_count
    completeness = valid_count / total_count

    return {
        'completeness': completeness,
        'bad_input_ratio': bad_input_count / total_count,
        'nan_ratio': nan_count / total_count,
        'valid_count': valid_count
    }


def compute_coefficient_of_variation(series: pd.Series) -> float:
    """
    Compute coefficient of variation (CV = std / mean).

    CV measures relative variability. Too low (<0.01) indicates static sensor,
    too high (>2.0) indicates noisy data.

    Args:
        series: Numeric data series

    Returns:
        float: Coefficient of variation, or 0.0 if mean is zero

    Example:
        >>> data = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        >>> cv = compute_coefficient_of_variation(data)
        >>> 0.4 < cv < 0.6  # mean=3, std≈1.41, cv≈0.47
        True
    """
    # Convert to numeric, filter out NaN and "Bad Input"
    numeric_series = pd.to_numeric(series, errors='coerce').dropna()

    if len(numeric_series) < 2:
        return 0.0

    mean = numeric_series.mean()
    std = numeric_series.std()

    if mean == 0 or np.isnan(mean):
        return 0.0

    return abs(std / mean)


def rank_metrics(
    df: pd.DataFrame,
    top_k: int = 3,
    quality_threshold: float = 0.8,
    cv_min: float = 0.01,
    cv_max: float = 2.0,
    domain_priorities: Optional[Dict[str, int]] = None
) -> List[str]:
    """
    Rank and select top K metrics from WaDi CSV.

    Ranking formula:
        score = completeness × min(cv, 1.0) × priority

    Args:
        df: WaDi DataFrame with all columns
        top_k: Number of top metrics to return (default 3)
        quality_threshold: Minimum completeness to consider (default 0.8)
        cv_min: Minimum CV to filter out static sensors (default 0.01)
        cv_max: Maximum CV to filter out noisy sensors (default 2.0)
        domain_priorities: Sensor type priority weights (default: FIT=3, PIT=2, LT=1, AIT=1)

    Returns:
        list: Top K metric column names sorted by score (highest first)

    Example:
        >>> ranked = rank_metrics(df, top_k=3)
        >>> ranked
        ['HMI_2_FIT_001.PV', 'HMI_2_PIT_001.PV', 'HMI_2_LT_001.PV']
    """
    if domain_priorities is None:
        domain_priorities = {
            'FIT': 3,  # Flow - high priority
            'PIT': 2,  # Pressure - medium priority
            'LT': 1,   # Level - low priority
            'AIT': 1,  # Analytical - low priority
            'DPIT': 1  # Differential pressure - low priority
        }

    # Filter to process value columns only
    pv_columns = [col for col in df.columns if is_process_value_column(col)]

    metric_scores = []

    for col in pv_columns:
        # Parse sensor type
        sensor_info = parse_sensor_type(col)
        if not sensor_info:
            continue

        # Compute quality
        quality = compute_data_quality(df[col])

        # Filter by completeness threshold
        if quality['completeness'] < quality_threshold:
            continue

        # Compute variability
        cv = compute_coefficient_of_variation(df[col])

        # Filter by CV range (too stable or too noisy)
        if cv < cv_min or cv > cv_max:
            continue

        # Get domain priority
        sensor_type = sensor_info['type']
        priority = domain_priorities.get(sensor_type, 1)

        # Compute score: completeness × min(cv, 1.0) × priority
        score = quality['completeness'] * min(cv, 1.0) * priority

        metric_scores.append({
            'column': col,
            'score': score,
            'completeness': quality['completeness'],
            'cv': cv,
            'priority': priority,
            'sensor_type': sensor_type,
            'zone': sensor_info['zone']
        })

    # Sort by score (highest first)
    metric_scores.sort(key=lambda x: x['score'], reverse=True)

    # Return top K column names
    return [m['column'] for m in metric_scores[:top_k]]


def rank_metrics_with_details(
    df: pd.DataFrame,
    top_k: int = 3,
    **kwargs
) -> List[Dict]:
    """
    Rank metrics and return detailed scoring information.

    Args:
        df: WaDi DataFrame
        top_k: Number of top metrics to return
        **kwargs: Additional parameters passed to rank_metrics()

    Returns:
        list: List of dicts with column, score, completeness, cv, priority, sensor_type, zone

    Example:
        >>> details = rank_metrics_with_details(df, top_k=3)
        >>> details[0]['column']
        'HMI_2_FIT_001.PV'
        >>> details[0]['score']
        2.85
    """
    quality_threshold = kwargs.get('quality_threshold', 0.8)
    cv_min = kwargs.get('cv_min', 0.01)
    cv_max = kwargs.get('cv_max', 2.0)
    domain_priorities = kwargs.get('domain_priorities')

    if domain_priorities is None:
        domain_priorities = {
            'FIT': 3,
            'PIT': 2,
            'LT': 1,
            'AIT': 1,
            'DPIT': 1
        }

    pv_columns = [col for col in df.columns if is_process_value_column(col)]
    metric_scores = []

    for col in pv_columns:
        sensor_info = parse_sensor_type(col)
        if not sensor_info:
            continue

        quality = compute_data_quality(df[col])

        if quality['completeness'] < quality_threshold:
            continue

        cv = compute_coefficient_of_variation(df[col])

        if cv < cv_min or cv > cv_max:
            continue

        sensor_type = sensor_info['type']
        priority = domain_priorities.get(sensor_type, 1)
        score = quality['completeness'] * min(cv, 1.0) * priority

        metric_scores.append({
            'column': col,
            'score': score,
            'completeness': quality['completeness'],
            'cv': cv,
            'priority': priority,
            'sensor_type': sensor_type,
            'zone': sensor_info['zone']
        })

    metric_scores.sort(key=lambda x: x['score'], reverse=True)

    return metric_scores[:top_k]


def apply_manual_override(
    auto_ranked: List[str],
    manual_include: Optional[List[str]] = None,
    manual_exclude: Optional[List[str]] = None,
    max_metrics: int = 3
) -> List[str]:
    """
    Apply manual metric overrides to automatic ranking.

    Args:
        auto_ranked: Automatically ranked metric list
        manual_include: Metrics to force include (even if not in top K)
        manual_exclude: Metrics to force exclude (even if in top K)
        max_metrics: Maximum number of metrics to return

    Returns:
        list: Final metric list with overrides applied

    Example:
        >>> auto = ['HMI_2_FIT_001.PV', 'HMI_2_PIT_001.PV', 'HMI_2_LT_001.PV']
        >>> manual_include = ['HMI_1_LT_002.PV']
        >>> manual_exclude = ['HMI_2_LT_001.PV']
        >>> result = apply_manual_override(auto, manual_include, manual_exclude)
        >>> 'HMI_1_LT_002.PV' in result
        True
        >>> 'HMI_2_LT_001.PV' not in result
        True
    """
    if manual_include is None:
        manual_include = []
    if manual_exclude is None:
        manual_exclude = []

    # Start with auto-ranked, excluding manual exclusions
    result = [m for m in auto_ranked if m not in manual_exclude]

    # Add manual inclusions (if not already present)
    for metric in manual_include:
        if metric not in result:
            result.append(metric)

    # Limit to max_metrics
    return result[:max_metrics]
