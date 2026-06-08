"""label-grouped baseline 配置定义。"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml


@dataclass
class LabelGroupedBaselineTrainingConfig:
    system_type: str
    data_path: str
    candidate_distributions: List[str] = field(
        default_factory=lambda: ["norm", "lognorm", "gamma", "weibull_min"]
    )
    normality_alpha: float = 0.05
    output_dir: str = ""
    learned_distributions_path: str = ""

    @classmethod
    def from_yaml(cls, config_path: str) -> "LabelGroupedBaselineTrainingConfig":
        raw = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
        output = raw.get("output", {})
        config = cls(
            system_type=raw.get("system_type", ""),
            data_path=raw.get("data_path", ""),
            candidate_distributions=list(
                raw.get("candidate_distributions", ["norm", "lognorm", "gamma", "weibull_min"])
            ),
            normality_alpha=float(raw.get("normality_alpha", 0.05)),
            output_dir=output.get(
                "dir",
                f"clustering_results/{raw.get('system_type', '')}/label_grouped_baseline",
            ),
            learned_distributions_path=output.get(
                "learned_distributions_path",
                f"clustering_results/{raw.get('system_type', '')}/learned_distributions_label_grouped.yaml",
            ),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.system_type not in {"rubis", "bsn", "swat", "wadi"}:
            raise ValueError(f"不支持的系统类型: {self.system_type}")
        if not self.data_path:
            raise ValueError("缺少必填字段: data_path")
        if not Path(self.data_path).exists():
            raise ValueError(f"数据路径不存在: {self.data_path}")
        if not self.candidate_distributions:
            raise ValueError("candidate_distributions不能为空")
        if not 0 < self.normality_alpha < 1:
            raise ValueError("normality_alpha必须位于(0, 1)区间内")
