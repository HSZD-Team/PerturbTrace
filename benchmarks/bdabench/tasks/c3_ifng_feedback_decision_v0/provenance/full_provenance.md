# Schmidt-family primary T-cell IFNG perturbation screen

- source_id: `S01_bda_schmidt_ifng`
- data_name: `IFNG`
- original_candidate_table: `BioDiscoveryAgent_repo/datasets/ground_truth_IFNG.csv`
- original_hit_set: `BioDiscoveryAgent_repo/datasets/topmovers_IFNG.npy`
- normalized_oracle_table: `BDAbench/tasks/c3_ifng_feedback_decision_v0/hidden/oracle_scores.csv`
- normalized_hit_set: `BDAbench/tasks/c3_ifng_feedback_decision_v0/hidden/hit_set.npy`
- original_action_column: `Gene`
- original_score_column: `Score`
- original_columns: `Gene, Score`
- original_candidate_row_count: 18418
- candidate_count_verified: 18418
- hit_count_verified: 920
- hidden_hit_rule: top 5 percent by absolute score
- oracle_score_semantics: signed log-fold-change from local Score column

## Transformation

The local BioDiscoveryAgent ground-truth table was normalized to a task-local `hidden/oracle_scores.csv` with exactly `action_id,score` columns. The local top-mover array was normalized to string action identifiers and saved as task-local `hidden/hit_set.npy`. The solver-facing candidate list was emitted separately as `public/candidate_actions.csv` without scores or hit labels.

## Source Provenance

local_artifact: BioDiscoveryAgent_repo/datasets/ground_truth_IFNG.csv
hit_set: BioDiscoveryAgent_repo/datasets/topmovers_IFNG.npy
source_note: BioDiscoveryAgent_repo/data/README.md points to Science DOI 10.1126/science.abj4008
