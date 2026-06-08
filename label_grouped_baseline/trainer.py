"""按 trace 文件名标签归组拟合分布。"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import DefaultDict, Dict, List, Tuple

import pandas as pd
import yaml

from cluster_analysis.core.distribution_fitting import ClusterDistributionFitter
from common.adapters import ParserFactory
from common.models.context import build_context_key
from common.models.distribution import DistributionParameters


TRACE_COLUMN_MAP = {
    "rubis": ("simTime(s)", "measuredAvgRespTime_{k}"),
    "swat": ("time", "y_0"),
    "wadi": ("simTime(s)", "HMI_2_LT_001.PV"),
}


class LabelGroupedBaselineTrainer:
    """按 norm 标签直接汇总 identity 段并拟合分布。"""

    ALGORITHM_NAME = "label_grouped_baseline"

    def __init__(
        self,
        system_type: str,
        candidate_distributions: List[str] | None = None,
        normality_alpha: float = 0.05,
    ):
        self.system_type = system_type
        self.parser = ParserFactory.create(system_type)
        self.distribution_fitter = ClusterDistributionFitter(
            candidate_distributions=candidate_distributions,
            normality_alpha=normality_alpha,
        )

    def fit(self, data_path: str) -> Dict[str, object]:
        grouped_parameters, grouped_contexts = self._collect_grouped_parameters(data_path)
        distributions: Dict[str, Dict[str, object]] = {}
        for cluster_id, group_label in enumerate(sorted(grouped_parameters.keys())):
            model = self.distribution_fitter.fit_cluster_distribution(
                cluster_id,
                grouped_parameters[group_label],
            )
            model_dict = model.to_dict()
            model_dict["cluster_id"] = cluster_id
            model_dict["dominant_norm"] = grouped_contexts[group_label]["dominant_norm"]
            context_features = dict(grouped_contexts[group_label]["context_features"])
            if context_features:
                model_dict["context_features"] = context_features
                model_dict["context_key"] = build_context_key(context_features)
            distributions[group_label] = model_dict

        return {
            "system_type": self.system_type,
            "learned_at": datetime.now().isoformat(),
            "algorithm": self.ALGORITHM_NAME,
            "distributions": distributions,
        }

    def fit_and_save(
        self,
        data_path: str,
        output_path: str | Path,
        config_path: str | None = None,
    ) -> Path:
        learned = self.fit(data_path)
        if config_path:
            learned["clustering_config"] = str(config_path)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            yaml.dump(learned, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return output

    def _collect_grouped_parameters(
        self,
        data_path: str,
    ) -> Tuple[DefaultDict[str, List[DistributionParameters]], Dict[str, Dict[str, object]]]:
        trace_files = sorted(Path(data_path).glob("*.txt"))
        if not trace_files:
            raise ValueError(f"目录{data_path}中未找到trace文件")

        grouped: DefaultDict[str, List[DistributionParameters]] = defaultdict(list)
        grouped_contexts: Dict[str, Dict[str, object]] = {}
        for trace_file in trace_files:
            metadata = self.parser.parse_filename(trace_file.name)
            if metadata is None:
                continue

            frame, time_column, value_column = self._load_trace_frame(trace_file, metadata)
            segment_parameters = self._extract_segment_parameters(frame, metadata, time_column, value_column)
            for group_label, parameter, dominant_norm, group_context in segment_parameters:
                grouped[group_label].append(parameter)
                if group_label not in grouped_contexts:
                    grouped_contexts[group_label] = {
                        "dominant_norm": dominant_norm,
                        "context_features": dict(group_context),
                    }

        if not grouped:
            raise ValueError(f"目录{data_path}中未提取到任何有效norm段")
        return grouped, grouped_contexts

    def _load_trace_frame(self, trace_file: Path, metadata) -> Tuple[pd.DataFrame, str, str]:
        frame = pd.read_csv(trace_file).dropna()
        if self.system_type == "bsn":
            target_component = f"/g3t1_{metadata.sensor_index + 1}"
            frame = frame[frame["component"] == target_component].copy()
            if frame.empty:
                raise ValueError(f"文件{trace_file.name}中未找到传感器{target_component}的数据")
            return frame, "logicalTime(s)", "cost"

        if self.system_type not in TRACE_COLUMN_MAP:
            raise ValueError(f"不支持的系统类型: {self.system_type}")
        time_column, value_column = TRACE_COLUMN_MAP[self.system_type]
        return frame, time_column, value_column

    def _extract_segment_parameters(
        self,
        frame: pd.DataFrame,
        metadata,
        time_column: str,
        value_column: str,
    ) -> List[Tuple[str, DistributionParameters, str, Dict[str, float]]]:
        parameters: List[Tuple[str, DistributionParameters, str, Dict[str, float]]] = []
        max_time = float(frame[time_column].max()) + 1.0
        for index, norm_label in enumerate(metadata.trace_config):
            if norm_label.startswith("abn"):
                continue
            start = float(metadata.start_time[index])
            end = (
                float(metadata.start_time[index + 1])
                if index + 1 < len(metadata.start_time)
                else max_time
            )
            segment = frame[(frame[time_column] >= start) & (frame[time_column] < end)].copy()
            if value_column not in segment.columns or segment.empty:
                continue

            values = segment[value_column].astype(float).tolist()
            if len(values) < 2:
                continue

            context_key, context_features = self.parser.get_segment_context(metadata, index, norm_label)
            mean_value = sum(values) / len(values)
            variance = 0.0
            if len(values) > 1:
                variance = sum((value - mean_value) ** 2 for value in values) / (len(values) - 1)
            std_dev = variance ** 0.5

            parameter = DistributionParameters(
                    norm_label=norm_label,
                    mean=float(mean_value),
                    variance=float(variance),
                    std_dev=float(std_dev),
                    min_value=float(min(values)),
                    max_value=float(max(values)),
                    sample_count=len(values),
                    position=index + 1,
                    filename=metadata.filename,
                    raw_values=values,
                    context_key=context_key,
                    context_features=context_features,
                )
            group_label, group_context = self._build_group_label(metadata, norm_label)
            parameters.append(
                (
                    group_label,
                    parameter,
                    norm_label,
                    group_context,
                )
            )

        return parameters

    def _build_group_label(self, metadata, norm_label: str) -> Tuple[str, Dict[str, float]]:
        if self.system_type == "bsn":
            sensor_index = int(metadata.sensor_index)
            return f"sensor{sensor_index}_{norm_label}", {"sensor_index": float(sensor_index)}
        return norm_label, {}
