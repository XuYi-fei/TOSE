# Proposal: Add BOCPD Detection Mode to Unified Detection Framework

## Why

The current detection pipeline evaluates each point independently against learned distributions and then aggregates raw anomalies to trace-level alarms. This supports probability-based anomaly detection, but it does not explicitly model temporal regime persistence or changepoint posterior.

The project now needs a second detection mode based on Bayesian Online Changepoint Detection (BOCPD), integrated into the same unified framework so it can:

- reuse existing `learned_distributions*.yaml`
- reuse context-conditioned candidate selection
- reuse the same trace-level `TP/FP/FN/TN` evaluation
- expose BOCPD state for downstream result analysis

## What Changes

- Add `detection.mode: bocpd` as a new first-class detection mode
- Add BOCPD-specific configuration under `detection.bocpd`
- Implement a `BOCPDDetector` that performs online recursion over learned distributions
- Preserve the current pointwise detector as `detection.mode: pointwise`
- Extend detection outputs with changepoint posterior, run length, and BOCPD alarm reasons

## Impact

- Affected specs:
  - `anomaly-detection`
  - `anomaly-detection-config`
  - `anomaly-detection-reporting`
- Affected code:
  - `anomaly_detection/config/config.py`
  - `anomaly_detection/core/detector.py`
  - `anomaly_detection/core/evaluator.py`
  - `anomaly_detection/visualization/reporter.py`
  - `detect.py`
