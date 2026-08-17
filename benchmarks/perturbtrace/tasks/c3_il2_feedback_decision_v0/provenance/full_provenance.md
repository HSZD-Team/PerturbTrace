# Schmidt-family primary T-cell IL2 perturbation screen

- source_id: `S02_bda_schmidt_il2`
- data_name: `IL2`
- original_candidate_table: `BioDiscoveryAgent_repo/datasets/ground_truth_IL2.csv`
- original_hit_set: `BioDiscoveryAgent_repo/datasets/topmovers_IL2.npy`
- normalized_oracle_table: `PerturbTrace/tasks/c3_il2_feedback_decision_v0/hidden/oracle_scores.csv`
- normalized_hit_set: `PerturbTrace/tasks/c3_il2_feedback_decision_v0/hidden/hit_set.npy`
- original_action_column: `Gene`
- original_score_column: `Score`
- original_columns: `Gene, Score`
- original_candidate_row_count: 18939
- candidate_count_verified: 18939
- hit_count_verified: 654
- hidden_hit_rule: top 5 percent by absolute score
- oracle_score_semantics: signed log-fold-change from local Score column

## Transformation

The local BioDiscoveryAgent ground-truth table was normalized to a task-local `hidden/oracle_scores.csv` with exactly `action_id,score` columns. The local top-mover array was normalized to string action identifiers and saved as task-local `hidden/hit_set.npy`. The solver-facing candidate list was emitted separately as `public/candidate_actions.csv` without scores or hit labels.

## Source Provenance

local_artifact: BioDiscoveryAgent_repo/datasets/ground_truth_IL2.csv
hit_set: BioDiscoveryAgent_repo/datasets/topmovers_IL2.npy
source_note: Shares Schmidt-family provenance with S01.
