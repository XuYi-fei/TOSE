"""Shared helpers for reading standardized GROUP detection result files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


RESULT_FIELDNAMES = [
    "system",
    "algorithm",
    "detection_mode",
    "cluster_count",
    "total_traces",
    "tp_count",
    "fp_count",
    "fn_count",
    "tn_count",
    "tp_rate",
    "fp_rate",
    "fn_rate",
    "precision",
    "recall",
    "f1_score",
    "hazard_lambda",
    "max_run_length",
    "state_prior",
    "changepoint_posterior_threshold",
    "raw_anomaly_rule",
    "tail_persistence_threshold",
]


def load_detection_result_row(system: str, algorithm: str) -> dict[str, Any] | None:
    """Load one standardized detection result row from JSON output."""
    detection_json_path = Path("detection_results") / system / f"detection_results_{algorithm}.json"
    if not detection_json_path.exists():
        return None

    payload = json.loads(detection_json_path.read_text(encoding="utf-8"))
    metadata = payload["metadata"]
    summary = payload["summary"]
    confusion = payload["confusion_matrix"]
    performance = payload["performance_metrics"]
    total = int(summary["total_traces"]) or 1
    detection_mode = metadata.get("detection_mode", "pointwise")
    bocpd = metadata.get("bocpd") or {}
    return {
        "system": system,
        "algorithm": algorithm,
        "detection_mode": detection_mode,
        "cluster_count": int(metadata.get("cluster_count", summary.get("cluster_count", 0))),
        "total_traces": total,
        "tp_count": int(confusion["TP"]),
        "fp_count": int(confusion["FP"]),
        "fn_count": int(confusion["FN"]),
        "tn_count": int(confusion["TN"]),
        "tp_rate": int(confusion["TP"]) / total,
        "fp_rate": int(confusion["FP"]) / total,
        "fn_rate": int(confusion["FN"]) / total,
        "precision": float(performance["precision"]),
        "recall": float(performance["recall"]),
        "f1_score": float(performance["f1_score"]),
        "hazard_lambda": bocpd.get("hazard_lambda", "") if detection_mode == "bocpd" else "",
        "max_run_length": bocpd.get("max_run_length", "") if detection_mode == "bocpd" else "",
        "state_prior": bocpd.get("state_prior", "") if detection_mode == "bocpd" else "",
        "changepoint_posterior_threshold": (
            bocpd.get("changepoint_posterior_threshold", "") if detection_mode == "bocpd" else ""
        ),
        "raw_anomaly_rule": bocpd.get("raw_anomaly_rule", "") if detection_mode == "bocpd" else "",
        "tail_persistence_threshold": (
            bocpd.get("tail_persistence_threshold", "") if detection_mode == "bocpd" else ""
        ),
    }
