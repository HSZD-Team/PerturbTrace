# Steinhart CRISPRa GD2 CAR-T exhaustion-resistance screen

- source_id: `S07_bda_steinhart_crispra_gd2_d22`
- data_name: `Steinhart_crispra_GD2_D22`
- original_candidate_table: `BioDiscoveryAgent_repo/datasets/ground_truth_Steinhart_crispra_GD2_D22.csv`
- original_hit_set: `BioDiscoveryAgent_repo/datasets/topmovers_Steinhart_crispra_GD2_D22.npy`
- normalized_oracle_table: `PerturbTrace/tasks/c3_cart_crispra_exhaustion_feedback_decision_v0/hidden/oracle_scores.csv`
- normalized_hit_set: `PerturbTrace/tasks/c3_cart_crispra_exhaustion_feedback_decision_v0/hidden/hit_set.npy`
- original_action_column: `0`
- original_score_column: `1`
- original_columns: `0, 1`
- original_candidate_row_count: 18797
- candidate_count_verified: 18797
- hit_count_verified: 149
- hidden_hit_rule: top positive resistance/exhaustion-rescue score
- oracle_score_semantics: local second column in local CSV

## Transformation

The local BioDiscoveryAgent ground-truth table was normalized to a task-local `hidden/oracle_scores.csv` with exactly `action_id,score` columns. The local top-mover array was normalized to string action identifiers and saved as task-local `hidden/hit_set.npy`. The solver-facing candidate list was emitted separately as `public/candidate_actions.csv` without scores or hit labels.

## Source Provenance

local_artifact: BioDiscoveryAgent_repo/datasets/ground_truth_Steinhart_crispra_GD2_D22.csv
hit_set: BioDiscoveryAgent_repo/datasets/topmovers_Steinhart_crispra_GD2_D22.npy
source_note: BioDiscoveryAgent local dataset and task prompt.
