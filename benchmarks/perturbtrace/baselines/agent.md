# Monitor Agent Contract

This file is the monitor-facing entrypoint for launching PerturbTrace Codex/LLM baseline evaluations.

The monitor is a user of the harness. It schedules runs, talks to the solver, handles retries, and aggregates results. It must not reimplement or modify harness-owned logic.

For the harness artifact layout and CLI details, also read:

```text
PerturbTrace/baselines/harness/README.md
```

## Required Baseline Config

The user or upstream controller should give the monitor a config with these fields:

```yaml
baseline_name: restricted_clean_demo
task_index: PerturbTrace/tasks/task_index.yaml
task_profiles:
  - PerturbTrace/tasks/c3_gdsc_drug_response_v0/task_manifest.yaml
skill: <external_solver_skill_dir>
strategy_version: restricted_clean_v1
output_dir: PerturbTrace/baselines/harness_runs/restricted_clean_v1
run_id_prefix: restricted_clean_v1
feedback_policy: true_feedback
solver:
  transport: codex_exec
  model: gpt-5.5
  reasoning_effort: xhigh
  one_continuous_conversation_per_run: true
concurrency: 1
max_repairs_per_round: 6
finalize_allow_incomplete: false
```

`skill` is a solver-facing strategy artifact supplied by the controller or user. This portable harness package does not include a default solver skill. `task_profiles` may be omitted when the monitor should run every manifest listed in `task_index`. For a smoke demo, pass exactly one `task_profile` and set `finalize_allow_incomplete: true` only if intentionally stopping before all rounds.

## Canonical Harness Commands

Use the decoupled harness as the experiment boundary:

```powershell
python -m PerturbTrace.baselines.harness.cli init-run `
  --run-id <run_id> `
  --strategy-version <strategy_version> `
  --task-profile <task_manifest.yaml> `
  --skill <skill_dir> `
  --output-dir <output_dir> `
  --feedback-policy <feedback_policy>

python -m PerturbTrace.baselines.harness.cli prepare-round `
  --run-root <run_root> `
  --round-index <0_based_round>

python -m PerturbTrace.baselines.harness.cli process-response `
  --run-root <run_root> `
  --round-index <0_based_round> `
  --raw-response <solver_response_file>

python -m PerturbTrace.baselines.harness.cli finalize-run `
  --run-root <run_root>
```

If `finalize_allow_incomplete` is true, append:

```powershell
--allow-incomplete
```

Do not rely on harness defaults for formal runs. Always pass `--task-profile`, `--skill`, `--output-dir`, `--strategy-version`, and `--run-id` explicitly.

## Monitor Loop

For each task and seed/run:

1. Build a unique `run_id`, for example `<run_id_prefix>_<task_slug>_r001`.
2. Call `init-run` and capture the printed `run_root`.
3. For each round from `0` to `rounds - 1`:
   - Call `prepare-round`.
   - Round 1 sends `round_1/system_prompt.txt` plus `round_1/initial_prompt.txt` to a fresh solver conversation.
   - Later rounds send only `round_N/feedback_prompt.txt` to the same solver conversation.
   - Save the solver response to any local text file.
   - Call `process-response`.
   - If status is `needs_repair`, send the returned `final_repair_prompt.txt` to the same solver conversation and call `process-response` again.
   - Stop the run as process-failed if repair attempts exceed `max_repairs_per_round`.
4. Call `finalize-run`.
5. Aggregate the result from `<run_root>/RUN_SUMMARY.json`.

The monitor may keep its own progress file outside each run root, but the canonical run evidence is the harness run root.

## Final Eval Read Path

For scoring and aggregation, read only:

```text
<run_root>/RUN_SUMMARY.json
```

Use this only for deeper inspection:

```text
<run_root>/metrics.json
<run_root>/leakage_audit.json
<run_root>/trace.jsonl
<run_root>/round_*/
```

The canonical `run_root` shape is:

```text
<output_dir>/<strategy_version>/<run_id>
```

The output paths are defined in:

```text
PerturbTrace/baselines/harness/artifacts.py
```

## Fixed Boundary

The monitor may:

- inspect completed harness run artifacts;
- keep its own sidecar memory;
- edit or create strategy skills when explicitly optimizing a strategy;
- launch new experiments through the harness CLI;
- compare `RUN_SUMMARY.json` files and decide the next skill revision.

The monitor must not:

- edit `PerturbTrace/baselines/harness/` during an eval run;
- edit harness-owned prompt templates, context assembly, validation, oracle, feedback clipping, metrics, or trace logic;
- add goal memory directly to solver prompts;
- pass prior-run gene names, action batches, observed scores, hidden labels, or rank-like lists into a solver-facing skill;
- ask the solver to read local files, inspect the repository, call validation, call the oracle, or fetch feedback;
- switch solvers between rounds of the same run unless the run is marked contaminated and abandoned.

The solver receives only harness-generated prompt text. The solver may use general scientific/literature prior if the experiment allows it, but it must not read hidden benchmark files or local run artifacts.

## Solver Adapter Responsibility

The harness does not launch Codex by itself. The monitor or one-click framework owns solver transport:

- create the fresh solver conversation;
- send harness prompt text;
- resume the same conversation for later rounds and repairs;
- write raw solver output to a file;
- pass that file to `process-response`;
- store transport logs separately if needed.

Historical reference implementation:

```text
PerturbTrace/baselines/harness_runs/xhigh_full_tasks_20260615_direct_prompt/direct_prompt_orchestrator.py
```

Use it as a reference for Codex transport only, not as harness core.

## Sidecar Memory

Keep goal memory outside the harness. Recommended root:

```text
PerturbTrace/baselines/goal_memory/<goal_id>/
```

Recommended files:

```text
raw_runs.jsonl
strategy_no_gene.jsonl
skill_revisions.jsonl
promotion_decisions.jsonl
```

`raw_runs.jsonl` may record run-level facts such as run id, harness version, skill version, process failures, prompt issues, and metrics. For restricted-clean strategy evolution, do not use it as direct solver context.

`strategy_no_gene.jsonl` is the only layer that should feed skill edits. It must not contain gene names, action batches, observed scores, hit labels, hidden thresholds, or rank-like lists.

## Skill Revision Rule

Before changing a skill, write a memory record explaining:

- what failed or improved;
- which no-gene strategy principle should change;
- why the change belongs in the skill rather than the harness;
- what one experimental lever the next run tests.

Keep skill bodies concise. A skill should be a reusable strategy workflow, not a run log, benchmark diary, or prompt dump.

Do not promote a strategy after one lucky run. A promoted skill revision needs independent fresh-run evidence, clean process metrics, and no leakage indicators.

Runs with harness edits, ad hoc prompt edits, solver local-file access, judge replacement suggestions, or memory injected into solver context are protocol-contaminated for restricted-clean comparison.
