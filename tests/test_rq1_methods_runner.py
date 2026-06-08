from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from anomaly_detection.core.evaluator import AggregatedMetrics


class RQ1MethodsRunnerTests(unittest.TestCase):
    def test_unified_runner_combines_baseline_and_group_rows(self) -> None:
        from rq_methods.runner import RQ1MethodsRunner

        baseline_rows = [
            {
                "system": "rubis",
                "method": "PRD",
                "total_traces": 2,
                "tp_count": 2,
                "fp_count": 0,
                "fn_count": 0,
                "tn_count": 0,
                "tp_rate": 1.0,
                "fp_rate": 0.0,
                "fn_rate": 0.0,
                "FN": 0.0,
                "FP": 0.0,
                "MTD": 1.0,
                "MLD": 1.0,
                "AR": 0.0,
                "precision": 1.0,
                "recall": 1.0,
                "f1_score": 1.0,
            }
        ]
        group_row = {
            "system": "rubis",
            "method": "GROUP",
            "total_traces": 2,
            "tp_count": 1,
            "fp_count": 0,
            "fn_count": 1,
            "tn_count": 0,
            "tp_rate": 0.5,
            "fp_rate": 0.0,
            "fn_rate": 0.5,
            "FN": 50.0,
            "FP": 0.0,
            "MTD": 3.0,
            "MLD": 3.0,
            "AR": 0.0,
            "precision": 1.0,
            "recall": 0.5,
            "f1_score": 2 / 3,
            "cluster_count": 4,
            "clustering_algorithm": "affinity_propagation",
        }

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "rq1"
            with patch("rq_methods.runner.BaselineExperimentRunner") as baseline_runner, patch(
                "rq_methods.runner.GroupMethodRunner"
            ) as group_runner:
                baseline_runner.return_value.run.return_value = baseline_rows
                group_runner.return_value.run_system.return_value = group_row

                rows = RQ1MethodsRunner(
                    systems=["rubis"],
                    methods=["PRD", "GROUP"],
                    output_dir=output_dir,
                ).run()

            self.assertEqual([row["method"] for row in rows], ["PRD", "GROUP"])
            self.assertTrue((output_dir / "summary" / "rq1_methods_summary.csv").exists())
            self.assertTrue((output_dir / "summary" / "rq1_methods_summary.json").exists())

    def test_group_adapter_uses_default_best_learned_distribution_file(self) -> None:
        from rq_methods.group_adapter import GroupMethodRunner

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "rubis_detection_config.yaml"
            abnormal_dir = tmp_path / "data" / "rubis" / "abnormal"
            abnormal_dir.mkdir(parents=True)
            (abnormal_dir / "trace.txt").write_text("time,value\n1,1.0\n", encoding="utf-8")
            learned_root = tmp_path / "clustering_results"
            learned_path = learned_root / "rubis" / "learned_distributions.yaml"
            learned_path.parent.mkdir(parents=True)
            learned_path.write_text("distributions: {}\n", encoding="utf-8")
            config_path.write_text("system_type: rubis\n", encoding="utf-8")

            fake_config = SimpleNamespace(
                system_type="rubis",
                learned_distributions="unused",
                test_data_path=str(abnormal_dir),
                detection=SimpleNamespace(
                    mode="pointwise",
                    sigma_threshold=3.0,
                    p_value_alpha=None,
                    alarm_count_policy="binomial_confidence_bound",
                    trace_alarm_confidence=0.99,
                    aggregation_method="max_p_value",
                    context_matching_strategy="nearest",
                    apply_context_mu_shift=True,
                    bocpd=SimpleNamespace(
                        hazard_lambda=50.0,
                        max_run_length=200,
                        state_prior="sample_count",
                        changepoint_posterior_threshold=0.5,
                        raw_anomaly_rule="cp_and_tail",
                        tail_persistence_threshold=2,
                    ),
                ),
                output=SimpleNamespace(dir=str(tmp_path / "out")),
            )
            fake_detector = SimpleNamespace(
                distributions={"cluster_0": object()},
                clustering_algorithm="affinity_propagation",
                point_anomaly_probability=0.0027,
                context_calibration_model=None,
                context_matching_strategy="nearest",
                apply_context_mu_shift=True,
                detection_mode="pointwise",
            )
            aggregate = AggregatedMetrics(
                total_traces=1,
                tp_count=1,
                fp_count=0,
                fn_count=0,
                tn_count=0,
                precision=1.0,
                recall=1.0,
                f1_score=1.0,
                avg_delay_loops=2.0,
                min_delay_loops=2,
                max_delay_loops=2,
                trace_metrics=[],
            )

            with patch("rq_methods.group_adapter.DetectionConfig.from_yaml", return_value=fake_config), patch(
                "rq_methods.group_adapter.AnomalyDetector.from_yaml", return_value=fake_detector
            ) as from_yaml, patch("rq_methods.group_adapter.AnomalyEvaluator") as evaluator_class, patch(
                "rq_methods.group_adapter.DetectionReporter"
            ) as reporter_class:
                evaluator_class.return_value.evaluate_trace.return_value = object()
                evaluator_class.return_value.aggregate_results.return_value = aggregate

                row = GroupMethodRunner(
                    config_map={"rubis": str(config_path)},
                    output_dir=tmp_path / "rq1",
                    learned_root=learned_root,
                ).run_system("rubis")

            from_yaml.assert_called_once()
            self.assertEqual(Path(from_yaml.call_args.args[0]), learned_path)
            self.assertEqual(row["method"], "GROUP")
            self.assertEqual(row["cluster_count"], 1)
            reporter_class.assert_called_once()


if __name__ == "__main__":
    unittest.main()
