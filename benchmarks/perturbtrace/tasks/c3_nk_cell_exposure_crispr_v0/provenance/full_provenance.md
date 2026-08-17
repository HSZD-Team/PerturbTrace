# Zhuang NK-cell exposure CRISPR knockout screen

- source_id: `S26_zhuang_nk_cell_crispr`
- input_table: `PerturbTrace/data_sources/raw_external/S26_zhuang_nk_cell_crispr/zhuang_orcs_screen1081_nk_cell_mageck.csv`
- normalized_oracle_table: `PerturbTrace/tasks/c3_nk_cell_exposure_crispr_v0/hidden/oracle_scores.csv`
- normalized_hit_set: `PerturbTrace/tasks/c3_nk_cell_exposure_crispr_v0/hidden/hit_set.npy`
- public_candidate_actions: `PerturbTrace/tasks/c3_nk_cell_exposure_crispr_v0/public/candidate_actions.csv`
- matrix_mode: `long`
- context_key: `BioGRID_ORCS_Screen_1081_Zhuang_NK_cell_exposure_MaGeCK`
- action_column: `gene`
- score_column: `score`
- hit_column: `hit_value`
- score_sign: `as_is`
- hit_mode: `threshold_lt`
- hit_percent: `5.0`
- hit_threshold: `0.05`
- candidate_count_verified: 20617
- hit_count_verified: 5792

## Transformation

The source table was normalized to task-local `hidden/oracle_scores.csv` with exactly `action_id,score` columns. Public solver input was emitted separately as `public/candidate_actions.csv`, exposing only action identifiers. Hit labels are stored only in `hidden/hit_set.npy`.

## Source Provenance

primary_paper: Zhuang et al., Nature Communications 2019, genome-wide CRISPR screen
  of cancer-cell response to natural killer cells.
public_database: BioGRID ORCS 2.0.18 Screen 1081.


## Raw Manifest

schema_version: 0.1
source_id: S26_zhuang_nk_cell_crispr
download_status: verified
downloaded_at: '2026-06-11'
downloaded_by: Codex
source_url: https://downloads.thebiogrid.org/Download/BioGRID-ORCS/Latest-Release/BIOGRID-ORCS-ALL-homo_sapiens-LATEST.screens.tar.gz
source_release: BioGRID ORCS 2.0.18 static human screens archive; selected screen
  tab file and screen index extracted streamingly
license_or_terms: BioGRID ORCS download page states BioGRID ORCS data are freely available
  without warranty; cite original contributing authors and BioGRID as applicable
raw_files:
- path: PerturbTrace/data_sources/raw_external/S26_zhuang_nk_cell_crispr/BIOGRID-ORCS-SCREEN_1081-2.0.18.screen.tab.txt
  description: BioGRID ORCS static full-size screen table BIOGRID-ORCS-SCREEN_1081-2.0.18.screen.tab.txt
  sha256: dbac87b3d833289ac0253e08ead0da6ca16765092b54575c6e98d6c92a57135c
  size_bytes: 2329906
- path: PerturbTrace/data_sources/raw_external/S26_zhuang_nk_cell_crispr/BIOGRID-ORCS-SCREEN_INDEX-2.0.18.index.tab.txt
  description: BioGRID ORCS 2.0.18 human screen index used to verify full-size availability
    and score semantics
  sha256: 6754e87ef758a3525ab7d690b183338f2ee6de72a36dde6e85fe19dee165f02d
  size_bytes: 1328911
- path: PerturbTrace/data_sources/raw_external/S26_zhuang_nk_cell_crispr/zhuang_orcs_screen1081_nk_cell_mageck.csv
  description: Derived BioGRID ORCS Screen 1081 gene-level score table from SCORE.1
  sha256: d873ff03e6b01a00f2001863dc600c12b462ab61d6d451f4b20847c58dd7b49c
  size_bytes: 613380
- path: PerturbTrace/data_sources/raw_external/S26_zhuang_nk_cell_crispr/zhuang_orcs_screen1081_metadata.json
  description: Projection metadata for BioGRID ORCS Screen 1081 static table normalization
  sha256: 3cc695c973ed526fbbbd35ad7cfe739afb011f92b36abf432ff649400f2a480a
  size_bytes: 679
normalization_plan:
  matrix_mode: long
  action_column: gene
  score_column: score
  hit_column: hit_value
  context_key: BioGRID_ORCS_Screen_1081_Zhuang_NK_cell_exposure_MaGeCK
  score_sign: as_is
  hit_mode: threshold_lt
  hit_percent: null
  hit_threshold: 0.05
  command: python .\PerturbTrace\data_sources\prepare_orcs_static_screen_task_table.py
    --source-id S26_zhuang_nk_cell_crispr --screen-file .\PerturbTrace\data_sources\raw_external\S26_zhuang_nk_cell_crispr\BIOGRID-ORCS-SCREEN_1081-2.0.18.screen.tab.txt
    --output-csv .\PerturbTrace\data_sources\raw_external\S26_zhuang_nk_cell_crispr\zhuang_orcs_screen1081_nk_cell_mageck.csv
    --metadata-json .\PerturbTrace\data_sources\raw_external\S26_zhuang_nk_cell_crispr\zhuang_orcs_screen1081_metadata.json
    --score-column SCORE.1 --hit-column SCORE.2 --score-aggregation mean --hit-aggregation
    min; python .\PerturbTrace\data_sources\normalize_action_score_table.py --source-id
    S26_zhuang_nk_cell_crispr --input-table .\PerturbTrace\data_sources\raw_external\S26_zhuang_nk_cell_crispr\zhuang_orcs_screen1081_nk_cell_mageck.csv
    --task-id C3_nk_cell_exposure_crispr_v0 --matrix-mode long --action-column gene
    --score-column score --hit-column hit_value --context-key BioGRID_ORCS_Screen_1081_Zhuang_NK_cell_exposure_MaGeCK
    --score-sign as_is --hit-mode threshold_lt --hit-threshold 0.05 --batch-size 128
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
  contains 20,617 unique gene actions after collapsing 80 duplicated symbols from
  the 20,697-row screen table. The hidden reward is the MaGeCK beta score from SCORE.1.
  Hidden hits use the screen p-value from SCORE.2 with p < 0.05, matching the BioGRID
  ORCS index significance criterion for Screen 1081. Public solver materials hide
  the source identity, screen id, raw table, p-value threshold, full score table,
  and global ranks.
## Review Update 2026-06-15

- Review decision: benchmark keeps only the sensitive direction for S26.
- Hidden hits were recomputed as the top 5 percent by lowest MaGeCK beta score.
- Resistance-direction hits are intentionally not mixed into this task.
- Candidate count: 20617; sensitive-direction top hits: 1031.
