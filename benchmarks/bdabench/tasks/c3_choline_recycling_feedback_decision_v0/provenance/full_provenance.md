# Scharenberg22 lysosomal choline recycling CRISPR screen

- source_id: `S06_bda_scharenberg22_choline`
- data_name: `Scharenberg22`
- original_candidate_table: `BioDiscoveryAgent_repo/datasets/ground_truth_Scharenberg22.csv`
- original_hit_set: `BioDiscoveryAgent_repo/datasets/topmovers_Scharenberg22.npy`
- normalized_oracle_table: `BDAbench/tasks/c3_choline_recycling_feedback_decision_v0/hidden/oracle_scores.csv`
- normalized_hit_set: `BDAbench/tasks/c3_choline_recycling_feedback_decision_v0/hidden/hit_set.npy`
- original_action_column: `Gene`
- original_score_column: `Score`
- original_columns: `Gene, Score`
- original_candidate_row_count: 1061
- candidate_count_verified: 1055
- hit_count_verified: 53
- hidden_hit_rule: top high score or top absolute score after assay review
- oracle_score_semantics: local Score column

## Transformation

The local BioDiscoveryAgent ground-truth table was normalized to a task-local `hidden/oracle_scores.csv` with exactly `action_id,score` columns. The local top-mover array was normalized to string action identifiers and saved as task-local `hidden/hit_set.npy`. The solver-facing candidate list was emitted separately as `public/candidate_actions.csv` without scores or hit labels.

## Source Provenance

local_artifact: BioDiscoveryAgent_repo/datasets/ground_truth_Scharenberg22.csv
hit_set: BioDiscoveryAgent_repo/datasets/topmovers_Scharenberg22.npy
source_note: BioDiscoveryAgent local dataset and task prompt.
