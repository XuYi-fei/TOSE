import csv
import json
import tempfile
import unittest
from pathlib import Path

import yaml


class RQ2KMeansBaselineTests(unittest.TestCase):
    def _write_wadi_trace(self, root: Path, split: str, idx: int = 0, abnormal_value: float = 90.0) -> Path:
        trace_dir = root / split
        trace_dir.mkdir(parents=True, exist_ok=True)
        filename = (
            f"eval_ident_trace-cnt-{idx:03d}-duration-18-config_num-3-"
            "trace_config-norm1,norm2,norm3-start_time-1,7,13.txt"
            if split == "identity"
            else f"eval_abn_trace-cnt-{idx:03d}-duration-24-config_num-4-"
                 "trace_config-norm1,norm2,norm3,abn1-start_time-1,7,13,19.txt"
        )
        path = trace_dir / filename

        values = [68.0] * 6 + [74.0] * 6 + [80.0] * 6
        labels = ["norm1"] * 6 + ["norm2"] * 6 + ["norm3"] * 6
        if split == "abnormal":
            values += [abnormal_value] * 6
            labels += ["abn1"] * 6

        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["simTime(s)", "HMI_2_LT_001.PV", "segment_label"])
            writer.writeheader()
            for ts, (value, label) in enumerate(zip(values, labels), start=1):
                writer.writerow(
                    {
                        "simTime(s)": ts,
                        "HMI_2_LT_001.PV": f"{value:.3f}",
                        "segment_label": label,
                    }
                )
        return path

    def _write_bsn_abnormal_trace(self, root: Path) -> Path:
        filename = (
            "eval_abn_trace-cnt-000-duration-24-sensor_index-1-config_num-4-"
            "trace_config-norm1,norm2,norm3,abn1-start_time-1,7,13,19.txt"
        )
        path = root / filename
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["logicalTime(s)", "logicalTimestamp(ms)", "component", "freq_double", "freq", "cost"],
            )
            writer.writeheader()
            for ts in range(1, 25):
                target_value = 1.0 if ts < 19 else 9.0
                writer.writerow(
                    {
                        "logicalTime(s)": ts,
                        "logicalTimestamp(ms)": ts * 1000,
                        "component": "/g3t1_1",
                        "freq_double": 6,
                        "freq": 6,
                        "cost": 100.0,
                    }
                )
                writer.writerow(
                    {
                        "logicalTime(s)": ts,
                        "logicalTimestamp(ms)": ts * 1000,
                        "component": "/g3t1_2",
                        "freq_double": 6,
                        "freq": 6,
                        "cost": target_value,
                    }
                )
        return path

    def _write_swat_abnormal_trace(self, root: Path) -> Path:
        filename = (
            "eval_abn_trace-cnt-000-duration-24-config_num-4-"
            "trace_config-norm1,norm2,norm3,abn1-start_time-1,7,13,19.txt"
        )
        path = root / filename
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["time", "water_tank", "noisy_B_in", "noisy_B_out", "u_1_in", "u_1_out", "y_0"],
            )
            writer.writeheader()
            for ts in range(1, 25):
                writer.writerow(
                    {
                        "time": ts,
                        "water_tank": "tank301",
                        "noisy_B_in": 0.0,
                        "noisy_B_out": 0.0,
                        "u_1_in": 0.0,
                        "u_1_out": 1.0,
                        "y_0": 0.2 if ts < 19 else 3.5,
                    }
                )
        return path

    def _write_learned_distribution(self, path: Path, mu: float, sigma: float = 0.5) -> None:
        path.write_text(
            yaml.dump(
                {
                    "system_type": "test",
                    "algorithm": "manual",
                    "distributions": {
                        "cluster_0": {
                            "mu": mu,
                            "sigma": sigma,
                            "variance": sigma ** 2,
                            "sample_count": 24,
                            "cluster_id": 0,
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

    def test_run_kmeans_baseline_training_saves_models_for_each_k(self):
        from cluster_kmeans_baseline import run_kmeans_baseline_clustering

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_wadi_trace(root, "identity", idx=0)
            self._write_wadi_trace(root, "identity", idx=1)

            config = {
                "system_type": "wadi",
                "data_path": str(root / "identity"),
                "k_values": [2, 3],
                "random_state": 42,
                "n_init": 10,
                "output": {"dir": str(root / "cluster_out")},
            }
            config_path = root / "cluster.yaml"
            config_path.write_text(yaml.dump(config), encoding="utf-8")

            success = run_kmeans_baseline_clustering(str(config_path), verbose=False)

            self.assertTrue(success)
            model_k2 = root / "cluster_out" / "baseline_model_k2.yaml"
            model_k3 = root / "cluster_out" / "baseline_model_k3.yaml"
            self.assertTrue(model_k2.exists())
            self.assertTrue(model_k3.exists())

            model = yaml.safe_load(model_k3.read_text(encoding="utf-8"))
            self.assertEqual(model["baseline_type"], "kmeans_numeric_distance")
            self.assertEqual(model["k"], 3)
            self.assertEqual([cluster["cluster_id"] for cluster in model["clusters"]], [0, 1, 2])
            self.assertEqual(sorted(cluster["center"] for cluster in model["clusters"]), [68.0, 74.0, 80.0])

    def test_run_kmeans_baseline_detection_outputs_per_k_and_best_summary(self):
        from cluster_kmeans_baseline import run_kmeans_baseline_clustering
        from detect_kmeans_baseline import run_kmeans_baseline_detection

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_wadi_trace(root, "identity", idx=0)
            self._write_wadi_trace(root, "identity", idx=1)
            self._write_wadi_trace(root, "abnormal", idx=0, abnormal_value=92.0)

            cluster_config = {
                "system_type": "wadi",
                "data_path": str(root / "identity"),
                "k_values": [2, 3],
                "random_state": 42,
                "n_init": 10,
                "output": {"dir": str(root / "cluster_out")},
            }
            cluster_config_path = root / "cluster.yaml"
            cluster_config_path.write_text(yaml.dump(cluster_config), encoding="utf-8")
            self.assertTrue(run_kmeans_baseline_clustering(str(cluster_config_path), verbose=False))

            detect_config = {
                "system_type": "wadi",
                "baseline_models_dir": str(root / "cluster_out"),
                "test_data_path": str(root / "abnormal"),
                "best_k_metric": "f1",
                "output": {"dir": str(root / "detect_out")},
            }
            detect_config_path = root / "detect.yaml"
            detect_config_path.write_text(yaml.dump(detect_config), encoding="utf-8")

            success = run_kmeans_baseline_detection(str(detect_config_path), verbose=False)

            self.assertTrue(success)
            self.assertTrue((root / "detect_out" / "detection_results_k2.json").exists())
            self.assertTrue((root / "detect_out" / "detection_results_k3.json").exists())
            summary_path = root / "detect_out" / "rq2_kmeans_summary.json"
            self.assertTrue(summary_path.exists())

            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["best_k_metric"], "f1")
            self.assertIn(summary["best_k"], [2, 3])
            self.assertEqual(len(summary["results"]), 2)
            self.assertTrue(any(item["is_best_k"] for item in summary["results"]))

    def test_anomaly_evaluator_supports_bsn_logical_time_and_sensor_index_filtering(self):
        from anomaly_detection.core.detector import AnomalyDetector
        from anomaly_detection.core.evaluator import AnomalyEvaluator

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            trace_path = self._write_bsn_abnormal_trace(root)
            learned_path = root / "learned.yaml"
            self._write_learned_distribution(learned_path, mu=1.0)

            detector = AnomalyDetector.from_yaml(str(learned_path), sigma_threshold=3.0)
            evaluator = AnomalyEvaluator(detector, "bsn")

            metrics = evaluator.evaluate_trace(trace_path)

            self.assertEqual(metrics.classification, "TP")
            self.assertEqual(metrics.first_raw_anomaly_time, 19)
            self.assertEqual(metrics.first_detection_time, 20)

    def test_anomaly_evaluator_supports_swat_time_column(self):
        from anomaly_detection.core.detector import AnomalyDetector
        from anomaly_detection.core.evaluator import AnomalyEvaluator

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            trace_path = self._write_swat_abnormal_trace(root)
            learned_path = root / "learned.yaml"
            self._write_learned_distribution(learned_path, mu=0.2)

            detector = AnomalyDetector.from_yaml(str(learned_path), sigma_threshold=3.0)
            evaluator = AnomalyEvaluator(detector, "swat")

            metrics = evaluator.evaluate_trace(trace_path)

            self.assertEqual(metrics.classification, "TP")
            self.assertEqual(metrics.first_raw_anomaly_time, 19)
            self.assertEqual(metrics.first_detection_time, 20)

    def test_trace_trigger_uses_binomial_confidence_bound(self):
        from anomaly_detection.core.detector import AnomalyDetector
        from anomaly_detection.core.evaluator import AnomalyEvaluator

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            trace_path = root / (
                "eval_abn_trace-cnt-000-duration-100-config_num-2-"
                "trace_config-norm1,abn1-start_time-1,51.txt"
            )
            learned_path = root / "learned.yaml"

            learned_path.write_text(
                yaml.dump(
                    {
                        "system_type": "wadi",
                        "algorithm": "manual",
                        "distributions": {
                            "cluster_0": {
                                "mu": 68.0,
                                "sigma": 1.0,
                                "variance": 1.0,
                                "sample_count": 100,
                                "cluster_id": 0,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            with trace_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["simTime(s)", "HMI_2_LT_001.PV", "segment_label"])
                writer.writeheader()
                for ts in range(1, 101):
                    value = 68.0
                    label = "norm1" if ts < 51 else "abn1"
                    if ts in {10, 60, 61, 62}:
                        value = 72.5
                    writer.writerow(
                        {
                            "simTime(s)": ts,
                            "HMI_2_LT_001.PV": f"{value:.3f}",
                            "segment_label": label,
                        }
                    )

            detector = AnomalyDetector.from_yaml(str(learned_path), sigma_threshold=3.0)
            evaluator = AnomalyEvaluator(
                detector,
                "wadi",
                alarm_count_policy="binomial_confidence_bound",
                trace_alarm_confidence=0.99,
            )

            metrics = evaluator.evaluate_trace(trace_path)

            self.assertEqual(metrics.first_raw_anomaly_time, 10)
            self.assertEqual(metrics.first_detection_time, 61)
            self.assertEqual(metrics.classification, "TP")
            self.assertEqual(metrics.trigger_alarm_count, 3)
            self.assertEqual(metrics.trigger_allowed_count, 2)


if __name__ == "__main__":
    unittest.main()
