import unittest

import numpy as np

from common.models import DistributionParameters


class SensorPartitionedClusteringTests(unittest.TestCase):
    def test_engine_partitions_bsn_clustering_by_sensor_index(self) -> None:
        from cluster_analysis.core.engine import ClusteringEngine

        parameters = []
        feature_rows = []
        clustering_rows = []

        for sensor_index, base_norm1, base_norm2 in [
            (0, 0.9000, 1.0350),
            (1, 0.9050, 1.0400),
        ]:
            for delta in [0.0, 0.0005]:
                for norm_label, mean_value in [
                    ("norm1", base_norm1 + delta),
                    ("norm2", base_norm2 + delta),
                ]:
                    parameters.append(
                        DistributionParameters(
                            norm_label=norm_label,
                            mean=mean_value,
                            variance=0.0001,
                            std_dev=0.01,
                            min_value=mean_value - 0.01,
                            max_value=mean_value + 0.01,
                            sample_count=50,
                            raw_values=[mean_value - 0.01, mean_value, mean_value + 0.01],
                            context_features={"sensor_index": float(sensor_index)},
                        )
                    )
                    feature_rows.append([mean_value, 0.0001])
                    clustering_rows.append([mean_value])

        engine = ClusteringEngine(
            system_type="bsn",
            algorithm_names=["gmm"],
            partition_context_features=["sensor_index"],
        )
        engine._attach_partition_context(parameters)

        feature_matrix = np.asarray(feature_rows, dtype=float)
        clustering_matrix = np.asarray(clustering_rows, dtype=float)
        result = engine._run_partitioned_algorithm(
            "gmm",
            feature_matrix,
            clustering_matrix,
            parameters,
        )

        self.assertEqual(result.n_clusters, 4)
        self.assertEqual(sorted(set(result.labels.tolist())), [0, 1, 2, 3])
        self.assertEqual(
            result.additional_metrics["partition_context_features"],
            ["sensor_index"],
        )
        self.assertEqual(
            sorted(result.additional_metrics["partition_summaries"].keys()),
            ["sensor_index=0.000000", "sensor_index=1.000000"],
        )


if __name__ == "__main__":
    unittest.main()
