from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch


class RQ2HoldoutRunnerTests(unittest.TestCase):
    def test_runner_trains_pro_and_gpd_per_holdout(self) -> None:
        from rq_methods.rq2_holdout_runner import RQ2HoldoutRunner

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data_rq1_holdout" / "rubis"
            for holdout_name in ("holdout_norm1", "holdout_norm2"):
                holdout_dir = data_root / holdout_name
                (holdout_dir / "identity").mkdir(parents=True)
                (holdout_dir / "abnormal").mkdir(parents=True)
                (holdout_dir / "abnormal" / f"{holdout_name}.txt").write_text("time,value\n1,1.0\n", encoding="utf-8")

            class FakeBaselineConfig:
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
                    "method": "PRO",
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
                    "method": "PRO",
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
                {
                    "system": "rubis",
                    "method": "GPD",
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
                    "MTD": 2.0,
                    "MLD": 2.0,
                    "AR": 0.0,
                    "precision": 1.0,
                    "recall": 1.0,
                    "f1_score": 1.0,
                },
                {
                    "system": "rubis",
                    "method": "GPD",
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
                    "MTD": 3.0,
                    "MLD": 3.0,
                    "AR": 0.0,
                    "precision": 1.0,
                    "recall": 1.0,
                    "f1_score": 1.0,
                },
            ]

            runner = RQ2HoldoutRunner(
                data_root=root / "data_rq1_holdout",
                output_dir=root / "rq_results",
                learned_root=root / "clustering_results_rq1_holdout",
                systems=["rubis"],
                methods=["PRO", "GPD"],
            )

            with patch("rq_methods.rq2_holdout_runner.BaselineIdentifier") as identifier_class, patch(
                "rq_methods.rq2_holdout_runner.BaselineEvaluator"
            ) as evaluator_class, patch(
                "rq_methods.rq2_holdout_runner.aggregate_results",
                side_effect=aggregate_side_effect,
            ) as aggregate_mock:
                identifier_class.return_value.identify.return_value = FakeBaselineConfig()
                evaluator_class.return_value.evaluate_directory.return_value = baseline_rows

                per_holdout_rows, summary_rows = runner.run()

            identify_calls = identifier_class.return_value.identify.call_args_list
            self.assertEqual(len(identify_calls), 4)
            self.assertEqual(identify_calls[0].args[0], "PRD")
            self.assertEqual(identify_calls[0].args[1], data_root / "holdout_norm1" / "identity")
            self.assertEqual(identify_calls[1].args[0], "GPD")
            self.assertEqual(evaluator_class.return_value.evaluate_directory.call_count, 4)
            self.assertEqual(aggregate_mock.call_count, 4)
            self.assertEqual(len(per_holdout_rows), 4)
            summary_by_method = {row["method"]: row for row in summary_rows}
            self.assertEqual(summary_by_method["PRO"]["holdout_count"], 2)
            self.assertEqual(summary_by_method["PRO"]["FP"], 50.0)
            self.assertEqual(summary_by_method["GPD"]["MTD"], 2.5)

    def test_runner_trains_group_per_holdout(self) -> None:
        from rq_methods.rq2_holdout_runner import RQ2HoldoutRunner

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

            runner = RQ2HoldoutRunner(
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
