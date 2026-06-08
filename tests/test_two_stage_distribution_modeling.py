import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
import yaml

from common.models import DistributionParameters


class TwoStageDistributionModelingTests(unittest.TestCase):
    def _make_parameter(
        self,
        norm_label: str,
        mean: float,
        variance: float,
        raw_values: list[float],
        filename: str,
        position: int,
    ) -> DistributionParameters:
        return DistributionParameters(
            norm_label=norm_label,
            mean=mean,
            variance=variance,
            std_dev=math.sqrt(variance),
            min_value=min(raw_values),
            max_value=max(raw_values),
            sample_count=len(raw_values),
            position=position,
            filename=filename,
            raw_values=raw_values,
        )

    def test_clustering_config_accepts_two_stage_distribution_modeling(self):
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
                        "algorithms": ["gmm"],
                        "distribution_modeling": {
                            "stage1_clustering_feature": "mu",
                            "candidate_distributions": ["norm", "gamma"],
                            "normality_alpha": 0.01,
                            "enable_context_calibration": True,
                            "context_modeling_method": "linear_mu",
                        },
                    }
                ),
                encoding="utf-8",
            )

            config = ClusteringConfig.from_yaml(str(config_path))

            self.assertEqual(config.stage1_clustering_feature, "mu")
            self.assertEqual(config.candidate_distributions, ["norm", "gamma"])
            self.assertEqual(config.normality_alpha, 0.01)
            self.assertTrue(config.enable_context_calibration)
            self.assertEqual(config.context_modeling_method, "linear_mu")

    def test_cluster_distribution_fitter_keeps_normal_for_gaussian_cluster(self):
        from cluster_analysis.core.distribution_fitting import ClusterDistributionFitter

        rng = np.random.default_rng(42)
        samples_a = rng.normal(loc=10.0, scale=1.2, size=120)
        samples_b = rng.normal(loc=10.2, scale=1.1, size=120)

        parameters = [
            self._make_parameter("norm1", float(samples_a.mean()), float(samples_a.var()), samples_a.tolist(), "a.txt", 1),
            self._make_parameter("norm1", float(samples_b.mean()), float(samples_b.var()), samples_b.tolist(), "b.txt", 2),
        ]

        fitter = ClusterDistributionFitter(candidate_distributions=["norm", "gamma"], normality_alpha=0.05)
        model = fitter.fit_cluster_distribution(cluster_id=0, parameters=parameters)

        self.assertEqual(model.distribution_type, "norm")
        self.assertGreater(model.goodness_of_fit["selected_p_value"], 0.05)
        self.assertEqual(model.sample_count, 240)

    def test_cluster_distribution_fitter_can_select_gamma_for_skewed_cluster(self):
        from cluster_analysis.core.distribution_fitting import ClusterDistributionFitter

        rng = np.random.default_rng(7)
        samples_a = rng.gamma(shape=2.0, scale=2.5, size=150)
        samples_b = rng.gamma(shape=2.2, scale=2.4, size=150)

        parameters = [
            self._make_parameter("norm2", float(samples_a.mean()), float(samples_a.var()), samples_a.tolist(), "c.txt", 1),
            self._make_parameter("norm2", float(samples_b.mean()), float(samples_b.var()), samples_b.tolist(), "d.txt", 2),
        ]

        fitter = ClusterDistributionFitter(
            candidate_distributions=["norm", "lognorm", "gamma", "weibull_min"],
            normality_alpha=0.05,
        )
        model = fitter.fit_cluster_distribution(cluster_id=1, parameters=parameters)

        self.assertNotEqual(model.distribution_type, "norm")
        self.assertIn(model.distribution_type, {"gamma", "lognorm", "weibull_min"})
        self.assertGreater(model.goodness_of_fit["selected_p_value"], 0.05)

    def test_detector_uses_max_p_value_across_heterogeneous_models(self):
        from anomaly_detection.core.detector import AnomalyDetector

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "learned_distributions.yaml"
            yaml_path.write_text(
                yaml.dump(
                    {
                        "system_type": "wadi",
                        "algorithm": "gmm",
                        "distributions": {
                            "cluster_0": {
                                "distribution_type": "gamma",
                                "fitted_params": {
                                    "shape_args": [2.0],
                                    "loc": 0.0,
                                    "scale": 2.0,
                                },
                                "mu": 4.0,
                                "sigma": math.sqrt(8.0),
                                "variance": 8.0,
                                "sample_count": 200,
                                "cluster_id": 0,
                            },
                            "cluster_1": {
                                "distribution_type": "norm",
                                "fitted_params": {
                                    "shape_args": [],
                                    "loc": 15.0,
                                    "scale": 1.0,
                                },
                                "mu": 15.0,
                                "sigma": 1.0,
                                "variance": 1.0,
                                "sample_count": 120,
                                "cluster_id": 1,
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            detector = AnomalyDetector.from_yaml(str(yaml_path), p_value_alpha=0.05)

            gamma_like = detector.detect_point(3.8)
            normal_like = detector.detect_point(15.1)
            abnormal = detector.detect_point(40.0)

            self.assertFalse(gamma_like.is_anomaly)
            self.assertEqual(gamma_like.closest_distribution, "cluster_0")
            self.assertGreater(gamma_like.best_p_value, 0.05)

            self.assertFalse(normal_like.is_anomaly)
            self.assertEqual(normal_like.closest_distribution, "cluster_1")
            self.assertGreater(normal_like.best_p_value, 0.05)

            self.assertTrue(abnormal.is_anomaly)
            self.assertLess(abnormal.best_p_value, 0.05)

    def test_reporter_persists_distribution_type_and_fitted_params(self):
        from cluster_analysis.core.result import AlgorithmResult, ClusteringResult
        from cluster_analysis.visualization.reporter import ClusteringReporter

        result = ClusteringResult(
            system_type="wadi",
            total_points=4,
            feature_matrix=np.array(
                [
                    [10.0, 1.0],
                    [10.2, 1.1],
                    [20.0, 4.0],
                    [20.2, 3.9],
                ]
            ),
            norm_labels=["norm1", "norm1", "norm2", "norm2"],
            filenames=["a.txt", "b.txt", "c.txt", "d.txt"],
            positions=[1, 2, 1, 2],
        )
        result.add_algorithm_result(
            AlgorithmResult(
                algorithm_name="gmm",
                n_clusters=2,
                labels=np.array([0, 0, 1, 1]),
                cluster_centers=np.array([[10.1, 1.05], [20.1, 3.95]]),
                additional_metrics={
                    "cluster_distribution_models": {
                        0: {
                            "cluster_id": 0,
                            "distribution_type": "norm",
                            "fitted_params": {"shape_args": [], "loc": 10.1, "scale": 1.0},
                            "mu": 10.1,
                            "sigma": 1.0,
                            "variance": 1.0,
                            "sample_count": 2,
                            "dominant_norm": "norm1",
                            "norm_label_distribution": {"norm1": 2},
                            "goodness_of_fit": {"selected_p_value": 0.72},
                            "context_key": "load=1.000000",
                            "context_features": {"load": 1.0},
                        },
                        1: {
                            "cluster_id": 1,
                            "distribution_type": "gamma",
                            "fitted_params": {"shape_args": [2.1], "loc": 0.0, "scale": 9.5},
                            "mu": 19.95,
                            "sigma": 4.5,
                            "variance": 20.25,
                            "sample_count": 2,
                            "dominant_norm": "norm2",
                            "norm_label_distribution": {"norm2": 2},
                            "goodness_of_fit": {"selected_p_value": 0.31},
                            "context_key": "load=2.000000",
                            "context_features": {"load": 2.0},
                        },
                    },
                    "context_calibration_model": {
                        "modeling_method": "linear_mu",
                        "feature_names": ["load"],
                        "intercept": 0.25,
                        "coefficients": {"load": 9.85},
                        "sample_count": 4,
                        "r_squared": 0.98,
                    },
                },
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = ClusteringReporter(result, tmpdir)
            output_path = Path(tmpdir) / "learned.yaml"
            saved_path = reporter.save_learned_distributions(output_path=output_path, algorithm_name="gmm")
            saved = yaml.safe_load(Path(saved_path).read_text(encoding="utf-8"))

            self.assertEqual(saved["distributions"]["cluster_0"]["distribution_type"], "norm")
            self.assertEqual(saved["distributions"]["cluster_1"]["distribution_type"], "gamma")
            self.assertEqual(saved["distributions"]["cluster_1"]["fitted_params"]["shape_args"], [2.1])
            self.assertEqual(saved["distributions"]["cluster_0"]["context_key"], "load=1.000000")
            self.assertEqual(saved["context_calibration_model"]["feature_names"], ["load"])


if __name__ == "__main__":
    unittest.main()
