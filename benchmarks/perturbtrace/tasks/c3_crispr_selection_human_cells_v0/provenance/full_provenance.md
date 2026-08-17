# Wang genetic screens in human cells using CRISPR-Cas9

- source_id: `S28_wang_crispr_human_cells`
- input_table: `PerturbTrace/data_sources/raw_external/S28_wang_crispr_human_cells/wang_kbm7_crispr_survival_gene_scores.csv`
- normalized_oracle_table: `PerturbTrace/tasks/c3_crispr_selection_human_cells_v0/hidden/oracle_scores.csv`
- normalized_hit_set: `PerturbTrace/tasks/c3_crispr_selection_human_cells_v0/hidden/hit_set.npy`
- public_candidate_actions: `PerturbTrace/tasks/c3_crispr_selection_human_cells_v0/public/candidate_actions.csv`
- matrix_mode: `long`
- context_key: `BioGRID_ORCS_Wang2014_KBM7_CRISPR_survival_gene_score`
- action_column: `gene`
- score_column: `score`
- hit_column: `hit_value`
- score_sign: `as_is`
- hit_mode: `threshold_gt`
- hit_percent: `5.0`
- hit_threshold: `1.30103`
- candidate_count_verified: 7114
- hit_count_verified: 321

## Transformation

The source table was normalized to task-local `hidden/oracle_scores.csv` with exactly `action_id,score` columns. Public solver input was emitted separately as `public/candidate_actions.csv`, exposing only action identifiers. Hit labels are stored only in `hidden/hit_set.npy`.

## Source Provenance

primary_paper: Wang et al., Science 2014, genetic screens in human cells using CRISPR-Cas9.


## Raw Manifest

schema_version: 0.1
source_id: S28_wang_crispr_human_cells
downloaded_at: '2026-06-10'
downloaded_by: Codex
source_release: BioGRID ORCS publication Dataset 1; Wang et al. Science 2014 supplementary
  tables for PMID24336569
license_or_terms: BioGRID ORCS page declares MIT License for this processed publication
  metadata/distribution
normalization_plan:
  command: python PerturbTrace/data_sources/prepare_wang_crispr_task_table.py --input-xlsx
    PerturbTrace/data_sources/raw_external/S28_wang_crispr_human_cells/24336569_S_Table_4.xlsx
    --output-csv PerturbTrace/data_sources/raw_external/S28_wang_crispr_human_cells/wang_kbm7_crispr_survival_gene_scores.csv
    --context KBM7
  matrix_mode: long
  action_column: gene
  score_column: score
  hit_column: hit_value
  score_sign: as_is
  hit_mode: threshold_gt
  hit_percent: null
  hit_threshold: 1.30103
  context_key: BioGRID_ORCS_Wang2014_KBM7_CRISPR_survival_gene_score
leakage_boundary:
  hide_from_solver:
  - source_url
  - source_release
  - raw_files
  - context_key
  - selected cell context
  - source table name
  - full score table
  - hit threshold
download_status: verified
source_url: https://orcs.thebiogrid.org/uploads/processed/5942c003b8b3f/24336569%20S%20Table%204.xlsx
raw_files:
- path: PerturbTrace/data_sources/raw_external/S28_wang_crispr_human_cells/24336569_S_Table_2.xlsx
  description: Wang et al. Science 2014 supplementary table 2 from BioGRID ORCS publication
    page
  sha256: baab9d54353fdab99195910937781976296fbb181a8cb1f575cdb7ec84f6c7e5
  size_bytes: 243476
- path: PerturbTrace/data_sources/raw_external/S28_wang_crispr_human_cells/24336569_S_Table_4.xlsx
  description: Wang et al. Science 2014 supplementary table 4 from BioGRID ORCS publication
    page
  sha256: dc3a8ba751bcab545385f06d0ab049e20bb757c37f7431974116027712b161b5
  size_bytes: 716235
- path: PerturbTrace/data_sources/raw_external/S28_wang_crispr_human_cells/wang_kbm7_crispr_survival_gene_scores.csv
  description: Derived Wang 2014 KBM7 CRISPR survival screen gene-level score table;
    score=-source gene score
  sha256: 6ea2415619c3a8821eac8ad89903bbe17ede61f64bc09cffaf32d0a55df44775
  size_bytes: 447212
notes: Table 4 contains 7,114 unique gene-level survival screen rows with source gene
  scores and corrected p-values for two cell contexts. The benchmark freezes the KBM7
  context as judge-only; reward is -source gene score because more negative source
  gene scores indicate stronger dropout/depletion. Hidden hits use corrected p < 0.05,
  represented as -log10(corrected p-value) > 1.30103.
