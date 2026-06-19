from pathlib import Path
import json
import os
import tempfile
import unittest


class DetectionMatrixResultsTests(unittest.TestCase):
    def test_load_detection_result_row_reads_standard_json_shape(self) -> None:
        from rq_methods.detection_matrix_results import load_detection_result_row

        payload = {
            "metadata": {
                "cluster_count": 7,
                "detection_mode": "pointwise",
            },
            "summary": {
                "total_traces": 200,
                "cluster_count": 7,
            },
            "confusion_matrix": {
                "TP": 180,
                "FP": 20,
                "FN": 0,
                "TN": 0,
            },
            "performance_metrics": {
                "precision": 0.9,
                "recall": 1.0,
                "f1_score": 0.9474,
            },
            "detection_delay": {
                "average_loops": 4.0,
                "minimum_loops": 1,
                "maximum_loops": 8,
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
                row = load_detection_result_row("rubis", "gmm")
            finally:
                os.chdir(current)

        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["system"], "rubis")
        self.assertEqual(row["algorithm"], "gmm")
        self.assertEqual(row["cluster_count"], 7)
        self.assertEqual(row["tp_count"], 180)
        self.assertEqual(row["fp_count"], 20)
        self.assertEqual(row["fn_count"], 0)
        self.assertEqual(row["precision"], 0.9)
        self.assertEqual(row["recall"], 1.0)
        self.assertEqual(row["f1_score"], 0.9474)

    def test_load_detection_result_row_returns_none_when_missing(self) -> None:
        from rq_methods.detection_matrix_results import load_detection_result_row

        with tempfile.TemporaryDirectory() as tmp:
            current = Path.cwd()
            try:
                os.chdir(tmp)
                row = load_detection_result_row("wadi", "mean_shift")
            finally:
                os.chdir(current)

        self.assertIsNone(row)


if __name__ == "__main__":
    unittest.main()
