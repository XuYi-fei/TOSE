"""ARI helpers for RQ4 GROUP-only clustering comparison."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from sklearn.metrics import adjusted_rand_score

from cluster_analysis.config.config import ClusteringConfig
from cluster_analysis.core.engine import ClusteringEngine
from cluster_analysis.core.result import ClusteringResult
from common.models import DistributionParameters


ALGORITHMS = [
    "hdbscan",
    "gmm",
    "affinity_propagation",
    "mean_shift",
]


SYSTEM_CLUSTERING_CONFIG_MAP = {
    "rubis": "configs/rubis_clustering_config.yaml",
    "bsn": "configs/bsn_clustering_config.yaml",
    "swat": "configs/swat_clustering_config.yaml",
    "wadi": "configs/wadi_clustering_config.yaml",
}


def truth_label_for_parameter(system: str, parameter: DistributionParameters) -> str:
    """Build the ground-truth label used by RQ4 ARI."""

    if system == "bsn":
        sensor_index = parameter.context_features.get("sensor_index")
        if sensor_index is None:
            raise ValueError("BSN parameter missing sensor_index context for ARI computation")
        return f"sensor{int(sensor_index)}_{parameter.norm_label}"
    return parameter.norm_label


def build_clustering_result_for_ari(
    system: str,
    *,
    algorithms: Iterable[str] = ALGORITHMS,
    config_path: str | Path | None = None,
) -> ClusteringResult:
    """Run identity clustering once and retain all algorithm labels for ARI."""

    resolved_config_path = Path(config_path or SYSTEM_CLUSTERING_CONFIG_MAP[system])
    config = ClusteringConfig.from_yaml(str(resolved_config_path))
    engine = ClusteringEngine(
        system_type=config.system_type,
        algorithm_names=list(algorithms),
        algorithm_params=config.algorithm_params,
        stage1_clustering_feature=config.stage1_clustering_feature,
        candidate_distributions=config.candidate_distributions,
        normality_alpha=config.normality_alpha,
        enable_context_calibration=config.enable_context_calibration,
        context_modeling_method=config.context_modeling_method,
        partition_context_features=config.partition_context_features,
        boundary_trim_points=config.boundary_trim_points,
    )
    return engine.run_clustering(config.data_path)


def compute_ari_from_result(
    system: str,
    algorithm: str,
    clustering_result: ClusteringResult,
) -> float:
    """Compute ARI from an already generated clustering result."""

    if algorithm not in clustering_result.algorithm_results:
        raise KeyError(f"{system} clustering result missing algorithm: {algorithm}")

    truth_labels = []
    for norm_label, filename, context_features in zip(
        clustering_result.norm_labels,
        clustering_result.filenames,
        clustering_result.context_features,
    ):
        parameter = DistributionParameters(
            norm_label=norm_label,
            mean=0.0,
            variance=0.0,
            std_dev=0.0,
            min_value=0.0,
            max_value=0.0,
            sample_count=0,
            filename=filename,
            context_features=context_features,
        )
        truth_labels.append(truth_label_for_parameter(system, parameter))

    predicted_labels = clustering_result.algorithm_results[algorithm].labels.tolist()
    return float(adjusted_rand_score(truth_labels, predicted_labels))


def compute_algorithm_ari(
    system: str,
    algorithm: str,
    *,
    config_path: str | Path | None = None,
) -> float:
    """Compatibility helper for one-off ARI evaluation."""
    result = build_clustering_result_for_ari(system, algorithms=[algorithm], config_path=config_path)
    return compute_ari_from_result(system, algorithm, result)


def summarize_ari_matrix(
    systems: Iterable[str],
    algorithms: Iterable[str] = ALGORITHMS,
) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for system in systems:
        clustering_result = build_clustering_result_for_ari(system, algorithms=algorithms)
        for algorithm in algorithms:
            rows.append(
                {
                    "system": system,
                    "algorithm": algorithm,
                    "ari": compute_ari_from_result(system, algorithm, clustering_result),
                }
            )
    return rows
