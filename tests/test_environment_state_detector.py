import unittest

import pandas as pd

from anomaly_detection.state.environment_detector import EnvironmentStateDetector


class EnvironmentStateDetectorTests(unittest.TestCase):
    def test_detect_states_falls_back_when_pump_columns_missing(self):
        values = [68.0] * 12 + [74.0] * 12 + [80.0] * 12
        df = pd.DataFrame({"HMI_2_LT_001.PV": values})

        detector = EnvironmentStateDetector(
            pump_columns=["HMI_2_P_001_STATUS", "HMI_2_P_002_STATUS"],
            num_states=3,
            fallback_metric="HMI_2_LT_001.PV",
        )

        state_labels = detector.detect_states(df)

        self.assertEqual(len(state_labels), len(df))
        self.assertEqual(len(set(state_labels.tolist())), 3)
        self.assertEqual(len(set(state_labels[:12].tolist())), 1)
        self.assertEqual(len(set(state_labels[12:24].tolist())), 1)
        self.assertEqual(len(set(state_labels[24:].tolist())), 1)


if __name__ == "__main__":
    unittest.main()
