import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
import numpy as np

from anomaly_detection.config.config import DetectionConfig
from anomaly_detection.core.detector import BOCPDDetector
from anomaly_detection.core.evaluator import AggregatedMetrics, TraceEvaluationMetrics, AnomalyPoint, AnomalyEvaluator
from anomaly_detection.visualization.reporter import DetectionReporter


class BOCPDDetectionModeTests(unittest.TestCase):
    def test_detection_config_accepts_bocpd_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "abnormal").mkdir()
            learned = root / "learned.yaml"
            learned.write_text(
                yaml.dump(
                    {
                        "system_type": "rubis",
                        "algorithm": "gmm",
                        "distributions": {
                            "norm1": {
                                "distribution_type": "norm",
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
                        "system_type": "rubis",
                        "learned_distributions": str(learned),
                        "test_data_path": str(root / "abnormal"),
                        "detection": {
                            "mode": "bocpd",
                            "bocpd": {
                                "hazard_lambda": 40,
                                "max_run_length": 50,
                                "state_prior": "sample_count",
                                "changepoint_posterior_threshold": 0.6,
                                "raw_anomaly_rule": "cp_and_tail",
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            config = DetectionConfig.from_yaml(str(config_path))

            self.assertEqual(config.detection.mode, "bocpd")
            self.assertEqual(config.detection.bocpd.hazard_lambda, 40.0)
            self.assertEqual(config.detection.bocpd.max_run_length, 50)
            self.assertEqual(config.detection.bocpd.state_prior, "sample_count")
            self.assertEqual(config.detection.bocpd.raw_anomaly_rule, "cp_and_tail")
            self.assertEqual(config.detection.bocpd.tail_persistence_threshold, 2)

    def test_bocpd_detector_tracks_changepoint_fields(self):
        distributions = {
            "norm1": {
                "distribution_type": "norm",
                "mu": 0.0,
                "sigma": 0.2,
                "variance": 0.04,
                "sample_count": 100,
                "cluster_id": 0,
            },
            "norm2": {
                "distribution_type": "norm",
                "mu": 5.0,
                "sigma": 0.2,
                "variance": 0.04,
                "sample_count": 100,
                "cluster_id": 1,
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            learned = Path(tmpdir) / "learned.yaml"
            learned.write_text(
                yaml.dump(
                    {
                        "system_type": "rubis",
                        "algorithm": "gmm",
                        "distributions": distributions,
                    }
                ),
                encoding="utf-8",
            )

            detector = BOCPDDetector.from_yaml(
                str(learned),
                sigma_threshold=3.0,
                hazard_lambda=5.0,
                max_run_length=20,
                state_prior="uniform",
                changepoint_posterior_threshold=0.2,
                raw_anomaly_rule="cp_only",
            )
            detector.reset_trace_state()

            stable = [detector.detect_point(0.01) for _ in range(6)]
            shifted = detector.detect_point(4.9)

            self.assertTrue(all(result.changepoint_probability is not None for result in stable))
            self.assertIsNotNone(shifted.changepoint_probability)
            self.assertIsNotNone(shifted.most_likely_run_length)
            self.assertEqual(shifted.detection_mode, "bocpd")
            self.assertGreaterEqual(shifted.changepoint_probability, 0.0)
            self.assertLessEqual(shifted.changepoint_probability, 1.0)

    def test_bocpd_tail_persistence_requires_consecutive_low_tail_points(self):
        distributions = {
            "norm1": {
                "distribution_type": "norm",
                "mu": 0.0,
                "sigma": 0.1,
                "variance": 0.01,
                "sample_count": 100,
                "cluster_id": 0,
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            learned = Path(tmpdir) / "learned.yaml"
            learned.write_text(
                yaml.dump(
                    {
                        "system_type": "rubis",
                        "algorithm": "gmm",
                        "distributions": distributions,
                    }
                ),
                encoding="utf-8",
            )

            detector = BOCPDDetector.from_yaml(
                str(learned),
                sigma_threshold=3.0,
                hazard_lambda=5.0,
                max_run_length=20,
                state_prior="uniform",
                changepoint_posterior_threshold=0.2,
                raw_anomaly_rule="tail_only",
                tail_persistence_threshold=2,
            )
            detector.reset_trace_state()

            first = detector.detect_point(0.35)
            second = detector.detect_point(0.36)

            self.assertFalse(first.is_anomaly)
            self.assertTrue(second.is_anomaly)
            self.assertIn("tail_persistence_satisfied", second.raw_anomaly_reasons)

    def test_reporter_outputs_bocpd_metadata_and_point_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = DetectionReporter(
                output_dir=tmpdir,
                file_suffix="bocpd",
                cluster_count=3,
                clustering_algorithm="gmm",
                alarm_count_policy="binomial_confidence_bound",
                sigma_threshold=3.0,
                point_anomaly_probability=0.0027,
                aggregation_method="max_p_value",
                trace_alarm_confidence=0.99,
                context_matching_strategy="nearest",
                apply_context_mu_shift=True,
                context_calibration_enabled=True,
                detection_mode="bocpd",
                bocpd_config={
                    "hazard_lambda": 50,
                    "max_run_length": 200,
                    "state_prior": "sample_count",
                    "changepoint_posterior_threshold": 0.5,
                    "raw_anomaly_rule": "cp_and_tail",
                },
            )

            point = AnomalyPoint(
                time=10.0,
                value=9.5,
                is_detected=True,
                z_scores={"norm1": 4.2},
                p_values={"norm1": 0.0002},
                best_p_value=0.0002,
                distribution_type="norm",
                closest_distribution="norm1",
                detection_mode="bocpd",
                best_tail_p_value=0.0002,
                best_log_likelihood=-12.5,
                changepoint_probability=0.81,
                most_likely_run_length=0,
                raw_anomaly_reasons=["high_changepoint_probability", "low_tail_probability"],
                candidate_distribution_count=3,
                top_matches=[
                    {"distribution_label": "norm1", "tail_probability": 0.0002, "log_likelihood": -12.5}
                ],
            )
            trace_metric = TraceEvaluationMetrics(
                filename="trace.txt",
                classification="TP",
                has_abn1=True,
                abn1_start_time=9.0,
                first_detection_time=10.0,
                first_raw_anomaly_time=10.0,
                detection_delay_loops=1,
                total_detection_count=1,
                trigger_alarm_count=1,
                trigger_allowed_count=0,
                detection_mode="bocpd",
                first_detection_changepoint_probability=0.81,
                first_detection_run_length=0,
                first_detection_best_distribution="norm1",
                first_detection_best_tail_p_value=0.0002,
                abnormal_time=2.0,
                abnormal_total_time=100.0,
                anomaly_points=[point],
            )
            aggregated = AggregatedMetrics(
                total_traces=1,
                tp_count=1,
                fp_count=0,
                fn_count=0,
                tn_count=0,
                precision=1.0,
                recall=1.0,
                f1_score=1.0,
                avg_delay_loops=1.0,
                min_delay_loops=1,
                max_delay_loops=1,
                abnormal_time=2.0,
                abnormal_total_time=100.0,
                trace_metrics=[trace_metric],
            )

            json_path = reporter.generate_json_report(aggregated, "rubis", "config.yaml")
            data = json.loads(Path(json_path).read_text(encoding="utf-8"))

            self.assertEqual(data["metadata"]["detection_mode"], "bocpd")
            self.assertEqual(data["summary"]["bocpd"]["hazard_lambda"], 50)
            trace_detail = data["trace_details"][0]
            self.assertEqual(trace_detail["first_detection_run_length"], 0)
            anomaly_point = trace_detail["anomaly_points"][0]
            self.assertEqual(anomaly_point["detection_mode"], "bocpd")
            self.assertAlmostEqual(anomaly_point["changepoint_probability"], 0.81, places=6)
            self.assertEqual(anomaly_point["raw_anomaly_reasons"][0], "high_changepoint_probability")

    def test_bocpd_trace_alarm_triggers_on_first_raw_anomaly(self):
        class StubDetector:
            detection_mode = "bocpd"
            sigma_threshold = 3.0
            point_anomaly_probability = 0.0026997960632601913

            def __init__(self):
                self.calls = 0

            def reset_trace_state(self):
                self.calls = 0

            def detect_point(self, value, context_key=None, context_features=None):
                self.calls += 1
                is_second = self.calls == 2
                return type(
                    "Result",
                    (),
                    {
                        "is_anomaly": is_second,
                        "closest_distribution": "norm1",
                        "best_p_value": 0.0001 if is_second else 0.5,
                        "all_p_values": {"norm1": 0.0001 if is_second else 0.5},
                        "distribution_type": "norm",
                        "all_z_scores": {"norm1": 4.0 if is_second else 0.1},
                        "min_z_score": 4.0 if is_second else 0.1,
                        "matched_context_key": None,
                        "context_match_strategy": "global",
                        "context_location_shift": 0.0,
                        "detection_mode": "bocpd",
                        "best_tail_p_value": 0.0001 if is_second else 0.5,
                        "best_log_likelihood": -12.0 if is_second else -0.1,
                        "changepoint_probability": 0.9 if is_second else 0.1,
                        "most_likely_run_length": 0 if is_second else 1,
                        "raw_anomaly_reasons": ["high_changepoint_probability", "low_tail_probability"] if is_second else [],
                        "candidate_distribution_count": 3,
                        "top_matches": [],
                    },
                )()

        evaluator = AnomalyEvaluator(StubDetector(), "rubis")
        trace_file = Path(
            "eval_abn_trace-cnt-000-duration-64800-config_num-2-trace_config-norm1,abn1-start_time-960,1200.txt"
        )

        with patch(
            "anomaly_detection.core.evaluator.load_trace_series",
            return_value=(np.array([960.0, 1200.0, 1210.0]), np.array([0.1, 0.2, 0.3])),
        ):
            metrics = evaluator.evaluate_trace(trace_file)

        self.assertEqual(metrics.first_raw_anomaly_time, 1200.0)
        self.assertEqual(metrics.first_detection_time, 1200.0)
        self.assertEqual(metrics.trigger_alarm_count, 1)
        self.assertEqual(metrics.trigger_allowed_count, 0)
        self.assertEqual(metrics.classification, "TP")


if __name__ == "__main__":
    unittest.main()
