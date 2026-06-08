import csv
import tempfile
import unittest
from pathlib import Path

import yaml


class WadiGenericFrameworkTests(unittest.TestCase):
    def _write_generic_wadi_trace(self, root: Path, split: str = "identity") -> Path:
        trace_dir = root / split
        trace_dir.mkdir(parents=True, exist_ok=True)
        filename = (
            "eval_ident_trace-cnt-000-duration-18-config_num-3-"
            "trace_config-norm1,norm2,norm3-start_time-1,7,13.txt"
            if split == "identity"
            else "eval_abn_trace-cnt-000-duration-24-config_num-4-"
                 "trace_config-norm1,norm2,norm3,abn1-start_time-1,7,13,19.txt"
        )
        path = trace_dir / filename
        rows = []
        values = [68.0] * 6 + [74.0] * 6 + [80.0] * 6
        labels = ["norm1"] * 6 + ["norm2"] * 6 + ["norm3"] * 6
        if split == "abnormal":
            values += [86.0] * 6
            labels += ["abn1"] * 6

        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["simTime(s)", "HMI_2_LT_001.PV", "segment_label"])
            writer.writeheader()
            for idx, (value, label) in enumerate(zip(values, labels), start=1):
                writer.writerow(
                    {
                        "simTime(s)": idx,
                        "HMI_2_LT_001.PV": f"{value:.3f}",
                        "segment_label": label,
                    }
                )
        return path

    def _write_trace_source_csv(self, root: Path, split: str = "identity") -> Path:
        trace_dir = root / split
        trace_dir.mkdir(parents=True, exist_ok=True)
        filename = (
            "eval_ident_trace-cnt-000-duration-18-config_num-3-"
            "trace_config-norm1,norm2,norm3-start_time-1,7,13.csv"
            if split == "identity"
            else "eval_abn_trace-cnt-000-duration-24-config_num-4-"
                 "trace_config-norm1,norm2,norm3,abn1-start_time-1,7,13,19.csv"
        )
        path = trace_dir / filename
        rows = []
        values = [68.0] * 6 + [74.0] * 6 + [80.0] * 6
        labels = ["norm1"] * 6 + ["norm2"] * 6 + ["norm3"] * 6
        if split == "abnormal":
            values += [86.0] * 6
            labels += ["abn1"] * 6

        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["time", "HMI_2_LT_001.PV", "segment_label"])
            writer.writeheader()
            for idx, (value, label) in enumerate(zip(values, labels), start=1):
                writer.writerow(
                    {
                        "time": f"2023-12-18 00:00:{idx:02d}+00:00",
                        "HMI_2_LT_001.PV": f"{value:.3f}",
                        "segment_label": label,
                    }
                )
        return path

    def test_parser_factory_supports_wadi(self):
        from common.adapters import ParserFactory

        parser = ParserFactory.create("wadi")
        self.assertEqual(parser.__class__.__name__, "WADIParser")

    def test_wadi_parser_extracts_distribution_parameters_from_txt_trace(self):
        from common.adapters import ParserFactory

        with tempfile.TemporaryDirectory() as tmpdir:
            trace_file = self._write_generic_wadi_trace(Path(tmpdir), split="identity")
            parser = ParserFactory.create("wadi")

            parameters = parser.parse_file(trace_file)

            self.assertEqual(len(parameters), 3)
            self.assertEqual([p.norm_label for p in parameters], ["norm1", "norm2", "norm3"])
            self.assertAlmostEqual(parameters[0].mean, 68.0, places=3)
            self.assertAlmostEqual(parameters[1].mean, 74.0, places=3)
            self.assertAlmostEqual(parameters[2].mean, 80.0, places=3)

    def test_wadi_configs_validate_under_generic_framework(self):
        from anomaly_detection.config.config import DetectionConfig
        from cluster_analysis.config.config import ClusteringConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_generic_wadi_trace(root, split="identity")
            self._write_generic_wadi_trace(root, split="abnormal")

            learned = root / "learned_distributions.yaml"
            learned.write_text(
                yaml.dump(
                    {
                        "system_type": "wadi",
                        "distributions": {
                            "norm1": {"mu": 68.0, "sigma": 1.0, "variance": 1.0, "sample_count": 6, "cluster_id": 0},
                            "norm2": {"mu": 74.0, "sigma": 1.0, "variance": 1.0, "sample_count": 6, "cluster_id": 1},
                            "norm3": {"mu": 80.0, "sigma": 1.0, "variance": 1.0, "sample_count": 6, "cluster_id": 2},
                        },
                    }
                ),
                encoding="utf-8",
            )

            cluster_cfg = root / "cluster.yaml"
            cluster_cfg.write_text(
                yaml.dump(
                    {
                        "system_type": "wadi",
                        "data_path": str(root / "identity"),
                        "algorithms": ["gmm"],
                        "output": {"dir": str(root / "cluster_out"), "visualizations": False, "report": False},
                    }
                ),
                encoding="utf-8",
            )

            detect_cfg = root / "detect.yaml"
            detect_cfg.write_text(
                yaml.dump(
                    {
                        "system_type": "wadi",
                        "learned_distributions": str(learned),
                        "test_data_path": str(root / "abnormal"),
                        "output": {"dir": str(root / "detect_out"), "generate_visualizations": False},
                    }
                ),
                encoding="utf-8",
            )

            clustering = ClusteringConfig.from_yaml(str(cluster_cfg))
            detection = DetectionConfig.from_yaml(str(detect_cfg))

            self.assertEqual(clustering.system_type, "wadi")
            self.assertEqual(detection.system_type, "wadi")

    def test_convert_wadi_trace_dataset_to_generic_layout(self):
        from scripts.build_wadi_generic_dataset import convert_trace_dataset

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_root = root / "wadi_trace"
            self._write_trace_source_csv(source_root, split="identity")
            self._write_trace_source_csv(source_root, split="abnormal")
            output_root = root / "wadi"

            summary = convert_trace_dataset(source_root=source_root, output_root=output_root)

            self.assertEqual(summary["identity_count"], 1)
            self.assertEqual(summary["abnormal_count"], 1)

            identity_files = list((output_root / "identity").glob("*.txt"))
            abnormal_files = list((output_root / "abnormal").glob("*.txt"))
            self.assertEqual(len(identity_files), 1)
            self.assertEqual(len(abnormal_files), 1)

            with identity_files[0].open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["simTime(s)"], "1")
            self.assertEqual(rows[-1]["simTime(s)"], "18")
            self.assertIn("HMI_2_LT_001.PV", rows[0])


if __name__ == "__main__":
    unittest.main()
