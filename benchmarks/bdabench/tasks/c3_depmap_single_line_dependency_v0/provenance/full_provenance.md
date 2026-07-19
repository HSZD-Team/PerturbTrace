# DepMap / Project Achilles genome-scale CRISPR dependency screens

- source_id: `S09_depmap_achilles`
- input_table: `BDAbench/data_sources/raw_external/S09_depmap_achilles/depmap_26q1_frozen_context_gene_effect.csv`
- normalized_oracle_table: `BDAbench/tasks/c3_depmap_single_line_dependency_v0/hidden/oracle_scores.csv`
- normalized_hit_set: `BDAbench/tasks/c3_depmap_single_line_dependency_v0/hidden/hit_set.npy`
- public_candidate_actions: `BDAbench/tasks/c3_depmap_single_line_dependency_v0/public/candidate_actions.csv`
- matrix_mode: `long`
- context_key: `ACH-000696`
- action_column: `gene`
- score_column: `score`
- score_sign: `negate`
- hit_mode: `top_score_percent`
- hit_percent: `5.0`
- candidate_count_verified: 18513
- hit_count_verified: 926

## Transformation

The source table was normalized to task-local `hidden/oracle_scores.csv` with exactly `action_id,score` columns. Public solver input was emitted separately as `public/candidate_actions.csv`, exposing only action identifiers. Hit labels are stored only in `hidden/hit_set.npy`.

## Source Provenance

project_url: https://depmap.org/portal/download/all/
source_note: Official DepMap download portal; freeze release before use.


## Raw Manifest

schema_version: 0.1
source_id: S09_depmap_achilles
download_status: verified
downloaded_at: null
downloaded_by: null
source_url: https://depmap.org/portal/api/download/files
source_note: BioDiscoveryAgent also references a Figshare Achilles feature CSV at
  https://figshare.com/ndownloader/files/49843176 for gene-search similarity. That
  file is an auxiliary feature matrix, not the hidden oracle dependency score table
  unless a source-specific audit proves an action-score column.
source_release: DepMap Public 26Q1; release_date=2026-04-01
license_or_terms: public DepMap portal download file index; retain release and hidden
  context in judge-only provenance
raw_files:
- path: BDAbench/data_sources/raw_external/S09_depmap_achilles/CRISPRGeneEffect_26Q1.csv
  description: DepMap Public 26Q1 CRISPRGeneEffect.csv from DepMap portal download
    file index
  sha256: e610a4cefb13a82b5b256b47eb08b63ff14843f8dbd0fb164bc0a32688e5b89e
  md5: e4f75f92348388459c91401d20a9724e
  size_bytes: 440646050
- path: BDAbench/data_sources/raw_external/S09_depmap_achilles/depmap_26q1_frozen_context_gene_effect.csv
  description: DepMap Public 26Q1 CRISPRGeneEffect gene-score table extracted for
    frozen hidden context ACH-000696
  sha256: d40caf07443a3c3d57d6293513a62f248e56601a929c44127be19084f0e636af
  size_bytes: 497615
normalization_plan:
  matrix_mode: long
  action_column: gene
  score_column: score
  context_key: ACH-000696
  score_sign: negate
  hit_mode: top_score_percent
  hit_percent: 5.0
  command: .\BioDiscoveryAgent_repo\.venv\Scripts\python.exe .\BDAbench\data_sources\normalize_action_score_table.py
    --source-id S09_depmap_achilles --input-table .\BDAbench\data_sources\raw_external\S09_depmap_achilles\depmap_26q1_frozen_context_gene_effect.csv
    --matrix-mode long --action-column gene --score-column score --context-key ACH-000696
    --score-sign negate --hit-mode top_score_percent --hit-percent 5 --batch-size
    128
leakage_boundary:
  hide_from_solver:
  - source_url
  - source_release
  - raw_files
  - context_key
  - full score table
notes: Frozen context ACH-000696 was selected by maximum non-null coverage in the
  26Q1 CRISPRGeneEffect matrix. Gene-effect scores are negated for benchmark reward
  so stronger dependency becomes higher score. Solver prompts must not expose the
  cell-line/context ID, release handle, or raw matrix names.
