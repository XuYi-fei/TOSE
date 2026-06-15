from pathlib import Path
import json
import tempfile
import unittest
import pandas as pd

from rq_methods.holdout_dataset import (
    DistributionSegment,
    build_experiment_layout,
    build_holdout_unit_id,
    write_generated_bsn_trace,
    write_generated_trace,
)


def _write_rubis_trace(path: Path, values_by_segment: list[tuple[str, int, list[float]]]) -> None:
    lines = [
        "simTime(s),controlServersDouble_{k-1},controlServers_{k-1},measuredArrivalRate_{k},measuredAvgRespTime_{k}"
    ]
    trace_config = []
    start_times = []
    time_value = 1
    for label, start_time, values in values_by_segment:
        trace_config.append(label)
        start_times.append(str(start_time))
        time_value = start_time
        for value in values:
            lines.append(f"{time_value},2,2,40,{value}")
            time_value += 1
    filename = (
        "eval_ident_trace-cnt-000-duration-30-config_num-3-"
        f"trace_config-{','.join(trace_config)}-start_time-{','.join(start_times)}.txt"
    )
    path.joinpath(filename).write_text("\n".join(lines) + "\n", encoding="utf-8")


class RQ1HoldoutDatasetTests(unittest.TestCase):
    def test_build_holdout_unit_id_uses_sensor_for_bsn(self) -> None:
        self.assertEqual(build_holdout_unit_id("rubis", "norm1", None), "norm1")
        self.assertEqual(build_holdout_unit_id("bsn", "norm2", 5), "sensor5_norm2")

    def test_build_experiment_layout_creates_holdout_specific_pools(self) -> None:
        segments = [
            DistributionSegment(
                system="rubis",
                source_trace="trace_a.txt",
                unit_id="norm1",
                norm_label="norm1",
                sensor_index=None,
                segment_index=0,
                start_time=1.0,
                end_time=4.0,
                sample_count=3,
                rows=[{"simTime(s)": 1, "measuredAvgRespTime_{k}": 1.0}],
                time_column="simTime(s)",
                value_column="measuredAvgRespTime_{k}",
                all_columns=[
                    "simTime(s)",
                    "controlServersDouble_{k-1}",
                    "controlServers_{k-1}",
                    "measuredArrivalRate_{k}",
                    "measuredAvgRespTime_{k}",
                ],
                static_row_values={
                    "controlServersDouble_{k-1}": 2,
                    "controlServers_{k-1}": 2,
                    "measuredArrivalRate_{k}": 40,
                },
            ),
            DistributionSegment(
                system="rubis",
                source_trace="trace_b.txt",
                unit_id="norm2",
                norm_label="norm2",
                sensor_index=None,
                segment_index=0,
                start_time=1.0,
                end_time=4.0,
                sample_count=3,
                rows=[{"simTime(s)": 1, "measuredAvgRespTime_{k}": 2.0}],
                time_column="simTime(s)",
                value_column="measuredAvgRespTime_{k}",
                all_columns=[
                    "simTime(s)",
                    "controlServersDouble_{k-1}",
                    "controlServers_{k-1}",
                    "measuredArrivalRate_{k}",
                    "measuredAvgRespTime_{k}",
                ],
                static_row_values={
                    "controlServersDouble_{k-1}": 2,
                    "controlServers_{k-1}": 2,
                    "measuredArrivalRate_{k}": 40,
                },
            ),
            DistributionSegment(
                system="rubis",
                source_trace="trace_c.txt",
                unit_id="norm3",
                norm_label="norm3",
                sensor_index=None,
                segment_index=0,
                start_time=1.0,
                end_time=4.0,
                sample_count=3,
                rows=[{"simTime(s)": 1, "measuredAvgRespTime_{k}": 3.0}],
                time_column="simTime(s)",
                value_column="measuredAvgRespTime_{k}",
                all_columns=[
                    "simTime(s)",
                    "controlServersDouble_{k-1}",
                    "controlServers_{k-1}",
                    "measuredArrivalRate_{k}",
                    "measuredAvgRespTime_{k}",
                ],
                static_row_values={
                    "controlServersDouble_{k-1}": 2,
                    "controlServers_{k-1}": 2,
                    "measuredArrivalRate_{k}": 40,
                },
            ),
        ]

        layout = build_experiment_layout("rubis", segments)

        self.assertEqual(sorted(layout.holdout_units), ["norm1", "norm2", "norm3"])
        self.assertEqual(sorted(layout.experiments["norm1"].train_units), ["norm2", "norm3"])
        self.assertEqual(layout.experiments["norm1"].holdout_unit, "norm1")

    def test_write_generated_trace_marks_last_segment_as_abn1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output_dir = tmp_path / "abnormal"
            output_dir.mkdir()
            segment_a = DistributionSegment(
                system="rubis",
                source_trace="trace_a.txt",
                unit_id="norm2",
                norm_label="norm2",
                sensor_index=None,
                segment_index=0,
                start_time=1.0,
                end_time=3.0,
                sample_count=2,
                rows=[
                    {"simTime(s)": 1, "measuredAvgRespTime_{k}": 1.0},
                    {"simTime(s)": 2, "measuredAvgRespTime_{k}": 1.1},
                ],
                time_column="simTime(s)",
                value_column="measuredAvgRespTime_{k}",
                all_columns=[
                    "simTime(s)",
                    "controlServersDouble_{k-1}",
                    "controlServers_{k-1}",
                    "measuredArrivalRate_{k}",
                    "measuredAvgRespTime_{k}",
                ],
                static_row_values={
                    "controlServersDouble_{k-1}": 2,
                    "controlServers_{k-1}": 2,
                    "measuredArrivalRate_{k}": 40,
                },
            )
            segment_b = DistributionSegment(
                system="rubis",
                source_trace="trace_b.txt",
                unit_id="norm1",
                norm_label="norm1",
                sensor_index=None,
                segment_index=0,
                start_time=1.0,
                end_time=3.0,
                sample_count=2,
                rows=[
                    {"simTime(s)": 1, "measuredAvgRespTime_{k}": 9.0},
                    {"simTime(s)": 2, "measuredAvgRespTime_{k}": 9.1},
                ],
                time_column="simTime(s)",
                value_column="measuredAvgRespTime_{k}",
                all_columns=[
                    "simTime(s)",
                    "controlServersDouble_{k-1}",
                    "controlServers_{k-1}",
                    "measuredArrivalRate_{k}",
                    "measuredAvgRespTime_{k}",
                ],
                static_row_values={
                    "controlServersDouble_{k-1}": 2,
                    "controlServers_{k-1}": 2,
                    "measuredArrivalRate_{k}": 40,
                },
            )

            meta = write_generated_trace(
                output_dir=output_dir,
                system="rubis",
                trace_kind="abnormal",
                trace_index=0,
                segments=[segment_a, segment_b],
                trace_labels=["norm2", "abn1"],
                config_num=2,
                sensor_index=None,
            )

            self.assertIn("abn1", meta["trace_config"])
            self.assertEqual(meta["trace_config"][-1], "abn1")
            self.assertTrue((output_dir / meta["filename"]).exists())
            self.assertEqual(meta["abn1_start_time"], meta["start_time"][-1])

    def test_write_generated_bsn_trace_keeps_all_six_sensors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            base_segment = DistributionSegment(
                system="bsn",
                source_trace="trace_a.txt",
                unit_id="sensor2_norm1",
                norm_label="norm1",
                sensor_index=2,
                segment_index=0,
                start_time=1.0,
                end_time=3.0,
                sample_count=2,
                rows=[
                    {"logicalTime(s)": 1, "cost": 0.91},
                    {"logicalTime(s)": 2, "cost": 0.92},
                ],
                time_column="logicalTime(s)",
                value_column="cost",
                all_columns=[
                    "logicalTime(s)",
                    "logicalTimestamp(ms)",
                    "component",
                    "freq_double",
                    "freq",
                    "cost",
                ],
                static_row_values={},
            )
            normal_segments_by_sensor = {
                sensor_index: [
                    DistributionSegment(
                        system="bsn",
                        source_trace=f"trace_{sensor_index}.txt",
                        unit_id=f"sensor{sensor_index}_norm1",
                        norm_label="norm1",
                        sensor_index=sensor_index,
                        segment_index=0,
                        start_time=1.0,
                        end_time=3.0,
                        sample_count=2,
                        rows=[
                            {"logicalTime(s)": 1, "cost": 0.8 + sensor_index * 0.01},
                            {"logicalTime(s)": 2, "cost": 0.81 + sensor_index * 0.01},
                        ],
                        time_column="logicalTime(s)",
                        value_column="cost",
                        all_columns=base_segment.all_columns,
                        static_row_values={},
                    )
                ]
                for sensor_index in range(6)
            }

            meta = write_generated_bsn_trace(
                output_dir=output_dir,
                trace_kind="abnormal",
                trace_index=0,
                target_sensor=2,
                target_segments=[base_segment],
                trace_labels=["abn1"],
                config_num=1,
                normal_segments_by_sensor=normal_segments_by_sensor,
                rng=__import__("random").Random(1),
            )

            frame = pd.read_csv(output_dir / meta["filename"])
            self.assertEqual(sorted(frame["component"].unique().tolist()), [f"/g3t1_{i}" for i in range(1, 7)])
            self.assertEqual(meta["sensor_index"], 2)
            self.assertEqual(meta["abn1_start_time"], 1)


if __name__ == "__main__":
    unittest.main()
