## 1. Implementation

- [ ] 1.1 Add detection config support for the theoretical alarm-count policy metadata
- [ ] 1.2 Add failing tests for threshold calculation and delayed trace-level triggering
- [ ] 1.3 Update the evaluator to trigger alarms only after raw anomalies exceed `ceil(n * p_sigma)`
- [ ] 1.4 Update detection reporting outputs to expose the new trigger policy and per-trace trigger details
- [ ] 1.5 Update formal detection configs to use the theoretical alarm-count policy
- [ ] 1.6 Re-run the affected BSN/RQ1 detection experiments and refresh summary outputs
- [ ] 1.7 Update RQ1 and README documentation to describe the new detection semantics
