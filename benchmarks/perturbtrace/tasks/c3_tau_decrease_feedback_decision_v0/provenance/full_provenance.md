# Sanchez21 tau-lowering directional CRISPR screen

- source_id: `S05_bda_sanchez21_tau_down`
- data_name: `Sanchez21_down`
- original_candidate_table: `BioDiscoveryAgent_repo/datasets/ground_truth_Sanchez21_down.csv`
- original_hit_set: `BioDiscoveryAgent_repo/datasets/topmovers_Sanchez21_down.npy`
- normalized_oracle_table: `PerturbTrace/tasks/c3_tau_decrease_feedback_decision_v0/hidden/oracle_scores.csv`
- normalized_hit_set: `PerturbTrace/tasks/c3_tau_decrease_feedback_decision_v0/hidden/hit_set.npy`
- original_action_column: `Gene`
- original_score_column: `Score`
- original_columns: `Gene, Score`
- original_candidate_row_count: 18469
- candidate_count_verified: 18469
- hit_count_verified: 924
- hidden_hit_rule: top tau-lowering genes or compatibility top absolute effect
- oracle_score_semantics: local Score column

## Transformation

The local BioDiscoveryAgent ground-truth table was normalized to a task-local `hidden/oracle_scores.csv` with exactly `action_id,score` columns. The local top-mover array was normalized to string action identifiers and saved as task-local `hidden/hit_set.npy`. The solver-facing candidate list was emitted separately as `public/candidate_actions.csv` without scores or hit labels.

## Source Provenance

local_artifact: BioDiscoveryAgent_repo/datasets/ground_truth_Sanchez21_down.csv
hit_set: BioDiscoveryAgent_repo/datasets/topmovers_Sanchez21_down.npy
source_note: Directional local variant of S04.
