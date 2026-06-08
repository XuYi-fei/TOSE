import csv
import tempfile
import unittest
from pathlib import Path

import yaml


class DetectWadiTraceIntegrationTests(unittest.TestCase):
    def test_run_wadi_detection_supports_metric_fallback_for_trace_inputs(self):
        from detect_wadi import run_wadi_detection

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            trace_dir = root / "abnormal"
            trace_dir.mkdir(parents=True, exist_ok=True)

            trace_file = trace_dir / "trace.csv"
            with trace_file.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["time", "HMI_2_LT_001.PV", "segment_label"])
                writer.writeheader()
                for idx in range(6):
                    writer.writerow({"time": idx, "HMI_2_LT_001.PV": 68.0, "segment_label": "norm1"})
                for idx in range(6, 12):
                    writer.writerow({"time": idx, "HMI_2_LT_001.PV": 74.0, "segment_label": "norm2"})
                for idx in range(12, 18):
                    writer.writerow({"time": idx, "HMI_2_LT_001.PV": 80.0, "segment_label": "norm3"})
                for idx in range(18, 24):
                    writer.writerow({"time": idx, "HMI_2_LT_001.PV": 86.0, "segment_label": "abn1"})

            distributions_path = root / "learned_distributions.yaml"
            distributions = {
                "lt_state_0": {"metric": "HMI_2_LT_001.PV", "state_id": 0, "mu": 68.0, "sigma": 0.5, "sample_count": 100},
                "lt_state_1": {"metric": "HMI_2_LT_001.PV", "state_id": 1, "mu": 74.0, "sigma": 0.5, "sample_count": 100},
                "lt_state_2": {"metric": "HMI_2_LT_001.PV", "state_id": 2, "mu": 80.0, "sigma": 0.5, "sample_count": 100},
            }
            distributions_path.write_text(yaml.dump({"distributions": distributions}), encoding="utf-8")

            config = {
                "dataset": {"name": "wadi", "test_data_path": str(trace_dir)},
                "adapter": {"type": "wadi", "manual_include": [], "manual_exclude": []},
                "detection": {
                    "mode": "state_conditional",
                    "state_threshold": 3.0,
                    "distributions_path": str(distributions_path),
                },
                "state_inference": {
                    "method": "pump_status",
                    "pump_columns": ["HMI_2_P_001_STATUS", "HMI_2_P_002_STATUS"],
                    "fallback_metric": "HMI_2_LT_001.PV",
                    "fallback_threshold": 0.0,
                },
                "output": {
                    "results_csv": str(root / "detection_results.csv"),
                    "results_json": str(root / "detection_results.json"),
                },
            }

            config_path = root / "detect_config.yaml"
            config_path.write_text(yaml.dump(config), encoding="utf-8")

            success = run_wadi_detection(str(config_path), verbose=False)

            self.assertTrue(success)
            self.assertTrue((root / "detection_results.csv").exists())


if __name__ == "__main__":
    unittest.main()
