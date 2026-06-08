"""
RQ2 baseline 训练器。
"""
from pathlib import Path
from typing import List

import numpy as np
from sklearn.cluster import KMeans

from common.utils.trace_series import get_target_metric_name, load_all_metric_values

from .model import ClusterDistanceStats, KMeansBaselineModel


class KMeansNumericBaselineTrainer:
    """对原始数值点执行 1D kmeans 的 baseline 训练器。"""

    DISTANCE_RULE = "cluster_distance_mean_plus_3sigma"

    def __init__(self, system_type: str, random_state: int = 42, n_init: int = 10):
        self.system_type = system_type
        self.random_state = random_state
        self.n_init = n_init

    def load_values(self, data_path: str) -> np.ndarray:
        return load_all_metric_values(data_path, self.system_type)

    def fit(self, values: np.ndarray, k: int) -> KMeansBaselineModel:
        features = values.reshape(-1, 1)
        model = KMeans(n_clusters=k, random_state=self.random_state, n_init=self.n_init)
        original_labels = model.fit_predict(features)
        centers = model.cluster_centers_.reshape(-1)
        ordered_cluster_ids = np.argsort(centers)

        clusters: List[ClusterDistanceStats] = []
        for new_cluster_id, original_cluster_id in enumerate(ordered_cluster_ids):
            center = float(centers[original_cluster_id])
            cluster_values = values[original_labels == original_cluster_id]
            distances = np.abs(cluster_values - center)
            distance_mean = float(distances.mean()) if len(distances) else 0.0
            distance_sigma = float(distances.std()) if len(distances) else 0.0
            clusters.append(
                ClusterDistanceStats(
                    cluster_id=new_cluster_id,
                    center=center,
                    sample_count=int(len(cluster_values)),
                    distance_mean=distance_mean,
                    distance_sigma=distance_sigma,
                    distance_threshold=float(distance_mean + 3 * distance_sigma),
                )
            )

        return KMeansBaselineModel(
            system_type=self.system_type,
            baseline_type="kmeans_numeric_distance",
            k=k,
            random_state=self.random_state,
            n_init=self.n_init,
            distance_threshold_rule=self.DISTANCE_RULE,
            target_metric=get_target_metric_name(self.system_type),
            clusters=clusters,
        )

    def fit_all(self, data_path: str, k_values: List[int], output_dir: str) -> List[Path]:
        values = self.load_values(data_path)
        output_root = Path(output_dir)
        output_root.mkdir(parents=True, exist_ok=True)
        saved_paths: List[Path] = []
        for k in sorted(k_values):
            baseline_model = self.fit(values, k)
            saved_paths.append(baseline_model.save(output_root / f"baseline_model_k{k}.yaml"))
        return saved_paths
