"""RQ1 evaluator and runner for ASE-style baselines on TOSE data."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

from . import config
from .detectors import create_detector
from .identifier import BaselineConfig, BaselineIdentifier
from .trace_adapter import BaselineTrace, TraceAdapter


@dataclass(frozen=True)
class TraceBaselineResult:
    filename: str
    classification: str
    abn_start_time: float | None
    first_detection_time: float | None
    detection_delay_loops: int | None
    abnormal_time: float
    abnormal_total_time: float


class BaselineEvaluator:
    """Evaluate one baseline config over abnormal traces."""

    def __init__(self, system_type: str, baseline_config: BaselineConfig):
        self.system_type = system_type
        self.config = baseline_config
        self.adapter = TraceAdapter(system_type)

    def evaluate_directory(self, abnormal_dir: Path | str) -> list[TraceBaselineResult]:
        return [self.evaluate_trace(trace_file) for trace_file in sorted(Path(abnormal_dir).glob("*.txt"))]

    def evaluate_trace(self, trace_file: Path) -> TraceBaselineResult:
        trace = self.adapter.load(trace_file)
        detector = create_detector(self.config.method, self.config.detectors[0])
        detector.reset()

        first_detection_time = None
        first_detection_index = None
        for index, (time_value, metric_value) in enumerate(zip(trace.times, trace.values)):
            _, alarm = detector.detect(float(metric_value))
            if alarm:
                first_detection_time = float(time_value)
                first_detection_index = index
                break

        return self._classify(trace, first_detection_time, first_detection_index)

    def _classify(
        self,
        trace: BaselineTrace,
        first_detection_time: float | None,
        first_detection_index: int | None,
    ) -> TraceBaselineResult:
        if trace.abn_start_time is None:
            classification = "TN" if first_detection_time is None else "FP"
            return TraceBaselineResult(
                filename=trace.filename,
                classification=classification,
                abn_start_time=None,
                first_detection_time=first_detection_time,
                detection_delay_loops=None,
                abnormal_time=0.0,
                abnormal_total_time=0.0,
            )

        abn_indices = [idx for idx, time_value in enumerate(trace.times) if float(time_value) >= trace.abn_start_time]
        if not abn_indices:
            raise ValueError(f"abn1 起点超出 trace 时间范围: {trace.filename}")
        abn_index = abn_indices[0]

        abnormal_total_time = float(trace.duration)
        if first_detection_time is None:
            return TraceBaselineResult(
                filename=trace.filename,
                classification="FN",
                abn_start_time=trace.abn_start_time,
                first_detection_time=None,
                detection_delay_loops=None,
                abnormal_time=max(float(trace.duration) - trace.abn_start_time, 0.0),
                abnormal_total_time=abnormal_total_time,
            )

        delay = int(first_detection_index - abn_index) if first_detection_index is not None else None
        classification = "TP" if first_detection_time >= trace.abn_start_time else "FP"
        abnormal_time = 0.0
        if classification == "TP":
            abnormal_time = first_detection_time - trace.abn_start_time + config.TIME_UNIT_PER_LOOP[self.system_type]

        return TraceBaselineResult(
            filename=trace.filename,
            classification=classification,
            abn_start_time=trace.abn_start_time,
            first_detection_time=first_detection_time,
            detection_delay_loops=delay,
            abnormal_time=abnormal_time,
            abnormal_total_time=abnormal_total_time,
        )


def aggregate_results(system: str, method: str, results: Iterable[TraceBaselineResult]) -> dict:
    result_list = list(results)
    total = len(result_list)
    tp_count = sum(1 for item in result_list if item.classification == "TP")
    fp_count = sum(1 for item in result_list if item.classification == "FP")
    fn_count = sum(1 for item in result_list if item.classification == "FN")
    tn_count = sum(1 for item in result_list if item.classification == "TN")
    delays = [item.detection_delay_loops for item in result_list if item.classification == "TP" and item.detection_delay_loops is not None]
    abnormal_total_time = sum(item.abnormal_total_time for item in result_list)
    abnormal_time = sum(item.abnormal_time for item in result_list)
    denominator = total or 1
    precision = tp_count / (tp_count + fp_count) if tp_count + fp_count else 0.0
    recall = tp_count / (tp_count + fn_count) if tp_count + fn_count else 0.0
    f1_score = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    return {
        "system": system,
        "method": method,
        "total_traces": total,
        "tp_count": tp_count,
        "fp_count": fp_count,
        "fn_count": fn_count,
        "tn_count": tn_count,
        "tp_rate": tp_count / denominator,
        "fp_rate": fp_count / denominator,
        "fn_rate": fn_count / denominator,
        "FN": fn_count / denominator * 100.0,
        "FP": fp_count / denominator * 100.0,
        "MTD": sum(delays) / len(delays) if delays else 0.0,
        "MLD": sum(delays) / len(delays) if delays else 0.0,
        "AR": abnormal_time / abnormal_total_time * 100.0 if abnormal_total_time else 0.0,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
    }


class BaselineExperimentRunner:
    """Run baseline identification and RQ1 detection across systems."""

    def __init__(
        self,
        systems: dict[str, dict[str, Path | str]] | None = None,
        output_dir: Path | str = "baseline_results",
        methods: list[str] | None = None,
    ):
        self.systems = systems or default_systems()
        self.output_dir = Path(output_dir)
        self.methods = [method.upper() for method in (methods or list(config.METHODS))]

    def run(self) -> list[dict]:
        rows: list[dict] = []
        for system, paths in self.systems.items():
            identity_dir = Path(paths["identity"])
            abnormal_dir = Path(paths["abnormal"])
            secondary_identity_dir = Path(paths["identity2"]) if "identity2" in paths else None
            for method in self.methods:
                baseline_config = BaselineIdentifier(system).identify(
                    method,
                    identity_dir,
                    secondary_identity_dir=secondary_identity_dir,
                )
                self._write_config(system, method, baseline_config)
                evaluator = BaselineEvaluator(system, baseline_config)
                trace_results = evaluator.evaluate_directory(abnormal_dir)
                self._write_trace_results(system, method, trace_results)
                rows.append(aggregate_results(system, method, trace_results))
        self._write_summary(rows)
        return rows

    def _write_config(self, system: str, method: str, baseline_config: BaselineConfig) -> None:
        baseline_config.write_json(self.output_dir / system / f"{method}.json")

    def _write_trace_results(self, system: str, method: str, results: list[TraceBaselineResult]) -> None:
        path = self.output_dir / system / f"detection_results_{method}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [result.__dict__ for result in results]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _write_summary(self, rows: list[dict]) -> None:
        summary_dir = self.output_dir / "summary"
        summary_dir.mkdir(parents=True, exist_ok=True)
        json_path = summary_dir / "rq1_baseline_summary.json"
        csv_path = summary_dir / "rq1_baseline_summary.csv"
        json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        fieldnames = [
            "system",
            "method",
            "total_traces",
            "tp_count",
            "fp_count",
            "fn_count",
            "tn_count",
            "tp_rate",
            "fp_rate",
            "fn_rate",
            "FN",
            "FP",
            "MTD",
            "MLD",
            "AR",
            "precision",
            "recall",
            "f1_score",
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def default_systems() -> dict[str, dict[str, Path]]:
    return {
        system: {
            "identity": Path("data") / system / "identity",
            "abnormal": Path("data") / system / "abnormal",
        }
        for system in ("rubis", "bsn", "swat", "wadi")
    }
