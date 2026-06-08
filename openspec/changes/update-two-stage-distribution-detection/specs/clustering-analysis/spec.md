## ADDED Requirements

### Requirement: Two-Stage Identity Clustering
The clustering pipeline SHALL perform stage-1 free clustering on identity segment means and SHALL model each resulting cluster with a fitted probability distribution in stage-2.

#### Scenario: Stage-1 uses means only
- **WHEN** the standard clustering pipeline loads identity traces
- **THEN** the clustering algorithm receives a feature matrix derived from segment `mu`
- **AND** reporting can still keep `[mu, variance]` as the visualization space

#### Scenario: Stage-2 stores heterogeneous models
- **WHEN** a clustering algorithm produces labels for identity segments
- **THEN** the pipeline SHALL gather raw samples for each cluster
- **AND** fit a distribution family for that cluster
- **AND** export `distribution_type`, `fitted_params`, and goodness-of-fit metadata to learned distributions YAML
