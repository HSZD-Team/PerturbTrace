# Shifrut genome-wide CRISPR screens in primary human T cells

- source_id: `S25_shifrut_primary_tcell_crispr`
- input_table: `PerturbTrace/data_sources/raw_external/S25_shifrut_primary_tcell_crispr/shifrut_fitdb_nonproliferating_vs_highproliferating_advantageous.csv`
- normalized_oracle_table: `PerturbTrace/tasks/c3_primary_tcell_function_screen_v0/hidden/oracle_scores.csv`
- normalized_hit_set: `PerturbTrace/tasks/c3_primary_tcell_function_screen_v0/hidden/hit_set.npy`
- public_candidate_actions: `PerturbTrace/tasks/c3_primary_tcell_function_screen_v0/public/candidate_actions.csv`
- matrix_mode: `long`
- context_key: `FITdb_cell_vs_cell_4_nonproliferating_vs_highly_proliferating_advantageous`
- action_column: `gene`
- score_column: `score`
- hit_column: `hit_value`
- score_sign: `as_is`
- hit_mode: `threshold_lt`
- hit_percent: `5.0`
- hit_threshold: `0.05`
- candidate_count_verified: 19106
- hit_count_verified: 962

## Transformation

The source table was normalized to task-local `hidden/oracle_scores.csv` with exactly `action_id,score` columns. Public solver input was emitted separately as `public/candidate_actions.csv`, exposing only action identifiers. Hit labels are stored only in `hidden/hit_set.npy`.

## Source Provenance

primary_paper: Shifrut et al., Cell 2018, genome-wide CRISPR screens in primary human
  T cells.


## Raw Manifest

schema_version: 0.1
source_id: S25_shifrut_primary_tcell_crispr
download_status: verified
downloaded_at: '2026-06-10'
downloaded_by: Codex
source_url: https://fitdb.lji.org/api/cell_vs_cell_4/advantageous
source_release: FITdb static web API snapshot accessed 2026-06-10; Shifrut 2018 cell_vs_cell
  screen 4
license_or_terms: FITdb public web API; retain API path and exact comparison in judge-only
  provenance
raw_files:
- path: PerturbTrace/data_sources/raw_external/S25_shifrut_primary_tcell_crispr/fitdb_cell_vs_cell_4_advantageous.json
  description: FITdb Shifrut 2018 non-proliferating versus highly proliferating T-cell
    advantageous/depleted gene table
  sha256: 68b582b77e6891d10ec7240ea258317a9cef5a3614bbba0d5a594ae8b18a4ef1
  size_bytes: 1800555
- path: PerturbTrace/data_sources/raw_external/S25_shifrut_primary_tcell_crispr/fitdb_cell_vs_cell_4_disadvantageous.json
  description: FITdb Shifrut 2018 companion disadvantageous/enriched gene table for
    provenance and direction audit
  sha256: 8358fac9cfb75044d1278f563a080555db2cc88834abe420e4625486964f089f
  size_bytes: 1663391
- path: PerturbTrace/data_sources/raw_external/S25_shifrut_primary_tcell_crispr/shifrut_fitdb_nonproliferating_vs_highproliferating_advantageous.csv
  description: Derived action-score table from FITdb advantageous direction; score=-neg_lfc,
    hit_value=neg_fdr
  sha256: b3f1d9fd2fe90ceb2babf174a698e31f7e5b133795f0d2fe9f5d6ac8790c2e3c
  size_bytes: 646429
normalization_plan:
  matrix_mode: long
  action_column: gene
  score_column: score
  hit_column: hit_value
  context_key: FITdb_cell_vs_cell_4_nonproliferating_vs_highly_proliferating_advantageous
  score_sign: as_is
  hit_mode: threshold_lt
  hit_percent: null
  hit_threshold: 0.05
  command: .\BioDiscoveryAgent_repo\.venv\Scripts\python.exe .\PerturbTrace\data_sources\normalize_action_score_table.py
    --source-id S25_shifrut_primary_tcell_crispr --input-table .\PerturbTrace\data_sources\raw_external\S25_shifrut_primary_tcell_crispr\shifrut_fitdb_nonproliferating_vs_highproliferating_advantageous.csv
    --task-id C3_primary_tcell_function_screen_v0 --matrix-mode long --action-column
    gene --score-column score --hit-column hit_value --context-key FITdb_cell_vs_cell_4_nonproliferating_vs_highly_proliferating_advantageous
    --score-sign as_is --hit-mode threshold_lt --hit-threshold 0.05 --batch-size 128
leakage_boundary:
  hide_from_solver:
  - source_url
  - source_release
  - raw_files
  - context_key
  - full score table
  - hit_column
  - hit_threshold
notes: The FITdb route /shifrut_2018/cell_vs_cell labels this comparison as non-proliferating
  T cells versus highly proliferating T cells. The advantageous/depleted API returns
  neg_lfc, neg_p_value, and neg_fdr for 19,114 rows; duplicate gene symbols are mean/min
  aggregated into 19,106 unique public actions. Benchmark reward is score=-neg_lfc
  so stronger depletion in the target comparison receives higher reward, while hidden
  hits use neg_fdr < 0.05.
