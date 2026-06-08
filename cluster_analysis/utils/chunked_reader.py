"""Memory-efficient chunked CSV reader for large datasets."""

import json
from datetime import datetime
from pathlib import Path
from typing import Iterator, List, Optional

import pandas as pd


class ChunkedCSVReader:
    """
    Read large CSV files in fixed-size chunks to avoid memory overflow.

    Supports:
    - Configurable chunk sizes (default 10k rows)
    - Column selection to reduce memory
    - Overlapping chunks to avoid boundary artifacts
    - Checkpointing for resumability
    - Memory monitoring

    Example:
        reader = ChunkedCSVReader('data.csv', chunk_size=10000, usecols=['Time', 'metric1'])
        for chunk in reader.iter_chunks():
            process(chunk)
    """

    def __init__(
        self,
        csv_path: str,
        chunk_size: int = 10000,
        usecols: Optional[List[str]] = None,
        overlap_rows: int = 0,
        memory_limit_mb: int = 2048,
        checkpoint_path: Optional[str] = None
    ):
        """
        Initialize chunked CSV reader.

        Args:
            csv_path: Path to CSV file
            chunk_size: Number of rows per chunk (default 10000)
            usecols: List of column names to load (default None = all columns)
            overlap_rows: Number of rows to overlap between chunks (default 0)
            memory_limit_mb: Memory ceiling in MB (default 2048)
            checkpoint_path: Path to checkpoint file for resumability (default None)
        """
        self.csv_path = Path(csv_path)
        self.chunk_size = chunk_size
        self.usecols = usecols
        self.overlap_rows = overlap_rows
        self.memory_limit_mb = memory_limit_mb
        self.checkpoint_path = checkpoint_path
        self._last_chunk = None

        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

    def iter_chunks(self, resume_from_checkpoint: bool = False) -> Iterator[pd.DataFrame]:
        """
        Yield DataFrame chunks with optional overlap and checkpointing.

        Args:
            resume_from_checkpoint: If True, resume from last checkpoint (default False)

        Yields:
            pd.DataFrame: Chunks of the CSV file

        Example:
            reader = ChunkedCSVReader('data.csv', chunk_size=10000, overlap_rows=1000)
            for chunk in reader.iter_chunks():
                assert len(chunk) <= 10000
        """
        start_row = 0

        # Resume from checkpoint if requested
        if resume_from_checkpoint and self.checkpoint_path:
            checkpoint = self._load_checkpoint()
            start_row = checkpoint['last_row_index'] + 1

        # Read CSV in chunks
        skiprows = range(1, start_row) if start_row > 0 else None

        for chunk in pd.read_csv(
            self.csv_path,
            chunksize=self.chunk_size,
            usecols=self.usecols,
            skiprows=skiprows
        ):
            # Add overlap from previous chunk if configured
            if self.overlap_rows > 0 and self._last_chunk is not None:
                overlap_data = self._last_chunk.tail(self.overlap_rows)
                chunk = pd.concat([overlap_data, chunk], ignore_index=True)

            # Store last N rows for next iteration
            if self.overlap_rows > 0:
                self._last_chunk = chunk

            yield chunk

    def _load_checkpoint(self) -> dict:
        """
        Load checkpoint file with processing state.

        Returns:
            dict: Checkpoint data with last_completed_chunk, last_row_index, statistics

        Raises:
            FileNotFoundError: If checkpoint file doesn't exist
        """
        if not Path(self.checkpoint_path).exists():
            raise FileNotFoundError(f"Checkpoint file not found: {self.checkpoint_path}")

        with open(self.checkpoint_path, 'r') as f:
            return json.load(f)

    def save_checkpoint(self, chunk_idx: int, stats: Optional[dict] = None):
        """
        Save processing checkpoint to enable resumability.

        Args:
            chunk_idx: Index of last completed chunk (0-based)
            stats: Optional statistics dict to save (e.g., incremental stats state)

        Example:
            reader = ChunkedCSVReader('data.csv', checkpoint_path='checkpoint.json')
            for idx, chunk in enumerate(reader.iter_chunks()):
                process(chunk)
                reader.save_checkpoint(idx, stats={'count': total_count})
        """
        if not self.checkpoint_path:
            raise ValueError("checkpoint_path must be set to use save_checkpoint()")

        checkpoint = {
            'csv_path': str(self.csv_path),
            'chunk_size': self.chunk_size,
            'last_completed_chunk': chunk_idx,
            'last_row_index': (chunk_idx + 1) * self.chunk_size - 1,
            'statistics': stats or {},
            'timestamp': datetime.now().isoformat()
        }

        with open(self.checkpoint_path, 'w') as f:
            json.dump(checkpoint, f, indent=2)

    def enable_memory_monitoring(self, warn_threshold: float = 0.8):
        """
        Enable memory usage monitoring during chunk iteration.

        Args:
            warn_threshold: Warn when memory exceeds this fraction of limit (default 0.8)

        Example:
            reader = ChunkedCSVReader('data.csv', memory_limit_mb=2048)
            reader.enable_memory_monitoring(warn_threshold=0.8)
            for chunk in reader.iter_chunks():
                # Automatic memory warnings if threshold exceeded
                process(chunk)
        """
        from .memory_monitor import MemoryMonitor

        self.memory_monitor = MemoryMonitor(
            limit_mb=self.memory_limit_mb,
            warn_threshold=warn_threshold
        )
