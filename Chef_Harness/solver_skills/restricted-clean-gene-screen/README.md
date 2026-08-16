# restricted-clean-gene-screen

Solver-facing strategy skill for BDAbench decoupled harness (`init-run --skill`).

This is **not** the `/bda` monitor skill. Monitor skill lives at `skills/bda/`.

## Verify locally

From `PerturbTrace/benchmarks/bdabench`:

```bash
PYTHONPATH=. python -m BDAbench.baselines.harness.cli init-run \
  --run-id smoke_solver_skill_001 \
  --strategy-version restricted_clean_gene_screen_v1 \
  --task-profile tasks/c3_cart_crispra_exhaustion_feedback_decision_v0/task_manifest.yaml \
  --skill /ABS/PATH/to/PerturbTrace/Chef_Harness/solver_skills/restricted-clean-gene-screen \
  --output-dir baselines/harness_runs/solver_skill_smoke \
  --feedback-policy true_feedback
```

Expect:

- printed `run_root`
- `skill_audit.json` with `"clean": true`
- after `prepare-round`, strategy text appears under `# Strategy` in `round_1/initial_prompt.txt`

## Use with `/bda` in Codex

Chinese:

```text
$bda 用 decoupled harness 演示一个 1-run 实际评测流程。
task 选 c3_cart_crispra_exhaustion_feedback_decision_v0。
monitor 必须用本地 shell 调用 python -m BDAbench.baselines.harness.cli。
solver 用 Codex 新线程，模型 gpt-5.5，reasoning xhigh；solver 不使用项目；solver 不要用 codex exec 启动。
solver_skill=/ABS/PATH/to/PerturbTrace/Chef_Harness/solver_skills/restricted-clean-gene-screen
允许 finalize --allow-incomplete（完成第 1 轮即可）。
跑完后回报 run_root 与 RUN_SUMMARY 摘要。
```

English:

```text
$bda Use the decoupled harness to demonstrate a real 1-run evaluation.
Task: c3_cart_crispra_exhaustion_feedback_decision_v0.
Monitor must use local shell to run: python -m BDAbench.baselines.harness.cli ...
Solver: open a new Codex thread, model gpt-5.5, reasoning xhigh; solver must not use a project; do not launch solver via codex exec.
solver_skill=/ABS/PATH/to/PerturbTrace/Chef_Harness/solver_skills/restricted-clean-gene-screen
Allow finalize --allow-incomplete (finishing round 1 is enough).
When done, report run_root and a RUN_SUMMARY summary.
```
