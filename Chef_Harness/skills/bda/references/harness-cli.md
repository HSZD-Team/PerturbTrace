# BDAbench Decoupled Harness CLI

Run from the portable package root (`Changjie_files/bdabench_decoupled_harness` in this workspace), so the `BDAbench` module resolves.

## Commands

```bash
python -m BDAbench.baselines.harness.cli init-run \
  --run-id <run_id> \
  --strategy-version <strategy_version> \
  --task-profile <task_manifest.yaml> \
  --skill <solver_skill_dir> \
  --output-dir <output_dir> \
  --feedback-policy true_feedback

python -m BDAbench.baselines.harness.cli prepare-round \
  --run-root <run_root> \
  --round-index <0_based>

python -m BDAbench.baselines.harness.cli process-response \
  --run-root <run_root> \
  --round-index <0_based> \
  --raw-response <solver_response.txt>

python -m BDAbench.baselines.harness.cli finalize-run \
  --run-root <run_root>
```

Smoke / incomplete finalize only when explicitly allowed:

```bash
python -m BDAbench.baselines.harness.cli finalize-run \
  --run-root <run_root> \
  --allow-incomplete
```

Always pass `--task-profile`, `--skill`, `--output-dir`, `--strategy-version`, and `--run-id` explicitly for real runs.

## One-run loop

1. `init-run` → print/capture `run_root`
2. `prepare-round --round-index 0`
3. Send to a **fresh** solver thread:
   - `round_1/system_prompt.txt`
   - `round_1/initial_prompt.txt`
4. Save solver output → `process-response`
5. If status is `needs_repair`, send `final_repair_prompt.txt` to the **same** solver thread and `process-response` again
6. Repeat prepare/process for remaining rounds (feedback prompt only after round 0)
7. `finalize-run`
8. Read `<run_root>/RUN_SUMMARY.json`

## Default smoke task in this repo

```text
tasks/c3_cart_crispra_exhaustion_feedback_decision_v0/task_manifest.yaml
```

Task index:

```text
tasks/task_index.yaml
```

## Solver transport notes (monitor-owned)

- Default demo: Codex app/session, model `gpt-5.5`, reasoning `xhigh`
- Open a new thread; do **not** use project context; do **not** use `codex exec`
- Solver sees only harness-generated prompt text
- Write raw solver text to a file before `process-response`
