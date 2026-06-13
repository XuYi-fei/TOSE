from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class RQ1LodoRunnerTests(unittest.TestCase):
    def test_lodo_runner_aggregates_holdout_results_per_method(self) -> None:
        from rq_methods.lodo_runner import aggregate_holdout_rows

        rows = [
            {"system": "rubis", "holdout_unit": "norm1", "method": "GROUP", "total_traces": 200, "tp_count": 180, "fp_count": 10, "fn_count": 10, "tn_count": 0, "FN": 5.0, "FP": 5.0, "MTD": 2.0, "MLD": 2.0, "AR": 0.0, "precision": 0.9, "recall": 0.95, "f1_score": 0.92},
            {"system": "rubis", "holdout_unit": "norm2", "method": "GROUP", "total_traces": 200, "tp_count": 190, "fp_count": 0, "fn_count": 10, "tn_count": 0, "FN": 5.0, "FP": 0.0, "MTD": 4.0, "MLD": 4.0, "AR": 0.0, "precision": 1.0, "recall": 0.95, "f1_score": 0.97},
        ]

        summary = aggregate_holdout_rows(rows)

        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["system"], "rubis")
        self.assertEqual(summary[0]["method"], "GROUP")
        self.assertEqual(summary[0]["holdout_count"], 2)
        self.assertEqual(summary[0]["FP"], 2.5)
        self.assertEqual(summary[0]["FN"], 5.0)
        self.assertEqual(summary[0]["MTD"], 3.0)

    def test_lodo_runner_uses_per_holdout_identity_and_abnormal_dirs(self) -> None:
        from rq_methods.lodo_runner import build_lodo_system_paths

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exp_dir = root / "rubis" / "holdout_norm1"
            (exp_dir / "identity").mkdir(parents=True)
            (exp_dir / "abnormal").mkdir(parents=True)

            mapping = build_lodo_system_paths(root, "rubis", "holdout_norm1")

            self.assertEqual(mapping["identity"], exp_dir / "identity")
            self.assertEqual(mapping["abnormal"], exp_dir / "abnormal")

    def test_lodo_runner_passes_holdout_group_paths(self) -> None:
        from rq_methods.lodo_runner import RQ1LodoRunner

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            holdout_dir = root / "data_rq1_lodo" / "rubis" / "holdout_norm1"
            (holdout_dir / "identity").mkdir(parents=True)
            (holdout_dir / "abnormal").mkdir(parents=True)
            learned_path = (
                root
                / "clustering_results_rq1_lodo"
                / "rubis"
                / "holdout_norm1"
                / "learned_distributions.yaml"
            )
            learned_path.parent.mkdir(parents=True)
            learned_path.write_text("metadata: {}\ndistributions: {}\n", encoding="utf-8")

            runner = RQ1LodoRunner(
                data_root=root / "data_rq1_lodo",
                output_dir=root / "rq_results",
                learned_root=root / "clustering_results_rq1_lodo",
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
            self.assertEqual(
                captured["learned_path"],
                learned_path,
            )
            self.assertEqual(captured["test_data_path"], holdout_dir / "abnormal")
            self.assertEqual(captured["output_dir"], root / "rq_results" / "rubis" / "holdout_norm1")


if __name__ == "__main__":
    unittest.main()
