import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from cluster_analysis.state_aware_clusterer import StateAwareClusterer


class StateAwareClustererHdbscanFallbackTests(unittest.TestCase):
    def test_fit_falls_back_to_raw_state_distribution_when_hdbscan_fails(self):
        np.random.seed(0)
        df = pd.DataFrame(
            {
                "HMI_2_LT_001.PV": np.concatenate(
                    [
                        np.random.normal(68.0, 0.2, 300),
                        np.random.normal(74.0, 0.2, 300),
                        np.random.normal(80.0, 0.2, 300),
                    ]
                )
            }
        )
        state_labels = np.array([0] * 300 + [1] * 300 + [2] * 300)

        with patch("cluster_analysis.state_aware_clusterer.HDBSCAN") as mock_hdbscan:
            mock_hdbscan.return_value.fit_predict.side_effect = OSError("Operation not permitted")

            clusterer = StateAwareClusterer(min_cluster_size=20)
            distributions = clusterer.fit(df, state_labels, "HMI_2_LT_001.PV")

        self.assertEqual(set(distributions.keys()), {"lt_state_0", "lt_state_1", "lt_state_2"})
        self.assertAlmostEqual(distributions["lt_state_0"]["mu"], 68.0, delta=0.2)
        self.assertAlmostEqual(distributions["lt_state_1"]["mu"], 74.0, delta=0.2)
        self.assertAlmostEqual(distributions["lt_state_2"]["mu"], 80.0, delta=0.2)


if __name__ == "__main__":
    unittest.main()
