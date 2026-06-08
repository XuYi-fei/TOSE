import unittest

import numpy as np
import pandas as pd

from cluster_analysis.state_aware_clusterer import StateAwareClusterer


class StateAwareClustererWritableInputTests(unittest.TestCase):
    def test_fit_accepts_pandas_backed_series_values(self):
        np.random.seed(0)
        df = pd.DataFrame(
            {
                "HMI_2_LT_001.PV": np.concatenate(
                    [
                        np.random.normal(68.0, 0.2, 1000),
                        np.random.normal(74.0, 0.2, 1000),
                        np.random.normal(80.0, 0.2, 1000),
                    ]
                )
            }
        )
        state_labels = np.array([0] * 1000 + [1] * 1000 + [2] * 1000)

        clusterer = StateAwareClusterer(min_cluster_size=50)
        distributions = clusterer.fit(df, state_labels, "HMI_2_LT_001.PV")

        self.assertEqual(set(distributions.keys()), {"lt_state_0", "lt_state_1", "lt_state_2"})


if __name__ == "__main__":
    unittest.main()
