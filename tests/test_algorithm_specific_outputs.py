import tempfile
import unittest
from pathlib import Path

import numpy as np
import yaml

from anomaly_detection.core.detector import AnomalyDetector
from anomaly_detection.core.evaluator import AggregatedMetrics, TraceEvaluationMetrics
from anomaly_detection.visualization.reporter import DetectionReporter
from cluster_analysis.core.result import AlgorithmResult, ClusteringResult
from cluster_analysis.visualization.reporter import ClusteringReporter


class AlgorithmSpecificOutputTests(unittest.TestCase):
    def test_clustering_config_accepts_save_per_algorithm_distributions(self):
        from cluster_analysis.config.config import ClusteringConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "identity").mkdir()
            config_path = root / "cluster.yaml"
            config_path.write_text(
                yaml.dump(
                    {
                        "system_type": "wadi",
                        "data_path": str(root / "identity"),
                        "algorithms": ["gmm", "mean_shift"],
                        "output": {
                            "dir": str(root / "cluster_out"),
                            "visualizations": False,
                            "report": False,
                            "save_per_algorithm_distributions": True,
                        },
                    }
                ),
                encoding="utf-8",
            )

            config = ClusteringConfig.from_yaml(str(config_path))

            self.assertTrue(config.save_per_algorithm_distributions)

    def test_detection_config_accepts_output_file_suffix(self):
        from anomaly_detection.config.config import DetectionConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "abnormal").mkdir()
            learned = root / "learned_distributions_gmm.yaml"
            learned.write_text(
                yaml.dump(
                    {
                        "system_type": "wadi",
                        "algorithm": "gmm",
                        "distributions": {
                            "norm1": {
                                "mu": 68.0,
                                "sigma": 1.0,
                                "variance": 1.0,
                                "sample_count": 10,
                                "cluster_id": 0,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            config_path = root / "detect.yaml"
            config_path.write_text(
                yaml.dump(
                    {
                        "system_type": "wadi",
                        "learned_distributions": str(learned),
                        "test_data_path": str(root / "abnormal"),
                        "output": {
                            "dir": str(root / "detect_out"),
                            "generate_visualizations": False,
                            "file_suffix": "gmm",
                        },
                    }
                ),
                encoding="utf-8",
            )

            config = DetectionConfig.from_yaml(str(config_path))

            self.assertEqual(config.output.file_suffix, "gmm")

    def test_detection_config_accepts_alarm_count_policy(self):
        from anomaly_detection.config.config import DetectionConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "abnormal").mkdir()
            learned = root / "learned.yaml"
            learned.write_text(
                yaml.dump(
                    {
                        "system_type": "wadi",
                        "algorithm": "gmm",
                        "distributions": {
                            "cluster_0": {
                                "mu": 68.0,
                                "sigma": 1.0,
                                "variance": 1.0,
                                "sample_count": 10,
                                "cluster_id": 0,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            config_path = root / "detect.yaml"
            config_path.write_text(
                yaml.dump(
                    {
                        "system_type": "wadi",
                        "learned_distributions": str(learned),
                        "test_data_path": str(root / "abnormal"),
                        "detection": {
                            "sigma_threshold": 3.0,
                            "alarm_count_policy": "binomial_confidence_bound",
                            "trace_alarm_confidence": 0.99,
                        },
                    }
                ),
                encoding="utf-8",
            )

            config = DetectionConfig.from_yaml(str(config_path))

            self.assertEqual(config.detection.alarm_count_policy, "binomial_confidence_bound")
            self.assertEqual(config.detection.trace_alarm_confidence, 0.99)

    def test_detection_config_accepts_context_detection_settings(self):
        from anomaly_detection.config.config import DetectionConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "abnormal").mkdir()
            learned = root / "learned.yaml"
            learned.write_text(
                yaml.dump(
                    {
                        "system_type": "bsn",
                        "algorithm": "gmm",
                        "distributions": {
                            "cluster_0": {
                                "mu": 1.0,
                                "sigma": 0.1,
                                "variance": 0.01,
                                "sample_count": 10,
                                "cluster_id": 0,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            config_path = root / "detect.yaml"
            config_path.write_text(
                yaml.dump(
                    {
                        "system_type": "bsn",
                        "learned_distributions": str(learned),
                        "test_data_path": str(root / "abnormal"),
                        "detection": {
                            "context_matching_strategy": "nearest",
                            "apply_context_mu_shift": True,
                        },
                    }
                ),
                encoding="utf-8",
            )

            config = DetectionConfig.from_yaml(str(config_path))

            self.assertEqual(config.detection.context_matching_strategy, "nearest")
            self.assertTrue(config.detection.apply_context_mu_shift)

    def test_detection_config_uses_sigma_derived_alpha_by_default(self):
        from anomaly_detection.config.config import DetectionConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "abnormal").mkdir()
            learned = root / "learned.yaml"
            learned.write_text(
                yaml.dump(
                    {
                        "system_type": "wadi",
                        "algorithm": "gmm",
                        "distributions": {
                            "cluster_0": {
                                "mu": 68.0,
                                "sigma": 1.0,
                                "variance": 1.0,
                                "sample_count": 10,
                                "cluster_id": 0,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            config_path = root / "detect.yaml"
            config_path.write_text(
                yaml.dump(
                    {
                        "system_type": "wadi",
                        "learned_distributions": str(learned),
                        "test_data_path": str(root / "abnormal"),
                        "detection": {
                            "sigma_threshold": 3.0,
                        },
                    }
                ),
                encoding="utf-8",
            )

            config = DetectionConfig.from_yaml(str(config_path))
            detector = AnomalyDetector.from_yaml(
                str(learned),
                sigma_threshold=config.detection.sigma_threshold,
                p_value_alpha=config.detection.p_value_alpha,
            )

            self.assertIsNone(config.detection.p_value_alpha)
            self.assertAlmostEqual(detector.point_anomaly_probability, 0.002699796, places=6)
            self.assertEqual(config.detection.mode, "pointwise")

    def test_clustering_reporter_can_export_specific_algorithm_distributions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = ClusteringResult(
                system_type="wadi",
                total_points=6,
                feature_matrix=np.array(
                    [
                        [68.0, 0.4],
                        [68.2, 0.5],
                        [74.0, 0.6],
                        [74.2, 0.5],
                        [80.0, 0.8],
                        [80.3, 0.9],
                    ]
                ),
                norm_labels=["norm1", "norm1", "norm2", "norm2", "norm3", "norm3"],
                filenames=["a", "a", "b", "b", "c", "c"],
                positions=[1, 1, 2, 2, 3, 3],
            )
            result.add_algorithm_result(
                AlgorithmResult(
                    algorithm_name="mean_shift",
                    n_clusters=2,
                    labels=np.array([0, 0, 1, 1, 1, 1]),
                    silhouette_score=0.9,
                    execution_time=0.1,
                )
            )
            result.add_algorithm_result(
                AlgorithmResult(
                    algorithm_name="gmm",
                    n_clusters=4,
                    labels=np.array([2, 3, 1, 1, 0, 0]),
                    silhouette_score=0.7,
                    execution_time=0.1,
                )
            )

            reporter = ClusteringReporter(result, tmpdir)
            output_path = Path(tmpdir) / "learned_distributions_gmm.yaml"

            saved_path = reporter.save_learned_distributions(
                output_path=output_path,
                clustering_config_path="configs/wadi_clustering_config.yaml",
                algorithm_name="gmm",
            )

            saved = yaml.safe_load(Path(saved_path).read_text(encoding="utf-8"))
            self.assertEqual(saved["algorithm"], "gmm")
            self.assertEqual(set(saved["distributions"].keys()), {"cluster_0", "cluster_1", "cluster_2", "cluster_3"})
            self.assertEqual(saved["distributions"]["cluster_0"]["dominant_norm"], "norm3")
            self.assertEqual(saved["distributions"]["cluster_1"]["dominant_norm"], "norm2")
            self.assertEqual(saved["distributions"]["cluster_2"]["dominant_norm"], "norm1")
            self.assertEqual(saved["distributions"]["cluster_3"]["dominant_norm"], "norm1")

    def test_detector_can_use_cluster_level_distributions_directly(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "learned_distributions_gmm.yaml"
            yaml_path.write_text(
                yaml.dump(
                    {
                        "system_type": "wadi",
                        "algorithm": "gmm",
                        "distributions": {
                            "cluster_0": {
                                "mu": 68.0,
                                "sigma": 0.5,
                                "variance": 0.25,
                                "sample_count": 80,
                                "cluster_id": 0,
                                "dominant_norm": "norm1",
                            },
                            "cluster_1": {
                                "mu": 74.0,
                                "sigma": 0.5,
                                "variance": 0.25,
                                "sample_count": 90,
                                "cluster_id": 1,
                                "dominant_norm": "norm2",
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            detector = AnomalyDetector.from_yaml(str(yaml_path), sigma_threshold=3.0)
            normal = detector.detect_point(74.3)
            abnormal = detector.detect_point(90.0)

            self.assertFalse(normal.is_anomaly)
            self.assertEqual(normal.closest_distribution, "cluster_1")
            self.assertTrue(abnormal.is_anomaly)

    def test_detection_reporter_appends_output_suffix(self):
        metrics = AggregatedMetrics(
            total_traces=1,
            tp_count=1,
            fp_count=0,
            fn_count=0,
            tn_count=0,
            precision=1.0,
            recall=1.0,
            f1_score=1.0,
            avg_delay_loops=0.0,
            min_delay_loops=0,
            max_delay_loops=0,
            abnormal_time=0.0,
            abnormal_total_time=0.0,
            trace_metrics=[
                TraceEvaluationMetrics(
                    filename="sample.txt",
                    classification="TP",
                    has_abn1=True,
                    abn1_start_time=10.0,
                    first_detection_time=10.0,
                    first_raw_anomaly_time=9.0,
                    detection_delay_loops=0,
                    total_detection_count=1,
                    trigger_alarm_count=2,
                    trigger_allowed_count=1,
                    abnormal_time=0.0,
                    abnormal_total_time=0.0,
                )
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = DetectionReporter(
                tmpdir,
                file_suffix="gmm",
                cluster_count=4,
                clustering_algorithm="gmm",
                alarm_count_policy="binomial_confidence_bound",
                sigma_threshold=3.0,
                point_anomaly_probability=0.002699796,
                aggregation_method="max_p_value",
            )

            report_path = reporter.generate_report(metrics, "wadi")
            json_path = reporter.generate_json_report(metrics, "wadi", "cfg.yaml")
            csv_path = reporter.generate_csv_report(metrics, "wadi")

            self.assertEqual(Path(report_path).name, "detection_report_gmm.md")
            self.assertEqual(Path(json_path).name, "detection_results_gmm.json")
            self.assertEqual(Path(csv_path).name, "detection_results_gmm.csv")

            report_text = Path(report_path).read_text(encoding="utf-8")
            self.assertIn("**辨识算法**: gmm", report_text)
            self.assertIn("**聚类簇数**: 4", report_text)
            self.assertIn("binomial_confidence_bound", report_text)

            json_data = yaml.safe_load(Path(json_path).read_text(encoding="utf-8"))
            self.assertEqual(json_data["metadata"]["clustering_algorithm"], "gmm")
            self.assertEqual(json_data["metadata"]["cluster_count"], 4)
            self.assertEqual(json_data["summary"]["cluster_count"], 4)
            self.assertEqual(json_data["metadata"]["alarm_count_policy"], "binomial_confidence_bound")
            self.assertEqual(json_data["metadata"]["sigma_threshold"], 3.0)
            self.assertEqual(json_data["metadata"]["aggregation_method"], "max_p_value")
            self.assertEqual(json_data["trace_details"][0]["first_raw_anomaly_time"], 9.0)
            self.assertEqual(json_data["trace_details"][0]["trigger_alarm_count"], 2)
            self.assertEqual(json_data["trace_details"][0]["trigger_allowed_count"], 1)

            csv_text = Path(csv_path).read_text(encoding="utf-8")
            self.assertIn("clustering_algorithm", csv_text)
            self.assertIn("cluster_count", csv_text)
            self.assertIn("first_raw_anomaly_time", csv_text)
            self.assertIn("trigger_alarm_count", csv_text)


if __name__ == "__main__":
    unittest.main()
