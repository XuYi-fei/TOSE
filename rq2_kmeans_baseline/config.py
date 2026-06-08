"""
RQ2 baseline 配置定义。
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml


def _validate_system_type(system_type: str) -> None:
    if system_type not in {"rubis", "bsn", "swat", "wadi"}:
        raise ValueError(f"不支持的系统类型: {system_type}")


@dataclass
class BaselineTrainingConfig:
    system_type: str
    data_path: str
    k_values: List[int] = field(default_factory=lambda: list(range(2, 11)))
    random_state: int = 42
    n_init: int = 10
    output_dir: str = ""

    @classmethod
    def from_yaml(cls, config_path: str) -> "BaselineTrainingConfig":
        raw = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
        output = raw.get("output", {})
        config = cls(
            system_type=raw.get("system_type", ""),
            data_path=raw.get("data_path", ""),
            k_values=list(raw.get("k_values", list(range(2, 11)))),
            random_state=int(raw.get("random_state", 42)),
            n_init=int(raw.get("n_init", 10)),
            output_dir=output.get("dir", f"clustering_results/{raw.get('system_type', '')}/rq2_kmeans_baseline"),
        )
        config.validate()
        return config

    def validate(self) -> None:
        _validate_system_type(self.system_type)
        if not self.data_path:
            raise ValueError("缺少必填字段: data_path")
        if not Path(self.data_path).exists():
            raise ValueError(f"数据路径不存在: {self.data_path}")
        if not self.k_values:
            raise ValueError("k_values不能为空")
        if any(k < 2 for k in self.k_values):
            raise ValueError("k_values中的k必须>=2")


@dataclass
class BaselineDetectionConfig:
    system_type: str
    baseline_models_dir: str
    test_data_path: str
    best_k_metric: str = "f1"
    output_dir: str = ""

    @classmethod
    def from_yaml(cls, config_path: str) -> "BaselineDetectionConfig":
        raw = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
        output = raw.get("output", {})
        config = cls(
            system_type=raw.get("system_type", ""),
            baseline_models_dir=raw.get("baseline_models_dir", ""),
            test_data_path=raw.get("test_data_path", ""),
            best_k_metric=raw.get("best_k_metric", "f1"),
            output_dir=output.get("dir", f"detection_results/{raw.get('system_type', '')}/rq2_kmeans_baseline"),
        )
        config.validate()
        return config

    def validate(self) -> None:
        _validate_system_type(self.system_type)
        if not self.baseline_models_dir:
            raise ValueError("缺少必填字段: baseline_models_dir")
        if not Path(self.baseline_models_dir).exists():
            raise ValueError(f"baseline模型目录不存在: {self.baseline_models_dir}")
        if not self.test_data_path:
            raise ValueError("缺少必填字段: test_data_path")
        if not Path(self.test_data_path).exists():
            raise ValueError(f"测试数据路径不存在: {self.test_data_path}")
        if self.best_k_metric not in {"f1", "recall", "precision"}:
            raise ValueError(f"不支持的best_k_metric: {self.best_k_metric}")
