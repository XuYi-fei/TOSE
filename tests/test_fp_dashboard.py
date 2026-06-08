import csv
import json
import tempfile
import unittest
from pathlib import Path

import yaml


class FPDashboardTests(unittest.TestCase):
    def _write_rubis_identity_trace(self, root: Path) -> Path:
        trace_dir = root / "data" / "rubis" / "identity"
        trace_dir.mkdir(parents=True, exist_ok=True)
        path = trace_dir / (
            "eval_ident_trace-cnt-000-duration-30-config_num-3-"
            "trace_config-norm1,norm2,norm3-start_time-1,11,21.txt"
        )
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["simTime(s)", "measuredAvgRespTime_{k}"])
            writer.writeheader()
            for t in range(1, 31):
                if t < 11:
                    value = 0.05
                elif t < 21:
                    value = 0.11
                else:
                    value = 0.03
                writer.writerow({"simTime(s)": t, "measuredAvgRespTime_{k}": value})
        return path

    def _write_rubis_abnormal_trace(self, root: Path) -> Path:
        trace_dir = root / "data" / "rubis" / "abnormal"
        trace_dir.mkdir(parents=True, exist_ok=True)
        path = trace_dir / (
            "eval_abn_trace-cnt-000-duration-30-config_num-4-"
            "trace_config-norm1,norm2,norm3,abn1-start_time-1,11,21,26.txt"
        )
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["simTime(s)", "measuredAvgRespTime_{k}"])
            writer.writeheader()
            for t in range(1, 31):
                if t < 11:
                    value = 0.05
                elif t < 21:
                    value = 0.11
                elif t < 26:
                    value = 0.03
                else:
                    value = 0.2
                writer.writerow({"simTime(s)": t, "measuredAvgRespTime_{k}": value})
        return path

    def _write_learned_distributions(self, root: Path) -> Path:
        path = root / "clustering_results" / "rubis" / "learned_distributions_label_grouped.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.dump(
                {
                    "system_type": "rubis",
                    "algorithm": "label_grouped_baseline",
                    "distributions": {
                        "norm1": {
                            "distribution_type": "norm",
                            "fitted_params": {"shape_args": [], "loc": 0.05, "scale": 0.005},
                            "mu": 0.05,
                            "sigma": 0.005,
                            "variance": 0.000025,
                            "sample_count": 10,
                            "cluster_id": 0,
                            "dominant_norm": "norm1",
                        },
                        "norm2": {
                            "distribution_type": "norm",
                            "fitted_params": {"shape_args": [], "loc": 0.11, "scale": 0.006},
                            "mu": 0.11,
                            "sigma": 0.006,
                            "variance": 0.000036,
                            "sample_count": 10,
                            "cluster_id": 1,
                            "dominant_norm": "norm2",
                        },
                        "norm3": {
                            "distribution_type": "norm",
                            "fitted_params": {"shape_args": [], "loc": 0.03, "scale": 0.004},
                            "mu": 0.03,
                            "sigma": 0.004,
                            "variance": 0.000016,
                            "sample_count": 10,
                            "cluster_id": 2,
                            "dominant_norm": "norm3",
                        },
                    },
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        return path

    def _write_detection_config(self, root: Path, learned_path: Path) -> Path:
        path = root / "configs" / "rubis_label_grouped_detect_config.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.dump(
                {
                    "system_type": "rubis",
                    "learned_distributions": str(learned_path),
                    "test_data_path": str(root / "data" / "rubis" / "abnormal"),
                    "output": {
                        "dir": str(root / "detection_results" / "rubis"),
                        "file_suffix": "label_grouped",
                    },
                }
            ),
            encoding="utf-8",
        )
        return path

    def _write_detection_result(self, root: Path, config_path: Path) -> Path:
        path = root / "detection_results" / "rubis" / "detection_results_label_grouped.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "metadata": {
                        "system_type": "rubis",
                        "config_path": str(config_path),
                        "clustering_algorithm": "label_grouped_baseline",
                        "cluster_count": 3,
                    },
                    "summary": {
                        "total_traces": 1,
                        "tp_traces": 0,
                        "fp_traces": 1,
                        "fn_traces": 0,
                        "tn_traces": 0,
                    },
                    "confusion_matrix": {"TP": 0, "FP": 1, "FN": 0, "TN": 0},
                    "performance_metrics": {"precision": 0.0, "recall": 0.0, "f1_score": 0.0},
                    "detection_delay": {"average_loops": None, "minimum_loops": None, "maximum_loops": None},
                    "trace_details": [
                        {
                            "filename": "eval_abn_trace-cnt-000-duration-30-config_num-4-trace_config-norm1,norm2,norm3,abn1-start_time-1,11,21,26.txt",
                            "classification": "FP",
                            "has_abn1": True,
                            "abn1_start_time": 26.0,
                            "first_detection_time": 12.0,
                            "first_raw_anomaly_time": 12.0,
                            "detection_delay_loops": -13,
                            "total_detection_count": 3,
                            "trigger_alarm_count": 2,
                            "trigger_allowed_count": 1,
                            "anomaly_points": [
                                {
                                    "time": 12.0,
                                    "value": 0.13,
                                    "closest_distribution": "norm2",
                                    "distribution_type": "norm",
                                    "best_p_value": 0.001,
                                    "matched_context_key": None,
                                    "context_match_strategy": "global",
                                    "context_location_shift": 0.0,
                                },
                                {
                                    "time": 13.0,
                                    "value": 0.131,
                                    "closest_distribution": "norm2",
                                    "distribution_type": "norm",
                                    "best_p_value": 0.0005,
                                    "matched_context_key": None,
                                    "context_match_strategy": "global",
                                    "context_location_shift": 0.0,
                                },
                            ],
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return path

    def _write_summary_files(self, root: Path) -> None:
        summary_dir = root / "detection_results" / "summary"
        summary_dir.mkdir(parents=True, exist_ok=True)
        (summary_dir / "label_grouped_fp_prefix_trace_breakdown.json").write_text(
            json.dumps(
                [
                    {
                        "system": "rubis",
                        "filename": "eval_abn_trace-cnt-000-duration-30-config_num-4-trace_config-norm1,norm2,norm3,abn1-start_time-1,11,21,26.txt",
                        "abn1_start_time": 26.0,
                        "prefix_point_count": 25,
                        "prefix_anomaly_count": 2,
                        "prefix_anomaly_ratio": 0.08,
                        "first_detection_time": 12.0,
                        "observed_count_at_trigger": 12,
                        "trigger_alarm_count": 2,
                        "trigger_allowed_count": 1,
                        "trigger_excess_count": 1,
                        "total_detection_count_whole_trace": 3,
                        "prefix_segment_anomaly_counts": "{\"norm2\": 2}",
                        "prefix_closest_distribution_counts": "{\"norm2\": 2}",
                        "first_10_prefix_anomaly_times": "[12.0, 13.0]",
                        "first_10_prefix_time_gaps": "[1.0]",
                        "max_local_prefix_streak_le_60s_gap": 2,
                    }
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (summary_dir / "identity_label_grouped_self_check.json").write_text(
            json.dumps(
                {
                    "rubis": {
                        "trace_count": 1,
                        "trace_with_outlier_count": 1,
                        "trace_with_outlier_ratio": 1.0,
                        "segment_count": 3,
                        "segments_with_outlier": 1,
                        "segment_outlier_ratio": 0.333,
                        "total_points": 30,
                        "outlier_points": 1,
                        "outlier_ratio": 0.033,
                        "expected_ratio_3sigma": 0.0027,
                        "excess_vs_expected_ratio": 12.0,
                        "lower_outliers": 0,
                        "upper_outliers": 1,
                        "groups": {
                            "norm2": {
                                "points": 10,
                                "outliers": 1,
                                "outlier_ratio": 0.1,
                                "expected_ratio_3sigma": 0.0027,
                                "excess_vs_expected_ratio": 37.0,
                                "lower_outliers": 0,
                                "upper_outliers": 1,
                                "segments": 1,
                                "segments_with_outlier": 1,
                                "segment_outlier_ratio": 1.0,
                                "traces_with_outlier": 1,
                            }
                        },
                    }
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _create_fixture_root(self, tmpdir: str) -> Path:
        root = Path(tmpdir)
        self._write_rubis_identity_trace(root)
        self._write_rubis_abnormal_trace(root)
        learned = self._write_learned_distributions(root)
        config = self._write_detection_config(root, learned)
        self._write_detection_result(root, config)
        self._write_summary_files(root)
        return root

    def test_scan_results_builds_dashboard_payload(self):
        from tools.fp_dashboard.data_loader import scan_dashboard_data

        with tempfile.TemporaryDirectory() as tmpdir:
            root = self._create_fixture_root(tmpdir)

            payload = scan_dashboard_data(root)

            self.assertIn("results", payload)
            self.assertIn("systems", payload)
            self.assertEqual(payload["systems"], ["rubis"])
            self.assertEqual(len(payload["results"]), 1)
            result = payload["results"][0]
            self.assertEqual(result["system"], "rubis")
            self.assertEqual(result["algorithm"], "label_grouped_baseline")
            self.assertEqual(result["distribution_count"], 3)
            self.assertEqual(result["distribution_source"]["sample_count"], 30)
            self.assertEqual(result["trace_count"], 1)
            self.assertEqual(result["fp_count"], 1)
            self.assertEqual(result["traces"][0]["prefix_point_count"], 25)
            self.assertEqual(result["traces"][0]["trigger_alarm_count"], 2)
            self.assertEqual(result["traces"][0]["trigger_allowed_count"], 1)
            self.assertEqual(result["traces"][0]["trigger_reason"]["closest_distribution"], "norm2")
            comparison = {item["label"]: item for item in result["distribution_comparison"]}
            self.assertEqual(comparison["norm2"]["identity_match_source"], "exact:norm2")
            self.assertEqual(comparison["norm2"]["fp_match_source"], "exact:norm2")
            self.assertEqual(comparison["norm2"]["identity_self_check"]["points"], 10)
            self.assertEqual(comparison["norm2"]["fp_prefix_check"]["prefix_outliers"], 2)
            self.assertAlmostEqual(
                result["traces"][0]["trigger_reason"]["deviation_sigma"],
                3.333333333333333,
            )

    def test_server_serves_dashboard_and_trace_detail(self):
        from tools.fp_dashboard.server import DashboardServer

        with tempfile.TemporaryDirectory() as tmpdir:
            root = self._create_fixture_root(tmpdir)
            server = DashboardServer(root=root, host="127.0.0.1", port=0)
            html = server.read_static_text("index.html")
            data = server.get_data_payload()
            rescan = server.get_scan_payload()
            detail = server.get_trace_detail_payload(
                "rubis:detection_results_label_grouped",
                "eval_abn_trace-cnt-000-duration-30-config_num-4-trace_config-norm1,norm2,norm3,abn1-start_time-1,11,21,26.txt",
            )

            self.assertIn("TOSE Detection", html)
            self.assertEqual(data["systems"], ["rubis"])
            self.assertEqual(rescan["status"], "ok")
            self.assertEqual(detail["filename"], "eval_abn_trace-cnt-000-duration-30-config_num-4-trace_config-norm1,norm2,norm3,abn1-start_time-1,11,21,26.txt")
            self.assertEqual(detail["trigger_reason"]["closest_distribution"], "norm2")
            self.assertGreater(len(detail["series"]), 0)
            self.assertEqual(detail["series"][0]["segment_label"], "norm1")

    def test_distribution_comparison_falls_back_to_norm_suffix_groups(self):
        from tools.fp_dashboard.data_loader import _build_distribution_comparison

        distribution_items = [
            {
                "label": "cluster_0",
                "distribution_type": "norm",
                "sample_count": 20,
                "mu": 1.0,
                "sigma": 0.1,
                "dominant_norm": "norm2",
                "context_features": {},
            }
        ]
        identity_groups = {
            "exact": {
                "sensor0_norm2": {
                    "points": 10,
                    "outliers": 1,
                    "outlier_ratio": 0.1,
                    "expected_ratio_3sigma": 0.0027,
                    "excess_vs_expected_ratio": 37.0,
                    "lower_outliers": 0,
                    "upper_outliers": 1,
                    "segments": 1,
                    "segments_with_outlier": 1,
                    "traces_with_outlier": 1,
                },
                "sensor1_norm2": {
                    "points": 20,
                    "outliers": 2,
                    "outlier_ratio": 0.1,
                    "expected_ratio_3sigma": 0.0027,
                    "excess_vs_expected_ratio": 37.0,
                    "lower_outliers": 1,
                    "upper_outliers": 1,
                    "segments": 2,
                    "segments_with_outlier": 1,
                    "traces_with_outlier": 1,
                },
            },
            "suffix": {
                "norm2": {
                    "points": 30,
                    "outliers": 3,
                    "outlier_ratio": 0.1,
                    "expected_ratio_3sigma": 0.0027,
                    "excess_vs_expected_ratio": 37.0,
                    "lower_outliers": 1,
                    "upper_outliers": 2,
                    "segments": 3,
                    "segments_with_outlier": 2,
                }
            },
        }
        fp_groups = {
            "exact": {
                "norm2": {
                    "fp_trace_count": 4,
                    "prefix_point_count": 100,
                    "prefix_anomaly_count": 8,
                    "trigger_trace_count": 4,
                }
            },
            "suffix": {
                "norm2": {
                    "fp_trace_count": 4,
                    "prefix_point_count": 100,
                    "prefix_anomaly_count": 8,
                    "trigger_trace_count": 4,
                }
            },
        }

        comparison = _build_distribution_comparison(
            "bsn",
            distribution_items,
            identity_groups,
            fp_groups,
        )[0]

        self.assertEqual(comparison["identity_match_source"], "dominant-suffix:norm2")
        self.assertEqual(comparison["fp_match_source"], "dominant:norm2")
        self.assertEqual(comparison["identity_self_check"]["points"], 30)
        self.assertEqual(comparison["fp_prefix_check"]["prefix_outliers"], 8)


if __name__ == "__main__":
    unittest.main()
