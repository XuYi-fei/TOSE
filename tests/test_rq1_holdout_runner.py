from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from anomaly_detection.core.evaluator import AggregatedMetrics


class RQ1HoldoutRunnerTests(unittest.TestCase):
    def test_aggregate_holdout_rows_groups_by_system_and_method(self) -> None:
        from rq_methods.holdout_runner import aggregate_holdout_rows

        rows = [
            {
                "system": "rubis",
                "method": "GROUP",
                "holdout_unit": "norm1",
                "total_traces": 200,
                "tp_count": 180,
                "fp_count": 10,
                "fn_count": 10,
                "tn_count": 0,
                "FN": 5.0,
                "FP": 5.0,
                "MTD": 2.0,
                "MLD": 2.0,
                "AR": 0.0,
                "precision": 0.9,
                "recall": 0.95,
                "f1_score": 0.92,
            },
            {
                "system": "rubis",
                "method": "GROUP",
                "holdout_unit": "norm2",
                "total_traces": 200,
                "tp_count": 190,
                "fp_count": 0,
                "fn_count": 10,
                "tn_count": 0,
                "FN": 5.0,
                "FP": 0.0,
                "MTD": 4.0,
                "MLD": 4.0,
                "AR": 0.0,
                "precision": 1.0,
                "recall": 0.95,
                "f1_score": 0.97,
            },
        ]

        summary = aggregate_holdout_rows(rows)

        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["system"], "rubis")
        self.assertEqual(summary[0]["method"], "GROUP")
        self.assertEqual(summary[0]["holdout_count"], 2)
        self.assertEqual(summary[0]["FP"], 2.5)
        self.assertEqual(summary[0]["FN"], 5.0)
        self.assertEqual(summary[0]["MTD"], 3.0)

    def test_runner_trains_baselines_once_per_system_and_evaluates_all_holdouts(self) -> None:
        from rq_methods.holdout_runner import RQ1HoldoutRunner

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data_rq1_holdout" / "rubis"
            for holdout_name in ("holdout_norm1", "holdout_norm2"):
                holdout_dir = data_root / holdout_name
                (holdout_dir / "identity").mkdir(parents=True)
                (holdout_dir / "abnormal").mkdir(parents=True)
                (holdout_dir / "abnormal" / f"{holdout_name}.txt").write_text("time,value\n1,1.0\n", encoding="utf-8")

            class FakeBaselineConfig:
                method = "SWD"
                system = "rubis"
                detector_count = 1
                detectors = [{"window_size": 3}]

                def write_json(self, path: Path) -> None:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("{}", encoding="utf-8")
            baseline_rows = [
                SimpleNamespace(__dict__={"filename": "holdout_norm1.txt", "classification": "TP"}),
            ]

            aggregate_side_effect = [
                {
                    "system": "rubis",
                    "method": "SWD",
                    "total_traces": 1,
                    "tp_count": 1,
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
                },
                {
                    "system": "rubis",
                    "method": "SWD",
                    "total_traces": 1,
                    "tp_count": 0,
                    "fp_count": 1,
                    "fn_count": 0,
                    "tn_count": 0,
                    "tp_rate": 0.0,
                    "fp_rate": 1.0,
                    "fn_rate": 0.0,
                    "FN": 0.0,
                    "FP": 100.0,
                    "MTD": 0.0,
                    "MLD": 0.0,
                    "AR": 0.0,
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1_score": 0.0,
                },
            ]

            runner = RQ1HoldoutRunner(
                data_root=root / "data_rq1_holdout",
                output_dir=root / "rq_results",
                learned_root=root / "clustering_results_rq1_holdout",
                systems=["rubis"],
                methods=["SWD"],
            )

            with patch("rq_methods.holdout_runner.BaselineIdentifier") as identifier_class, patch(
                "rq_methods.holdout_runner.BaselineEvaluator"
            ) as evaluator_class, patch(
                "rq_methods.holdout_runner.aggregate_results",
                side_effect=aggregate_side_effect,
            ) as aggregate_mock:
                identifier_class.return_value.identify.return_value = FakeBaselineConfig()
                evaluator_class.return_value.evaluate_directory.return_value = baseline_rows

                per_holdout_rows, summary_rows = runner.run()

            identifier_class.return_value.identify.assert_called_once_with("SWD", Path("data") / "rubis" / "identity")
            self.assertEqual(evaluator_class.return_value.evaluate_directory.call_count, 2)
            self.assertEqual(aggregate_mock.call_count, 2)
            self.assertEqual(len(per_holdout_rows), 2)
            self.assertEqual(summary_rows[0]["holdout_count"], 2)
            self.assertEqual(summary_rows[0]["FP"], 50.0)

    def test_runner_trains_group_per_holdout(self) -> None:
        from rq_methods.holdout_runner import RQ1HoldoutRunner

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            holdout_dir = root / "data_rq1_holdout" / "rubis" / "holdout_norm1"
            (holdout_dir / "identity").mkdir(parents=True)
            (holdout_dir / "abnormal").mkdir(parents=True)
            learned_path = (
                root
                / "clustering_results_rq1_holdout"
                / "rubis"
                / "holdout_norm1"
                / "learned_distributions.yaml"
            )
            learned_path.parent.mkdir(parents=True)
            learned_path.write_text("metadata: {}\ndistributions: {}\n", encoding="utf-8")

            runner = RQ1HoldoutRunner(
                data_root=root / "data_rq1_holdout",
                output_dir=root / "rq_results",
                learned_root=root / "clustering_results_rq1_holdout",
                systems=["rubis"],
                methods=["GROUP"],
            )

            captured: dict[str, object] = {}

            def fake_run_system(self, system: str, **kwargs):
                captured["system"] = system
                captured.update(kwargs)
                return {
                    "system": system,
                    "method": "GROUP",
                    "total_traces": 200,
                    "tp_count": 200,
                    "fp_count": 0,
                    "fn_count": 0,
                    "tn_count": 0,
                    "FN": 0.0,
                    "FP": 0.0,
                    "MTD": 0.0,
                    "MLD": 0.0,
                    "AR": 0.0,
                    "precision": 1.0,
                    "recall": 1.0,
                    "f1_score": 1.0,
                }

            with patch(
                "rq_methods.group_adapter.GroupMethodRunner.run_system_with_overrides",
                new=fake_run_system,
            ):
                runner.run()

            self.assertEqual(captured["system"], "rubis")
            self.assertEqual(captured["learned_path"], learned_path)
            self.assertEqual(captured["test_data_path"], holdout_dir / "abnormal")
            self.assertEqual(captured["output_dir"], root / "rq_results" / "rubis" / "holdout_norm1")

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
