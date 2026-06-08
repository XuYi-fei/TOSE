"""Tests for ChunkedCSVReader."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from cluster_analysis.utils import ChunkedCSVReader


class TestChunkedCSVReader:
    """Test suite for ChunkedCSVReader."""

    @pytest.fixture
    def sample_csv(self):
        """Create a temporary CSV file with test data."""
        df = pd.DataFrame({
            'Time': pd.date_range('2023-01-01', periods=25000, freq='1min'),
            'metric1': range(25000),
            'metric2': [x * 2 for x in range(25000)],
            'metric3': [x * 3 for x in range(25000)]
        })

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            df.to_csv(f.name, index=False)
            csv_path = f.name

        yield csv_path

        # Cleanup
        Path(csv_path).unlink()

    def test_basic_chunked_reading(self, sample_csv):
        """Test basic chunked iteration with default chunk size."""
        reader = ChunkedCSVReader(sample_csv, chunk_size=10000)

        chunks = list(reader.iter_chunks())

        assert len(chunks) == 3  # 25000 / 10000 = 3 chunks (10k, 10k, 5k)
        assert len(chunks[0]) == 10000
        assert len(chunks[1]) == 10000
        assert len(chunks[2]) == 5000

    def test_column_selection(self, sample_csv):
        """Test loading only selected columns."""
        reader = ChunkedCSVReader(
            sample_csv,
            chunk_size=10000,
            usecols=['Time', 'metric1']
        )

        chunk = next(reader.iter_chunks())

        assert list(chunk.columns) == ['Time', 'metric1']
        assert 'metric2' not in chunk.columns

    def test_overlapping_chunks(self, sample_csv):
        """Test chunk overlap to avoid boundary artifacts."""
        reader = ChunkedCSVReader(
            sample_csv,
            chunk_size=10000,
            overlap_rows=1000
        )

        chunks = list(reader.iter_chunks())

        # First chunk: 10000 rows
        assert len(chunks[0]) == 10000

        # Second chunk: 1000 (overlap) + 10000 = 11000 rows
        assert len(chunks[1]) == 11000

        # Verify overlap: last 1000 rows of chunk 0 == first 1000 rows of chunk 1
        # (after accounting for overlap being prepended)
        assert chunks[0].iloc[-1]['metric1'] == chunks[1].iloc[999]['metric1']

    def test_checkpoint_save_and_load(self, sample_csv):
        """Test checkpoint save and resume functionality."""
        checkpoint_path = tempfile.mktemp(suffix='.json')

        reader = ChunkedCSVReader(
            sample_csv,
            chunk_size=10000,
            checkpoint_path=checkpoint_path
        )

        # Process first chunk and save checkpoint
        for idx, chunk in enumerate(reader.iter_chunks()):
            if idx == 0:
                reader.save_checkpoint(idx, stats={'count': len(chunk)})
                break

        # Verify checkpoint file was created
        assert Path(checkpoint_path).exists()

        # Verify checkpoint can be loaded
        checkpoint = reader._load_checkpoint()
        assert checkpoint['last_completed_chunk'] == 0
        assert checkpoint['chunk_size'] == 10000
        assert checkpoint['statistics']['count'] == 10000

        # Cleanup
        Path(checkpoint_path).unlink()

    def test_file_not_found(self):
        """Test error handling for missing CSV file."""
        with pytest.raises(FileNotFoundError):
            ChunkedCSVReader('nonexistent.csv')

    def test_total_row_count(self, sample_csv):
        """Test that all rows are read across chunks."""
        reader = ChunkedCSVReader(sample_csv, chunk_size=7000)

        total_rows = sum(len(chunk) for chunk in reader.iter_chunks())

        assert total_rows == 25000

    def test_checkpoint_without_path(self, sample_csv):
        """Test that save_checkpoint raises error without checkpoint_path."""
        reader = ChunkedCSVReader(sample_csv, chunk_size=10000)

        with pytest.raises(ValueError, match="checkpoint_path must be set"):
            reader.save_checkpoint(0)


@pytest.mark.skipif(
    not Path('data/wadi/WaDi.A3_Dec 2023 Historian Data_original.csv').exists(),
    reason="WaDi CSV not found"
)
def test_iterate_wadi_csv():
    """
    Integration test: Process full WaDi CSV in chunks.

    Expected: Processes 290MB CSV in ~170 chunks, peak memory < 3GB
    """
    csv_path = 'data/wadi/WaDi.A3_Dec 2023 Historian Data_original.csv'

    reader = ChunkedCSVReader(
        csv_path,
        chunk_size=10000,
        usecols=['Time', 'HMI_2_FIT_001.PV', 'HMI_2_PIT_001.PV', 'HMI_2_LT_001.PV']
    )

    chunk_count = 0
    total_rows = 0

    for chunk in reader.iter_chunks():
        assert len(chunk) <= 10000
        assert 'Time' in chunk.columns
        chunk_count += 1
        total_rows += len(chunk)

    # WaDi has approximately 1.7M rows
    assert chunk_count >= 170
    assert total_rows >= 1700000
