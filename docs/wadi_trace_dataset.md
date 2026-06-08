# WaDi Trace Dataset Extraction

## Purpose

This flow builds a trace-style WaDi dataset from the local raw file in `wadi-original/`.
It is separate from the existing `data/wadi/identity/*.csv` raw-CSV training path used by
`cluster_wadi.py`.

Target output:

- `200` identity traces
- `200` abnormal traces
- each identity trace contains `3` normal segments
- each abnormal trace contains `3` normal segments plus `1` synthetic abnormal segment

## Source

- Raw CSV: `wadi-original/data/WaDi.A3_Dec 2023 Historian Data_original.csv`
- Metric: `HMI_2_LT_001.PV`

`HMI_2_LT_001.PV` is used because the current project investigation found it produces a
stable three-region separation that is suitable for trace extraction. The pump status
columns were not reliable enough for this trace-building task.

## State Definition

The extractor converts the metric into three coarse states with fixed thresholds:

- `norm1` / low: `value < 71.1`
- `norm2` / normal: `71.1 <= value < 77.4`
- `norm3` / high: `value >= 77.4`

The script first finds contiguous same-state segments, then cuts each segment into
non-overlapping fixed windows.

Default window length:

- `180` points per segment

## Trace Construction

Identity traces are assembled from sampled state windows:

- alternating patterns: `norm1,norm2,norm3` and `norm3,norm2,norm1`

Abnormal traces reuse the same three-distribution normal prefix, then append:

- `abn1`: a synthetic `mean_shift` segment derived from the last normal segment

Shift rule:

- if the last normal segment is `norm3`, `abn1 = norm3 + 6.0`
- if the last normal segment is `norm1`, `abn1 = norm1 - 6.0`

This keeps the abnormal data simple, explicit, and traceable in the manifest.

## Output Layout

Running the extractor writes:

- `data/wadi_trace/identity/*.csv`
- `data/wadi_trace/abnormal/*.csv`
- `data/wadi_trace/manifests/trace_manifest.json`
- `data/wadi_trace/reports/dataset_summary.json`

Each trace CSV records:

- timestamp
- `HMI_2_LT_001.PV`
- `segment_label`
- source window metadata for provenance

## Command

```bash
python3 scripts/extract_wadi_trace_dataset.py \
  --source-csv "wadi-original/data/WaDi.A3_Dec 2023 Historian Data_original.csv" \
  --output-root data/wadi_trace \
  --identity-count 200 \
  --abnormal-count 200 \
  --segment-len 180 \
  --seed 42
```

## Notes

- This dataset is intended for trace-style clustering and anomaly testing.
- The abnormal split is synthetic and currently includes only `mean_shift`.
- Identity and abnormal normal-prefix windows are sampled from disjoint source pools.
