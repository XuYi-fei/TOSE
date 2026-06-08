"""
RQ2 baseline 模型定义与序列化。
"""
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

import yaml


@dataclass
class ClusterDistanceStats:
    cluster_id: int
    center: float
    sample_count: int
    distance_mean: float
    distance_sigma: float
    distance_threshold: float


@dataclass
class KMeansBaselineModel:
    system_type: str
    baseline_type: str
    k: int
    random_state: int
    n_init: int
    distance_threshold_rule: str
    target_metric: str
    clusters: List[ClusterDistanceStats]

    def to_dict(self) -> dict:
        return {
            "system_type": self.system_type,
            "baseline_type": self.baseline_type,
            "k": self.k,
            "random_state": self.random_state,
            "n_init": self.n_init,
            "distance_threshold_rule": self.distance_threshold_rule,
            "target_metric": self.target_metric,
            "clusters": [asdict(cluster) for cluster in self.clusters],
        }

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.dump(self.to_dict(), sort_keys=False), encoding="utf-8")
        return path

    @classmethod
    def from_yaml(cls, path: str | Path) -> "KMeansBaselineModel":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls(
            system_type=raw["system_type"],
            baseline_type=raw["baseline_type"],
            k=int(raw["k"]),
            random_state=int(raw["random_state"]),
            n_init=int(raw["n_init"]),
            distance_threshold_rule=raw["distance_threshold_rule"],
            target_metric=raw["target_metric"],
            clusters=[ClusterDistanceStats(**cluster) for cluster in raw["clusters"]],
        )
