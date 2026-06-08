#!/usr/bin/env python3
"""
WaDi Anomaly Detection Script

Detects anomalies in WaDi test traces using state-conditional distributions
learned during training.

Usage:
    python detect_wadi.py --config configs/wadi_detection_config.yaml
"""

import argparse
import logging
import sys
from pathlib import Path
import yaml
import pandas as pd
import numpy as np

from cluster_analysis.adapters.wadi.wadi_adapter import WadiAdapter
from anomaly_detection.state.environment_detector import EnvironmentStateDetector
from anomaly_detection.state_conditional_detector import StateConditionalDetector


logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Configure logging output.

    Args:
        verbose: Whether to output detailed logs
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='[%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def load_config(config_path: str) -> dict:
    """Load detection configuration from YAML file.

    Args:
        config_path: Path to configuration YAML

    Returns:
        dict: Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    return config


def run_wadi_detection(config_path: str, verbose: bool = False) -> bool:
    """Execute WaDi anomaly detection workflow.

    Args:
        config_path: Path to detection configuration YAML
        verbose: Whether to output detailed logs

    Returns:
        bool: True if detection succeeded
    """
    setup_logging(verbose)

    try:
        # 1. Load configuration
        logger.info(f"Loading configuration: {config_path}")
        config = load_config(config_path)

        dataset_config = config['dataset']
        adapter_config = config.get('adapter', {})
        detection_config = config.get('detection', {})
        state_config = config.get('state_inference', {})
        output_config = config.get('output', {})

        # 2. Initialize WaDi adapter
        logger.info("Initializing WaDi adapter...")
        adapter = WadiAdapter(
            manual_include=adapter_config.get('manual_include', []),
            manual_exclude=adapter_config.get('manual_exclude', [])
        )

        # 3. Load test data
        test_data_path = dataset_config['test_data_path']
        logger.info(f"Loading test data from: {test_data_path}")

        # Get test trace files
        test_path = Path(test_data_path)
        if test_path.is_dir():
            test_files = sorted(test_path.glob('*.csv'))
            if not test_files:
                raise ValueError(f"No CSV files found in {test_data_path}")
            logger.info(f"Found {len(test_files)} test trace files")
        else:
            test_files = [test_path]
            logger.info(f"Single test file: {test_path.name}")

        # 4. Load learned distributions
        distributions_path = detection_config['distributions_path']
        logger.info(f"Loading learned distributions from: {distributions_path}")

        detector = StateConditionalDetector(
            distributions_path=distributions_path,
            mode=detection_config.get('mode', 'state_conditional'),
            cross_state_threshold=detection_config.get('cross_state_threshold', 2.5)
        )

        # 5. Initialize state detector
        logger.info("Initializing environment state detector...")
        pump_columns = state_config['pump_columns']

        state_detector = EnvironmentStateDetector(
            pump_columns=pump_columns,
            num_states=3,  # Infer from learned distributions
            auto_detect_states=state_config.get('auto_detect_states', False),
            max_states=state_config.get('max_states', 5),
            fallback_metric=state_config.get('fallback_metric'),
            fallback_threshold=state_config.get('fallback_threshold', 0.2),
        )

        # 6. Process each test trace
        logger.info(f"Starting anomaly detection on {len(test_files)} trace(s)...")

        all_results = []
        detection_threshold = detection_config.get('state_threshold', 3.0)

        for test_file in test_files:
            logger.info(f"Processing: {test_file.name}")

            # Load test trace
            df = adapter.load_abnormal_data(str(test_file))
            logger.info(f"  Loaded {len(df)} rows")

            # Infer operational states
            state_labels = state_detector.detect_states(df)
            logger.info(f"  Detected {len(set(state_labels))} operational states")

            # Detect anomalies
            anomalies = detector.detect(
                df,
                state_labels,
                threshold=detection_threshold
            )

            # Add trace metadata
            anomalies['trace_file'] = test_file.name

            all_results.append(anomalies)

            # Log per-trace summary
            anomaly_count = anomalies['is_anomaly'].sum()
            anomaly_rate = anomaly_count / len(anomalies) if len(anomalies) > 0 else 0.0
            logger.info(
                f"  Anomalies: {anomaly_count}/{len(anomalies)} ({anomaly_rate:.1%})"
            )

        # 7. Combine results
        combined_results = pd.concat(all_results, ignore_index=True)

        # 8. Save results
        output_csv = Path(output_config.get('results_csv', 'detection_results/wadi/results.csv'))
        output_csv.parent.mkdir(parents=True, exist_ok=True)

        combined_results.to_csv(output_csv, index=False)
        logger.info(f"Saved detection results to: {output_csv}")

        # Optional: Save JSON summary
        if 'results_json' in output_config:
            import json
            output_json = Path(output_config['results_json'])
            output_json.parent.mkdir(parents=True, exist_ok=True)

            # Per-trace summary
            trace_summaries = []
            for trace_file in test_files:
                trace_data = combined_results[combined_results['trace_file'] == trace_file.name]
                anomaly_count = trace_data['is_anomaly'].sum()
                total_count = len(trace_data)

                trace_summaries.append({
                    'trace_file': trace_file.name,
                    'total_samples': int(total_count),
                    'anomaly_count': int(anomaly_count),
                    'anomaly_rate': float(anomaly_count / total_count) if total_count > 0 else 0.0
                })

            summary = {
                'config_file': str(config_path),
                'distributions_path': distributions_path,
                'detection_threshold': detection_threshold,
                'detection_mode': detection_config.get('mode', 'state_conditional'),
                'total_traces': len(test_files),
                'total_samples': len(combined_results),
                'total_anomalies': int(combined_results['is_anomaly'].sum()),
                'overall_anomaly_rate': float(combined_results['is_anomaly'].sum() / len(combined_results)),
                'traces': trace_summaries
            }

            with open(output_json, 'w') as f:
                json.dump(summary, f, indent=2)

            logger.info(f"Saved detection summary to: {output_json}")

        # 9. Print summary
        print("\n" + "="*60)
        print("WaDi Anomaly Detection Summary")
        print("="*60)
        print(f"Test traces: {len(test_files)}")
        print(f"Total samples: {len(combined_results)}")
        print(f"Anomalies detected: {combined_results['is_anomaly'].sum()}")
        print(f"Anomaly rate: {combined_results['is_anomaly'].sum() / len(combined_results):.1%}")
        print(f"Detection threshold: {detection_threshold}σ")
        print(f"Detection mode: {detection_config.get('mode', 'state_conditional')}")
        print(f"Results: {output_csv}")
        print("="*60)

        return True

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return False
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return False
    except Exception as e:
        logger.error(f"Execution failed: {e}", exc_info=verbose)
        return False


def main():
    """CLI main entry point."""
    parser = argparse.ArgumentParser(
        description='WaDi Anomaly Detection - Detect anomalies using state-conditional distributions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Run detection with WaDi configuration
  python detect_wadi.py --config configs/wadi_detection_config.yaml

  # Enable verbose logging
  python detect_wadi.py --config configs/wadi_detection_config.yaml --verbose
        """
    )

    parser.add_argument(
        '--config', '-c',
        required=True,
        help='Path to detection configuration YAML file'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Execute detection
    success = run_wadi_detection(
        config_path=args.config,
        verbose=args.verbose
    )

    # Set exit code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
