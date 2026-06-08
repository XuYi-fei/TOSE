#!/usr/bin/env python3
"""Build a WaDi trace-style dataset from the raw normal-operation CSV."""

from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


LOW_THRESHOLD = 71.1
HIGH_THRESHOLD = 77.4
DEFAULT_MEAN_SHIFT = 6.0
METRIC_COLUMN = "HMI_2_LT_001.PV"
TIME_COLUMN = "Time"
FALLBACK_TIME_COLUMNS = ("timestamp", "datetime", "date")

STATE_TO_NORM = {
    "low": "norm1",
    "normal": "norm2",
    "high": "norm3",
}
NORM_TO_STATE = {value: key for key, value in STATE_TO_NORM.items()}


@dataclass(frozen=True)
class SourcePoint:
    row_index: int
    time: str
    value: float
    state: str


@dataclass(frozen=True)
class StateSegment:
    state: str
    start_index: int
    end_index: int
    points: List[SourcePoint]

    @property
    def length(self) -> int:
        return len(self.points)


@dataclass(frozen=True)
class Window:
    window_id: str
    state: str
    source_row_start: int
    source_row_end: int
    source_time_start: str
    source_time_end: str
    values: List[float]
    times: List[str]


def classify_state(value: float, low_threshold: float = LOW_THRESHOLD, high_threshold: float = HIGH_THRESHOLD) -> str:
    if value < low_threshold:
        return "low"
    if value < high_threshold:
        return "normal"
    return "high"


def resolve_time_column(fieldnames: List[str] | None) -> str:
    if not fieldnames:
        raise ValueError("Source CSV has no header row")

    if TIME_COLUMN in fieldnames:
        return TIME_COLUMN

    for fieldname in fieldnames:
        if fieldname and fieldname.lower() in FALLBACK_TIME_COLUMNS:
            return fieldname

    if fieldnames[0] == "":
        return ""

    raise ValueError(f"Missing required time column: {TIME_COLUMN}")


def load_source_points(source_csv: Path) -> tuple[List[SourcePoint], str]:
    points: List[SourcePoint] = []
    with source_csv.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if METRIC_COLUMN not in reader.fieldnames:
            raise ValueError(f"Missing required metric column: {METRIC_COLUMN}")
        time_column = resolve_time_column(reader.fieldnames)

        for row_index, row in enumerate(reader):
            try:
                value = float(row[METRIC_COLUMN])
            except (TypeError, ValueError):
                continue
            points.append(
                SourcePoint(
                    row_index=row_index,
                    time=row[time_column],
                    value=value,
                    state=classify_state(value),
                )
            )

    if not points:
        raise ValueError("No valid WaDi points found in source CSV")
    return points, time_column


def build_state_segments(points: List[SourcePoint]) -> List[StateSegment]:
    segments: List[StateSegment] = []
    current: List[SourcePoint] = []
    current_state: Optional[str] = None

    for point in points:
        if current_state is None or point.state == current_state:
            current_state = point.state
            current.append(point)
            continue

        segments.append(
            StateSegment(
                state=current_state,
                start_index=current[0].row_index,
                end_index=current[-1].row_index,
                points=current,
            )
        )
        current_state = point.state
        current = [point]

    if current:
        segments.append(
            StateSegment(
                state=current_state or current[0].state,
                start_index=current[0].row_index,
                end_index=current[-1].row_index,
                points=current,
            )
        )

    return segments


def build_window_pools(segments: List[StateSegment], segment_len: int) -> Dict[str, List[Window]]:
    pools: Dict[str, List[Window]] = {"low": [], "normal": [], "high": []}

    for segment_idx, segment in enumerate(segments):
        n_windows = segment.length // segment_len
        for window_idx in range(n_windows):
            start = window_idx * segment_len
            chunk = segment.points[start : start + segment_len]
            window = Window(
                window_id=f"{segment.state}-seg{segment_idx:04d}-win{window_idx:02d}",
                state=segment.state,
                source_row_start=chunk[0].row_index,
                source_row_end=chunk[-1].row_index,
                source_time_start=chunk[0].time,
                source_time_end=chunk[-1].time,
                values=[point.value for point in chunk],
                times=[point.time for point in chunk],
            )
            pools[segment.state].append(window)

    return pools


def ensure_capacity(pools: Dict[str, List[Window]], identity_count: int, abnormal_count: int) -> None:
    needed = identity_count + abnormal_count
    for state in ("low", "normal", "high"):
        available = len(pools[state])
        if available < needed:
            raise ValueError(
                f"Not enough {state} windows: need {needed}, available {available}"
            )


def _pattern_for_index(index: int) -> List[str]:
    if index % 2 == 0:
        return ["norm1", "norm2", "norm3"]
    return ["norm3", "norm2", "norm1"]


def _sample_window_sequences(
    pools: Dict[str, List[Window]],
    count: int,
    seed: int,
    offset: int,
) -> List[List[Window]]:
    shuffled = {state: list(items) for state, items in pools.items()}
    rng = random.Random(seed)
    for items in shuffled.values():
        rng.shuffle(items)

    selections: List[List[Window]] = []
    for index in range(count):
        pattern = _pattern_for_index(index)
        sequence: List[Window] = []
        for norm_label in pattern:
            state = NORM_TO_STATE[norm_label]
            sequence.append(shuffled[state][offset + index])
        selections.append(sequence)

    return selections


def _identity_filename(trace_index: int, pattern: List[str], segment_len: int) -> str:
    starts = [1 + i * segment_len for i in range(len(pattern))]
    duration = segment_len * len(pattern)
    return (
        f"eval_ident_trace-cnt-{trace_index:03d}-duration-{duration}"
        f"-config_num-{len(pattern)}-trace_config-{','.join(pattern)}"
        f"-start_time-{','.join(str(x) for x in starts)}.csv"
    )


def _abnormal_filename(trace_index: int, pattern: List[str], segment_len: int) -> str:
    full_pattern = pattern + ["abn1"]
    starts = [1 + i * segment_len for i in range(len(full_pattern))]
    duration = segment_len * len(full_pattern)
    return (
        f"eval_abn_trace-cnt-{trace_index:03d}-duration-{duration}"
        f"-config_num-{len(full_pattern)}-trace_config-{','.join(full_pattern)}"
        f"-start_time-{','.join(str(x) for x in starts)}.csv"
    )


def _write_trace_csv(
    output_path: Path,
    metric_column: str,
    segment_entries: List[Dict[str, object]],
) -> None:
    fieldnames = [
        "time",
        metric_column,
        "segment_label",
        "source_window_id",
        "source_row_start",
        "source_row_end",
        "source_time_start",
        "source_time_end",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for segment in segment_entries:
            for row in segment["rows"]:
                writer.writerow(row)


def _rows_from_window(window: Window, segment_label: str, metric_column: str) -> List[Dict[str, object]]:
    rows = []
    for time_value, metric_value in zip(window.times, window.values):
        rows.append(
            {
                "time": time_value,
                metric_column: f"{metric_value:.6f}",
                "segment_label": segment_label,
                "source_window_id": window.window_id,
                "source_row_start": window.source_row_start,
                "source_row_end": window.source_row_end,
                "source_time_start": window.source_time_start,
                "source_time_end": window.source_time_end,
            }
        )
    return rows


def _rows_from_abnormal(
    base_window: Window,
    shift: float,
    metric_column: str,
) -> List[Dict[str, object]]:
    rows = []
    for time_value, metric_value in zip(base_window.times, base_window.values):
        rows.append(
            {
                "time": time_value,
                metric_column: f"{metric_value + shift:.6f}",
                "segment_label": "abn1",
                "source_window_id": f"{base_window.window_id}-abn1",
                "source_row_start": base_window.source_row_start,
                "source_row_end": base_window.source_row_end,
                "source_time_start": base_window.source_time_start,
                "source_time_end": base_window.source_time_end,
            }
        )
    return rows


def _manifest_segment(window: Window, segment_label: str) -> Dict[str, object]:
    return {
        "segment_label": segment_label,
        "state": window.state,
        "window_id": window.window_id,
        "source_row_start": window.source_row_start,
        "source_row_end": window.source_row_end,
        "source_time_start": window.source_time_start,
        "source_time_end": window.source_time_end,
    }


def generate_trace_dataset(
    source_csv: Path | str,
    output_root: Path | str,
    identity_count: int = 200,
    abnormal_count: int = 200,
    segment_len: int = 180,
    seed: int = 42,
    low_threshold: float = LOW_THRESHOLD,
    high_threshold: float = HIGH_THRESHOLD,
    abnormal_shift: float = DEFAULT_MEAN_SHIFT,
) -> Dict[str, object]:
    source_csv = Path(source_csv)
    output_root = Path(output_root)

    points, source_time_column = load_source_points(source_csv)
    # Threshold args are accepted for future extension; current source points are classified once.
    if low_threshold != LOW_THRESHOLD or high_threshold != HIGH_THRESHOLD:
        reclas = [
            SourcePoint(
                row_index=point.row_index,
                time=point.time,
                value=point.value,
                state=classify_state(point.value, low_threshold, high_threshold),
            )
            for point in points
        ]
        points = reclas

    segments = build_state_segments(points)
    pools = build_window_pools(segments, segment_len)
    ensure_capacity(pools, identity_count, abnormal_count)

    identity_sequences = _sample_window_sequences(pools, identity_count, seed, offset=0)
    abnormal_sequences = _sample_window_sequences(pools, abnormal_count, seed + 1, offset=identity_count)

    identity_dir = output_root / "identity"
    abnormal_dir = output_root / "abnormal"
    manifests_dir = output_root / "manifests"
    reports_dir = output_root / "reports"
    for path in (identity_dir, abnormal_dir, manifests_dir, reports_dir):
        path.mkdir(parents=True, exist_ok=True)

    manifest_traces: List[Dict[str, object]] = []

    for trace_index, windows in enumerate(identity_sequences):
        pattern = _pattern_for_index(trace_index)
        filename = _identity_filename(trace_index, pattern, segment_len)
        trace_path = identity_dir / filename
        segment_entries = []
        manifest_segments = []

        for segment_label, window in zip(pattern, windows):
            segment_entries.append(
                {
                    "segment_label": segment_label,
                    "rows": _rows_from_window(window, segment_label, METRIC_COLUMN),
                }
            )
            manifest_segments.append(_manifest_segment(window, segment_label))

        _write_trace_csv(trace_path, METRIC_COLUMN, segment_entries)
        manifest_traces.append(
            {
                "trace_id": f"identity-{trace_index:03d}",
                "split": "identity",
                "filename": filename,
                "trace_config": pattern,
                "duration": segment_len * len(pattern),
                "abnormal_type": "none",
                "abnormal_shift": 0.0,
                "segments": manifest_segments,
            }
        )

    for trace_index, windows in enumerate(abnormal_sequences):
        pattern = _pattern_for_index(trace_index)
        filename = _abnormal_filename(trace_index, pattern, segment_len)
        trace_path = abnormal_dir / filename
        segment_entries = []
        manifest_segments = []

        for segment_label, window in zip(pattern, windows):
            segment_entries.append(
                {
                    "segment_label": segment_label,
                    "rows": _rows_from_window(window, segment_label, METRIC_COLUMN),
                }
            )
            manifest_segments.append(_manifest_segment(window, segment_label))

        last_norm = pattern[-1]
        base_window = windows[-1]
        shift = abnormal_shift if last_norm == "norm3" else -abnormal_shift
        segment_entries.append(
            {
                "segment_label": "abn1",
                "rows": _rows_from_abnormal(base_window, shift, METRIC_COLUMN),
            }
        )
        manifest_segments.append(
            {
                **_manifest_segment(base_window, "abn1"),
                "window_id": f"{base_window.window_id}-abn1",
                "state": "synthetic_mean_shift",
            }
        )

        _write_trace_csv(trace_path, METRIC_COLUMN, segment_entries)
        manifest_traces.append(
            {
                "trace_id": f"abnormal-{trace_index:03d}",
                "split": "abnormal",
                "filename": filename,
                "trace_config": pattern + ["abn1"],
                "duration": segment_len * (len(pattern) + 1),
                "abnormal_type": "mean_shift",
                "abnormal_shift": shift,
                "segments": manifest_segments,
            }
        )

    manifest = {
        "source_csv": str(source_csv),
        "metric_column": METRIC_COLUMN,
        "time_column": source_time_column or "<blank-first-column>",
        "segment_len": segment_len,
        "thresholds": {"low": low_threshold, "high": high_threshold},
        "seed": seed,
        "traces": manifest_traces,
    }
    (manifests_dir / "trace_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    summary = {
        "source_csv": str(source_csv),
        "identity_count": identity_count,
        "abnormal_count": abnormal_count,
        "segment_len": segment_len,
        "seed": seed,
        "thresholds": {"low": low_threshold, "high": high_threshold},
        "window_pool_sizes": {state: len(items) for state, items in pools.items()},
    }
    (reports_dir / "dataset_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return summary


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract WaDi trace-style datasets from raw CSV.")
    parser.add_argument("--source-csv", required=True, help="Path to the raw WaDi normal-operation CSV.")
    parser.add_argument("--output-root", required=True, help="Output root directory for the trace dataset.")
    parser.add_argument("--identity-count", type=int, default=200, help="Number of identity traces to generate.")
    parser.add_argument("--abnormal-count", type=int, default=200, help="Number of abnormal traces to generate.")
    parser.add_argument("--segment-len", type=int, default=180, help="Points per segment.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for window sampling.")
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    summary = generate_trace_dataset(
        source_csv=args.source_csv,
        output_root=args.output_root,
        identity_count=args.identity_count,
        abnormal_count=args.abnormal_count,
        segment_len=args.segment_len,
        seed=args.seed,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
