# Hagel KR (2022) BioGRID ORCS Screen 1953 hidden-oracle task

- source_id: `S66_hagel_cart_exposure_hupt3_crispr`
- input_table: `PerturbTrace/data_sources/raw_external/S66_hagel_cart_exposure_hupt3_crispr/hagel_cart_exposure_hupt3_crispr_screen1953_scores.csv`
- normalized_oracle_table: `PerturbTrace/tasks/c3_cart_exposure_resistance_crispr_screen_v0/hidden/oracle_scores.csv`
- normalized_hit_set: `PerturbTrace/tasks/c3_cart_exposure_resistance_crispr_screen_v0/hidden/hit_set.npy`
- public_candidate_actions: `PerturbTrace/tasks/c3_cart_exposure_resistance_crispr_screen_v0/public/candidate_actions.csv`
- matrix_mode: `long`
- context_key: `BioGRID_ORCS_Screen_1953_hagel_cart_exposure_hupt3_crispr`
- action_column: `gene`
- score_column: `score`
- hit_column: `hit_value`
- score_sign: `as_is`
- hit_mode: `threshold_gt`
- hit_percent: `5.0`
- hit_threshold: `0.5`
- candidate_count_verified: 20079
- hit_count_verified: 884

## Transformation

The source table was normalized to task-local `hidden/oracle_scores.csv` with exactly `action_id,score` columns. Public solver input was emitted separately as `public/candidate_actions.csv`, exposing only action identifiers. Hit labels are stored only in `hidden/hit_set.npy`.

## Source Provenance

primary_paper_or_source: Hagel KR (2022); source handle 36548402
public_database: BioGRID ORCS 2.0.18 Screen 1953
screen_rationale: Regulation of cancer cell response to immune system
full_size_available: 'Yes'


## Raw Manifest

schema_version: 0.1
source_id: S66_hagel_cart_exposure_hupt3_crispr
download_status: verified
downloaded_at: '2026-06-11'
downloaded_by: Codex
source_url: https://downloads.thebiogrid.org/Download/BioGRID-ORCS/Latest-Release/BIOGRID-ORCS-ALL-homo_sapiens-LATEST.screens.tar.gz
source_release: BioGRID ORCS 2.0.18 static human screens archive; selected screen
  tab files and screen index extracted streamingly
license_or_terms: BioGRID ORCS download page states BioGRID ORCS data are freely available
  without warranty; cite original contributing authors and BioGRID as applicable
raw_files:
- path: PerturbTrace/data_sources/raw_external/S66_hagel_cart_exposure_hupt3_crispr/BIOGRID-ORCS-SCREEN_INDEX-2.0.18.index.tab.txt
  description: BioGRID ORCS 2.0.18 human screen index used to verify full-size availability
    and score semantics
  sha256: 6754e87ef758a3525ab7d690b183338f2ee6de72a36dde6e85fe19dee165f02d
  size_bytes: 1328911
- path: PerturbTrace/data_sources/raw_external/S66_hagel_cart_exposure_hupt3_crispr/BIOGRID-ORCS-SCREEN_1953-2.0.18.screen.tab.txt
  description: BioGRID ORCS static full-size screen table BIOGRID-ORCS-SCREEN_1953-2.0.18.screen.tab.txt
  sha256: bb629f85b6741bae8fbef10bf7306cc7c2122e225b597958ac28b410487d1d94
  size_bytes: 2275833
- path: PerturbTrace/data_sources/raw_external/S66_hagel_cart_exposure_hupt3_crispr/hagel_cart_exposure_hupt3_crispr_screen1953_scores.csv
  description: Derived BioGRID ORCS Screen 1953 gene-level score table from SCORE.1
  sha256: 176a38fff5ea18bdc229f73a2c4449a965a2309b062250454c308fb89777088a
  size_bytes: 562524
- path: PerturbTrace/data_sources/raw_external/S66_hagel_cart_exposure_hupt3_crispr/hagel_cart_exposure_hupt3_crispr_screen1953_metadata.json
  description: Projection metadata for BioGRID ORCS Screen 1953 static table normalization
  sha256: 66d3ec72e46797ffe7acbedcc97bba97e5f6c26519c3d76c4861bd67e88b830f
  size_bytes: 744
normalization_plan:
  matrix_mode: long
  action_column: gene
  score_column: score
  hit_column: hit_value
  context_key: BioGRID_ORCS_Screen_1953_hagel_cart_exposure_hupt3_crispr
  score_sign: as_is
  hit_mode: threshold_gt
  hit_percent: null
  hit_threshold: 0.5
  command: prepare_orcs_static_screen_task_table.py --source-id S66_hagel_cart_exposure_hupt3_crispr
    --screen-file BIOGRID-ORCS-SCREEN_1953-2.0.18.screen.tab.txt --score-column SCORE.1
    --hit-from-author; normalize_action_score_table.py --source-id S66_hagel_cart_exposure_hupt3_crispr
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
notes: BioGRID ORCS full-size Screen 1953 selected as an expansion hidden-oracle task;
  public materials hide exact condition and screen identity.
