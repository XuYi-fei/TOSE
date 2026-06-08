"""WaDi dataset adapter implementation."""

from pathlib import Path
from typing import List, Optional, Dict
import pandas as pd

from ..base_adapter import BaseAdapter
from ...utils import ChunkedCSVReader
from .sensor_parser import parse_sensor_type, is_process_value_column, get_pump_columns, group_by_zone
from .metric_selector import rank_metrics, rank_metrics_with_details, apply_manual_override


class WadiAdapter(BaseAdapter):
    """
    Adapter for WaDi (Water Distribution) industrial control system dataset.

    WaDi characteristics:
    - 141 columns (31 PV metrics, 50+ status/control, timestamp)
    - Industrial sensor nomenclature (LT/FIT/PIT/AIT/DPIT)
    - 290MB CSV files with 1.7M rows
    - 3-zone architecture (HMI_1, HMI_2, HMI_3)
    - "Bad Input" strings for invalid readings

    Example:
        >>> adapter = WadiAdapter()
        >>> df = adapter.load_identity_data('data/wadi/WaDi.A3_Dec 2023 Historian Data_original.csv')
        >>> metrics = adapter.get_metrics()
        >>> print(metrics)
        ['HMI_2_FIT_001.PV', 'HMI_2_PIT_001.PV', 'HMI_2_LT_001.PV']
    """

    def __init__(
        self,
        top_k: int = 3,
        quality_threshold: float = 0.8,
        cv_min: float = 0.01,
        cv_max: float = 2.0,
        manual_include: Optional[List[str]] = None,
        manual_exclude: Optional[List[str]] = None,
        chunk_size: int = 10000,
        memory_limit_mb: int = 2048
    ):
        """
        Initialize WaDi adapter.

        Args:
            top_k: Number of top metrics to select (default 3)
            quality_threshold: Minimum data completeness (default 0.8 = 80%)
            cv_min: Minimum CV to avoid static sensors (default 0.01)
            cv_max: Maximum CV to avoid noisy sensors (default 2.0)
            manual_include: Metrics to force include (default None)
            manual_exclude: Metrics to force exclude (default None)
            chunk_size: Rows per chunk for large files (default 10000)
            memory_limit_mb: Memory ceiling in MB (default 2048)
        """
        self.top_k = top_k
        self.quality_threshold = quality_threshold
        self.cv_min = cv_min
        self.cv_max = cv_max
        self.manual_include = manual_include or []
        self.manual_exclude = manual_exclude or []
        self.chunk_size = chunk_size
        self.memory_limit_mb = memory_limit_mb

        self._metrics: Optional[List[str]] = None
        self._pump_columns: Optional[List[str]] = None
        self._loaded_df: Optional[pd.DataFrame] = None

    def load_identity_data(self, data_path: str) -> pd.DataFrame:
        """
        Load WaDi identity (normal) data from CSV.

        Uses ChunkedCSVReader for memory-efficient loading if file is large.

        Args:
            data_path: Path to WaDi CSV file

        Returns:
            pd.DataFrame: Loaded and preprocessed data

        Raises:
            FileNotFoundError: If CSV file doesn't exist
        """
        csv_path = Path(data_path)

        if not csv_path.exists():
            raise FileNotFoundError(f"WaDi CSV not found: {data_path}")

        if csv_path.is_dir():
            csv_files = sorted(csv_path.glob('*.csv'))
            if not csv_files:
                raise FileNotFoundError(f"No CSV files found in directory: {data_path}")
            df = pd.concat([pd.read_csv(file) for file in csv_files], ignore_index=True)
        else:
            # Check file size to decide chunked vs direct loading
            file_size_mb = csv_path.stat().st_size / (1024 * 1024)

            if file_size_mb > 100:  # Use chunked loading for files > 100MB
                df = self._load_chunked(csv_path)
            else:
                df = pd.read_csv(csv_path)

        # Preprocess
        df = self.preprocess(df)

        # Cache for metric selection
        self._loaded_df = df

        return df

    def _load_chunked(self, csv_path: Path) -> pd.DataFrame:
        """
        Load large CSV using ChunkedCSVReader.

        Args:
            csv_path: Path to CSV file

        Returns:
            pd.DataFrame: Concatenated chunks
        """
        reader = ChunkedCSVReader(
            str(csv_path),
            chunk_size=self.chunk_size,
            memory_limit_mb=self.memory_limit_mb
        )

        chunks = []
        for chunk in reader.iter_chunks():
            chunks.append(chunk)

        return pd.concat(chunks, ignore_index=True)

    def load_abnormal_data(self, data_path: str) -> pd.DataFrame:
        """
        Load WaDi abnormal data.

        Args:
            data_path: Path to abnormal CSV file

        Returns:
            pd.DataFrame: Loaded abnormal data
        """
        # Same loading logic as identity data
        return self.load_identity_data(data_path)

    def rank_metrics(self) -> List[Dict]:
        """
        Get ranked metrics with detailed scoring information.

        Returns detailed ranking with quality, CV, and scores for each metric.

        Returns:
            list: List of dicts with keys: metric, quality, cv, priority, score
                  Sorted by score in descending order

        Example:
            >>> adapter = WadiAdapter(top_k=3)
            >>> adapter.load_identity_data('data/wadi/WaDi.csv')
            >>> ranked = adapter.rank_metrics()
            >>> ranked[0]
            {'metric': 'HMI_2_FIT_001.PV', 'quality': 0.95, 'cv': 0.85, 'priority': 3, 'score': 2.42}
        """
        if self._loaded_df is None:
            raise ValueError("Must call load_identity_data() before rank_metrics()")

        # Use rank_metrics_with_details to get full ranking info
        details = rank_metrics_with_details(
            self._loaded_df,
            top_k=self.top_k,
            quality_threshold=self.quality_threshold,
            cv_min=self.cv_min,
            cv_max=self.cv_max
        )

        # Rename 'column' to 'metric' and 'completeness' to 'quality'
        return [
            {
                'metric': d['column'],
                'quality': d['completeness'],
                'cv': d['cv'],
                'priority': d['priority'],
                'score': d['score']
            }
            for d in details
        ]

    def get_metrics(self) -> List[str]:
        """
        Get selected metrics for clustering.

        Automatically ranks metrics by quality × variability × priority,
        then applies manual overrides if configured.

        Returns:
            list: Selected metric column names

        Example:
            >>> adapter = WadiAdapter(top_k=3)
            >>> adapter.load_identity_data('data/wadi/WaDi.csv')
            >>> adapter.get_metrics()
            ['HMI_2_FIT_001.PV', 'HMI_2_PIT_001.PV', 'HMI_2_LT_001.PV']
        """
        if self._metrics is not None:
            return self._metrics

        # Get auto-ranked metrics (extract column names from detailed ranking)
        ranked_details = self.rank_metrics()
        auto_ranked = [d['metric'] for d in ranked_details]

        # Apply manual overrides
        self._metrics = apply_manual_override(
            auto_ranked,
            manual_include=self.manual_include,
            manual_exclude=self.manual_exclude,
            max_metrics=self.top_k
        )

        return self._metrics

    def get_pump_columns(self) -> List[str]:
        """
        Get pump status columns for environment state detection.

        Returns:
            list: Pump status column names

        Example:
            >>> adapter.get_pump_columns()
            ['HMI_2_P_001_STATUS', 'HMI_2_P_002_STATUS']
        """
        if self._pump_columns is not None:
            return self._pump_columns

        if self._loaded_df is None:
            raise ValueError("Must call load_identity_data() first")

        self._pump_columns = get_pump_columns(self._loaded_df.columns.tolist())

        return self._pump_columns

    def group_by_zone(self, metrics: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """
        Group metrics by HMI zone.

        Args:
            metrics: Metric list to group (default: use self.get_metrics())

        Returns:
            dict: Metrics grouped by zone {'HMI_1': [...], 'HMI_2': [...], 'HMI_3': [...]}

        Example:
            >>> adapter.group_by_zone()
            {'HMI_2': ['HMI_2_FIT_001.PV', 'HMI_2_PIT_001.PV', 'HMI_2_LT_001.PV']}
        """
        if metrics is None:
            metrics = self.get_metrics()

        return group_by_zone(metrics)

    def parse_sensor_type(self, column_name: str) -> Optional[Dict[str, str]]:
        """
        Parse sensor information from column name.

        Args:
            column_name: Column name (e.g., 'HMI_2_FIT_001.PV')

        Returns:
            dict: Sensor info with type, measurement, unit, zone, etc.
            None: If column doesn't match pattern

        Example:
            >>> adapter.parse_sensor_type('HMI_2_FIT_001.PV')
            {'type': 'FIT', 'measurement': 'flow', 'unit': 'L/s', 'zone': 'HMI_2', ...}
        """
        return parse_sensor_type(column_name)

    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess WaDi data.

        Preprocessing steps:
        1. Parse timestamp column
        2. Handle "Bad Input" strings (convert to NaN)
        3. Convert numeric columns to float

        Args:
            df: Raw DataFrame

        Returns:
            pd.DataFrame: Preprocessed DataFrame
        """
        # Parse timestamp
        if 'Time' in df.columns:
            df['Time'] = pd.to_datetime(df['Time'])

        # Handle "Bad Input" in all PV columns
        pv_columns = [col for col in df.columns if is_process_value_column(col)]

        for col in pv_columns:
            # Replace "Bad Input" with NaN
            df[col] = df[col].replace('Bad Input', pd.NA)

            # Convert to numeric
            df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    @classmethod
    def from_config(cls, config: Dict) -> 'WadiAdapter':
        """
        Create WadiAdapter from configuration dict.

        Args:
            config: Configuration dictionary

        Returns:
            WadiAdapter: Configured adapter instance

        Example:
            >>> config = {
            ...     'top_k': 3,
            ...     'manual_include': ['HMI_1_LT_002.PV'],
            ...     'manual_exclude': ['HMI_3_AIT_001.PV']
            ... }
            >>> adapter = WadiAdapter.from_config(config)
        """
        return cls(
            top_k=config.get('top_k', 3),
            quality_threshold=config.get('quality_threshold', 0.8),
            cv_min=config.get('cv_min', 0.01),
            cv_max=config.get('cv_max', 2.0),
            manual_include=config.get('manual_include'),
            manual_exclude=config.get('manual_exclude'),
            chunk_size=config.get('chunk_size', 10000),
            memory_limit_mb=config.get('memory_limit_mb', 2048)
        )
