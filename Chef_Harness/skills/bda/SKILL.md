---
name: bda
description: Run BDAbench gene-screening evals as an eval monitor via the decoupled harness. Use when the user invokes /bda or $bda, asks for BDAbench / gene-screen evaluation, or wants a local 1-run harness demo with run_root and RUN_SUMMARY returned.
---

# /bda — BDAbench Eval Monitor

You are the **eval monitor**, not the solver and not the harness core.

Read before acting:

1. `references/monitor-contract.md`
2. `references/harness-cli.md`
3. Optional Chef defaults in `skill.config.yaml` (ignore unknown keys if running inside native Codex)

## Goal

From the user prompt, run one BDAbench evaluation session end-to-end through the **decoupled harness CLI**, then report:

- absolute `run_root`
- `RUN_SUMMARY.json` path
- short metric / completion summary

Prefer `scripts/summarize_run.py <run_root>` for the final summary when available.

## Resolve Inputs

Parse the user request into:

| Slot | Default (smoke) | Notes |
|---|---|---|
| `task` | `c3_cart_crispra_exhaustion_feedback_decision_v0` | Resolve via `tasks/task_index.yaml` / task folder under BDAbench package |
| `runtime` / selector harness | `codex` | May be `pi` or `opencode`; this is who runs **this monitor skill** |
| `solver` | Codex app/session, model `gpt-5.5`, effort `xhigh` | Fresh thread; **solver must not use project**; **solver must not be launched via `codex exec`** |
| `solver_skill` | required external dir with `SKILL.md` | Strategy skill for the solver, not this `/bda` skill |
| `rounds` | task manifest value | For smoke demo, 1-run / allow incomplete only if user asks |
| `package_root` | nearest BDAbench portable package | Directory that contains `BDAbench/`, `baselines/`, `tasks/` |

If `solver_skill` is missing, stop and ask for a path (or create one only when the user explicitly wants a strategy skill drafted).

Natural-language examples that should trigger this skill:

- Chinese: `/bda 帮我基于这个文件夹里的文件去做基因筛选`
- English: `/bda Help me run a gene-screen evaluation based on the files in this folder`
- English: `$bda 1-run demo on cart_crispra_exhaustion`
- Chinese: plain `"用 decoupled harness 跑一个 BDAbench 评测"`
- English: plain `"Run a BDAbench evaluation with the decoupled harness"`

## Runtime Selection

`runtime` selects the **monitor/selector harness**, not the benchmark engine.

- Default: `codex`
- Also supported later: `pi`, `opencode`
- Benchmark engine stays `bdabench` (decoupled harness CLI)

If Chef_Harness launched you, honor its `--harness` / config override. If native Codex invoked `$bda`, you are already on the `codex` runtime.

## Tooling note (critical)

Two different “exec” ideas — do not confuse them:

1. **Monitor shell is allowed and required.** You SHOULD use local shell / command execution to run  
   `python -m BDAbench.baselines.harness.cli ...`, read artifacts, and summarize results.
2. **Solver transport must not use `codex exec`.** Launch the solver as a fresh Codex app/session thread (no project). Do not use `codex exec` as the solver runner.

If the user says “不要用 exec” / “do not use exec”, interpret it as (2), not (1).

## Hard Boundaries

You may:

- call BDAbench harness CLI via local shell (`init-run` → `prepare-round` → `process-response` → `finalize-run`)
- open / resume the **solver** conversation for prompt text only
- inspect completed `run_root` artifacts and summarize them

You must not:

- edit `baselines/harness/` or oracle / metrics / prompt-assembly code during a run
- let the solver read manifests, hidden files, run artifacts, or repo internals
- inject prior-run gene lists / scores / ranks into solver prompts or solver skills
- reimplement membership checks, oracle scoring, or metrics yourself

## Monitor Loop (minimal)

Work from `package_root` so `python -m BDAbench.baselines.harness.cli` resolves.

1. `init-run` with explicit `--task-profile`, `--skill`, `--output-dir`, `--strategy-version`, `--run-id`
2. Capture printed `run_root`
3. For each needed round:
   - `prepare-round`
   - Send only harness-written prompt files to a **fresh** solver thread (round 0) or the **same** thread (later rounds / repairs)
   - Save raw solver text → `process-response`
   - On `needs_repair`, send repair prompt to the same solver thread; stop if repairs exceed limit
4. `finalize-run` (add `--allow-incomplete` only when the user/smoke config allows it)
5. Read `<run_root>/RUN_SUMMARY.json` and report paths + summary

## After finalize: visualize

If `run_root` exists and contains `RUN_SUMMARY.json`, immediately invoke the sibling skill **`bda-viz`**:

```bash
python "<workspace>/skills/bda-viz/scripts/render_report.py" "<run_root>"
```

Include the printed `report.html` path in your final reply. If `bda-viz` is installed as a Codex skill, you may also `$bda-viz` with the same `run_root`.

## Final Reply Contract

Always end with:

```text
run_root: <absolute path>
summary: <absolute path>/RUN_SUMMARY.json
report_html: <absolute path>/report.html
complete: <bool>
primary_metric: <value or n/a>
notes: <one short line>
```

If the run failed, still return the best-known `run_root` and the failure reason. Skip `report_html` when there is no summary to render.
