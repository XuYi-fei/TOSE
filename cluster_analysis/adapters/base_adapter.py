"""Base adapter interface for dataset-specific trace loading and parsing."""

from abc import ABC, abstractmethod
from typing import List, Optional
import pandas as pd


class BaseAdapter(ABC):
    """
    Abstract base class for dataset adapters.

    Each dataset (RUBIS, BSN, SWAT, WaDi) has unique file formats and naming conventions.
    Adapters provide a unified interface for:
    - Loading identity/abnormal trace data
    - Parsing metric names
    - Selecting relevant metrics for clustering
    """

    @abstractmethod
    def load_identity_data(self, data_path: str) -> pd.DataFrame:
        """
        Load identity (normal behavior) data for clustering.

        Args:
            data_path: Path to identity dataset (file or directory)

        Returns:
            pd.DataFrame: Loaded data with parsed timestamps and metrics

        Raises:
            FileNotFoundError: If data path doesn't exist
        """
        pass

    @abstractmethod
    def load_abnormal_data(self, data_path: str) -> pd.DataFrame:
        """
        Load abnormal data for testing detection.

        Args:
            data_path: Path to abnormal dataset (file or directory)

        Returns:
            pd.DataFrame: Loaded data with parsed timestamps and metrics

        Raises:
            FileNotFoundError: If data path doesn't exist
        """
        pass

    @abstractmethod
    def get_metrics(self) -> List[str]:
        """
        Get list of metric column names for clustering.

        Returns:
            list: Column names of metrics to cluster

        Example:
            >>> adapter = WadiAdapter()
            >>> adapter.get_metrics()
            ['HMI_2_FIT_001.PV', 'HMI_2_PIT_001.PV', 'HMI_2_LT_001.PV']
        """
        pass

    def get_timestamp_column(self) -> str:
        """
        Get name of timestamp column.

        Returns:
            str: Name of timestamp column (default 'Time')
        """
        return 'Time'

    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply dataset-specific preprocessing.

        Args:
            df: Raw loaded DataFrame

        Returns:
            pd.DataFrame: Preprocessed DataFrame

        Default implementation does nothing. Override for custom preprocessing.
        """
        return df
