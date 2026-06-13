# RQ1 LODO Dataset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild RQ1 around leave-one-distribution-out datasets generated from identity segments and rerun all baseline/GROUP methods on the new data.

**Architecture:** Extract reusable identity segments into manifests, generate one holdout dataset per distribution unit under a new `data_rq1_lodo/` root, and add a new RQ1 runner that evaluates all methods per holdout unit and aggregates system-level metrics. Reuse existing `cluster.py`, detection, and baseline code as much as possible by preserving the file-based trace format and final `abn1` semantics.

**Tech Stack:** Python, existing TOSE adapters/parsers, baseline methods, anomaly detection, JSON manifests, unittest.

---

### Task 1: Lock dataset semantics with tests

**Files:**
- Create: `tests/test_rq1_lodo_dataset.py`
- Create: `tests/test_rq1_lodo_runner.py`

- [ ] **Step 1: Write failing tests for unit extraction and holdout naming**
- [ ] **Step 2: Run targeted unittest and confirm failure**
- [ ] **Step 3: Add failing tests for abnormal trace generation and aggregated summary**
- [ ] **Step 4: Re-run tests and confirm failure**

### Task 2: Implement dataset builder

**Files:**
- Create: `rq_methods/lodo_dataset.py`
- Create: `scripts/build_rq1_lodo_dataset.py`

- [ ] **Step 1: Implement segment manifest extraction**
- [ ] **Step 2: Implement per-holdout identity/abnormal trace generation**
- [ ] **Step 3: Write manifests and dataset layout**
- [ ] **Step 4: Run targeted tests**

### Task 3: Implement LODO runner

**Files:**
- Create: `rq_methods/lodo_runner.py`
- Create: `scripts/run_rq1_lodo_methods_matrix.py`

- [ ] **Step 1: Reuse baseline and GROUP runners per holdout directory**
- [ ] **Step 2: Aggregate per-holdout results into per-system summaries**
- [ ] **Step 3: Run targeted tests**

### Task 4: Generate data and rerun experiments

**Files:**
- Modify: `docs/rq1_experiment_status.md`

- [ ] **Step 1: Generate `data_rq1_lodo/` for all systems**
- [ ] **Step 2: Run full LODO RQ1 matrix**
- [ ] **Step 3: Record outputs and summarize results**
- [ ] **Step 4: Commit**
