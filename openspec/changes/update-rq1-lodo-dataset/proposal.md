# Change: Rebuild RQ1 Around Leave-One-Distribution-Out Data

## Why
The current RQ1 uses prebuilt abnormal traces whose anomaly segments are not strictly aligned with the distribution units seen during identification. This makes the experiment hard to interpret and can inflate or distort FP/FN because the detection traces are not generated from the same controlled partition used for identification.

## What Changes
- Rebuild RQ1 data generation around leave-one-distribution-out (LODO) experiments.
- Define distribution units from identity trace segments:
  - `rubis/swat/wadi`: `norm_label`
  - `bsn`: `sensor_index + norm_label`
- For each holdout unit:
  - build identity traces only from non-holdout units
  - build 200 abnormal traces whose prefixes use non-holdout units and whose final `abn1` segment uses the holdout unit
- Add reproducible manifests for segments, generated traces, and per-holdout experiment metadata.
- Add a new RQ1 runner that executes baseline and GROUP methods over all holdout units and aggregates results per system/method.

## Impact
- Affected specs: `rq1-lodo-evaluation`
- Affected code:
  - `scripts/`
  - `rq_methods/`
  - `baseline_methods/`
  - `docs/rq1_experiment_status.md`
