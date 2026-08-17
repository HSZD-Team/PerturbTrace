# JUMP Cell Painting perturbation morphology dataset

- source_id: `S16_jump_cell_painting`
- input_table: `PerturbTrace/data_sources/raw_external/S16_jump_cell_painting/jump_crispr_morphology_shift_50pc_gene_scores.csv`
- normalized_oracle_table: `PerturbTrace/tasks/c3_cell_painting_morphology_v0/hidden/oracle_scores.csv`
- normalized_hit_set: `PerturbTrace/tasks/c3_cell_painting_morphology_v0/hidden/hit_set.npy`
- public_candidate_actions: `PerturbTrace/tasks/c3_cell_painting_morphology_v0/public/candidate_actions.csv`
- matrix_mode: `long`
- context_key: `JUMP_CRISPR_hidden_50pc_morphology_shift`
- action_column: `action_id`
- score_column: `score`
- hit_column: ``
- score_sign: `as_is`
- hit_mode: `top_abs_percent`
- hit_percent: `5.0`
- hit_threshold: `None`
- candidate_count_verified: 7972
- hit_count_verified: 399

## Transformation

The source table was normalized to task-local `hidden/oracle_scores.csv` with exactly `action_id,score` columns. Public solver input was emitted separately as `public/candidate_actions.csv`, exposing only action identifiers. Hit labels are stored only in `hidden/hit_set.npy`.

## Source Provenance

project_url: https://jump-cellpainting.broadinstitute.org/
source_note: Public JUMP-CP morphology profiles.


## Raw Manifest

schema_version: 0.1
source_id: S16_jump_cell_painting
downloaded_at: '2026-06-10'
downloaded_by: Codex
source_release: JUMP Cell Painting cpg0016 assembled CRISPR profiles v1.0a; jump-cellpainting/datasets
  v0.12 metadata snapshot
license_or_terms: JUMP Cell Painting public Cell Painting Gallery / Zenodo distribution;
  retain source identity and exact profile path in judge-only provenance
normalization_plan:
  command: python PerturbTrace/data_sources/prepare_jump_cell_painting_task_table.py --input-parquet
    PerturbTrace/data_sources/raw_external/S16_jump_cell_painting/jump_crispr_profiles_wellpos_cc_var_mad_outlier_featselect_sphering_harmony_PCA_corrected.parquet
    --crispr-metadata PerturbTrace/data_sources/raw_external/S16_jump_cell_painting/extracted/jump-cellpainting-datasets-1819876/metadata/crispr.csv.gz
    --output-csv PerturbTrace/data_sources/raw_external/S16_jump_cell_painting/jump_crispr_morphology_shift_50pc_gene_scores.csv
    --metadata-json PerturbTrace/data_sources/raw_external/S16_jump_cell_painting/jump_crispr_morphology_shift_50pc_metadata.json
    --feature-count 50 --min-replicates 2
  matrix_mode: long
  action_column: action_id
  score_column: score
  score_sign: as_is
  hit_mode: top_abs_percent
  hit_percent: 5.0
  context_key: JUMP_CRISPR_hidden_50pc_morphology_shift
leakage_boundary:
  hide_from_solver:
  - source_url
  - source_release
  - raw_files
  - context_key
  - profile feature columns
  - control symbol
  - full score table
  - hit threshold
download_status: verified
source_url: https://cellpainting-gallery.s3.amazonaws.com/cpg0016-jump-assembled/source_all/workspace/profiles_assembled/CRISPR/v1.0a/profiles_wellpos_cc_var_mad_outlier_featselect_sphering_harmony_PCA_corrected.parquet
raw_files:
- path: PerturbTrace/data_sources/raw_external/S16_jump_cell_painting/jump_cellpainting_datasets_v0.12.zip
  description: Zenodo snapshot of jump-cellpainting/datasets v0.12 metadata and dataset
    manifests
  sha256: b917b7985f86640e50b6551417a9322d780b6627a81fc9c65e5f02cb36e63912
  size_bytes: 14766710
- path: PerturbTrace/data_sources/raw_external/S16_jump_cell_painting/jump_crispr_profiles_wellpos_cc_var_mad_outlier_featselect_sphering_harmony_PCA_corrected.parquet
  description: JUMP Cell Painting CRISPR assembled morphology profiles, PCA-corrected
    feature-selected harmonized parquet
  sha256: 019cd1b767db48dad6fbab5cbc483449a229a44c2193d2341a8d331d067204c8
  size_bytes: 79866678
- path: PerturbTrace/data_sources/raw_external/S16_jump_cell_painting/jump_crispr_morphology_shift_50pc_gene_scores.csv
  description: Derived JUMP Cell Painting CRISPR gene-level hidden morphology-effect
    score table
  sha256: 22637cd53707edabfb61c8afb4291b2f10594652b2b5facb5222fede48364a24
  size_bytes: 220937
- path: PerturbTrace/data_sources/raw_external/S16_jump_cell_painting/jump_crispr_morphology_shift_50pc_metadata.json
  description: Projection metadata for JUMP Cell Painting CRISPR morphology aggregation
  sha256: 7b664e082118184a2fab092015448d6e677bcaa51fef9b99888271452468ffd1
  size_bytes: 1934
notes: The JUMP metadata zip provides the profile_index and CRISPR JCP2022-to-gene
  mapping. The CRISPR assembled parquet has 51,185 well-level profiles and 259 PCA-corrected
  morphology features. The hidden task aggregates 7,972 gene actions with at least
  two profiles; score is the Euclidean distance between each gene's mean profile and
  the non-targeting control over the first 50 morphology components.
