import csv
import tempfile
import unittest
from pathlib import Path

import yaml

from common.adapters import ParserFactory


class IdentityBoundaryTrimTests(unittest.TestCase):
    def test_clustering_config_accepts_boundary_trim_points(self):
        from cluster_analysis.config.config import ClusteringConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "identity").mkdir()
            config_path = root / "cluster.yaml"
            config_path.write_text(
                yaml.dump(
                    {
                        "system_type": "rubis",
                        "data_path": str(root / "identity"),
                        "algorithms": ["gmm"],
                        "distribution_modeling": {
                            "boundary_trim_points": 10,
                        },
                    }
                ),
                encoding="utf-8",
            )

            config = ClusteringConfig.from_yaml(str(config_path))

            self.assertEqual(config.boundary_trim_points, 10)

    def test_rubis_parser_trims_points_around_identity_boundaries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            trace_path = root / (
                "eval_ident_trace-cnt-000-duration-90-config_num-3-"
                "trace_config-norm1,norm2,norm3-start_time-1,31,61.txt"
            )
            with trace_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["simTime(s)", "measuredAvgRespTime_{k}"],
                )
                writer.writeheader()
                for t in range(1, 91):
                    writer.writerow(
                        {
                            "simTime(s)": t,
                            "measuredAvgRespTime_{k}": float(t),
                        }
                    )

            parser = ParserFactory.create("rubis", boundary_trim_points=10)
            metadata = parser.parse_filename(trace_path.name)
            segments = parser.parse_trace_file(trace_path, metadata)

            self.assertEqual(segments["norm1"]["simTime(s)"].tolist(), list(range(1, 21)))
            self.assertEqual(segments["norm2"]["simTime(s)"].tolist(), list(range(41, 51)))
            self.assertEqual(segments["norm3"]["simTime(s)"].tolist(), list(range(71, 91)))

            parameters = parser.parse_file(trace_path)
            self.assertEqual([param.sample_count for param in parameters], [20, 10, 20])

    def test_zero_boundary_trim_preserves_existing_identity_segmentation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            trace_path = root / (
                "eval_ident_trace-cnt-000-duration-30-config_num-3-"
                "trace_config-norm1,norm2,norm3-start_time-1,11,21.txt"
            )
            with trace_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["simTime(s)", "measuredAvgRespTime_{k}"],
                )
                writer.writeheader()
                for t in range(1, 31):
                    writer.writerow(
                        {
                            "simTime(s)": t,
                            "measuredAvgRespTime_{k}": float(t),
                        }
                    )

            parser = ParserFactory.create("rubis", boundary_trim_points=0)
            metadata = parser.parse_filename(trace_path.name)
            segments = parser.parse_trace_file(trace_path, metadata)

            self.assertEqual(segments["norm1"]["simTime(s)"].tolist(), list(range(1, 11)))
            self.assertEqual(segments["norm2"]["simTime(s)"].tolist(), list(range(11, 21)))
            self.assertEqual(segments["norm3"]["simTime(s)"].tolist(), list(range(21, 31)))


if __name__ == "__main__":
    unittest.main()
