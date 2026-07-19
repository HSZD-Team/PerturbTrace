# Genomics of Drug Sensitivity in Cancer drug response screens

- source_id: `S14_gdsc`
- input_table: `BDAbench/data_sources/raw_external/S14_gdsc/gdsc2_sidm00136_drug_auc.csv`
- normalized_oracle_table: `BDAbench/tasks/c3_gdsc_drug_response_v0/hidden/oracle_scores.csv`
- normalized_hit_set: `BDAbench/tasks/c3_gdsc_drug_response_v0/hidden/hit_set.npy`
- public_candidate_actions: `BDAbench/tasks/c3_gdsc_drug_response_v0/public/candidate_actions.csv`
- matrix_mode: `long`
- context_key: `SIDM00136`
- action_column: `drug`
- score_column: `score`
- score_sign: `negate`
- hit_mode: `top_score_percent`
- hit_percent: `5.0`
- candidate_count_verified: 286
- hit_count_verified: 15

## Transformation

The source table was normalized to task-local `hidden/oracle_scores.csv` with exactly `action_id,score` columns. Public solver input was emitted separately as `public/candidate_actions.csv`, exposing only action identifiers. Hit labels are stored only in `hidden/hit_set.npy`.

## Source Provenance

primary_paper: Iorio et al., Cell 2016, pharmacogenomic interactions in cancer.
source_note: GDSC download resource.


## Raw Manifest

schema_version: 0.1
source_id: S14_gdsc
download_status: verified
downloaded_at: null
downloaded_by: null
source_url: https://cog.sanger.ac.uk/cancerrxgene/GDSC_release8.5/GDSC2_fitted_dose_response_27Oct23.xlsx
source_note: GDSC downloads; freeze release and response metric before normalization.
source_release: GDSC release 8.5, GDSC2 fitted dose-response 27Oct23
license_or_terms: public GDSC download page; retain original source URL and release
  in judge-only provenance
raw_files:
- path: BDAbench/data_sources/raw_external/S14_gdsc/gdsc2_sidm00136_drug_auc.csv
  description: GDSC2 release 8.5 public drug AUC table extracted for frozen hidden
    context SIDM00136
  sha256: 5c1da3f705c88d5583bbdd23656e3c9e36c11943aaf964fc56b43c04e57e3577
  size_bytes: 5763
- path: BDAbench/data_sources/raw_external/S14_gdsc/GDSC2_fitted_dose_response_27Oct23.xlsx
  description: GDSC release 8.5 GDSC2 fitted dose-response xlsx from official bulk
    download
  sha256: f950a7027be265f8a7a74220a27fd18cbd368485349bd8c2048e88bb1cd07560
  size_bytes: 21330376
normalization_plan:
  matrix_mode: long
  action_column: drug
  score_column: score
  context_key: SIDM00136
  score_sign: negate
  hit_mode: top_score_percent
  hit_percent: 5.0
  command: .\BioDiscoveryAgent_repo\.venv\Scripts\python.exe .\BDAbench\data_sources\normalize_action_score_table.py
    --source-id S14_gdsc --input-table .\BDAbench\data_sources\raw_external\S14_gdsc\gdsc2_sidm00136_drug_auc.csv
    --matrix-mode long --action-column drug --score-column score --score-sign negate
    --hit-mode top_score_percent --hit-percent 5 --batch-size 32
leakage_boundary:
  hide_from_solver:
  - source_url
  - source_release
  - raw_files
  - context_key
  - full score table
notes: Frozen context SIDM00136 was selected because it has the maximum public GDSC2
  release 8.5 drug-response coverage in the downloaded table; solver prompts must
  not expose the cell-line or source identifiers.
## Review Update 2026-06-15

- Score definition changed from negated raw AUC to 该细胞系相对该药物全细胞系分布的敏感性z-score.
- Formula: `(mean AUC for the same drug across public GDSC cell lines - hidden-cell AUC) / drug AUC standard deviation`.
- Positive scores mean the hidden cell line is more sensitive than the all-cell-line distribution for that drug.
- Derived input table: `BDAbench/data_sources/raw_external/S14_gdsc/gdsc2_sidm00136_drug_sensitivity_zscore.csv`.
- Candidate count: 286; top 5 percent hits: 15.
