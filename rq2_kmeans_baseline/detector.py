"""
基于最近中心距离的 RQ2 baseline 检测器。
"""
from pathlib import Path
from typing import Dict

from anomaly_detection.core.detector import DetectionResult

from .model import KMeansBaselineModel


class KMeansDistanceDetector:
    """最近中心距离检测器。"""

    def __init__(self, baseline_model: KMeansBaselineModel):
        self.model = baseline_model
        self.clusters = baseline_model.clusters

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "KMeansDistanceDetector":
        return cls(KMeansBaselineModel.from_yaml(yaml_path))

    def detect_point(self, value: float) -> DetectionResult:
        all_distances: Dict[str, float] = {
            f"cluster_{cluster.cluster_id}": abs(value - cluster.center)
            for cluster in self.clusters
        }
        all_scores: Dict[str, float] = {}
        for cluster in self.clusters:
            label = f"cluster_{cluster.cluster_id}"
            distance = all_distances[label]
            if cluster.distance_threshold <= 0:
                score = 0.0
            else:
                score = max(0.0, 1.0 - (distance / cluster.distance_threshold))
            all_scores[label] = score

        closest_label = min(all_distances, key=all_distances.get)
        closest_distance = all_distances[closest_label]
        best_score = all_scores[closest_label]
        cluster_id = int(closest_label.split("_")[1])
        threshold = self.clusters[cluster_id].distance_threshold
        return DetectionResult(
            is_anomaly=closest_distance > threshold,
            closest_distribution=closest_label,
            best_p_value=best_score,
            all_p_values=all_scores,
            distribution_type="distance_threshold",
            min_z_score=closest_distance,
            all_z_scores=all_distances,
        )
