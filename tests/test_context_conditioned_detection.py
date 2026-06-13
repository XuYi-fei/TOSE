import math
import tempfile
import unittest
from pathlib import Path

import yaml

from common.adapters import ParserFactory
from common.models import ContextCalibrationModel, DistributionParameters


class ContextConditionedDetectionTests(unittest.TestCase):
    def test_bsn_parser_extracts_segment_context(self):
        parser = ParserFactory.create("bsn")
        filename = (
            "eval_ident_trace-cnt-000-duration-600-sensor_index-3-config_num-3-"
            "trace_config-norm3,norm1,norm2-start_time-1,171,463-"
            "env_cptime-463-offset-0.0,0.0225-batt_cptime-171-"
            "B_offset_percent-0.075,0.0.txt"
        )

        metadata = parser.parse_filename(filename)

        self.assertIsNotNone(metadata)
        key0, features0 = parser.get_segment_context(metadata, 0, "norm3")
        key1, features1 = parser.get_segment_context(metadata, 1, "norm1")
        key2, features2 = parser.get_segment_context(metadata, 2, "norm2")

        self.assertEqual(key0, "batt_offset_percent=0.075000|env_offset=0.000000|sensor_index=3.000000")
        self.assertEqual(features0, {"env_offset": 0.0, "batt_offset_percent": 0.075, "sensor_index": 3.0})
        self.assertEqual(key1, "batt_offset_percent=0.000000|env_offset=0.000000|sensor_index=3.000000")
        self.assertEqual(features1, {"env_offset": 0.0, "batt_offset_percent": 0.0, "sensor_index": 3.0})
        self.assertEqual(key2, "batt_offset_percent=0.000000|env_offset=0.022500|sensor_index=3.000000")
        self.assertEqual(features2, {"env_offset": 0.0225, "batt_offset_percent": 0.0, "sensor_index": 3.0})

    def test_context_calibration_model_learns_bsn_like_mu_shift(self):
        parameters = [
            DistributionParameters(
                norm_label="cluster_a",
                mean=0.9,
                variance=1e-4,
                std_dev=0.01,
                min_value=0.85,
                max_value=0.95,
                sample_count=100,
                context_features={"env_offset": 0.0, "batt_offset_percent": 0.0},
            ),
            DistributionParameters(
                norm_label="cluster_b",
                mean=1.035,
                variance=1e-4,
                std_dev=0.01,
                min_value=0.99,
                max_value=1.08,
                sample_count=100,
                context_features={"env_offset": 0.0225, "batt_offset_percent": 0.0},
            ),
            DistributionParameters(
                norm_label="cluster_c",
                mean=0.9675,
                variance=1e-4,
                std_dev=0.01,
                min_value=0.92,
                max_value=1.01,
                sample_count=100,
                context_features={"env_offset": 0.0, "batt_offset_percent": 0.075},
            ),
        ]

        model = ContextCalibrationModel.fit(parameters)

        self.assertIsNotNone(model)
        self.assertAlmostEqual(model.predict({"env_offset": 0.025, "batt_offset_percent": 0.0}), 1.05, places=6)

    def test_detector_applies_context_location_shift(self):
        from anomaly_detection.core.detector import AnomalyDetector

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "learned_distributions.yaml"
            yaml_path.write_text(
                yaml.dump(
                    {
                        "system_type": "bsn",
                        "algorithm": "gmm",
                        "context_calibration_model": {
                            "modeling_method": "linear_mu",
                            "feature_names": ["batt_offset_percent", "env_offset"],
                            "intercept": 0.9,
                            "coefficients": {
                                "batt_offset_percent": 0.9,
                                "env_offset": 6.0,
                            },
                            "sample_count": 300,
                            "r_squared": 1.0,
                        },
                        "distributions": {
                            "cluster_0": {
                                "distribution_type": "norm",
                                "fitted_params": {"shape_args": [], "loc": 0.9, "scale": 0.01},
                                "mu": 0.9,
                                "sigma": 0.01,
                                "variance": 0.0001,
                                "sample_count": 100,
                                "cluster_id": 0,
                                "context_key": "batt_offset_percent=0.000000|env_offset=0.000000",
                                "context_features": {"env_offset": 0.0, "batt_offset_percent": 0.0},
                            },
                            "cluster_1": {
                                "distribution_type": "norm",
                                "fitted_params": {"shape_args": [], "loc": 1.035, "scale": 0.01},
                                "mu": 1.035,
                                "sigma": 0.01,
                                "variance": 0.0001,
                                "sample_count": 100,
                                "cluster_id": 1,
                                "context_key": "batt_offset_percent=0.000000|env_offset=0.022500",
                                "context_features": {"env_offset": 0.0225, "batt_offset_percent": 0.0},
                            },
                            "cluster_2": {
                                "distribution_type": "norm",
                                "fitted_params": {"shape_args": [], "loc": 0.9675, "scale": 0.01},
                                "mu": 0.9675,
                                "sigma": 0.01,
                                "variance": 0.0001,
                                "sample_count": 100,
                                "cluster_id": 2,
                                "context_key": "batt_offset_percent=0.075000|env_offset=0.000000",
                                "context_features": {"env_offset": 0.0, "batt_offset_percent": 0.075},
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            detector = AnomalyDetector.from_yaml(str(yaml_path), sigma_threshold=3.0)
            result = detector.detect_point(
                1.05,
                context_features={"env_offset": 0.025, "batt_offset_percent": 0.0},
            )

            self.assertFalse(result.is_anomaly)
            self.assertEqual(result.closest_distribution, "cluster_1")
            self.assertEqual(result.context_match_strategy, "nearest")
            self.assertEqual(result.matched_context_key, "batt_offset_percent=0.000000|env_offset=0.022500")
            self.assertAlmostEqual(result.context_location_shift, 0.015, places=6)
            self.assertGreater(result.best_p_value, 0.05)

    def test_detector_does_not_recompute_context_shift_for_same_distribution(self):
        from anomaly_detection.core.detector import AnomalyDetector
        from anomaly_detection.core.distribution import LearnedDistribution

        distributions = {
            "cluster_0": LearnedDistribution.from_dict(
                "cluster_0",
                {
                    "distribution_type": "norm",
                    "fitted_params": {"shape_args": [], "loc": 0.9, "scale": 0.01},
                    "mu": 0.9,
                    "sigma": 0.01,
                    "variance": 0.0001,
                    "sample_count": 100,
                    "cluster_id": 0,
                    "context_features": {"env_offset": 0.0},
                },
            ),
            "cluster_1": LearnedDistribution.from_dict(
                "cluster_1",
                {
                    "distribution_type": "norm",
                    "fitted_params": {"shape_args": [], "loc": 1.0, "scale": 0.01},
                    "mu": 1.0,
                    "sigma": 0.01,
                    "variance": 0.0001,
                    "sample_count": 100,
                    "cluster_id": 1,
                    "context_features": {"env_offset": 0.02},
                },
            ),
            "cluster_2": LearnedDistribution.from_dict(
                "cluster_2",
                {
                    "distribution_type": "norm",
                    "fitted_params": {"shape_args": [], "loc": 1.1, "scale": 0.01},
                    "mu": 1.1,
                    "sigma": 0.01,
                    "variance": 0.0001,
                    "sample_count": 100,
                    "cluster_id": 2,
                    "context_features": {"env_offset": 0.04},
                },
            ),
        }
        model = ContextCalibrationModel(
            modeling_method="linear_mu",
            feature_names=["env_offset"],
            intercept=0.0,
            coefficients={"env_offset": 1.0},
            sample_count=300,
            r_squared=1.0,
        )
        detector = AnomalyDetector(
            distributions=distributions,
            sigma_threshold=3.0,
            context_calibration_model=model,
            context_matching_strategy="global",
            apply_context_mu_shift=True,
        )

        original = detector._context_location_shift
        call_count = {"value": 0}

        def wrapped(distribution, context_features):
            call_count["value"] += 1
            return original(distribution, context_features)

        detector._context_location_shift = wrapped

        result = detector.detect_point(1.01, context_features={"env_offset": 0.02})

        self.assertEqual(result.closest_distribution, "cluster_1")
        self.assertEqual(call_count["value"], len(distributions))

    def test_detector_routes_candidates_by_partition_context_first(self):
        from anomaly_detection.core.detector import AnomalyDetector

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "learned_distributions.yaml"
            yaml_path.write_text(
                yaml.dump(
                    {
                        "system_type": "bsn",
                        "algorithm": "gmm",
                        "partition_context_features": ["sensor_index"],
                        "distributions": {
                            "sensor0_norm1": {
                                "distribution_type": "norm",
                                "fitted_params": {"shape_args": [], "loc": 0.9000, "scale": 0.01},
                                "mu": 0.9000,
                                "sigma": 0.01,
                                "variance": 0.0001,
                                "sample_count": 100,
                                "cluster_id": 0,
                                "context_key": "sensor_index=0.000000|state=1.000000",
                                "context_features": {"sensor_index": 0.0, "state": 1.0},
                                "partition_context_key": "sensor_index=0.000000",
                                "partition_context_features": {"sensor_index": 0.0},
                            },
                            "sensor0_norm2": {
                                "distribution_type": "norm",
                                "fitted_params": {"shape_args": [], "loc": 1.0350, "scale": 0.01},
                                "mu": 1.0350,
                                "sigma": 0.01,
                                "variance": 0.0001,
                                "sample_count": 100,
                                "cluster_id": 1,
                                "context_key": "sensor_index=0.000000|state=2.000000",
                                "context_features": {"sensor_index": 0.0, "state": 2.0},
                                "partition_context_key": "sensor_index=0.000000",
                                "partition_context_features": {"sensor_index": 0.0},
                            },
                            "sensor2_norm3": {
                                "distribution_type": "norm",
                                "fitted_params": {"shape_args": [], "loc": 0.9675, "scale": 0.01},
                                "mu": 0.9675,
                                "sigma": 0.01,
                                "variance": 0.0001,
                                "sample_count": 100,
                                "cluster_id": 2,
                                "context_key": "sensor_index=2.000000|state=3.000000",
                                "context_features": {"sensor_index": 2.0, "state": 3.0},
                                "partition_context_key": "sensor_index=2.000000",
                                "partition_context_features": {"sensor_index": 2.0},
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            detector = AnomalyDetector.from_yaml(str(yaml_path), sigma_threshold=3.0)
            result = detector.detect_point(
                0.9675,
                context_features={"sensor_index": 0.0, "state": 99.0},
            )

            self.assertEqual(result.matched_context_key, "sensor_index=0.000000")
            self.assertEqual(result.context_match_strategy, "partition_exact")
            self.assertEqual({item["distribution_label"] for item in result.top_matches}, {"sensor0_norm1", "sensor0_norm2"})
            self.assertNotEqual(result.closest_distribution, "sensor2_norm3")


if __name__ == "__main__":
    unittest.main()
