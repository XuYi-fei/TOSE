from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class RunRQ4GroupAlgorithmsMatrixTests(unittest.TestCase):
    def test_main_runs_consistency_check_by_default(self) -> None:
        from scripts.run_rq4_group_algorithms_matrix import main

        fake_rows = [
            {
                "system": "rubis",
                "algorithm": "gmm",
                "ari": 1.0,
                "tp_count": 175,
                "fp_count": 25,
                "fn_count": 0,
                "precision": 0.875,
                "recall": 1.0,
            }
        ]

        with tempfile.TemporaryDirectory() as tmp, patch(
            "scripts.run_rq4_group_algorithms_matrix.RQ4Runner"
        ) as runner_cls, patch(
            "scripts.run_rq4_group_algorithms_matrix.validate_rq4_matches_rq1_summary",
            return_value=[],
        ) as validate_mock:
            runner_cls.return_value.run.return_value = fake_rows
            exit_code = main(["--systems", "rubis", "--algorithms", "gmm", "--output-dir", tmp])

        self.assertEqual(exit_code, 0)
        validate_mock.assert_called_once()

    def test_main_can_skip_consistency_check(self) -> None:
        from scripts.run_rq4_group_algorithms_matrix import main

        fake_rows = [
            {
                "system": "rubis",
                "algorithm": "gmm",
                "ari": 1.0,
                "tp_count": 175,
                "fp_count": 25,
                "fn_count": 0,
                "precision": 0.875,
                "recall": 1.0,
            }
        ]

        with tempfile.TemporaryDirectory() as tmp, patch(
            "scripts.run_rq4_group_algorithms_matrix.RQ4Runner"
        ) as runner_cls, patch(
            "scripts.run_rq4_group_algorithms_matrix.validate_rq4_matches_rq1_summary",
            return_value=[],
        ) as validate_mock:
            runner_cls.return_value.run.return_value = fake_rows
            exit_code = main(
                ["--systems", "rubis", "--algorithms", "gmm", "--output-dir", tmp, "--skip-consistency-check"]
            )

        self.assertEqual(exit_code, 0)
        validate_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
