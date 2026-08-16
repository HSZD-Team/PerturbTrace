# PerturbTrace

Evaluating Feedback Use by AI Co-Scientist Agents in Perturbation Discovery

## What's in this repo

| Name | Path | Description |
|---|---|---|
| PerturbTraceBench | [`benchmarks/bdabench/`](./benchmarks/bdabench/) | benchmark test cases |
| PerturbTrace Framework | [`Chef_Harness/`](./Chef_Harness/) | local launcher harness |

![PerturbTrace Framework](./Chef_Harness/docs/chef_harness_architecture.png)

## PerturbTraceBench

| Task | Screen | Action |
|---|---|---|
| [`c3_il2_feedback_decision_v0`](./benchmarks/bdabench/tasks/c3_il2_feedback_decision_v0/public_task_brief.md) | Primary T-cell IL2 | gene |
| [`c3_ifng_feedback_decision_v0`](./benchmarks/bdabench/tasks/c3_ifng_feedback_decision_v0/public_task_brief.md) | Primary T-cell IFNG | gene |
| [`c3_cart_adenosine_feedback_decision_v0`](./benchmarks/bdabench/tasks/c3_cart_adenosine_feedback_decision_v0/public_task_brief.md) | CAR-T adenosine | gene |
| [`c3_cart_crispra_exhaustion_feedback_decision_v0`](./benchmarks/bdabench/tasks/c3_cart_crispra_exhaustion_feedback_decision_v0/public_task_brief.md) | CAR-T CRISPRa exhaustion | gene activation |
| [`c3_cart_exposure_resistance_crispr_screen_v0`](./benchmarks/bdabench/tasks/c3_cart_exposure_resistance_crispr_screen_v0/public_task_brief.md) | CAR-T exposure (HuPT3) | gene |
| [`c3_cart_exposure_resistance_kp4_crispr_screen_v0`](./benchmarks/bdabench/tasks/c3_cart_exposure_resistance_kp4_crispr_screen_v0/public_task_brief.md) | CAR-T exposure (KP4) | gene |
| [`c3_choline_recycling_feedback_decision_v0`](./benchmarks/bdabench/tasks/c3_choline_recycling_feedback_decision_v0/public_task_brief.md) | Lysosomal choline recycling | gene |
| [`c3_tau_absolute_feedback_decision_v0`](./benchmarks/bdabench/tasks/c3_tau_absolute_feedback_decision_v0/public_task_brief.md) | Endogenous tau | gene |
| [`c3_tau_decrease_feedback_decision_v0`](./benchmarks/bdabench/tasks/c3_tau_decrease_feedback_decision_v0/public_task_brief.md) | Tau-lowering | gene |
| [`c3_primary_tcell_function_screen_v0`](./benchmarks/bdabench/tasks/c3_primary_tcell_function_screen_v0/public_task_brief.md) | Primary T-cell function | gene |
| [`c3_nk_cell_exposure_crispr_v0`](./benchmarks/bdabench/tasks/c3_nk_cell_exposure_crispr_v0/public_task_brief.md) | NK-cell exposure | gene |
| [`c3_phagocytosis_crispr_screen_v0`](./benchmarks/bdabench/tasks/c3_phagocytosis_crispr_screen_v0/public_task_brief.md) | Phagocytosis | gene |
| [`c3_crispr_selection_human_cells_v0`](./benchmarks/bdabench/tasks/c3_crispr_selection_human_cells_v0/public_task_brief.md) | CRISPR selection in human cells | gene |
| [`c3_depmap_single_line_dependency_v0`](./benchmarks/bdabench/tasks/c3_depmap_single_line_dependency_v0/public_task_brief.md) | DepMap / Achilles dependency | gene |
| [`c3_project_drive_dependency_v0`](./benchmarks/bdabench/tasks/c3_project_drive_dependency_v0/public_task_brief.md) | Project DRIVE RNAi dependency | gene |
| [`c3_gdsc_drug_response_v0`](./benchmarks/bdabench/tasks/c3_gdsc_drug_response_v0/public_task_brief.md) | GDSC drug response | drug |
| [`c3_cell_painting_morphology_v0`](./benchmarks/bdabench/tasks/c3_cell_painting_morphology_v0/public_task_brief.md) | JUMP Cell Painting morphology | compound or gene |

## Chef_Harness

Install: [`Chef_Harness/README.md`](./Chef_Harness/README.md).

Demo:

https://github.com/user-attachments/assets/74e4251f-cae6-4e14-bbf7-c236d2bef658

## License

[MIT](./LICENSE)
