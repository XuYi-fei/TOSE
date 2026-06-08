from pathlib import Path
import tempfile
import unittest

from baseline_methods.evaluator import BaselineExperimentRunner
from baseline_methods.identifier import BaselineIdentifier
from baseline_methods.trace_adapter import TraceAdapter


def _write_rubis_trace(path: Path, values: list[tuple[int, float]]) -> None:
    lines = ["simTime(s),controlServersDouble_{k-1},controlServers_{k-1},measuredArrivalRate_{k},measuredAvgRespTime_{k}"]
    lines.extend(f"{time},2,2,40,{value}" for time, value in values)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_bsn_trace(
    path: Path,
    values_by_time_sensor: dict[int, list[float]],
) -> None:
    lines = ["logicalTime(s),logicalTimestamp(ms),component,freq_double,freq,cost"]
    for time, sensor_values in values_by_time_sensor.items():
        for sensor_index, value in enumerate(sensor_values):
            lines.append(f"{time},{time * 1000},/g3t1_{sensor_index + 1},6,6,{value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class ASEBaselineAdapterTests(unittest.TestCase):
    def test_trace_adapter_reads_tose_abn_start_time_and_series(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            trace_file = tmp_path / (
                "eval_abn_trace-cnt-000-duration-5-config_num-2-"
                "trace_config-norm1,abn1-start_time-1,4.txt"
            )
            _write_rubis_trace(trace_file, [(1, 0.1), (2, 0.2), (3, 0.3), (4, 9.0), (5, 10.0)])

            trace = TraceAdapter("rubis").load(trace_file)

            self.assertEqual(trace.abn_start_time, 4)
            self.assertIsNone(trace.sensor_index)
            self.assertEqual(trace.duration, 5)
            self.assertEqual(trace.times.tolist(), [1, 2, 3, 4, 5])
            self.assertEqual(trace.values.tolist(), [0.1, 0.2, 0.3, 9.0, 10.0])

    def test_prob_identifier_uses_first_identity_split_for_epsilon_and_second_for_mu(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            identity_dir = tmp_path / "identity"
            identity_dir.mkdir()
            second_dir = tmp_path / "identity2"
            second_dir.mkdir()

            _write_rubis_trace(
                identity_dir / "eval_ident_trace-cnt-000-duration-6-config_num-1-trace_config-norm1-start_time-1.txt",
                [(1, 1.0), (2, 1.0), (3, 1.0), (4, 1.0), (5, 1.0), (6, 10.0)],
            )
            _write_rubis_trace(
                second_dir / "eval_ident_trace-cnt-001-duration-6-config_num-1-trace_config-norm1-start_time-1.txt",
                [(1, 2.0), (2, 2.0), (3, 2.0), (4, 2.0), (5, 2.0), (6, 2.0)],
            )

            config = BaselineIdentifier("rubis").identify("PRD", identity_dir, secondary_identity_dir=second_dir)

            self.assertEqual(config.method, "PRD")
            self.assertEqual(config.detector_count, 1)
            self.assertGreater(config.detectors[0]["epsilon"], 0.0)
            self.assertAlmostEqual(config.detectors[0]["mu"], 2.0)

    def test_baseline_runner_writes_summary_for_selected_methods(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            identity_dir = tmp_path / "identity"
            abnormal_dir = tmp_path / "abnormal"
            output_dir = tmp_path / "baseline_results"
            identity_dir.mkdir()
            abnormal_dir.mkdir()

            for idx in range(2):
                _write_rubis_trace(
                    identity_dir / f"eval_ident_trace-cnt-00{idx}-duration-40-config_num-1-trace_config-norm1-start_time-1.txt",
                    [(time, 1.0) for time in range(1, 41)],
                )
            for idx in range(2):
                _write_rubis_trace(
                    abnormal_dir / (
                        f"eval_abn_trace-cnt-00{idx}-duration-40-config_num-2-"
                        "trace_config-norm1,abn1-start_time-1,30.txt"
                    ),
                    [(time, 1.0 if time < 30 else 12.0) for time in range(1, 41)],
                )

            runner = BaselineExperimentRunner(
                systems={"rubis": {"identity": identity_dir, "abnormal": abnormal_dir}},
                output_dir=output_dir,
                methods=["PRD", "SWD"],
            )

            rows = runner.run()

            self.assertEqual({(row["system"], row["method"]) for row in rows}, {("rubis", "PRD"), ("rubis", "SWD")})
            self.assertTrue(all(row["total_traces"] == 2 for row in rows))
            self.assertTrue(all(row["fn_count"] == 0 for row in rows))
            self.assertTrue((output_dir / "summary" / "rq1_baseline_summary.csv").exists())
            self.assertTrue((output_dir / "summary" / "rq1_baseline_summary.json").exists())

    def test_bsn_baseline_uses_all_six_sensors_and_target_sensor_alarm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            identity_dir = tmp_path / "identity"
            abnormal_dir = tmp_path / "abnormal"
            identity_dir.mkdir()
            abnormal_dir.mkdir()

            normal_values = {time: [1.0, 2.0, 3.0, 4.0, 5.0, 6.0] for time in range(1, 41)}
            _write_bsn_trace(
                identity_dir / (
                    "eval_ident_trace-cnt-000-duration-40-sensor_index-2-config_num-1-"
                    "trace_config-norm1-start_time-1.txt"
                ),
                normal_values,
            )

            abnormal_values = {}
            for time in range(1, 41):
                values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
                if time >= 30:
                    values[2] = 30.0
                abnormal_values[time] = values
            _write_bsn_trace(
                abnormal_dir / (
                    "eval_abn_trace-cnt-000-duration-40-sensor_index-2-config_num-2-"
                    "trace_config-norm1,abn1-start_time-1,30.txt"
                ),
                abnormal_values,
            )

            baseline_config = BaselineIdentifier("bsn").identify("SWD", identity_dir)
            self.assertEqual(baseline_config.detector_count, 6)
            self.assertEqual(len(baseline_config.detectors), 6)

            results = BaselineExperimentRunner(
                systems={"bsn": {"identity": identity_dir, "abnormal": abnormal_dir}},
                output_dir=tmp_path / "baseline_results",
                methods=["SWD"],
            ).run()

            self.assertEqual(results[0]["tp_count"], 1)
            self.assertEqual(results[0]["fp_count"], 0)
            self.assertEqual(results[0]["fn_count"], 0)


if __name__ == "__main__":
    unittest.main()
