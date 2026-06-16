from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class RQ3RunnerTests(unittest.TestCase):
    def test_compute_utility_is_complement_of_ar(self) -> None:
        from rq_methods.metrics import compute_utility_from_ar

        self.assertEqual(compute_utility_from_ar(0.0), 100.0)
        self.assertEqual(compute_utility_from_ar(12.5), 87.5)
        self.assertEqual(compute_utility_from_ar(100.0), 0.0)

    def test_rq3_runner_reuses_rq1_results_and_writes_summary(self) -> None:
        from rq_methods.rq3_runner import RQ3Runner

        fake_holdout_rows = [
            {
                "system": "rubis",
                "method": "GROUP",
                "holdout_unit": "norm1",
                "holdout_count": 1,
                "total_traces": 200,
                "tp_count": 200,
                "fp_count": 0,
                "fn_count": 0,
                "tn_count": 0,
                "FN": 0.0,
                "FP": 0.0,
                "MTD": 1.0,
                "MLD": 1.0,
                "AR": 2.5,
                "precision": 1.0,
                "recall": 1.0,
                "f1_score": 1.0,
            }
        ]
        fake_summary_rows = [
            {
                "system": "rubis",
                "method": "GROUP",
                "holdout_count": 1,
                "total_traces": 200,
                "tp_count": 200,
                "fp_count": 0,
                "fn_count": 0,
                "tn_count": 0,
                "FN": 0.0,
                "FP": 0.0,
                "MTD": 1.0,
                "MLD": 1.0,
                "AR": 2.5,
                "precision": 1.0,
                "recall": 1.0,
                "f1_score": 1.0,
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "rq_results" / "rq3"
            with patch("rq_methods.rq3_runner.RQ1HoldoutRunner") as runner_class:
                runner_class.return_value.run.return_value = (fake_holdout_rows, fake_summary_rows)
                _, rows = RQ3Runner(output_dir=output_dir, systems=["rubis"], methods=["GROUP"]).run()

            self.assertEqual(rows[0]["utility"], 97.5)
            summary_csv = output_dir / "summary" / "rq3_system_summary.csv"
            self.assertTrue(summary_csv.exists())
            content = summary_csv.read_text(encoding="utf-8")
            self.assertIn("utility", content)
            self.assertIn("97.5", content)


if __name__ == "__main__":
    unittest.main()
