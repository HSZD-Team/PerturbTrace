# Haney phagocytosis CRISPR knockout screen

- source_id: `S27_haney_phagocytosis_crispr`
- input_table: `BDAbench/data_sources/raw_external/S27_haney_phagocytosis_crispr/haney_orcs_screen1140_phagocytosis_castle.csv`
- normalized_oracle_table: `BDAbench/tasks/c3_phagocytosis_crispr_screen_v0/hidden/oracle_scores.csv`
- normalized_hit_set: `BDAbench/tasks/c3_phagocytosis_crispr_screen_v0/hidden/hit_set.npy`
- public_candidate_actions: `BDAbench/tasks/c3_phagocytosis_crispr_screen_v0/public/candidate_actions.csv`
- matrix_mode: `long`
- context_key: `BioGRID_ORCS_Screen_1140_Haney_phagocytosis_CasTLE`
- action_column: `gene`
- score_column: `score`
- hit_column: `hit_value`
- score_sign: `as_is`
- hit_mode: `threshold_gt`
- hit_percent: `5.0`
- hit_threshold: `21.2`
- candidate_count_verified: 20398
- hit_count_verified: 260

## Transformation

The source table was normalized to task-local `hidden/oracle_scores.csv` with exactly `action_id,score` columns. Public solver input was emitted separately as `public/candidate_actions.csv`, exposing only action identifiers. Hit labels are stored only in `hidden/hit_set.npy`.

## Source Provenance

primary_paper: Haney et al., Nature Genetics 2018, genome-wide CRISPR screens for
  regulators of phagocytosis.
public_database: BioGRID ORCS 2.0.18 Screen 1140.


## Raw Manifest

schema_version: 0.1
source_id: S27_haney_phagocytosis_crispr
download_status: verified
downloaded_at: '2026-06-11'
downloaded_by: Codex
source_url: https://downloads.thebiogrid.org/Download/BioGRID-ORCS/Latest-Release/BIOGRID-ORCS-ALL-homo_sapiens-LATEST.screens.tar.gz
source_release: BioGRID ORCS 2.0.18 static human screens archive; selected screen
  tab file and screen index extracted streamingly
license_or_terms: BioGRID ORCS download page states BioGRID ORCS data are freely available
  without warranty; cite original contributing authors and BioGRID as applicable
raw_files:
- path: BDAbench/data_sources/raw_external/S27_haney_phagocytosis_crispr/BIOGRID-ORCS-SCREEN_1140-2.0.18.screen.tab.txt
  description: BioGRID ORCS static full-size screen table BIOGRID-ORCS-SCREEN_1140-2.0.18.screen.tab.txt
  sha256: 61b4555d88f5da13ea13e979f6c97dfe177589593d36b70537f74775f082bdf5
  size_bytes: 2124431
- path: BDAbench/data_sources/raw_external/S27_haney_phagocytosis_crispr/BIOGRID-ORCS-SCREEN_INDEX-2.0.18.index.tab.txt
  description: BioGRID ORCS 2.0.18 human screen index used to verify full-size availability
    and score semantics
  sha256: 6754e87ef758a3525ab7d690b183338f2ee6de72a36dde6e85fe19dee165f02d
  size_bytes: 1328911
- path: BDAbench/data_sources/raw_external/S27_haney_phagocytosis_crispr/haney_orcs_screen1140_phagocytosis_castle.csv
  description: Derived BioGRID ORCS Screen 1140 gene-level score table from SCORE.1
  sha256: 1c8292902d92d0dc617a998ade033a826d240addd2581aec0b5c55d8334291ae
  size_bytes: 496696
- path: BDAbench/data_sources/raw_external/S27_haney_phagocytosis_crispr/haney_orcs_screen1140_metadata.json
  description: Projection metadata for BioGRID ORCS Screen 1140 static table normalization
  sha256: 42fd72ad924db246b42ab54f1519c4e3577928702e342f63835896625394cde3
  size_bytes: 694
normalization_plan:
  matrix_mode: long
  action_column: gene
  score_column: score
  hit_column: hit_value
  context_key: BioGRID_ORCS_Screen_1140_Haney_phagocytosis_CasTLE
  score_sign: as_is
  hit_mode: threshold_gt
  hit_percent: null
  hit_threshold: 21.2
  command: python .\BDAbench\data_sources\prepare_orcs_static_screen_task_table.py
    --source-id S27_haney_phagocytosis_crispr --screen-file .\BDAbench\data_sources\raw_external\S27_haney_phagocytosis_crispr\BIOGRID-ORCS-SCREEN_1140-2.0.18.screen.tab.txt
    --output-csv .\BDAbench\data_sources\raw_external\S27_haney_phagocytosis_crispr\haney_orcs_screen1140_phagocytosis_castle.csv
    --metadata-json .\BDAbench\data_sources\raw_external\S27_haney_phagocytosis_crispr\haney_orcs_screen1140_metadata.json
    --score-column SCORE.1 --hit-column SCORE.1 --score-aggregation max --hit-aggregation
    max; python .\BDAbench\data_sources\normalize_action_score_table.py --source-id
    S27_haney_phagocytosis_crispr --input-table .\BDAbench\data_sources\raw_external\S27_haney_phagocytosis_crispr\haney_orcs_screen1140_phagocytosis_castle.csv
    --task-id C3_phagocytosis_crispr_screen_v0 --matrix-mode long --action-column
    gene --score-column score --hit-column hit_value --context-key BioGRID_ORCS_Screen_1140_Haney_phagocytosis_CasTLE
    --score-sign as_is --hit-mode threshold_gt --hit-threshold 21.2 --batch-size 128
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
notes: Initial static ORCS full-size screen extraction complete; derived task table
  contains 20,398 unique gene actions after collapsing 108 duplicated symbols from
  the 20,506-row screen table. The hidden reward is the CasTLE score from SCORE.1.
  Hidden hits use CasTLE score > 21.2, matching the BioGRID ORCS index significance
  criterion for Screen 1140. Public solver materials hide the source identity, screen
  id, raw table, score threshold, full score table, and global ranks.
