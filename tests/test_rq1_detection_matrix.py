from pathlib import Path
import json
import os
import tempfile
import unittest


class RQ1DetectionMatrixTests(unittest.TestCase):
    def test_rebuild_summary_from_existing_results_uses_standard_result_files(self) -> None:
        from scripts.run_rq1_detection_matrix import rebuild_summary_from_existing_results

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
                "TP": 190,
                "FP": 10,
                "FN": 0,
                "TN": 0,
            },
            "performance_metrics": {
                "precision": 0.95,
                "recall": 1.0,
                "f1_score": 0.9743,
            },
            "detection_delay": {
                "average_loops": 2.0,
                "minimum_loops": 1,
                "maximum_loops": 6,
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_dir = root / "detection_results" / "rubis"
            result_dir.mkdir(parents=True)
            (result_dir / "detection_results_gmm.json").write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
            current = Path.cwd()
            try:
                os.chdir(root)
                rows = rebuild_summary_from_existing_results(
                    systems=["rubis"],
                    algorithms=["gmm"],
                    output_dir=root / "summary",
                )
            finally:
                os.chdir(current)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["tp_count"], 190)
            csv_path = root / "summary" / "detection_matrix_summary.csv"
            self.assertTrue(csv_path.exists())
            csv_text = csv_path.read_text(encoding="utf-8")
            self.assertIn("rubis", csv_text)
            self.assertIn("gmm", csv_text)


if __name__ == "__main__":
    unittest.main()
