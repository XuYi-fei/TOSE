import csv
import tempfile
import unittest
from pathlib import Path

import yaml


class LabelGroupedBaselineTests(unittest.TestCase):
    def _write_swat_identity_trace(
        self,
        root: Path,
        idx: int,
        config_labels: str,
        start_times: str,
        values_by_label: dict[str, float],
    ) -> Path:
        trace_dir = root / "identity"
        trace_dir.mkdir(parents=True, exist_ok=True)
        path = trace_dir / (
            f"eval_ident_trace-cnt-{idx:03d}-duration-24-config_num-{len(config_labels.split(','))}-"
            f"trace_config-{config_labels}-start_time-{start_times}.txt"
        )
        labels = config_labels.split(",")
        starts = [int(x) for x in start_times.split(",")]
        rows = []
        end_time = 25
        for i, label in enumerate(labels):
            start = starts[i]
            end = starts[i + 1] if i + 1 < len(starts) else end_time
            value = values_by_label[label]
            for t in range(start, end):
                rows.append(
                    {
                        "time": t,
                        "water_tank": "tank301",
                        "noisy_B_in": 0.0,
                        "noisy_B_out": 0.0,
                        "u_1_in": 0.0,
                        "u_1_out": 1.0,
                        "y_0": value,
                    }
                )
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "time",
                    "water_tank",
                    "noisy_B_in",
                    "noisy_B_out",
                    "u_1_in",
                    "u_1_out",
                    "y_0",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)
        return path

    def _write_swat_abnormal_trace(self, root: Path, idx: int = 0) -> Path:
        trace_dir = root / "abnormal"
        trace_dir.mkdir(parents=True, exist_ok=True)
        path = trace_dir / (
            f"eval_abn_trace-cnt-{idx:03d}-duration-24-config_num-4-"
            "trace_config-norm1,norm2,norm3,abn1-start_time-1,7,13,19.txt"
        )
        rows = []
        for t in range(1, 25):
            if t < 7:
                value = 0.0
            elif t < 13:
                value = 0.37
            elif t < 19:
                value = -0.37
            else:
                value = 1.5
            rows.append(
                {
                    "time": t,
                    "water_tank": "tank301",
                    "noisy_B_in": 0.0,
                    "noisy_B_out": 0.0,
                    "u_1_in": 0.0,
                    "u_1_out": 1.0,
                    "y_0": value,
                }
            )
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "time",
                    "water_tank",
                    "noisy_B_in",
                    "noisy_B_out",
                    "u_1_in",
                    "u_1_out",
                    "y_0",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)
        return path

    def _write_bsn_identity_trace(
        self,
        root: Path,
        idx: int,
        sensor_index: int,
        values_by_label: dict[str, float],
    ) -> Path:
        trace_dir = root / "identity"
        trace_dir.mkdir(parents=True, exist_ok=True)
        path = trace_dir / (
            f"eval_ident_trace-cnt-{idx:03d}-duration-24-sensor_index-{sensor_index}-config_num-3-"
            "trace_config-norm1,norm2,norm3-start_time-1,9,17.txt"
        )
        rows = []
        for t in range(1, 25):
            if t < 9:
                label = "norm1"
            elif t < 17:
                label = "norm2"
            else:
                label = "norm3"
            rows.append(
                {
                    "logicalTime(s)": t,
                    "logicalTimestamp(ms)": t * 1000,
                    "component": f"/g3t1_{sensor_index + 1}",
                    "freq_double": 6,
                    "freq": 6,
                    "cost": values_by_label[label],
                }
            )
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "logicalTime(s)",
                    "logicalTimestamp(ms)",
                    "component",
                    "freq_double",
                    "freq",
                    "cost",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)
        return path

    def _write_bsn_abnormal_trace(self, root: Path, sensor_index: int, idx: int = 0) -> Path:
        trace_dir = root / "abnormal"
        trace_dir.mkdir(parents=True, exist_ok=True)
        path = trace_dir / (
            f"eval_abn_trace-cnt-{idx:03d}-duration-24-sensor_index-{sensor_index}-config_num-4-"
            "trace_config-norm1,norm2,norm3,abn1-start_time-1,9,17,21.txt"
        )
        rows = []
        for t in range(1, 25):
            if t < 9:
                value = 10.0
            elif t < 17:
                value = 20.0
            elif t < 21:
                value = 30.0
            else:
                value = 80.0
            rows.append(
                {
                    "logicalTime(s)": t,
                    "logicalTimestamp(ms)": t * 1000,
                    "component": f"/g3t1_{sensor_index + 1}",
                    "freq_double": 6,
                    "freq": 6,
                    "cost": value,
                }
            )
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "logicalTime(s)",
                    "logicalTimestamp(ms)",
                    "component",
                    "freq_double",
                    "freq",
                    "cost",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_label_grouped_training_outputs_three_distributions_and_keeps_repeated_segments(self):
        from cluster_label_grouped_baseline import run_label_grouped_baseline_clustering

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_swat_identity_trace(
                root,
                0,
                "norm3,norm1,norm3,norm1",
                "1,7,13,19",
                {"norm1": 0.0, "norm3": -0.37},
            )
            self._write_swat_identity_trace(
                root,
                1,
                "norm2,norm1,norm2",
                "1,9,17",
                {"norm1": 0.0, "norm2": 0.37},
            )
            self._write_swat_identity_trace(
                root,
                2,
                "norm1,norm2,norm3",
                "1,9,17",
                {"norm1": 0.0, "norm2": 0.37, "norm3": -0.37},
            )

            config_path = root / "cluster.yaml"
            config_path.write_text(
                yaml.dump(
                    {
                        "system_type": "swat",
                        "data_path": str(root / "identity"),
                        "output": {
                            "dir": str(root / "cluster_out"),
                            "learned_distributions_path": str(
                                root / "cluster_out" / "learned_distributions_label_grouped.yaml"
                            ),
                        },
                    }
                ),
                encoding="utf-8",
            )

            success = run_label_grouped_baseline_clustering(str(config_path), verbose=False)

            self.assertTrue(success)
            learned = root / "cluster_out" / "learned_distributions_label_grouped.yaml"
            self.assertTrue(learned.exists())
            saved = yaml.safe_load(learned.read_text(encoding="utf-8"))
            self.assertEqual(saved["algorithm"], "label_grouped_baseline")
            self.assertEqual(set(saved["distributions"].keys()), {"norm1", "norm2", "norm3"})
            self.assertEqual(saved["distributions"]["norm1"]["sample_count"], 28)
            self.assertEqual(saved["distributions"]["norm2"]["sample_count"], 24)
            self.assertEqual(saved["distributions"]["norm3"]["sample_count"], 20)

    def test_label_grouped_detection_uses_independent_suffix_outputs(self):
        from cluster_label_grouped_baseline import run_label_grouped_baseline_clustering
        from detect import run_detection

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_swat_identity_trace(
                root,
                0,
                "norm1,norm2,norm3",
                "1,7,13",
                {"norm1": 0.0, "norm2": 0.37, "norm3": -0.37},
            )
            self._write_swat_identity_trace(
                root,
                1,
                "norm1,norm2,norm3",
                "1,7,13",
                {"norm1": 0.01, "norm2": 0.36, "norm3": -0.36},
            )
            self._write_swat_abnormal_trace(root)

            cluster_out = root / "cluster_out"
            detect_out = root / "detect_out"
            cluster_config_path = root / "cluster.yaml"
            cluster_config_path.write_text(
                yaml.dump(
                    {
                        "system_type": "swat",
                        "data_path": str(root / "identity"),
                        "output": {
                            "dir": str(cluster_out),
                            "learned_distributions_path": str(
                                cluster_out / "learned_distributions_label_grouped.yaml"
                            ),
                        },
                    }
                ),
                encoding="utf-8",
            )
            self.assertTrue(run_label_grouped_baseline_clustering(str(cluster_config_path), verbose=False))

            detect_config_path = root / "detect.yaml"
            detect_config_path.write_text(
                yaml.dump(
                    {
                        "system_type": "swat",
                        "learned_distributions": str(
                            cluster_out / "learned_distributions_label_grouped.yaml"
                        ),
                        "test_data_path": str(root / "abnormal"),
                        "output": {
                            "dir": str(detect_out),
                            "file_suffix": "label_grouped",
                            "generate_visualizations": False,
                        },
                    }
                ),
                encoding="utf-8",
            )

            success = run_detection(str(detect_config_path), verbose=False)

            self.assertTrue(success)
            self.assertTrue((detect_out / "detection_results_label_grouped.json").exists())
            self.assertTrue((detect_out / "detection_results_label_grouped.csv").exists())
            self.assertTrue((detect_out / "detection_report_label_grouped.md").exists())
            payload = yaml.safe_load(
                (detect_out / "detection_results_label_grouped.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["metadata"]["clustering_algorithm"], "label_grouped_baseline")
            self.assertEqual(payload["metadata"]["cluster_count"], 3)

    def test_bsn_label_grouped_training_splits_by_sensor_index(self):
        from cluster_label_grouped_baseline import run_label_grouped_baseline_clustering

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_bsn_identity_trace(
                root,
                idx=0,
                sensor_index=0,
                values_by_label={"norm1": 10.0, "norm2": 20.0, "norm3": 30.0},
            )
            self._write_bsn_identity_trace(
                root,
                idx=1,
                sensor_index=1,
                values_by_label={"norm1": 100.0, "norm2": 200.0, "norm3": 300.0},
            )

            config_path = root / "cluster.yaml"
            config_path.write_text(
                yaml.dump(
                    {
                        "system_type": "bsn",
                        "data_path": str(root / "identity"),
                        "output": {
                            "dir": str(root / "cluster_out"),
                            "learned_distributions_path": str(
                                root / "cluster_out" / "learned_distributions_label_grouped.yaml"
                            ),
                        },
                    }
                ),
                encoding="utf-8",
            )

            success = run_label_grouped_baseline_clustering(str(config_path), verbose=False)

            self.assertTrue(success)
            saved = yaml.safe_load(
                (root / "cluster_out" / "learned_distributions_label_grouped.yaml").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                set(saved["distributions"].keys()),
                {
                    "sensor0_norm1",
                    "sensor0_norm2",
                    "sensor0_norm3",
                    "sensor1_norm1",
                    "sensor1_norm2",
                    "sensor1_norm3",
                },
            )
            self.assertEqual(saved["distributions"]["sensor0_norm1"]["context_features"]["sensor_index"], 0.0)
            self.assertEqual(saved["distributions"]["sensor1_norm1"]["context_features"]["sensor_index"], 1.0)

    def test_bsn_label_grouped_detection_matches_current_sensor_only(self):
        from cluster_label_grouped_baseline import run_label_grouped_baseline_clustering
        from detect import run_detection

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_bsn_identity_trace(
                root,
                idx=0,
                sensor_index=0,
                values_by_label={"norm1": 10.0, "norm2": 20.0, "norm3": 30.0},
            )
            self._write_bsn_identity_trace(
                root,
                idx=1,
                sensor_index=1,
                values_by_label={"norm1": 100.0, "norm2": 200.0, "norm3": 300.0},
            )
            self._write_bsn_abnormal_trace(root, sensor_index=0, idx=0)

            cluster_out = root / "cluster_out"
            detect_out = root / "detect_out"
            cluster_config = root / "cluster.yaml"
            cluster_config.write_text(
                yaml.dump(
                    {
                        "system_type": "bsn",
                        "data_path": str(root / "identity"),
                        "output": {
                            "dir": str(cluster_out),
                            "learned_distributions_path": str(
                                cluster_out / "learned_distributions_label_grouped.yaml"
                            ),
                        },
                    }
                ),
                encoding="utf-8",
            )
            self.assertTrue(run_label_grouped_baseline_clustering(str(cluster_config), verbose=False))

            detect_config = root / "detect.yaml"
            detect_config.write_text(
                yaml.dump(
                    {
                        "system_type": "bsn",
                        "learned_distributions": str(
                            cluster_out / "learned_distributions_label_grouped.yaml"
                        ),
                        "test_data_path": str(root / "abnormal"),
                        "output": {
                            "dir": str(detect_out),
                            "file_suffix": "label_grouped",
                            "generate_visualizations": False,
                        },
                    }
                ),
                encoding="utf-8",
            )

            success = run_detection(str(detect_config), verbose=False)

            self.assertTrue(success)
            payload = yaml.safe_load(
                (detect_out / "detection_results_label_grouped.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["metadata"]["cluster_count"], 6)
            trace_detail = payload["trace_details"][0]
            self.assertEqual(trace_detail["classification"], "TP")


if __name__ == "__main__":
    unittest.main()
