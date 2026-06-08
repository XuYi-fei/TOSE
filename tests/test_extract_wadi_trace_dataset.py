import csv
import json
import tempfile
import unittest
from pathlib import Path


class ExtractWadiTraceDatasetTests(unittest.TestCase):
    def _create_source_csv(self, root: Path) -> Path:
        csv_path = root / "wadi_source.csv"
        rows = []

        # Create enough non-overlapping windows for both identity and abnormal splits.
        state_specs = [
            ("low", 68.0),
            ("normal", 74.0),
            ("high", 80.0),
        ]

        current_time = 0
        for cycle_idx in range(8):
            for state_name, base in state_specs:
                for point_idx in range(12):
                    value = base + ((point_idx % 3) - 1) * 0.1 + cycle_idx * 0.01
                    rows.append(
                        {
                            "Time": f"2023-12-18 00:00:{current_time:02d}+00:00",
                            "HMI_2_LT_001.PV": f"{value:.3f}",
                        }
                    )
                    current_time += 1

        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["Time", "HMI_2_LT_001.PV"])
            writer.writeheader()
            writer.writerows(rows)

        return csv_path

    def test_generate_trace_dataset_outputs_expected_artifacts(self):
        from scripts.extract_wadi_trace_dataset import generate_trace_dataset

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_csv = self._create_source_csv(root)
            output_root = root / "wadi_trace"

            summary = generate_trace_dataset(
                source_csv=source_csv,
                output_root=output_root,
                identity_count=2,
                abnormal_count=2,
                segment_len=6,
                seed=7,
            )

            self.assertEqual(summary["identity_count"], 2)
            self.assertEqual(summary["abnormal_count"], 2)

            identity_files = sorted((output_root / "identity").glob("*.csv"))
            abnormal_files = sorted((output_root / "abnormal").glob("*.csv"))
            self.assertEqual(len(identity_files), 2)
            self.assertEqual(len(abnormal_files), 2)

            report_path = output_root / "reports" / "dataset_summary.json"
            manifest_path = output_root / "manifests" / "trace_manifest.json"
            self.assertTrue(report_path.exists())
            self.assertTrue(manifest_path.exists())

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["traces"]), 4)
            self.assertEqual(
                {trace["abnormal_type"] for trace in manifest["traces"] if trace["split"] == "abnormal"},
                {"mean_shift"},
            )

            identity_sources = {
                tuple(segment["window_id"] for segment in trace["segments"])
                for trace in manifest["traces"]
                if trace["split"] == "identity"
            }
            abnormal_sources = {
                tuple(segment["window_id"] for segment in trace["segments"][:-1])
                for trace in manifest["traces"]
                if trace["split"] == "abnormal"
            }
            self.assertTrue(identity_sources.isdisjoint(abnormal_sources))

    def test_generated_abnormal_trace_has_shifted_final_segment(self):
        from scripts.extract_wadi_trace_dataset import generate_trace_dataset

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_csv = self._create_source_csv(root)
            output_root = root / "wadi_trace"

            generate_trace_dataset(
                source_csv=source_csv,
                output_root=output_root,
                identity_count=1,
                abnormal_count=1,
                segment_len=6,
                seed=11,
            )

            abnormal_file = next((output_root / "abnormal").glob("*.csv"))
            with abnormal_file.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

            segment_labels = [row["segment_label"] for row in rows]
            self.assertEqual(segment_labels.count("abn1"), 6)
            self.assertEqual(segment_labels[:18], ["norm1"] * 6 + ["norm2"] * 6 + ["norm3"] * 6)

            norm3_values = [float(row["HMI_2_LT_001.PV"]) for row in rows if row["segment_label"] == "norm3"]
            abn_values = [float(row["HMI_2_LT_001.PV"]) for row in rows if row["segment_label"] == "abn1"]
            self.assertGreater(sum(abn_values) / len(abn_values), sum(norm3_values) / len(norm3_values) + 5.0)

    def test_generate_trace_dataset_accepts_blank_first_time_column(self):
        from scripts.extract_wadi_trace_dataset import generate_trace_dataset

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_csv = root / "wadi_source_blank_time.csv"

            rows = []
            current_time = 0
            for state_name, base in (("low", 68.0), ("normal", 74.0), ("high", 80.0)):
                for _ in range(12):
                    rows.append(
                        {
                            "": f"2023-12-18 00:00:{current_time:02d}+00:00",
                            "HMI_2_LT_001.PV": f"{base:.3f}",
                        }
                    )
                    current_time += 1
            rows = rows * 4

            with source_csv.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["", "HMI_2_LT_001.PV"])
                writer.writeheader()
                writer.writerows(rows)

            output_root = root / "wadi_trace"
            summary = generate_trace_dataset(
                source_csv=source_csv,
                output_root=output_root,
                identity_count=1,
                abnormal_count=1,
                segment_len=6,
                seed=3,
            )

            self.assertEqual(summary["identity_count"], 1)
            self.assertTrue((output_root / "manifests" / "trace_manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
