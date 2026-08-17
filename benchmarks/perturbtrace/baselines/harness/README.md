# Decoupled PerturbTrace Harness

This folder is the canonical handoff surface for running Codex/LLM evaluations against PerturbTrace hidden-oracle tasks.

The repository contains many data-building, analysis, and historical-run scripts. They are not part of the minimal harness. For running an eval, think in terms of one run root, one task manifest, one solver conversation, and one final summary file.

## Minimal Mental Model

The harness has five jobs:

1. Load a task manifest.
2. Build solver-safe prompts.
3. Record solver responses.
4. Validate and submit valid action batches to the hidden oracle.
5. Finalize metrics and write a stable summary.

Only the solver chooses actions. Everything else is deterministic harness logic.

## Main Entrypoint

Use:

```powershell
python -m PerturbTrace.baselines.harness.cli <command> ...
```

Commands:

- `init-run`: create a run root and snapshot the solver skill.
- `prepare-round`: write the next round prompt under the run root.
- `process-response`: record a solver response, run membership validation, request repair if needed, or submit to oracle if complete.
- `prepare-final` and `submit-final`: lower-level draft/final split, kept for explicit judge-mediated flows.
- `finalize-run`: compute metrics, leakage audit, and final summary.

For one-click orchestration, prefer `process-response` over manually calling `prepare-final` plus `submit-final`.

## Runtime Dependencies

This folder intentionally uses shared framework modules instead of duplicating them:

- `PerturbTrace.baselines.framework.profile`: task manifest loader.
- `PerturbTrace.baselines.framework.types`: shared dataclasses.
- `PerturbTrace.baselines.framework.actions`: solver output parser and batch validator.
- `PerturbTrace.baselines.framework.oracle`: hidden oracle scoring.
- `PerturbTrace.baselines.framework.metrics`: metric computation.
- `PerturbTrace.baselines.framework.leakage`: prompt/trace leakage audit.
- `PerturbTrace.baselines.framework.trace`: low-level trace writer.

The eval also needs:

- `tasks/task_index.yaml`
- `tasks/*/task_manifest.yaml`
- each task's `public/`, `hidden/`, and `public_task_brief.md`
- one solver-facing skill directory containing `SKILL.md`

## Canonical Artifact Layout

All output paths are defined by `artifacts.py`.

The run root is:

```text
<output_dir>/<strategy_version>/<run_id>
```

Default output dir:

```text
PerturbTrace/baselines/harness_runs
```

The downstream evaluator should treat `run_root` as the only directory handle.

Root-level files:

```text
harness_config.json       # run config and task profile path
skill_snapshot/SKILL.md   # exact solver-facing skill used in this run
skill_audit.json          # static audit of the skill
trace.jsonl               # event stream
observations.json         # all oracle feedback returned so far
batches.json              # all parsed/submitted batches
membership_checks.json    # all membership checks
metrics.json              # full final metrics
leakage_audit.json        # final leakage audit
RUN_SUMMARY.json          # primary file for final eval aggregation
```

Per-round files:

```text
round_1/system_prompt.txt
round_1/initial_prompt.txt
round_1/solver_response_attempt_1.txt
round_1/membership_check_attempt_1.json
round_1/final_repair_prompt.txt
round_1/observations.json

round_2/feedback_prompt.txt
...
```

## What Final Eval Should Read

For aggregate evaluation, read only:

```text
<run_root>/RUN_SUMMARY.json
```

Use `metrics.json` only when the evaluator needs the complete metric object. Use per-round files only for debugging, auditing, or reproducing a process failure.

`RUN_SUMMARY.json` includes:

- `run_id`
- `strategy_version`
- `task_id`
- `rounds_submitted`
- `expected_rounds`
- `complete`
- `primary_metric`
- `top_effect_recall`
- `precision_at_budget`
- `auc_hdc`
- `round_hit_gain`
- `valid_unique_actions`
- `total_submitted_actions`
- `invalid_action_rate`
- `duplicate_action_rate`
- `parse_failure_count`
- `batch_fill_failure_rate`
- `leakage_label`
- `metrics_path`
- `leakage_audit_path`

## One-Run Flow

```powershell
$runRoot = python -m PerturbTrace.baselines.harness.cli init-run `
  --run-id example_run `
  --strategy-version example_strategy `
  --task-profile PerturbTrace/tasks/c3_gdsc_drug_response_v0/task_manifest.yaml `
  --skill PerturbTrace/skills/restricted-clean-perturbation-strategy

python -m PerturbTrace.baselines.harness.cli prepare-round `
  --run-root $runRoot `
  --round-index 0

# Send round_1/system_prompt.txt + round_1/initial_prompt.txt to the solver.
# Save the solver answer to a response file.

python -m PerturbTrace.baselines.harness.cli process-response `
  --run-root $runRoot `
  --round-index 0 `
  --raw-response path/to/solver_response.txt

# If status is needs_repair, send the returned final_repair_prompt.txt to the
# same solver conversation and call process-response again with the repair output.

python -m PerturbTrace.baselines.harness.cli finalize-run `
  --run-root $runRoot
```

Repeat `prepare-round` and `process-response` until all task rounds are submitted.

## Boundary Rules

- The solver receives only prompt text generated by the harness.
- The solver should not read task manifests, hidden files, harness code, old run directories, or oracle outputs.
- The solver may use general scientific/literature prior if the experiment allows it; this is not encoded as a solver-facing prohibition here.
- The harness owns parser, membership checking, oracle access, feedback clipping, metrics, and trace writing.
- The one-click supervisor should own scheduling, solver transport, retries, and aggregate collection only.

## What Not To Treat As Harness Core

These are useful but not part of the minimal run loop:

- `data_sources/*`: upstream ETL and audit scripts.
- `analysis/*`: report and comparison builders.
- `baselines/runs/*`: historical IFNG run artifacts.
- `baselines/harness_runs/*`: past run outputs and orchestration prototypes.
- `baselines/framework/native.py`: alternate judge-mediated backend, not the canonical decoupled harness path.
