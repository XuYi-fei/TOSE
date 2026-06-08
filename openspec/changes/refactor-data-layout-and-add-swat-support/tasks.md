# Tasks: Refactor Data Layout and Add SWAT Support

## Phase 1: Data Reorganization (DRG)
- [ ] Create `data/` directory structure with system and type subdirectories
  - [ ] Create `data/{rubis,bsn,swat,wadi}/{identity,abnormal}` directories
  - [ ] Verify directory structure created successfully
- [ ] Move RUBIS evaluation data to new locations
  - [ ] Move `rubis_evaluation_data/eval_ident_traces/*` to `data/rubis/identity/`
  - [ ] Move `rubis_evaluation_data/eval_abn_traces/*` to `data/rubis/abnormal/`
  - [ ] Verify file counts match (200 identity, 200 abnormal)
- [ ] Move BSN evaluation data to new locations
  - [ ] Move `bsn_evaluation_data/eval_ident_traces/*` to `data/bsn/identity/`
  - [ ] Verify file count matches
- [ ] Move SWAT evaluation data to new locations
  - [ ] Move `swat_evaluation_data/eval_ident_traces/*` to `data/swat/identity/`
  - [ ] Verify file count matches (should be 200 files)
- [ ] Move WADI evaluation data if exists
  - [ ] Check if `wadi_evaluation_data/` exists
  - [ ] Move to `data/wadi/identity/` if present
- [ ] Verify data integrity
  - [ ] Check total file counts in `data/` match original counts
  - [ ] Spot-check file contents unchanged
  - [ ] Test: Load sample trace from new location
- [ ] Clean up old directories (after verification)
  - [ ] Remove `rubis_evaluation_data/` directory
  - [ ] Remove `bsn_evaluation_data/` directory
  - [ ] Remove `swat_evaluation_data/` directory
  - [ ] Remove `wadi_evaluation_data/` directory if moved

## Phase 2: SWAT Parser Implementation (SWP)
- [ ] Analyze SWAT data format in detail
  - [ ] Document CSV column structure (time, water_tank, ..., y_0)
  - [ ] Confirm filename pattern matches RUBIS exactly
  - [ ] Identify target column (`y_0`) and time column (`time`)
  - [ ] Test: Parse sample SWAT filename manually
- [ ] Create SWAT parser module
  - [ ] Create `common/adapters/swat.py` file
  - [ ] Implement `SWATParser` class inheriting from `RUBISParser`
  - [ ] Override `TARGET_COLUMN = 'y_0'` and `TIME_COLUMN = 'time'`
  - [ ] Override `parse_trace_file()` to use SWAT column names
  - [ ] Override `extract_parameters()` to use SWAT target column
  - [ ] Add class docstring explaining SWAT data format and inheritance rationale
- [ ] Create SWAT metadata support
  - [ ] Add `SWATMetadata` type alias in `common/models/metadata.py` (alias to RUBISMetadata)
  - [ ] Or reuse RUBISMetadata directly if no SWAT-specific fields needed
  - [ ] Update type hints in SWATParser
- [ ] Register SWAT parser in factory
  - [ ] Update `common/adapters/__init__.py` to import SWATParser
  - [ ] Register SWAT parser in `ParserFactory` with key `'swat'`
  - [ ] Test: `ParserFactory.create('swat')` returns SWATParser instance
  - [ ] Test: `ParserFactory.list_parsers()` includes 'swat'
- [ ] Add unit tests for SWAT parser
  - [ ] Test filename parsing with sample SWAT trace filename
  - [ ] Test trace file parsing and segmentation
  - [ ] Test parameter extraction from segments
  - [ ] Test handling of missing or malformed files
  - [ ] Verify extracted parameters have correct fields (mean, variance, sample_count)

## Phase 3: Configuration Updates (CFG)
- [ ] Update RUBIS clustering configuration
  - [ ] Edit `configs/rubis_clustering_config.yaml`
  - [ ] Change `data_path` from `rubis_evaluation_data/eval_ident_traces` to `data/rubis/identity`
  - [ ] Test: Load config successfully
  - [ ] Test: Config validation passes
- [ ] Update RUBIS detection configuration
  - [ ] Edit `configs/rubis_detection_config.yaml`
  - [ ] Change `test_data_path` from `rubis_evaluation_data/eval_abn_traces` to `data/rubis/abnormal`
  - [ ] Change `learned_distributions` path if needed
  - [ ] Test: Load config successfully
- [ ] Update BSN clustering configuration
  - [ ] Edit `configs/bsn_clustering_config.yaml`
  - [ ] Change `data_path` from `bsn_evaluation_data/eval_ident_traces` to `data/bsn/identity`
  - [ ] Test: Load config successfully
- [ ] Update BSN detection configuration (if exists)
  - [ ] Edit `configs/bsn_detection_config.yaml` if present
  - [ ] Update paths to new data layout
- [ ] Create SWAT clustering configuration
  - [ ] Create `configs/swat_clustering_config.yaml`
  - [ ] Set `system_type: swat`
  - [ ] Set `data_path: data/swat/identity`
  - [ ] Configure algorithms: hdbscan, gmm, affinity_propagation, mean_shift
  - [ ] Configure output: `clustering_results/swat`
  - [ ] Add Chinese comments explaining SWAT-specific settings
  - [ ] Test: Load config successfully
  - [ ] Test: Config validation passes (check data_path exists)
- [ ] Create SWAT detection configuration
  - [ ] Create `configs/swat_detection_config.yaml`
  - [ ] Set `system_type: swat`
  - [ ] Set `learned_distributions: clustering_results/swat/learned_distributions.yaml`
  - [ ] Set `test_data_path: data/swat/abnormal`
  - [ ] Configure detection parameters (sigma_threshold: 3.0)
  - [ ] Configure output: `detection_results/swat`
  - [ ] Add note that abnormal data may not exist yet
  - [ ] Test: Load config successfully (may skip validation if abnormal dir empty)
- [ ] Validate all configuration files
  - [ ] Load each config file and check for errors
  - [ ] Verify all data paths exist and are accessible
  - [ ] Verify all output directories can be created

## Phase 4: Integration Testing (INT)
- [ ] Test SWAT clustering workflow end-to-end
  - [ ] Run: `python cluster.py --config configs/swat_clustering_config.yaml`
  - [ ] Verify: Loads 200 SWAT trace files successfully
  - [ ] Verify: Extracts ~600 distribution parameters (3 per file × 200 files)
  - [ ] Verify: Clustering completes in <10 seconds
  - [ ] Verify: Generates `clustering_results/swat/learned_distributions.yaml`
  - [ ] Verify: Learned distributions contains 3 clusters (norm1, norm2, norm3)
  - [ ] Verify: Each distribution has mu, sigma, variance, sample_count fields
  - [ ] Verify: Generates 4 visualization PNG files
  - [ ] Verify: Generates `clustering_results/swat/clustering_report.md`
  - [ ] Verify: Report contains Chinese text labels and SWAT-specific content
- [ ] Test SWAT detection workflow (if abnormal data available)
  - [ ] Check if `data/swat/abnormal/` contains trace files
  - [ ] If yes, run: `python detect.py --config configs/swat_detection_config.yaml`
  - [ ] Verify: Detection completes successfully
  - [ ] Verify: Generates `detection_results/swat/detection_report.md`
  - [ ] Verify: Report shows metrics (TP, FP, TN, FN, Precision, Recall, F1)
  - [ ] If no abnormal data, document limitation in SWAT documentation
- [ ] Test RUBIS regression (clustering)
  - [ ] Run: `python cluster.py --config configs/rubis_clustering_config.yaml`
  - [ ] Verify: Loads 200 RUBIS identity traces from new path
  - [ ] Verify: Generates learned_distributions.yaml
  - [ ] Verify: Results consistent with previous runs (same cluster count, similar mu/sigma)
  - [ ] Verify: Visualizations generated correctly
- [ ] Test RUBIS regression (detection)
  - [ ] Run: `python detect.py --config configs/rubis_detection_config.yaml`
  - [ ] Verify: Loads 200 RUBIS abnormal traces from new path
  - [ ] Verify: Detection completes successfully
  - [ ] Verify: Metrics similar to previous baseline
  - [ ] Verify: Report generated with Chinese text
- [ ] Test BSN regression (clustering)
  - [ ] Run: `python cluster.py --config configs/bsn_clustering_config.yaml`
  - [ ] Verify: Loads BSN identity traces from new path
  - [ ] Verify: Clustering completes successfully
  - [ ] Verify: Results match expectations
- [ ] Verify parser factory registration
  - [ ] Test: `ParserFactory.create('swat')` returns correct parser instance
  - [ ] Test: `ParserFactory.create('rubis')` still works
  - [ ] Test: `ParserFactory.create('bsn')` still works
  - [ ] Test: Invalid system type raises appropriate error
- [ ] Performance validation
  - [ ] SWAT clustering: <10 seconds for 200 files
  - [ ] RUBIS clustering: <10 seconds (regression check)
  - [ ] BSN clustering: <10 seconds (regression check)
  - [ ] SWAT detection: <10 seconds if abnormal data exists

## Phase 5: Documentation (DOC)
- [ ] Update main README.md
  - [ ] Add "Data Organization" section explaining new `data/` structure
  - [ ] Add visual tree diagram of data layout
  - [ ] Explain `identity/` vs `abnormal/` semantics
  - [ ] Update "Quick Start" examples with new paths
  - [ ] Add "Supported Systems" section listing RUBIS, BSN, SWAT
  - [ ] For each system, document: domain, metric, data availability
  - [ ] Update clustering usage examples for all three systems
  - [ ] Update detection usage examples for systems with abnormal data
  - [ ] Add note about WADI being reserved for future use
- [ ] Create data migration guide
  - [ ] Create `docs/data_migration_guide.md`
  - [ ] Document old → new path mappings
  - [ ] Provide step-by-step migration commands
  - [ ] Include verification steps
  - [ ] Add troubleshooting section for common migration issues
- [ ] Create SWAT system documentation
  - [ ] Add SWAT section to README or create `docs/swat_system.md`
  - [ ] Document SWAT data format (CSV columns, time column, target column)
  - [ ] Explain SWAT filename pattern
  - [ ] Provide SWAT clustering example with expected output
  - [ ] Provide SWAT detection example (placeholder if no abnormal data)
  - [ ] Document SWAT-specific configuration options
  - [ ] Add references to SWAT dataset if available
- [ ] Update configuration documentation
  - [ ] Document `data_path` field points to `data/{system}/identity`
  - [ ] Document `test_data_path` field points to `data/{system}/abnormal`
  - [ ] Provide configuration file reference table
  - [ ] Add examples for all three system types
- [ ] Update developer guide (if exists)
  - [ ] Document how to add a new system type
  - [ ] Reference SWATParser as example of simple parser (inherits from RUBIS)
  - [ ] Document ParserFactory registration process
  - [ ] Add checklist for new system integration
- [ ] Verify documentation completeness
  - [ ] All new features documented (data layout, SWAT support)
  - [ ] All config files documented
  - [ ] Migration guide complete and tested
  - [ ] Usage examples verified to work
  - [ ] Chinese text used where appropriate (section headers, comments)

## Phase 6: Final Validation and Cleanup (FIN)
- [ ] Run full regression test suite
  - [ ] Re-run all Phase 4 integration tests
  - [ ] Verify zero regressions in RUBIS workflows
  - [ ] Verify zero regressions in BSN workflows
  - [ ] Verify SWAT workflows complete successfully
- [ ] Code quality checks
  - [ ] All SWAT parser code has Chinese docstrings
  - [ ] All key logic has Chinese comments
  - [ ] Code formatting consistent (autopep8/black)
  - [ ] No unused imports or debug code
  - [ ] Type hints added where appropriate
- [ ] Review and finalize configurations
  - [ ] All config files have Chinese comments
  - [ ] All paths validated
  - [ ] All required fields present
  - [ ] Default values appropriate for each system
- [ ] Update OpenSpec tasks status
  - [ ] Mark all completed tasks as [x]
  - [ ] Document any deviations from original plan
  - [ ] Update validation checkpoints status
- [ ] Archive old evaluation data directories
  - [ ] Optionally tar and archive old directories as backup
  - [ ] Or fully remove if verification complete
- [ ] Final documentation review
  - [ ] README.md reviewed for completeness
  - [ ] Migration guide tested by following steps exactly
  - [ ] SWAT documentation accurate and helpful
  - [ ] All examples tested and working

---

## Validation Checkpoints

- After Phase 1: All data moved successfully, file counts verified
- After Phase 2: SWAT parser can parse sample trace files
- After Phase 3: All configs load without errors, paths validated
- After Phase 4: All three systems (RUBIS, BSN, SWAT) clustering workflows work
- After Phase 5: Documentation complete, migration guide tested
- After Phase 6: Full regression suite passes, no breaking changes

## Dependencies

- **Phase 2** depends on **Phase 1** (needs data in new locations to test parser)
- **Phase 3** depends on **Phase 1** (configs reference new paths)
- **Phase 4** depends on **Phase 1, 2, 3** (integration tests need all pieces)
- **Phase 5** can partially overlap with **Phase 4** (write docs while testing)
- **Phase 6** depends on all previous phases (final validation)

## Success Criteria

1. ✅ Data reorganized into `data/{system}/{identity|abnormal}/` structure
2. ✅ SWAT parser implemented and registered
3. ✅ SWAT clustering workflow successful (200 files → learned_distributions.yaml)
4. ✅ RUBIS and BSN workflows still work (regression tests pass)
5. ✅ All configuration files updated and validated
6. ✅ Documentation complete (README, migration guide, SWAT docs)
7. ✅ Zero breaking changes to existing functionality

## Estimated Time

- **Phase 1**: 1-2 hours (data movement and verification)
- **Phase 2**: 2-3 hours (parser implementation and tests)
- **Phase 3**: 1 hour (config updates)
- **Phase 4**: 2-3 hours (comprehensive integration testing)
- **Phase 5**: 2-3 hours (documentation)
- **Phase 6**: 1 hour (final validation)

**Total**: 9-13 hours
