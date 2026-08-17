# Project DRIVE large-scale cancer RNAi dependency screens

- source_id: `S11_project_drive_rnai`
- input_table: `PerturbTrace/data_sources/raw_external/S11_project_drive_rnai/drive_demeter2_frozen_context_gene_dependency.csv`
- normalized_oracle_table: `PerturbTrace/tasks/c3_project_drive_dependency_v0/hidden/oracle_scores.csv`
- normalized_hit_set: `PerturbTrace/tasks/c3_project_drive_dependency_v0/hidden/hit_set.npy`
- public_candidate_actions: `PerturbTrace/tasks/c3_project_drive_dependency_v0/public/candidate_actions.csv`
- matrix_mode: `long`
- context_key: `SF295_CENTRAL_NERVOUS_SYSTEM`
- action_column: `gene`
- score_column: `score`
- score_sign: `negate`
- hit_mode: `top_score_percent`
- hit_percent: `5.0`
- candidate_count_verified: 7975
- hit_count_verified: 399

## Transformation

The source table was normalized to task-local `hidden/oracle_scores.csv` with exactly `action_id,score` columns. Public solver input was emitted separately as `public/candidate_actions.csv`, exposing only action identifiers. Hit labels are stored only in `hidden/hit_set.npy`.

## Source Provenance

primary_paper: McDonald et al., Cell 2017, Project DRIVE.
source_note: Useful RNAi contrast to CRISPR dependency tasks.


## Raw Manifest

schema_version: 0.1
source_id: S11_project_drive_rnai
download_status: verified
downloaded_at: null
downloaded_by: null
source_url: https://ndownloader.figshare.com/files/11489693
source_release: DEMETER2 Data v6; release_date=2020-04-09
license_or_terms: DepMap portal file index / Figshare download; retain release and
  hidden context in judge-only provenance
raw_files:
- path: PerturbTrace/data_sources/raw_external/S11_project_drive_rnai/sample_info.csv
  description: DEMETER2 Data v6 sample info metadata
  sha256: 8dcbd6da1e4858e7fa5b3910e8cf3feb1045a0c31a2e5d252eb3f2afe86dd036
  size_bytes: 76352
- path: PerturbTrace/data_sources/raw_external/S11_project_drive_rnai/D2_DRIVE_CL_data.csv
  description: DEMETER2 Data v6 Project DRIVE cell-line metadata
  sha256: c41be38026e570317978f89cebc28c14f803ffbf4b034e0865fa217cc71b5479
  size_bytes: 43938
- path: PerturbTrace/data_sources/raw_external/S11_project_drive_rnai/D2_DRIVE_gene_dep_scores.csv
  description: DEMETER2 Data v6 Project DRIVE gene dependency scores
  sha256: 3f863c296188be1aa8a491ef5489b135a9bfd65266f05d0690225d20fc38254b
  size_bytes: 58652780
- path: PerturbTrace/data_sources/raw_external/S11_project_drive_rnai/drive_demeter2_frozen_context_gene_dependency.csv
  description: DEMETER2 Data v6 Project DRIVE gene dependency table extracted for
    frozen hidden context SF295_CENTRAL_NERVOUS_SYSTEM
  sha256: 0d946d4d7a47af4a1f6e0c2c291e4df7ab552258f440a0607d9c2fc8cbca5420
  size_bytes: 210603
normalization_plan:
  matrix_mode: long
  action_column: gene
  score_column: score
  context_key: SF295_CENTRAL_NERVOUS_SYSTEM
  score_sign: negate
  hit_mode: top_score_percent
  hit_percent: 5.0
  command: .\BioDiscoveryAgent_repo\.venv\Scripts\python.exe .\PerturbTrace\data_sources\normalize_action_score_table.py
    --source-id S11_project_drive_rnai --input-table .\PerturbTrace\data_sources\raw_external\S11_project_drive_rnai\drive_demeter2_frozen_context_gene_dependency.csv
    --matrix-mode long --action-column gene --score-column score --context-key SF295_CENTRAL_NERVOUS_SYSTEM
    --score-sign negate --hit-mode top_score_percent --hit-percent 5 --batch-size
    128
leakage_boundary:
  hide_from_solver:
  - source_url
  - source_release
  - raw_files
  - context_key
  - full score table
notes: Frozen context SF295_CENTRAL_NERVOUS_SYSTEM was selected by maximum non-null
  coverage in the Project DRIVE DEMETER2 gene dependency matrix. DEMETER2 dependency
  scores are negated for benchmark reward so stronger dependency becomes higher score.
  Solver prompts must not expose the cell-line/context ID, release handle, or raw
  matrix names.
