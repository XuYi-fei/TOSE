#!/usr/bin/env python3
"""Run clustering for every standardized RQ1 holdout dataset."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cluster_analysis.cli import run_clustering


SYSTEM_CONFIG_MAP = {
    "rubis": "configs/rubis_clustering_config.yaml",
    "bsn": "configs/bsn_clustering_config.yaml",
    "swat": "configs/swat_clustering_config.yaml",
    "wadi": "configs/wadi_clustering_config.yaml",
}


def _rewrite_config(base_config: Path, identity_dir: Path, output_dir: Path, temp_dir: Path) -> Path:
    import yaml

    config = yaml.safe_load(base_config.read_text(encoding="utf-8"))
    config["data_path"] = str(identity_dir)
    config.setdefault("output", {})
    config["output"]["dir"] = str(output_dir)
    config["output"]["learned_distributions_path"] = str(output_dir / "learned_distributions.yaml")
    temp_dir.mkdir(parents=True, exist_ok=True)
    config_path = temp_dir / f"{output_dir.parent.name}_{output_dir.name}_{base_config.name}"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return config_path


def main() -> int:
    import os

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default="data_rq1_holdout", type=Path)
    parser.add_argument("--output-root", default="clustering_results_rq1_holdout", type=Path)
    parser.add_argument("--systems", nargs="+", default=["rubis", "bsn", "swat", "wadi"])
    parser.add_argument("--temp-config-root", default="tmp-test/rq1_holdout_configs", type=Path)
    args = parser.parse_args()
    os.environ.setdefault("MPLBACKEND", "Agg")
    os.environ.setdefault("MPLCONFIGDIR", str((Path("tmp-test") / "mplconfig").resolve()))

    for system in args.systems:
        base_config = Path(SYSTEM_CONFIG_MAP[system])
        for holdout_dir in sorted((args.data_root / system).glob("holdout_*")):
            if not holdout_dir.is_dir():
                continue
            identity_dir = holdout_dir / "identity"
            output_dir = args.output_root / system / holdout_dir.name
            temp_config = _rewrite_config(base_config, identity_dir, output_dir, args.temp_config_root)
            ok = run_clustering(str(temp_config), verbose=False)
            if not ok:
                raise SystemExit(f"clustering failed for {system}/{holdout_dir.name}")
            print(f"{system}/{holdout_dir.name}: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
