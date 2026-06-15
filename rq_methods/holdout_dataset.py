"""Build holdout-based RQ1 datasets from identity traces."""

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
import random
from typing import Any, Iterable

import pandas as pd

from common.adapters import ParserFactory


DEFAULT_IDENTITY_TRACE_COUNT = 200
DEFAULT_ABNORMAL_TRACE_COUNT = 200
BSN_SENSOR_COUNT = 6

TRACE_COLUMN_MAP = {
    "rubis": ("simTime(s)", "measuredAvgRespTime_{k}"),
    "swat": ("time", "y_0"),
    "wadi": ("simTime(s)", "HMI_2_LT_001.PV"),
}


@dataclass(frozen=True)
class DistributionSegment:
    system: str
    source_trace: str
    unit_id: str
    norm_label: str
    sensor_index: int | None
    segment_index: int
    start_time: float
    end_time: float
    sample_count: int
    rows: list[dict[str, Any]]
    time_column: str
    value_column: str
    all_columns: list[str]
    static_row_values: dict[str, Any]

    def to_manifest_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("rows", None)
        return data


@dataclass(frozen=True)
class HoldoutExperiment:
    system: str
    holdout_unit: str
    train_units: list[str]
    normal_prefix_pool: list[DistributionSegment]
    abnormal_suffix_pool: list[DistributionSegment]


@dataclass(frozen=True)
class ExperimentLayout:
    system: str
    units: dict[str, list[DistributionSegment]]
    holdout_units: list[str]
    experiments: dict[str, HoldoutExperiment]


def build_holdout_unit_id(system: str, norm_label: str, sensor_index: int | None) -> str:
    if system == "bsn":
        if sensor_index is None:
            raise ValueError("BSN segment 缺少 sensor_index")
        return f"sensor{sensor_index}_{norm_label}"
    return norm_label


def extract_identity_segments(
    system: str,
    identity_dir: Path,
    boundary_trim_points: int = 0,
) -> list[DistributionSegment]:
    parser = ParserFactory.create(system, boundary_trim_points=boundary_trim_points)
    trace_files = sorted(identity_dir.glob("*.txt"))
    segments: list[DistributionSegment] = []
    for trace_file in trace_files:
        metadata = parser.parse_filename(trace_file.name)
        if metadata is None:
            continue
        df = pd.read_csv(trace_file).dropna()
        parsed_segments = parser.parse_trace_file(trace_file, metadata)

        if system == "bsn":
            target_component = f"/g3t1_{metadata.sensor_index + 1}"
            time_column = "logicalTime(s)"
            value_column = "cost"
            static_columns = [
                "logicalTimestamp(ms)",
                "component",
                "freq_double",
                "freq",
            ]
            filtered_df = df[df["component"] == target_component].copy()
            all_columns = list(df.columns)
        else:
            time_column, value_column = TRACE_COLUMN_MAP[system]
            static_columns = [
                column for column in df.columns
                if column not in {time_column, value_column}
            ]
            filtered_df = df
            all_columns = list(df.columns)

        for segment_index, norm_label in enumerate(metadata.trace_config):
            segment_df = parsed_segments.get(norm_label)
            if segment_df is None or segment_df.empty:
                continue
            sensor_index = getattr(metadata, "sensor_index", None)
            unit_id = build_holdout_unit_id(system, norm_label, sensor_index)
            first_row = segment_df.iloc[0].to_dict()
            static_row_values = {
                column: first_row.get(column)
                for column in static_columns
            }
            rows = [
                {
                    time_column: row[time_column],
                    value_column: row[value_column],
                }
                for row in segment_df.to_dict("records")
            ]
            segments.append(
                DistributionSegment(
                    system=system,
                    source_trace=trace_file.name,
                    unit_id=unit_id,
                    norm_label=norm_label,
                    sensor_index=sensor_index,
                    segment_index=segment_index,
                    start_time=float(segment_df[time_column].min()),
                    end_time=float(segment_df[time_column].max()) + 1.0,
                    sample_count=len(segment_df),
                    rows=rows,
                    time_column=time_column,
                    value_column=value_column,
                    all_columns=all_columns,
                    static_row_values=static_row_values,
                )
            )
    return segments


def build_experiment_layout(system: str, segments: list[DistributionSegment]) -> ExperimentLayout:
    units: dict[str, list[DistributionSegment]] = {}
    for segment in segments:
        units.setdefault(segment.unit_id, []).append(segment)

    holdout_units = sorted(units)
    experiments: dict[str, HoldoutExperiment] = {}
    for holdout_unit in holdout_units:
        train_units = [unit for unit in holdout_units if unit != holdout_unit]
        normal_prefix_pool = [
            segment
            for unit in train_units
            for segment in units[unit]
        ]
        abnormal_suffix_pool = list(units[holdout_unit])
        experiments[holdout_unit] = HoldoutExperiment(
            system=system,
            holdout_unit=holdout_unit,
            train_units=train_units,
            normal_prefix_pool=normal_prefix_pool,
            abnormal_suffix_pool=abnormal_suffix_pool,
        )
    return ExperimentLayout(
        system=system,
        units=units,
        holdout_units=holdout_units,
        experiments=experiments,
    )


def _default_trace_prefix_segment_count(train_unit_count: int) -> int:
    if train_unit_count <= 1:
        return 1
    if train_unit_count == 2:
        return 2
    return 3


def _compose_rows(system: str, segments: list[DistributionSegment]) -> tuple[list[dict[str, Any]], list[int]]:
    if not segments:
        raise ValueError("segments 不能为空")
    time_column = segments[0].time_column
    value_column = segments[0].value_column
    current_time = 1 if system == "bsn" or system == "wadi" else (2 if system == "swat" else 960)
    start_times: list[int] = []
    rows: list[dict[str, Any]] = []
    for segment in segments:
        start_times.append(int(current_time))
        for row in segment.rows:
            output_row = dict(segment.static_row_values)
            output_row[time_column] = current_time
            output_row[value_column] = row[value_column]
            if system == "bsn":
                output_row["component"] = f"/g3t1_{segment.sensor_index + 1}"
                output_row["logicalTimestamp(ms)"] = current_time * 1000
            rows.append(output_row)
            current_time += 1
    return rows, start_times


def _rows_to_csv(system: str, segments: list[DistributionSegment]) -> tuple[str, list[int], int]:
    rows, start_times = _compose_rows(system, segments)
    all_columns = segments[0].all_columns
    frame = pd.DataFrame(rows, columns=all_columns)
    csv_text = frame.to_csv(index=False)
    duration = int(len(frame))
    return csv_text, start_times, duration


def _sample_segment_values(
    segment: DistributionSegment,
    required_length: int,
    rng: random.Random,
) -> list[float]:
    values = [float(row[segment.value_column]) for row in segment.rows]
    if not values:
        raise ValueError(f"segment {segment.source_trace} 无有效数值")
    if len(values) == required_length:
        return values
    if len(values) > required_length:
        start = rng.randint(0, len(values) - required_length)
        return values[start : start + required_length]

    repeats = (required_length + len(values) - 1) // len(values)
    return (values * repeats)[:required_length]


def _bsn_normal_segments_by_sensor(
    layout: ExperimentLayout,
    train_units: list[str],
) -> dict[int, list[DistributionSegment]]:
    segments_by_sensor = {sensor_index: [] for sensor_index in range(BSN_SENSOR_COUNT)}
    for unit in train_units:
        for segment in layout.units[unit]:
            if segment.sensor_index is None:
                raise ValueError("BSN segment 缺少 sensor_index")
            segments_by_sensor[segment.sensor_index].append(segment)
    return segments_by_sensor


def _compose_bsn_trace(
    target_sensor: int,
    target_segments: list[DistributionSegment],
    normal_segments_by_sensor: dict[int, list[DistributionSegment]],
    rng: random.Random,
) -> tuple[str, list[int], int]:
    if not target_segments:
        raise ValueError("BSN target_segments 不能为空")

    segment_lengths = [segment.sample_count for segment in target_segments]
    start_times: list[int] = []
    current_time = 1
    sensor_value_map: dict[int, list[float]] = {}

    for sensor_index in range(BSN_SENSOR_COUNT):
        sampled_values: list[float] = []
        if sensor_index == target_sensor:
            sampled_segments = target_segments
        else:
            pool = normal_segments_by_sensor.get(sensor_index, [])
            if not pool:
                raise ValueError(f"BSN 传感器 {sensor_index} 缺少正常段候选")
            sampled_segments = [rng.choice(pool) for _ in target_segments]

        for segment, required_length in zip(sampled_segments, segment_lengths):
            sampled_values.extend(_sample_segment_values(segment, required_length, rng))
        sensor_value_map[sensor_index] = sampled_values

    rows: list[dict[str, Any]] = []
    total_duration = sum(segment_lengths)
    for segment_length in segment_lengths:
        start_times.append(current_time)
        for offset in range(segment_length):
            logical_time = current_time + offset
            for sensor_index in range(BSN_SENSOR_COUNT):
                rows.append(
                    {
                        "logicalTime(s)": logical_time,
                        "logicalTimestamp(ms)": logical_time * 1000,
                        "component": f"/g3t1_{sensor_index + 1}",
                        "freq_double": 6.0,
                        "freq": 6,
                        "cost": sensor_value_map[sensor_index][logical_time - 1],
                    }
                )
        current_time += segment_length

    frame = pd.DataFrame(
        rows,
        columns=[
            "logicalTime(s)",
            "logicalTimestamp(ms)",
            "component",
            "freq_double",
            "freq",
            "cost",
        ],
    )
    return frame.to_csv(index=False), start_times, total_duration


def write_generated_trace(
    output_dir: Path,
    system: str,
    trace_kind: str,
    trace_index: int,
    segments: list[DistributionSegment],
    trace_labels: list[str],
    config_num: int,
    sensor_index: int | None,
) -> dict[str, Any]:
    if system == "bsn":
        raise ValueError("BSN 需使用 write_generated_bsn_trace 生成")

    csv_text, start_times, duration = _rows_to_csv(system, segments)
    start_time_str = ",".join(str(value) for value in start_times)
    trace_config_str = ",".join(trace_labels)
    sensor_part = f"-sensor_index-{sensor_index}" if system == "bsn" and sensor_index is not None else ""
    filename = (
        f"eval_{'ident' if trace_kind == 'identity' else 'abn'}_trace-"
        f"cnt-{trace_index:03d}-duration-{duration}{sensor_part}-config_num-{config_num}-"
        f"trace_config-{trace_config_str}-start_time-{start_time_str}.txt"
    )
    path = output_dir / filename
    path.write_text(csv_text, encoding="utf-8")
    metadata = {
        "filename": filename,
        "trace_kind": trace_kind,
        "trace_config": trace_labels,
        "start_time": start_times,
        "duration": duration,
        "config_num": config_num,
        "source_units": [segment.unit_id for segment in segments],
    }
    if trace_kind == "abnormal":
        metadata["abn1_start_time"] = start_times[-1]
    if system == "bsn" and sensor_index is not None:
        metadata["sensor_index"] = sensor_index
    return metadata


def write_generated_bsn_trace(
    output_dir: Path,
    trace_kind: str,
    trace_index: int,
    target_sensor: int,
    target_segments: list[DistributionSegment],
    trace_labels: list[str],
    config_num: int,
    normal_segments_by_sensor: dict[int, list[DistributionSegment]],
    rng: random.Random,
) -> dict[str, Any]:
    csv_text, start_times, duration = _compose_bsn_trace(
        target_sensor=target_sensor,
        target_segments=target_segments,
        normal_segments_by_sensor=normal_segments_by_sensor,
        rng=rng,
    )
    filename = (
        f"eval_{'ident' if trace_kind == 'identity' else 'abn'}_trace-"
        f"cnt-{trace_index:03d}-duration-{duration}-sensor_index-{target_sensor}-"
        f"config_num-{config_num}-trace_config-{','.join(trace_labels)}-"
        f"start_time-{','.join(str(value) for value in start_times)}.txt"
    )
    path = output_dir / filename
    path.write_text(csv_text, encoding="utf-8")

    metadata = {
        "filename": filename,
        "trace_kind": trace_kind,
        "trace_config": trace_labels,
        "start_time": start_times,
        "duration": duration,
        "config_num": config_num,
        "source_units": [segment.unit_id for segment in target_segments],
        "sensor_index": target_sensor,
    }
    if trace_kind == "abnormal":
        metadata["abn1_start_time"] = start_times[-1]
    return metadata


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def generate_holdout_dataset(
    root_dir: Path,
    layout: ExperimentLayout,
    holdout_unit: str,
    identity_trace_count: int = DEFAULT_IDENTITY_TRACE_COUNT,
    abnormal_trace_count: int = DEFAULT_ABNORMAL_TRACE_COUNT,
    rng_seed: int = 42,
) -> Path:
    experiment = layout.experiments[holdout_unit]
    output_dir = root_dir / layout.system / f"holdout_{holdout_unit}"
    identity_dir = output_dir / "identity"
    abnormal_dir = output_dir / "abnormal"
    manifests_dir = output_dir / "manifests"
    for directory in (identity_dir, abnormal_dir, manifests_dir):
        directory.mkdir(parents=True, exist_ok=True)

    rng = random.Random(rng_seed + sum(ord(ch) for ch in holdout_unit))
    prefix_segment_count = _default_trace_prefix_segment_count(len(experiment.train_units))
    identity_manifest = []
    abnormal_manifest = []

    if layout.system == "bsn":
        normal_segments_by_sensor = _bsn_normal_segments_by_sensor(layout, experiment.train_units)
        holdout_sensor = layout.units[holdout_unit][0].sensor_index
        if holdout_sensor is None:
            raise ValueError("BSN holdout unit 缺少 sensor_index")

        for trace_index in range(identity_trace_count):
            available_sensors = [sensor for sensor, pool in normal_segments_by_sensor.items() if pool]
            target_sensor = rng.choice(available_sensors)
            target_pool = normal_segments_by_sensor[target_sensor]
            target_segments = [rng.choice(target_pool) for _ in range(prefix_segment_count)]
            trace_labels = [segment.norm_label for segment in target_segments]
            identity_manifest.append(
                write_generated_bsn_trace(
                    output_dir=identity_dir,
                    trace_kind="identity",
                    trace_index=trace_index,
                    target_sensor=target_sensor,
                    target_segments=target_segments,
                    trace_labels=trace_labels,
                    config_num=len(trace_labels),
                    normal_segments_by_sensor=normal_segments_by_sensor,
                    rng=rng,
                )
            )

        for trace_index in range(abnormal_trace_count):
            prefix_pool = normal_segments_by_sensor[holdout_sensor]
            prefix_segments = [rng.choice(prefix_pool) for _ in range(prefix_segment_count)]
            suffix_segment = rng.choice(experiment.abnormal_suffix_pool)
            target_segments = prefix_segments + [suffix_segment]
            trace_labels = [segment.norm_label for segment in prefix_segments] + ["abn1"]
            abnormal_manifest.append(
                write_generated_bsn_trace(
                    output_dir=abnormal_dir,
                    trace_kind="abnormal",
                    trace_index=trace_index,
                    target_sensor=holdout_sensor,
                    target_segments=target_segments,
                    trace_labels=trace_labels,
                    config_num=len(trace_labels),
                    normal_segments_by_sensor=normal_segments_by_sensor,
                    rng=rng,
                )
            )

        _write_json(
            manifests_dir / "experiment.json",
            {
                "system": layout.system,
                "holdout_unit": holdout_unit,
                "train_units": experiment.train_units,
                "identity_trace_count": identity_trace_count,
                "abnormal_trace_count": abnormal_trace_count,
            },
        )
        _write_json(manifests_dir / "identity_trace_manifest.json", identity_manifest)
        _write_json(manifests_dir / "abnormal_trace_manifest.json", abnormal_manifest)
        return output_dir

    for trace_index in range(identity_trace_count):
        chosen_segments = [rng.choice(experiment.normal_prefix_pool) for _ in range(prefix_segment_count)]
        trace_labels = [segment.norm_label for segment in chosen_segments]
        config_num = len(trace_labels)
        sensor_index = chosen_segments[0].sensor_index if layout.system == "bsn" else None
        identity_manifest.append(
            write_generated_trace(
                output_dir=identity_dir,
                system=layout.system,
                trace_kind="identity",
                trace_index=trace_index,
                segments=chosen_segments,
                trace_labels=trace_labels,
                config_num=config_num,
                sensor_index=sensor_index,
            )
        )

    for trace_index in range(abnormal_trace_count):
        prefix_segments = [rng.choice(experiment.normal_prefix_pool) for _ in range(prefix_segment_count)]
        suffix_segment = rng.choice(experiment.abnormal_suffix_pool)
        chosen_segments = prefix_segments + [suffix_segment]
        trace_labels = [segment.norm_label for segment in prefix_segments] + ["abn1"]
        config_num = len(trace_labels)
        sensor_index = suffix_segment.sensor_index if layout.system == "bsn" else None
        abnormal_manifest.append(
            write_generated_trace(
                output_dir=abnormal_dir,
                system=layout.system,
                trace_kind="abnormal",
                trace_index=trace_index,
                segments=chosen_segments,
                trace_labels=trace_labels,
                config_num=config_num,
                sensor_index=sensor_index,
            )
        )

    _write_json(
        manifests_dir / "experiment.json",
        {
            "system": layout.system,
            "holdout_unit": holdout_unit,
            "train_units": experiment.train_units,
            "identity_trace_count": identity_trace_count,
            "abnormal_trace_count": abnormal_trace_count,
        },
    )
    _write_json(manifests_dir / "identity_trace_manifest.json", identity_manifest)
    _write_json(manifests_dir / "abnormal_trace_manifest.json", abnormal_manifest)
    return output_dir


def generate_holdout_dataset_root(
    data_root: Path,
    output_root: Path,
    systems: Iterable[str],
    identity_trace_count: int = DEFAULT_IDENTITY_TRACE_COUNT,
    abnormal_trace_count: int = DEFAULT_ABNORMAL_TRACE_COUNT,
    boundary_trim_points: int = 10,
) -> dict[str, ExperimentLayout]:
    manifests_root = output_root / "manifests"
    manifests_root.mkdir(parents=True, exist_ok=True)
    layouts: dict[str, ExperimentLayout] = {}
    for system in systems:
        identity_dir = data_root / system / "identity"
        segments = extract_identity_segments(system, identity_dir, boundary_trim_points=boundary_trim_points)
        layout = build_experiment_layout(system, segments)
        layouts[system] = layout
        _write_json(
            manifests_root / f"{system}_segments.json",
            [segment.to_manifest_dict() for segment in segments],
        )
        for holdout_unit in layout.holdout_units:
            generate_holdout_dataset(
                root_dir=output_root,
                layout=layout,
                holdout_unit=holdout_unit,
                identity_trace_count=identity_trace_count,
                abnormal_trace_count=abnormal_trace_count,
            )
    return layouts
