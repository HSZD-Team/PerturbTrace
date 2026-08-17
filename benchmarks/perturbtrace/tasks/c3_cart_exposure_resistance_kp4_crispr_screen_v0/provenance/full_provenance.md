# Hagel KR (2022) BioGRID ORCS Screen 1954 hidden-oracle task

- source_id: `S67_hagel_cart_exposure_kp4_crispr`
- input_table: `PerturbTrace/data_sources/raw_external/S67_hagel_cart_exposure_kp4_crispr/hagel_cart_exposure_kp4_crispr_screen1954_scores.csv`
- normalized_oracle_table: `PerturbTrace/tasks/c3_cart_exposure_resistance_kp4_crispr_screen_v0/hidden/oracle_scores.csv`
- normalized_hit_set: `PerturbTrace/tasks/c3_cart_exposure_resistance_kp4_crispr_screen_v0/hidden/hit_set.npy`
- public_candidate_actions: `PerturbTrace/tasks/c3_cart_exposure_resistance_kp4_crispr_screen_v0/public/candidate_actions.csv`
- matrix_mode: `long`
- context_key: `BioGRID_ORCS_Screen_1954_hagel_cart_exposure_kp4_crispr`
- action_column: `gene`
- score_column: `score`
- hit_column: `hit_value`
- score_sign: `as_is`
- hit_mode: `threshold_gt`
- hit_percent: `5.0`
- hit_threshold: `0.5`
- candidate_count_verified: 20079
- hit_count_verified: 532

## Transformation

The source table was normalized to task-local `hidden/oracle_scores.csv` with exactly `action_id,score` columns. Public solver input was emitted separately as `public/candidate_actions.csv`, exposing only action identifiers. Hit labels are stored only in `hidden/hit_set.npy`.

## Source Provenance

primary_paper_or_source: Hagel KR (2022); source handle 36548402
public_database: BioGRID ORCS 2.0.18 Screen 1954
screen_rationale: Regulation of cancer cell response to immune system
full_size_available: 'Yes'


## Raw Manifest

schema_version: 0.1
source_id: S67_hagel_cart_exposure_kp4_crispr
download_status: verified
downloaded_at: '2026-06-11'
downloaded_by: Codex
source_url: https://downloads.thebiogrid.org/Download/BioGRID-ORCS/Latest-Release/BIOGRID-ORCS-ALL-homo_sapiens-LATEST.screens.tar.gz
source_release: BioGRID ORCS 2.0.18 static human screens archive; selected screen
  tab files and screen index extracted streamingly
license_or_terms: BioGRID ORCS download page states BioGRID ORCS data are freely available
  without warranty; cite original contributing authors and BioGRID as applicable
raw_files:
- path: PerturbTrace/data_sources/raw_external/S67_hagel_cart_exposure_kp4_crispr/BIOGRID-ORCS-SCREEN_INDEX-2.0.18.index.tab.txt
  description: BioGRID ORCS 2.0.18 human screen index used to verify full-size availability
    and score semantics
  sha256: 6754e87ef758a3525ab7d690b183338f2ee6de72a36dde6e85fe19dee165f02d
  size_bytes: 1328911
- path: PerturbTrace/data_sources/raw_external/S67_hagel_cart_exposure_kp4_crispr/BIOGRID-ORCS-SCREEN_1954-2.0.18.screen.tab.txt
  description: BioGRID ORCS static full-size screen table BIOGRID-ORCS-SCREEN_1954-2.0.18.screen.tab.txt
  sha256: ebb1667af2b806d72330f4649098284578dde49108a0cd4d88a479450997da39
  size_bytes: 2274936
- path: PerturbTrace/data_sources/raw_external/S67_hagel_cart_exposure_kp4_crispr/hagel_cart_exposure_kp4_crispr_screen1954_scores.csv
  description: Derived BioGRID ORCS Screen 1954 gene-level score table from SCORE.1
  sha256: ac8ebbb1eb3524fd26bfa8412e55149d6f93f4b5e419147296557c1e70bc316d
  size_bytes: 562416
- path: PerturbTrace/data_sources/raw_external/S67_hagel_cart_exposure_kp4_crispr/hagel_cart_exposure_kp4_crispr_screen1954_metadata.json
  description: Projection metadata for BioGRID ORCS Screen 1954 static table normalization
  sha256: a1973ff6fab4b77b1553eacc5d666be1862c06567fa5f60dedf1e7ace5055c88
  size_bytes: 736
normalization_plan:
  matrix_mode: long
  action_column: gene
  score_column: score
  hit_column: hit_value
  context_key: BioGRID_ORCS_Screen_1954_hagel_cart_exposure_kp4_crispr
  score_sign: as_is
  hit_mode: threshold_gt
  hit_percent: null
  hit_threshold: 0.5
  command: prepare_orcs_static_screen_task_table.py --source-id S67_hagel_cart_exposure_kp4_crispr
    --screen-file BIOGRID-ORCS-SCREEN_1954-2.0.18.screen.tab.txt --score-column SCORE.1
    --hit-from-author; normalize_action_score_table.py --source-id S67_hagel_cart_exposure_kp4_crispr
    --hit-column hit_value --hit-mode threshold_gt --hit-threshold 0.5
leakage_boundary:
  hide_from_solver:
  - source_url
  - source_release
  - raw_files
  - screen_id
  - context_key
  - full score table
  - score_column
  - hit_column
  - hit_threshold
  - global ranks
notes: BioGRID ORCS full-size Screen 1954 selected as an expansion hidden-oracle task;
  public materials hide exact condition and screen identity.
