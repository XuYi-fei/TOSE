from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import yaml

from anomaly_detection.core.distribution import LearnedDistribution
from common.adapters import ParserFactory
from common.utils.trace_series import load_trace_series


@dataclass
class DashboardBundle:
    payload: Dict[str, Any]
    result_index: Dict[str, Dict[str, Any]]


def scan_dashboard_data(root: str | Path) -> Dict[str, Any]:
    return scan_dashboard_bundle(root).payload


def scan_dashboard_bundle(root: str | Path) -> DashboardBundle:
    root_path = Path(root).resolve()
    results = []
    result_index: Dict[str, Dict[str, Any]] = {}
    identity_self_check = _load_json_if_exists(
        root_path / "detection_results" / "summary" / "identity_label_grouped_self_check.json"
    ) or {}
    identity_group_rows = _flatten_identity_groups(identity_self_check)
    fp_breakdown_rows = _load_json_if_exists(
        root_path / "detection_results" / "summary" / "label_grouped_fp_prefix_trace_breakdown.json"
    ) or []
    fp_breakdown_map = {
        (row["system"], row["filename"]): row
        for row in fp_breakdown_rows
    }
    fp_group_summary = _aggregate_fp_groups(fp_breakdown_rows)

    detection_files = sorted(root_path.glob("detection_results/*/detection_results*.json"))
    for detection_file in detection_files:
        detection_payload = json.loads(detection_file.read_text(encoding="utf-8"))
        metadata = detection_payload.get("metadata", {})
        system = str(metadata.get("system_type", "")).strip()
        if not system:
            continue

        config_path = _resolve_path(root_path, metadata.get("config_path"))
        detect_config = _load_yaml_if_exists(config_path) or {}
        learned_path = _resolve_path(root_path, detect_config.get("learned_distributions"))
        learned_payload = _load_yaml_if_exists(learned_path) or {}
        distributions = learned_payload.get("distributions", {})
        result_id = f"{system}:{detection_file.stem}"

        distribution_items = []
        total_distribution_samples = 0
        for label, raw_dist in distributions.items():
            dist = LearnedDistribution.from_dict(label, raw_dist)
            total_distribution_samples += int(dist.sample_count)
            distribution_items.append(
                {
                    "label": label,
                    "distribution_type": dist.distribution_type,
                    "sample_count": int(dist.sample_count),
                    "mu": float(dist.mu or 0.0),
                    "sigma": float(dist.sigma or 0.0),
                    "variance": float(dist.variance or 0.0),
                    "dominant_norm": raw_dist.get("dominant_norm"),
                    "cluster_id": raw_dist.get("cluster_id"),
                    "context_key": raw_dist.get("context_key"),
                    "context_features": raw_dist.get("context_features") or {},
                    "fitted_params": raw_dist.get("fitted_params") or {},
                    "support": raw_dist.get("support") or {},
                }
            )

        trace_summaries = []
        trace_map: Dict[str, Dict[str, Any]] = {}
        for trace in detection_payload.get("trace_details", []):
            filename = trace["filename"]
            breakdown = fp_breakdown_map.get((system, filename), {})
            trigger_reason = _build_trigger_reason(trace, distributions)
            trace_summary = {
                "filename": filename,
                "classification": trace.get("classification"),
                "has_abn1": bool(trace.get("has_abn1")),
                "abn1_start_time": trace.get("abn1_start_time"),
                "first_detection_time": trace.get("first_detection_time"),
                "first_raw_anomaly_time": trace.get("first_raw_anomaly_time"),
                "detection_delay_loops": trace.get("detection_delay_loops"),
                "total_detection_count": trace.get("total_detection_count"),
                "trigger_alarm_count": trace.get("trigger_alarm_count"),
                "trigger_allowed_count": trace.get("trigger_allowed_count"),
                "prefix_point_count": breakdown.get("prefix_point_count"),
                "prefix_anomaly_count": breakdown.get("prefix_anomaly_count"),
                "prefix_anomaly_ratio": breakdown.get("prefix_anomaly_ratio"),
                "observed_count_at_trigger": breakdown.get("observed_count_at_trigger"),
                "trigger_excess_count": breakdown.get("trigger_excess_count"),
                "prefix_segment_anomaly_counts": _safe_json_loads(
                    breakdown.get("prefix_segment_anomaly_counts")
                ),
                "prefix_closest_distribution_counts": _safe_json_loads(
                    breakdown.get("prefix_closest_distribution_counts")
                ),
                "first_prefix_anomaly_times": _safe_json_loads(
                    breakdown.get("first_10_prefix_anomaly_times")
                ),
                "max_local_prefix_streak_le_60s_gap": breakdown.get(
                    "max_local_prefix_streak_le_60s_gap"
                ),
                "trigger_reason": trigger_reason,
            }
            trace_summaries.append(trace_summary)
            trace_map[filename] = {
                "raw": trace,
                "summary": trace_summary,
            }

        trace_summaries.sort(
            key=lambda item: (
                _classification_rank(item.get("classification")),
                -(item.get("prefix_anomaly_count") or -1),
                str(item.get("filename")),
            )
        )
        confusion = detection_payload.get("confusion_matrix", {})
        perf = detection_payload.get("performance_metrics", {})
        result_record = {
            "id": result_id,
            "system": system,
            "algorithm": metadata.get("clustering_algorithm"),
            "cluster_count": metadata.get("cluster_count"),
            "detection_file": str(detection_file.relative_to(root_path)),
            "detection_config_path": str(config_path.relative_to(root_path)) if config_path else None,
            "learned_distributions_path": str(learned_path.relative_to(root_path)) if learned_path else None,
            "test_data_path": detect_config.get("test_data_path"),
            "distribution_count": len(distribution_items),
            "distribution_source": {
                "path": str(learned_path.relative_to(root_path)) if learned_path else None,
                "sample_count": total_distribution_samples,
                "distribution_items": distribution_items,
            },
            "identity_self_check": identity_self_check.get(system),
            "distribution_comparison": _build_distribution_comparison(
                system,
                distribution_items,
                identity_group_rows.get(system, {}),
                fp_group_summary.get(system, {}),
            ),
            "trace_count": len(trace_summaries),
            "fp_count": int(confusion.get("FP", 0)),
            "tp_count": int(confusion.get("TP", 0)),
            "fn_count": int(confusion.get("FN", 0)),
            "tn_count": int(confusion.get("TN", 0)),
            "precision": perf.get("precision"),
            "recall": perf.get("recall"),
            "f1_score": perf.get("f1_score"),
            "traces": trace_summaries,
        }
        results.append(result_record)
        result_index[result_id] = {
            "record": result_record,
            "trace_map": trace_map,
            "distributions": distributions,
            "root": root_path,
        }

    results.sort(key=lambda item: (item["system"], str(item["algorithm"]), str(item["id"])))
    payload = {
        "generated_at": datetime.now().isoformat(),
        "root": str(root_path),
        "systems": sorted({item["system"] for item in results}),
        "results": results,
    }
    return DashboardBundle(payload=payload, result_index=result_index)


def build_trace_detail(bundle: DashboardBundle, root: str | Path, result_id: str, filename: str) -> Dict[str, Any]:
    indexed = bundle.result_index[result_id]
    record = indexed["record"]
    trace_entry = indexed["trace_map"][filename]
    trace_raw = trace_entry["raw"]
    summary = trace_entry["summary"]
    root_path = Path(root).resolve()
    trace_file = root_path / "data" / record["system"] / "abnormal" / filename
    if not trace_file.exists():
        trace_file = root_path / "data" / record["system"] / "identity" / filename
    parser = ParserFactory.create(record["system"])
    metadata = parser.parse_filename(filename)
    time_values, value_values = load_trace_series(trace_file, record["system"])
    anomaly_map = {
        float(point["time"]): point
        for point in trace_raw.get("anomaly_points", [])
    }

    series = []
    for time, value in zip(time_values.tolist(), value_values.tolist()):
        segment_label = _segment_label_for_time(metadata, float(time))
        anomaly = anomaly_map.get(float(time))
        series.append(
            {
                "time": float(time),
                "value": float(value),
                "segment_label": segment_label,
                "is_anomaly": anomaly is not None,
                "closest_distribution": anomaly.get("closest_distribution") if anomaly else None,
                "best_p_value": anomaly.get("best_p_value") if anomaly else None,
            }
        )

    trigger_time = summary.get("first_detection_time")
    trigger_index = None
    if trigger_time is not None:
        for index, item in enumerate(series):
            if float(item["time"]) == float(trigger_time):
                trigger_index = index
                break
    start = max(0, (trigger_index or 0) - 8)
    end = min(len(series), (trigger_index or 0) + 9)
    trigger_window = series[start:end]

    return {
        "result_id": result_id,
        "system": record["system"],
        "algorithm": record["algorithm"],
        "cluster_count": record["cluster_count"],
        "filename": filename,
        "trace_length": len(series),
        "source_path": str(trace_file.relative_to(root_path)),
        "summary": summary,
        "trigger_reason": summary.get("trigger_reason"),
        "series": series,
        "trigger_window": trigger_window,
        "distribution_items": record["distribution_source"]["distribution_items"],
    }


def _load_yaml_if_exists(path: Optional[Path]) -> Optional[Dict[str, Any]]:
    if path is None or not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_json_if_exists(path: Optional[Path]) -> Optional[Any]:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_path(root: Path, value: Any) -> Optional[Path]:
    if not value:
        return None
    path = Path(str(value))
    resolved = path if path.is_absolute() else (root / path)
    return resolved.resolve()


def _safe_json_loads(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return value


def _build_trigger_reason(
    trace_detail: Dict[str, Any],
    distributions: Dict[str, Dict[str, Any]],
) -> Dict[str, Any] | None:
    first_detection_time = trace_detail.get("first_detection_time")
    if first_detection_time is None:
        return None

    trigger_point = None
    for point in trace_detail.get("anomaly_points", []):
        if float(point["time"]) == float(first_detection_time):
            trigger_point = point
            break
    if trigger_point is None and trace_detail.get("anomaly_points"):
        trigger_point = trace_detail["anomaly_points"][0]
    if trigger_point is None:
        return None

    distribution_label = trigger_point.get("closest_distribution")
    raw_distribution = distributions.get(distribution_label or "")
    if not raw_distribution:
        return {
            "closest_distribution": distribution_label,
            "point_value": trigger_point.get("value"),
        }

    distribution = LearnedDistribution.from_dict(distribution_label, raw_distribution)
    value = float(trigger_point["value"])
    mu = float(distribution.mu or 0.0)
    sigma = float(distribution.sigma or 0.0)
    deviation_value = value - mu
    deviation_sigma = deviation_value / sigma if sigma else 0.0
    return {
        "closest_distribution": distribution_label,
        "distribution_type": distribution.distribution_type,
        "point_value": value,
        "distribution_mu": mu,
        "distribution_sigma": sigma,
        "best_p_value": trigger_point.get("best_p_value"),
        "deviation_value": deviation_value,
        "deviation_sigma": deviation_sigma,
        "trigger_explanation": (
            f"累计偏离点数 {trace_detail.get('trigger_alarm_count')} > 容忍数 "
            f"{trace_detail.get('trigger_allowed_count')}，当前点最接近 {distribution_label}，"
            f"偏离 {deviation_sigma:.2f}σ"
        ),
    }


def _classification_rank(classification: Optional[str]) -> int:
    order = {"FP": 0, "FN": 1, "TP": 2, "TN": 3}
    return order.get(str(classification), 9)


def _segment_label_for_time(metadata: Any, time_value: float) -> Optional[str]:
    if metadata is None or not metadata.trace_config or not metadata.start_time:
        return None
    active_index = len(metadata.trace_config) - 1
    for index, start in enumerate(metadata.start_time):
        if float(time_value) < float(start):
            active_index = max(0, index - 1)
            break
    return metadata.trace_config[active_index]


def _flatten_identity_groups(identity_self_check: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    flattened: Dict[str, Dict[str, Any]] = {}
    for system, payload in identity_self_check.items():
        groups = dict((payload or {}).get("groups") or {})
        flattened[system] = {
            "exact": groups,
            "suffix": _aggregate_stats_by_suffix(groups),
        }
    return flattened


def _aggregate_fp_groups(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    grouped: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for row in rows:
        system = str(row.get("system"))
        parsed = _safe_json_loads(row.get("prefix_closest_distribution_counts")) or {}
        sys_group = grouped.setdefault(
            system,
            {
                "exact": {},
                "suffix": {},
            },
        )
        for label, count in parsed.items():
            exact_stats = sys_group["exact"].setdefault(
                str(label),
                {
                    "fp_trace_count": 0,
                    "prefix_point_count": 0,
                    "prefix_anomaly_count": 0,
                    "trigger_trace_count": 0,
                },
            )
            exact_stats["prefix_anomaly_count"] += int(count)
            exact_stats["prefix_point_count"] += int(row.get("prefix_point_count") or 0)
            exact_stats["trigger_trace_count"] += 1
            suffix_key = _norm_suffix(str(label))
            if suffix_key:
                suffix_stats = sys_group["suffix"].setdefault(
                    suffix_key,
                    {
                        "fp_trace_count": 0,
                        "prefix_point_count": 0,
                        "prefix_anomaly_count": 0,
                        "trigger_trace_count": 0,
                    },
                )
                suffix_stats["prefix_anomaly_count"] += int(count)
                suffix_stats["prefix_point_count"] += int(row.get("prefix_point_count") or 0)
                suffix_stats["trigger_trace_count"] += 1
        for label in parsed.keys():
            sys_group["exact"][str(label)]["fp_trace_count"] += 1
            suffix_key = _norm_suffix(str(label))
            if suffix_key:
                sys_group["suffix"][suffix_key]["fp_trace_count"] += 1
    return grouped


def _build_distribution_comparison(
    system: str,
    distribution_items: list[Dict[str, Any]],
    identity_groups: Dict[str, Any],
    fp_groups: Dict[str, Any],
) -> list[Dict[str, Any]]:
    comparisons = []
    for distribution in distribution_items:
        label = str(distribution["label"])
        dominant_norm = distribution.get("dominant_norm")
        identity_match = _resolve_group_stats(identity_groups, label, dominant_norm)
        fp_match = _resolve_group_stats(fp_groups, label, dominant_norm)
        identity = identity_match["stats"]
        fp = fp_match["stats"]
        identity_points = int(identity.get("points") or 0)
        identity_outliers = int(identity.get("outliers") or 0)
        fp_prefix_points = int(fp.get("prefix_point_count") or 0)
        fp_prefix_outliers = int(fp.get("prefix_anomaly_count") or 0)
        comparisons.append(
            {
                "label": label,
                "distribution_type": distribution["distribution_type"],
                "sample_count": distribution["sample_count"],
                "mu": distribution["mu"],
                "sigma": distribution["sigma"],
                "dominant_norm": distribution.get("dominant_norm"),
                "context_features": distribution.get("context_features") or {},
                "identity_match_source": identity_match["source"],
                "fp_match_source": fp_match["source"],
                "identity_self_check": {
                    "points": identity_points,
                    "outliers": identity_outliers,
                    "outlier_ratio": identity.get("outlier_ratio"),
                    "expected_ratio_3sigma": identity.get("expected_ratio_3sigma"),
                    "excess_vs_expected_ratio": identity.get("excess_vs_expected_ratio"),
                    "lower_outliers": identity.get("lower_outliers"),
                    "upper_outliers": identity.get("upper_outliers"),
                    "segments": identity.get("segments"),
                    "segments_with_outlier": identity.get("segments_with_outlier"),
                },
                "fp_prefix_check": {
                    "fp_trace_count": int(fp.get("fp_trace_count") or 0),
                    "prefix_points": fp_prefix_points,
                    "prefix_outliers": fp_prefix_outliers,
                    "prefix_outlier_ratio": (
                        fp_prefix_outliers / fp_prefix_points if fp_prefix_points else None
                    ),
                },
            }
        )
    comparisons.sort(key=lambda item: str(item["label"]))
    return comparisons


def _norm_suffix(label: str) -> Optional[str]:
    match = re.search(r"(norm\d+)$", label)
    if match:
        return match.group(1)
    return None


def _aggregate_stats_by_suffix(groups: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    aggregated: Dict[str, Dict[str, Any]] = {}
    for label, stats in groups.items():
        suffix = _norm_suffix(str(label))
        if not suffix:
            continue
        target = aggregated.setdefault(
            suffix,
            {
                "points": 0,
                "outliers": 0,
                "lower_outliers": 0,
                "upper_outliers": 0,
                "segments": 0,
                "segments_with_outlier": 0,
                "traces_with_outlier": 0,
                "_expected_ratio_weighted": 0.0,
            },
        )
        points = int(stats.get("points") or 0)
        target["points"] += points
        target["outliers"] += int(stats.get("outliers") or 0)
        target["lower_outliers"] += int(stats.get("lower_outliers") or 0)
        target["upper_outliers"] += int(stats.get("upper_outliers") or 0)
        target["segments"] += int(stats.get("segments") or 0)
        target["segments_with_outlier"] += int(stats.get("segments_with_outlier") or 0)
        target["traces_with_outlier"] += int(stats.get("traces_with_outlier") or 0)
        expected_ratio = stats.get("expected_ratio_3sigma")
        if expected_ratio is not None:
            target["_expected_ratio_weighted"] += float(expected_ratio) * max(points, 1)

    for stats in aggregated.values():
        points = int(stats.get("points") or 0)
        outliers = int(stats.get("outliers") or 0)
        segments = int(stats.get("segments") or 0)
        segments_with_outlier = int(stats.get("segments_with_outlier") or 0)
        stats["outlier_ratio"] = (outliers / points) if points else None
        stats["segment_outlier_ratio"] = (
            segments_with_outlier / segments if segments else None
        )
        weighted = float(stats.pop("_expected_ratio_weighted", 0.0))
        stats["expected_ratio_3sigma"] = (weighted / points) if points else None
        expected_ratio = stats.get("expected_ratio_3sigma")
        if expected_ratio:
            stats["excess_vs_expected_ratio"] = (stats["outlier_ratio"] or 0.0) / expected_ratio
        else:
            stats["excess_vs_expected_ratio"] = None
    return aggregated


def _resolve_group_stats(
    lookup: Dict[str, Dict[str, Dict[str, Any]]],
    label: str,
    dominant_norm: Any,
) -> Dict[str, Any]:
    if not lookup:
        return {"stats": {}, "source": "missing"}

    dominant_key = str(dominant_norm) if dominant_norm else None
    exact = lookup.get("exact") or {}
    suffix = lookup.get("suffix") or {}

    if label in exact:
        return {"stats": exact[label], "source": f"exact:{label}"}
    if dominant_key and dominant_key in exact:
        return {"stats": exact[dominant_key], "source": f"dominant:{dominant_key}"}

    label_suffix = _norm_suffix(label)
    if label_suffix and label_suffix in suffix:
        return {"stats": suffix[label_suffix], "source": f"suffix:{label_suffix}"}

    dominant_suffix = _norm_suffix(dominant_key or "")
    if dominant_suffix and dominant_suffix in suffix:
        return {"stats": suffix[dominant_suffix], "source": f"dominant-suffix:{dominant_suffix}"}

    return {"stats": {}, "source": "unmatched"}
