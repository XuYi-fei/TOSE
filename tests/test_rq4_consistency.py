from pathlib import Path
import csv
import tempfile
import unittest


class RQ4ConsistencyTests(unittest.TestCase):
    def test_compare_group_matrix_rows_reports_full_match(self) -> None:
        from rq_methods.rq4_consistency import SHARED_FIELDS, compare_group_matrix_rows

        rq1_row = {
            "system": "rubis",
            "algorithm": "gmm",
            "cluster_count": "3",
            "tp_count": "175",
            "fp_count": "25",
            "fn_count": "0",
            "precision": "0.875",
            "recall": "1.0",
            "f1_score": "0.9333",
        }
        rq4_row = dict(rq1_row)

        diffs = compare_group_matrix_rows(rq1_row, rq4_row)
        self.assertEqual(SHARED_FIELDS, ["cluster_count", "tp_count", "fp_count", "fn_count", "precision", "recall", "f1_score"])
        self.assertEqual(diffs, [])

    def test_compare_group_matrix_rows_reports_mismatches(self) -> None:
        from rq_methods.rq4_consistency import compare_group_matrix_rows

        rq1_row = {
            "system": "wadi",
            "algorithm": "hdbscan",
            "cluster_count": "21",
            "tp_count": "189",
            "fp_count": "0",
            "fn_count": "11",
            "precision": "1.0",
            "recall": "0.945",
            "f1_score": "0.9717",
        }
        rq4_row = dict(rq1_row)
        rq4_row["fn_count"] = "9"

        diffs = compare_group_matrix_rows(rq1_row, rq4_row)
        self.assertEqual(diffs, [("fn_count", "11", "9")])

    def test_validate_rq4_matches_rq1_summary_accepts_matching_csvs(self) -> None:
        from rq_methods.rq4_consistency import validate_rq4_matches_rq1_summary

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rq1_path = root / "detection_matrix_summary.csv"
            rq4_path = root / "rq4_group_algorithms_summary.csv"

            fieldnames_rq1 = [
                "system",
                "algorithm",
                "cluster_count",
                "tp_count",
                "fp_count",
                "fn_count",
                "precision",
                "recall",
                "f1_score",
            ]
            fieldnames_rq4 = ["ari", *fieldnames_rq1]
            rows = [
                {
                    "system": "rubis",
                    "algorithm": "gmm",
                    "cluster_count": "3",
                    "tp_count": "175",
                    "fp_count": "25",
                    "fn_count": "0",
                    "precision": "0.875",
                    "recall": "1.0",
                    "f1_score": "0.9333",
                }
            ]

            with rq1_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames_rq1)
                writer.writeheader()
                writer.writerows(rows)

            with rq4_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames_rq4)
                writer.writeheader()
                writer.writerow({"ari": "1.0", **rows[0]})

            mismatches = validate_rq4_matches_rq1_summary(rq1_path, rq4_path)

        self.assertEqual(mismatches, [])


if __name__ == "__main__":
    unittest.main()
