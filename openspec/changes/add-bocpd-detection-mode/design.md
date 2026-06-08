# Design: BOCPD Detection Mode

## Context

The existing detection pipeline already provides:

- learned-distribution loading
- context-aware candidate selection
- optional context-based mean shifting
- pointwise anomaly scoring by marginal probability
- trace-level alarm triggering by cumulative raw anomaly counts

This change adds a BOCPD-based online detector without changing clustering outputs or the existing trace-level evaluation contract.

## Goals

- Add BOCPD as a configurable detection mode
- Map BOCPD predictive probabilities onto the existing learned distribution representation
- Preserve compatibility with current reporting and evaluation outputs

## Non-Goals

- No clustering-side BOCPD implementation
- No changes to learned distribution export format
- No replacement of the current pointwise mode

## Architecture

### Detection modes

The detection entrypoint selects one of two detectors:

- `pointwise`: existing `AnomalyDetector`
- `bocpd`: new `BOCPDDetector`

Both detectors expose a common operational surface:

- `detect_point(...) -> DetectionResult`
- `reset_trace_state() -> None`

The evaluator remains responsible for:

- iterating over trace points
- counting raw anomalies
- computing the allowed anomaly count
- converting point alarms into trace-level classifications

### BOCPD state

Per trace, the BOCPD detector maintains:

- run-length posterior
- per-run distribution posterior weights
- most likely run length
- latest changepoint posterior

State is reset at the beginning of each trace.

### Emission model

For each point, candidate distributions are selected by the same context logic already used in pointwise detection.

Each candidate distribution provides:

- `tail_probability`: used by anomaly semantics
- `log_likelihood`: used by BOCPD recursion

The detector updates:

- growth probabilities from weighted likelihoods of the previous run state
- changepoint probability from the configured prior over known distributions

### Raw anomaly semantics

The default rule is `cp_and_tail`:

- the changepoint posterior must exceed the configured threshold
- the best-match tail probability must remain below the configured `alpha`

This prevents normal switching among known distributions from being treated as anomalies by default.

## Configuration

New config fields:

```yaml
detection:
  mode: pointwise | bocpd
  bocpd:
    hazard_lambda: 50
    max_run_length: 200
    state_prior: uniform | sample_count
    changepoint_posterior_threshold: 0.5
    raw_anomaly_rule: cp_and_tail | cp_only | tail_only
```

Defaults must preserve compatibility for existing configs by keeping `mode=pointwise`.

## Reporting

Outputs must include detector mode metadata and, for BOCPD runs, point-level state:

- changepoint probability
- most likely run length
- best tail probability
- best log likelihood
- raw anomaly reasons

These fields are required in JSON output and should be propagated to CSV/Markdown where appropriate.

## Testing

Required validation includes:

- existing pointwise mode does not regress
- BOCPD config parsing and validation
- trace-state reset behavior
- BOCPD output fields present in JSON results
- normal known-distribution transitions do not trigger anomalies under default settings
