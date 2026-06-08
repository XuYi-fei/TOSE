#!/usr/bin/env python3
"""
将 abnormal trace 的平缓前缀替换为对应 identity trace 的前缀。

用途：
1. 验证当前 FP 是否主要来自 abnormal 前缀与 identity 的偏移；
2. 生成一份新的测试集，保留 abn1 之后的异常段不变；
3. 输出到独立目录，避免覆盖原始 abnormal 数据。
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
import sys
from collections import defaultdict

import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.adapters.bsn import BSNParser
from common.adapters.rubis import RUBISParser
from common.adapters.swat import SWATParser
from common.adapters.wadi import WADIParser


PARSERS = {
    "rubis": RUBISParser,
    "bsn": BSNParser,
    "swat": SWATParser,
    "wadi": WADIParser,
}


def _freeze(value):
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((key, _freeze(val)) for key, val in value.items()))
    return value


def _metadata_signature(metadata) -> Tuple:
    if metadata is None:
        raise ValueError("metadata is None")

    data = asdict(metadata) if is_dataclass(metadata) else dict(vars(metadata))
    data.pop("cnt", None)
    data.pop("filename", None)
    data.pop("config_num", None)
    data["trace_config"] = tuple(label for label in data["trace_config"] if not str(label).startswith("abn"))
    data.pop("start_time", None)
    return tuple(sorted((key, _freeze(val)) for key, val in data.items()))


def _list_trace_files(directory: Path) -> List[Path]:
    return sorted([path for path in directory.iterdir() if path.is_file() and not path.name.startswith(".")])


def _parse_time_series(df: pd.DataFrame, time_column: str) -> pd.Series:
    return pd.to_numeric(df[time_column], errors="coerce")


def _normal_segment_bounds(metadata) -> List[Tuple[int, int, str]]:
    normal_labels = [label for label in metadata.trace_config if not str(label).startswith("abn")]
    bounds: List[Tuple[int, int, str]] = []
    for idx, label in enumerate(normal_labels):
        start = int(metadata.start_time[idx])
        if idx + 1 < len(metadata.start_time):
            end = int(metadata.start_time[idx + 1])
        else:
            end = int(metadata.start_time[-1]) + 1
        bounds.append((start, end, label))
    return bounds


def _resample_values(values: np.ndarray, target_len: int) -> np.ndarray:
    if target_len <= 0:
        return np.asarray([], dtype=float)
    if len(values) == 0:
        return np.zeros(target_len, dtype=float)
    if len(values) == target_len:
        return values.astype(float, copy=False)
    if len(values) == 1:
        return np.repeat(float(values[0]), target_len)
    source_x = np.linspace(0.0, 1.0, num=len(values))
    target_x = np.linspace(0.0, 1.0, num=target_len)
    return np.interp(target_x, source_x, values.astype(float))


def _target_metric_column(system: str, parser) -> str:
    if system == "bsn":
        return "cost"
    return getattr(parser, "TARGET_COLUMN")


def _target_component(metadata) -> Optional[str]:
    if hasattr(metadata, "sensor_index"):
        return f"/g3t1_{int(metadata.sensor_index) + 1}"
    return None


def _segment_row_mask(
    df: pd.DataFrame,
    time_column: str,
    start: int,
    end: int,
    component: Optional[str] = None,
) -> pd.Series:
    times = _parse_time_series(df, time_column)
    mask = (times >= start) & (times < end)
    if component is not None and "component" in df.columns:
        mask = mask & (df["component"] == component)
    return mask


def _build_segment_pool(system: str, parser, identity_files: Iterable[Path]) -> Dict[Tuple[str, int], List[Dict[str, object]]]:
    pool: Dict[Tuple[str, int], List[Dict[str, object]]] = defaultdict(list)
    metric_column = _target_metric_column(system, parser)

    for path in identity_files:
        metadata = parser.parse_filename(path.name)
        if metadata is None:
            continue
        try:
            segments = parser.parse_trace_file(path, metadata)
        except Exception:
            continue

        for position, label in enumerate([label for label in metadata.trace_config if not str(label).startswith("abn")], start=1):
            segment_df = segments.get(label)
            if segment_df is None or segment_df.empty or metric_column not in segment_df.columns:
                continue
            values = pd.to_numeric(segment_df[metric_column], errors="coerce").dropna().to_numpy()
            if len(values) == 0:
                continue
            source = {
                "file": path.name,
                "label": label,
                "position": position,
                "values": values,
            }
            pool[(label, position)].append(source)
            pool[(label, 0)].append(source)

    return pool


def _pick_source_segment(
    pool: Dict[Tuple[str, int], List[Dict[str, object]]],
    label: str,
    position: int,
    target_len: int,
) -> Optional[Dict[str, object]]:
    candidates = pool.get((label, position), []) or pool.get((label, 0), [])
    if not candidates:
        return None
    return min(candidates, key=lambda item: (abs(len(item["values"]) - target_len), item["file"]))


def _replace_prefix(
    system: str,
    parser,
    segment_pool: Dict[Tuple[str, int], List[Dict[str, object]]],
    abnormal_path: Path,
    output_path: Path,
) -> Dict[str, object]:
    metadata = parser.parse_filename(abnormal_path.name)
    if metadata is None:
        raise ValueError(f"无法解析文件名: {abnormal_path.name}")

    abnormal_df = pd.read_csv(abnormal_path)
    time_column = abnormal_df.columns[0]
    metric_column = _target_metric_column(system, parser)
    component = _target_component(metadata)

    segment_sources: List[Dict[str, object]] = []
    normal_bounds = _normal_segment_bounds(metadata)

    for position, (start, end, label) in enumerate(normal_bounds, start=1):
        abn_mask = _segment_row_mask(abnormal_df, time_column, start, end, component)
        target_index = abnormal_df.loc[abn_mask].index
        target_len = len(target_index)
        if target_len == 0:
            continue

        source = _pick_source_segment(segment_pool, label, position, target_len)
        if source is None:
            source = _pick_source_segment(segment_pool, label, 0, target_len)
        if source is None:
            continue

        replaced_values = _resample_values(np.asarray(source["values"]), target_len)
        abnormal_df.loc[target_index, metric_column] = replaced_values
        segment_sources.append(
            {
                "position": position,
                "label": label,
                "source_file": source["file"],
                "source_len": int(len(source["values"])),
                "target_len": int(target_len),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    abnormal_df.to_csv(output_path, index=False)

    return {
        "system": system,
        "filename": abnormal_path.name,
        "output_file": output_path.name,
        "segment_sources": segment_sources,
        "output_rows": int(len(abnormal_df)),
    }


def build_dataset(system: str, output_root: Path) -> Dict[str, object]:
    parser = PARSERS[system]()
    identity_dir = Path(f"data/{system}/identity")
    abnormal_dir = Path(f"data/{system}/abnormal")
    output_dir = output_root / system / "abnormal_prefix_replaced"

    if not identity_dir.exists():
        raise FileNotFoundError(f"缺少 identity 目录: {identity_dir}")
    if not abnormal_dir.exists():
        raise FileNotFoundError(f"缺少 abnormal 目录: {abnormal_dir}")

    segment_pool = _build_segment_pool(system, parser, _list_trace_files(identity_dir))
    abnormal_files = _list_trace_files(abnormal_dir)

    results: List[Dict[str, object]] = []
    for abnormal_path in abnormal_files:
        results.append(
            _replace_prefix(
                system=system,
                parser=parser,
                segment_pool=segment_pool,
                abnormal_path=abnormal_path,
                output_path=output_dir / abnormal_path.name,
            )
        )

    manifest = {
        "system": system,
        "generated_at": datetime.now().isoformat(),
        "identity_dir": str(identity_dir),
        "abnormal_source_dir": str(abnormal_dir),
        "output_dir": str(output_dir),
        "total_files": len(results),
        "files": results,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "replacement_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="构建 prefix replaced abnormal 数据集")
    parser.add_argument(
        "--systems",
        nargs="*",
        default=["rubis", "bsn", "swat", "wadi"],
        choices=sorted(PARSERS.keys()),
        help="要处理的 subject systems",
    )
    parser.add_argument(
        "--output-root",
        default="data",
        help="输出根目录，默认仍在 data/ 下创建独立子目录",
    )
    args = parser.parse_args()

    output_root = Path(args.output_root)
    summary = {"generated_at": datetime.now().isoformat(), "systems": []}
    for system in args.systems:
        manifest = build_dataset(system, output_root)
        summary["systems"].append(
            {
                "system": system,
                "output_dir": manifest["output_dir"],
                "total_files": manifest["total_files"],
            }
        )
        print(f"[OK] {system}: {manifest['total_files']} files -> {manifest['output_dir']}")

    (output_root / "prefix_replaced_dataset_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
