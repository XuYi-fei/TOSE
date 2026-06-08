## 1. Implementation
- [x] 1.1 Extend detection config to support `detection.mode` and `detection.bocpd.*`
- [x] 1.2 Refactor detector layer so pointwise and BOCPD detectors share a compatible interface
- [x] 1.3 Implement BOCPD recursion over learned distributions with per-run state weights
- [x] 1.4 Reset BOCPD state at trace boundaries inside the unified evaluation loop
- [x] 1.5 Extend JSON/CSV/Markdown reporting with BOCPD metadata and point-level state
- [x] 1.6 Add or update configs/examples for running BOCPD mode
- [x] 1.7 Add regression tests for pointwise mode and new tests for BOCPD mode

## 2. Verification
- [x] 2.1 Run focused tests for config parsing and detector behavior
- [x] 2.2 Run one end-to-end BOCPD detection experiment on a representative subject system
- [x] 2.3 Confirm JSON output contains BOCPD state fields without breaking existing readers
