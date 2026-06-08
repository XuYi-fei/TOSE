# Capability: Chunked Data Processing

**Capability ID:** `chunked_data_processing`
**Change:** `integrate-wadi-dataset-adapter`
**Status:** Proposed

## Overview

Chunked Data Processing enables memory-efficient loading and processing of large CSV files (290MB+) by reading data in fixed-size windows and computing statistics incrementally.

## ADDED Requirements

### Requirement: Read CSV in Fixed-Size Chunks

**ID:** `WADI-CHUNK-001`

The system SHALL load large CSV files in configurable chunk sizes to avoid memory overflow.

#### Scenario: Iterate Through 290MB CSV in 10k-Row Chunks

**Given** a WaDi CSV file with 1.7M rows and 141 columns (290MB)

**When** loaded with `ChunkedCSVReader(csv_path, chunk_size=10000)`

**Then** the system SHALL:
1. Yield DataFrames of 10,000 rows each (except last chunk)
2. Parse only timestamp and selected metric columns (not all 141)
3. Keep peak memory usage < 3GB
4. Complete full file iteration in <60 seconds

**Example**:
```python
reader = ChunkedCSVReader('data/wadi/WaDi.A3_Dec 2023 Historian Data_original.csv', chunk_size=10000)

chunk_count = 0
for chunk in reader.iter_chunks():
    assert len(chunk) <= 10000
    assert 'Time' in chunk.columns
    chunk_count += 1

assert chunk_count == 170  # 1.7M rows / 10k ≈ 170 chunks
```

#### Scenario: Select Columns to Reduce Memory

**Given** configuration specifying 5 metric columns out of 141 total

**When** chunks are read with `usecols` parameter

**Then** the system SHALL:
- Load only specified columns (Time + 5 metrics = 6 columns)
- Reduce memory per chunk by ~96% (6/141)
- Enable processing of 50k-row chunks instead of 10k

**Example**:
```python
reader = ChunkedCSVReader(
    csv_path,
    chunk_size=50000,
    usecols=['Time', 'HMI_2_FIT_001.PV', 'HMI_2_PIT_001.PV', 'HMI_2_LT_001.PV']
)
```

---

### Requirement: Incremental Statistics Computation

**ID:** `WADI-CHUNK-002`

The system SHALL compute dataset-wide statistics (mean, variance) incrementally across chunks using Welford's online algorithm to avoid two-pass reading.

#### Scenario: Compute Mean and Std Across Chunks

**Given** metric values split across multiple chunks:
```
Chunk 1: [1.0, 2.0, 3.0]
Chunk 2: [4.0, 5.0, 6.0]
Chunk 3: [7.0, 8.0, 9.0]
```

**When** incremental statistics are computed

**Then** the system SHALL:
1. Update running mean and M2 (sum of squared differences) after each chunk
2. Compute final mean = 5.0 and std = 2.738 (matching single-pass result)
3. Match within 0.1% of batch-computed statistics

**Welford's Algorithm**:
```python
class IncrementalStats:
    def __init__(self):
        self.count = 0
        self.mean = 0.0
        self.M2 = 0.0  # Sum of squared differences

    def update(self, new_value):
        self.count += 1
        delta = new_value - self.mean
        self.mean += delta / self.count
        delta2 = new_value - self.mean
        self.M2 += delta * delta2

    def variance(self):
        return self.M2 / self.count if self.count > 1 else 0.0

    def std(self):
        return math.sqrt(self.variance())
```

**Example**:
```python
stats = IncrementalStats()
for chunk in reader.iter_chunks():
    for value in chunk['HMI_2_FIT_001.PV']:
        stats.update(value)

assert abs(stats.mean - 5.0) < 0.001
assert abs(stats.std() - 2.738) < 0.001
```

---

### Requirement: Handle Chunk Boundary Artifacts

**ID:** `WADI-CHUNK-003`

The system SHALL provide overlapping chunk windows to avoid state transition artifacts at chunk boundaries.

#### Scenario: Overlap Chunks by 10% to Capture Transitions

**Given** a state transition occurring at row 10,005 (just after chunk 1 boundary)

**When** chunks are read with `overlap_rows=1000` (10% overlap)

**Then** the system SHALL:
1. Chunk 1: rows [0, 10000]
2. Chunk 2: rows [9000, 19000] (overlaps 1000 rows with chunk 1)
3. Include transition at row 10,005 in both chunks
4. Deduplicate overlapping rows after processing

**Example**:
```python
reader = ChunkedCSVReader(csv_path, chunk_size=10000, overlap_rows=1000)

chunk1, chunk2 = list(reader.iter_chunks())[:2]
assert chunk1.iloc[-1]['Time'] == chunk2.iloc[1000]['Time']  # Overlap verification
```

---

### Requirement: Monitor Memory Usage During Processing

**ID:** `WADI-CHUNK-004`

The system SHALL log peak memory usage and warn if approaching configured limit.

#### Scenario: Warn When Memory Exceeds 80% of Limit

**Given** a configured memory limit of 2048 MB

**When** chunk processing reaches 1640 MB (80% of limit)

**Then** the system SHALL:
- Log warning: "Memory usage at 80% (1640/2048 MB), consider reducing chunk size"
- Suggest new chunk size: current_size × (target_memory / current_memory)
- Continue processing (no crash)

**Example**:
```python
reader = ChunkedCSVReader(csv_path, chunk_size=10000, memory_limit_mb=2048)
reader.enable_memory_monitoring(warn_threshold=0.8)

for chunk in reader.iter_chunks():
    process_chunk(chunk)
    # Automatic memory warnings if threshold exceeded
```

---

### Requirement: Checkpoint Progress for Resumability

**ID:** `WADI-CHUNK-005`

The system SHALL save processing checkpoints to allow resuming from failures.

#### Scenario: Resume from Chunk 75 After Crash

**Given** a processing run that crashed at chunk 75 of 170

**When** restarted with `resume_from_checkpoint=True`

**Then** the system SHALL:
1. Load checkpoint file `processing_checkpoint.json`
2. Read `last_completed_chunk: 74`
3. Skip chunks 0-74 and resume from chunk 75
4. Update checkpoint after each chunk

**Checkpoint File Format**:
```json
{
  "csv_path": "data/wadi/WaDi.A3_Dec 2023 Historian Data_original.csv",
  "chunk_size": 10000,
  "last_completed_chunk": 74,
  "last_row_index": 749999,
  "statistics": {
    "HMI_2_FIT_001.PV": {"count": 750000, "mean": 1.205, "M2": 1200500.3}
  },
  "timestamp": "2026-01-18T14:23:45"
}
```

**Example**:
```python
reader = ChunkedCSVReader(csv_path, chunk_size=10000, checkpoint_path='checkpoint.json')

for chunk_idx, chunk in reader.iter_chunks(resume_from_checkpoint=True):
    process_chunk(chunk)
    reader.save_checkpoint(chunk_idx)  # Auto-save after each chunk
```

---

## Implementation Notes

### ChunkedCSVReader Class

```python
import pandas as pd
from pathlib import Path
from typing import Iterator, List, Optional

class ChunkedCSVReader:
    def __init__(
        self,
        csv_path: str,
        chunk_size: int = 10000,
        usecols: Optional[List[str]] = None,
        overlap_rows: int = 0,
        memory_limit_mb: int = 2048,
        checkpoint_path: Optional[str] = None
    ):
        self.csv_path = Path(csv_path)
        self.chunk_size = chunk_size
        self.usecols = usecols
        self.overlap_rows = overlap_rows
        self.memory_limit_mb = memory_limit_mb
        self.checkpoint_path = checkpoint_path

    def iter_chunks(self, resume_from_checkpoint: bool = False) -> Iterator[pd.DataFrame]:
        """Yield chunks with optional overlap and checkpointing"""
        start_row = 0
        if resume_from_checkpoint and self.checkpoint_path:
            checkpoint = self._load_checkpoint()
            start_row = checkpoint['last_row_index'] + 1

        for chunk in pd.read_csv(
            self.csv_path,
            chunksize=self.chunk_size,
            usecols=self.usecols,
            skiprows=range(1, start_row) if start_row > 0 else None
        ):
            yield chunk

    def _load_checkpoint(self) -> dict:
        with open(self.checkpoint_path, 'r') as f:
            return json.load(f)

    def save_checkpoint(self, chunk_idx: int, stats: dict):
        checkpoint = {
            'csv_path': str(self.csv_path),
            'chunk_size': self.chunk_size,
            'last_completed_chunk': chunk_idx,
            'last_row_index': (chunk_idx + 1) * self.chunk_size,
            'statistics': stats,
            'timestamp': datetime.now().isoformat()
        }
        with open(self.checkpoint_path, 'w') as f:
            json.dump(checkpoint, f, indent=2)
```

### Memory Monitoring

```python
import psutil

def monitor_memory_usage(threshold_pct: float, limit_mb: int):
    process = psutil.Process()
    mem_mb = process.memory_info().rss / 1024 / 1024

    if mem_mb > limit_mb * threshold_pct:
        logging.warning(f"Memory usage at {mem_mb:.0f}/{limit_mb} MB ({mem_mb/limit_mb*100:.0f}%)")
        return False
    return True
```

### Configuration Schema

```yaml
processing:
  chunk_size: 10000  # Rows per chunk
  overlap_rows: 1000  # Overlap for state transitions
  memory_limit_mb: 2048  # Memory ceiling
  memory_warn_threshold: 0.8  # Warn at 80%
  checkpoint:
    enabled: true
    path: processing_checkpoint.json
    save_interval: 10  # Save every 10 chunks
  selected_columns:  # Subset to reduce memory
    - Time
    - HMI_2_FIT_001.PV
    - HMI_2_PIT_001.PV
    - HMI_2_LT_001.PV
```

## Cross-References

- **Depends On**: None (foundational capability)
- **Enables**:
  - `wadi_metric_adapter` (memory-efficient CSV loading)
  - `multimodal_clustering` (chunked clustering processing)
- **Related**: `environment_state_detection` (state detection across chunks)

## Testing

### Unit Tests
- `test_chunked_iteration`: Large CSV → correct number of chunks
- `test_incremental_stats`: Split data → matches batch statistics
- `test_chunk_overlap`: Overlapping chunks → correct row ranges
- `test_memory_warning`: High memory → warning logged

### Integration Tests
- `test_resume_from_checkpoint`: Crash simulation → resume from correct chunk
- `test_full_file_processing`: 290MB CSV → completes without memory error

### Performance Tests
- `test_memory_limit_compliance`: Process full dataset → peak memory < 3GB
- `test_processing_time`: 290MB CSV → complete in <60 seconds
- `test_incremental_vs_batch_accuracy`: Incremental stats → <0.1% difference from batch
