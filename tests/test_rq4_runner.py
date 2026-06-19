from pathlib import Path
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from common.models import DistributionParameters


class RQ4RunnerTests(unittest.TestCase):
    def test_truth_label_for_bsn_uses_sensor_and_norm(self) -> None:
        from rq_methods.rq4_ari import truth_label_for_parameter

        parameter = DistributionParameters(
            norm_label="norm2",
            mean=1.0,
            variance=0.1,
            std_dev=0.316,
            min_value=0.5,
            max_value=1.5,
            sample_count=30,
            context_features={"sensor_index": 3.0},
        )

        self.assertEqual(truth_label_for_parameter("bsn", parameter), "sensor3_norm2")
        self.assertEqual(truth_label_for_parameter("rubis", parameter), "norm2")

    def test_rq4_runner_writes_group_only_summary_with_ari(self) -> None:
        from rq_methods.rq4_runner import RQ4Runner

        fake_detection_row = {
            "system": "rubis",
            "algorithm": "gmm",
            "detection_mode": "pointwise",
            "cluster_count": 3,
            "total_traces": 200,
            "tp_count": 190,
            "fp_count": 10,
            "fn_count": 0,
            "tn_count": 0,
            "tp_rate": 0.95,
            "fp_rate": 0.05,
            "fn_rate": 0.0,
            "precision": 0.95,
            "recall": 1.0,
            "f1_score": 0.9743,
            "hazard_lambda": "",
            "max_run_length": "",
            "state_prior": "",
            "changepoint_posterior_threshold": "",
            "raw_anomaly_rule": "",
            "tail_persistence_threshold": "",
        }

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "rq_results" / "rq4"
            with patch("rq_methods.rq4_runner.evaluate_system_algorithm", return_value=dict(fake_detection_row)), patch(
                "rq_methods.rq4_runner.build_clustering_result_for_ari",
                return_value=object(),
            ), patch(
                "rq_methods.rq4_runner.compute_ari_from_result",
                return_value=0.9123,
            ):
                rows = RQ4Runner(
                    systems=["rubis"],
                    algorithms=["gmm"],
                    output_dir=output_dir,
                ).run()

            self.assertEqual(rows[0]["ari"], 0.9123)
            csv_path = output_dir / "summary" / "rq4_group_algorithms_summary.csv"
            self.assertTrue(csv_path.exists())
            csv_text = csv_path.read_text(encoding="utf-8")
            self.assertIn("ari", csv_text)
            self.assertIn("0.9123", csv_text)

    def test_rq4_runner_does_not_reuse_detection_results_by_default(self) -> None:
        from rq_methods.rq4_runner import RQ4Runner

        payload = {
            "metadata": {
                "cluster_count": 3,
                "detection_mode": "pointwise",
            },
            "summary": {
                "total_traces": 200,
                "cluster_count": 3,
            },
            "confusion_matrix": {
                "TP": 175,
                "FP": 25,
                "FN": 0,
                "TN": 0,
            },
            "performance_metrics": {
                "precision": 0.875,
                "recall": 1.0,
                "f1_score": 0.9333,
            },
            "detection_delay": {
                "average_loops": 3.3,
                "minimum_loops": 0,
                "maximum_loops": 6,
            },
        }
        fresh_detection_row = {
            "system": "rubis",
            "algorithm": "gmm",
            "detection_mode": "pointwise",
            "cluster_count": 9,
            "total_traces": 200,
            "tp_count": 180,
            "fp_count": 20,
            "fn_count": 0,
            "tn_count": 0,
            "tp_rate": 0.9,
            "fp_rate": 0.1,
            "fn_rate": 0.0,
            "precision": 0.9,
            "recall": 1.0,
            "f1_score": 0.9474,
            "hazard_lambda": "",
            "max_run_length": "",
            "state_prior": "",
            "changepoint_posterior_threshold": "",
            "raw_anomaly_rule": "",
            "tail_persistence_threshold": "",
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            detection_dir = root / "detection_results" / "rubis"
            detection_dir.mkdir(parents=True)
            (detection_dir / "detection_results_gmm.json").write_text(json.dumps(payload), encoding="utf-8")

            with patch(
                "rq_methods.rq4_runner.build_clustering_result_for_ari",
                return_value=object(),
            ), patch(
                "rq_methods.rq4_runner.compute_ari_from_result",
                return_value=0.9,
            ), patch(
                "rq_methods.rq4_runner.evaluate_system_algorithm",
                return_value=dict(fresh_detection_row),
            ) as eval_mock:
                current = Path.cwd()
                try:
                    os.chdir(root)
                    rows = RQ4Runner(
                        systems=["rubis"],
                        algorithms=["gmm"],
                        output_dir=root / "rq_results" / "rq4",
                    ).run()
                finally:
                    os.chdir(current)

            eval_mock.assert_called_once()
            self.assertEqual(rows[0]["cluster_count"], 9)

    def test_rq4_runner_can_reuse_existing_detection_results(self) -> None:
        from rq_methods.rq4_runner import RQ4Runner

        payload = {
            "metadata": {
                "cluster_count": 3,
                "detection_mode": "pointwise",
            },
            "summary": {
                "total_traces": 200,
                "cluster_count": 3,
            },
            "confusion_matrix": {
                "TP": 175,
                "FP": 25,
                "FN": 0,
                "TN": 0,
            },
            "performance_metrics": {
                "precision": 0.875,
                "recall": 1.0,
                "f1_score": 0.9333,
            },
            "detection_delay": {
                "average_loops": 3.3,
                "minimum_loops": 0,
                "maximum_loops": 6,
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            detection_dir = root / "detection_results" / "rubis"
            detection_dir.mkdir(parents=True)
            (detection_dir / "detection_results_gmm.json").write_text(json.dumps(payload), encoding="utf-8")

            with patch("rq_methods.rq4_runner.build_clustering_result_for_ari",
                return_value=object(),
            ), patch(
                "rq_methods.rq4_runner.compute_ari_from_result",
                return_value=0.9,
            ), patch(
                "rq_methods.rq4_runner.evaluate_system_algorithm",
            ) as eval_mock:
                current = Path.cwd()
                try:
                    os.chdir(root)
                    rows = RQ4Runner(
                        systems=["rubis"],
                        algorithms=["gmm"],
                        output_dir=root / "rq_results" / "rq4",
                        reuse_detection_results=True,
                    ).run()
                finally:
                    os.chdir(current)

            eval_mock.assert_not_called()
            self.assertEqual(rows[0]["tp_count"], 175)


if __name__ == "__main__":
    unittest.main()
