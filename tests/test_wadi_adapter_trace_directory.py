import tempfile
import unittest
from pathlib import Path

import pandas as pd

from cluster_analysis.adapters.wadi.wadi_adapter import WadiAdapter


class WadiAdapterTraceDirectoryTests(unittest.TestCase):
    def test_load_identity_data_from_trace_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            trace_dir = root / "identity"
            trace_dir.mkdir(parents=True, exist_ok=True)

            for file_idx, values in enumerate(([68.0, 68.1], [74.0, 74.1, 80.0])):
                df = pd.DataFrame(
                    {
                        "time": [f"2023-12-18 00:00:0{i}" for i in range(len(values))],
                        "HMI_2_LT_001.PV": values,
                        "segment_label": ["norm1"] * len(values),
                    }
                )
                df.to_csv(trace_dir / f"trace_{file_idx:03d}.csv", index=False)

            adapter = WadiAdapter()
            df = adapter.load_identity_data(str(trace_dir))

            self.assertEqual(len(df), 5)
            self.assertIn("HMI_2_LT_001.PV", df.columns)


if __name__ == "__main__":
    unittest.main()
