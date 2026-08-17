# Carnevale22 adenosine-condition engineered T-cell screen

- source_id: `S03_bda_carnevale22_adenosine`
- data_name: `Carnevale22_Adenosine`
- original_candidate_table: `BioDiscoveryAgent_repo/datasets/ground_truth_Carnevale22_Adenosine.csv`
- original_hit_set: `BioDiscoveryAgent_repo/datasets/topmovers_Carnevale22_Adenosine.npy`
- normalized_oracle_table: `PerturbTrace/tasks/c3_cart_adenosine_feedback_decision_v0/hidden/oracle_scores.csv`
- normalized_hit_set: `PerturbTrace/tasks/c3_cart_adenosine_feedback_decision_v0/hidden/hit_set.npy`
- original_action_column: `Gene`
- original_score_column: `Score`
- original_columns: `Gene, Score`
- original_candidate_row_count: 18861
- candidate_count_verified: 18861
- hit_count_verified: 943
- hidden_hit_rule: freeze as directional efficacy boost or absolute effect before formal runs
- oracle_score_semantics: local Score column

## Transformation

The local BioDiscoveryAgent ground-truth table was normalized to a task-local `hidden/oracle_scores.csv` with exactly `action_id,score` columns. The local top-mover array was normalized to string action identifiers and saved as task-local `hidden/hit_set.npy`. The solver-facing candidate list was emitted separately as `public/candidate_actions.csv` without scores or hit labels.

## Source Provenance

local_artifact: BioDiscoveryAgent_repo/datasets/ground_truth_Carnevale22_Adenosine.csv
hit_set: BioDiscoveryAgent_repo/datasets/topmovers_Carnevale22_Adenosine.npy
source_note: BioDiscoveryAgent local dataset and task prompt.
