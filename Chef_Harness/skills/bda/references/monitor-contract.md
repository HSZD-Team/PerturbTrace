# Monitor Contract (condensed)

Source of truth in the portable package:

```text
baselines/agent.md
baselines/harness/README.md
```

## Roles

| Role | Owns |
|---|---|
| Monitor (`/bda`) | schedule runs, solver transport, retries, aggregate `RUN_SUMMARY` |
| Decoupled harness CLI | prompts, validation, oracle, metrics, traces |
| Solver | choose actions from harness prompt text only |

## Required config fields

```yaml
task_profiles:
  - <task_manifest.yaml>
skill: <external_solver_skill_dir>   # solver strategy SKILL.md
strategy_version: <string>
output_dir: <dir>
run_id_prefix: <string>
feedback_policy: true_feedback
solver:
  transport: codex_app_session       # not harness-owned; monitor-owned
  model: gpt-5.5
  reasoning_effort: xhigh
  one_continuous_conversation_per_run: true
max_repairs_per_round: 6
finalize_allow_incomplete: false
```

## Boundaries

Monitor may:

- launch harness CLI commands
- inspect completed run artifacts
- keep sidecar memory outside `run_root`
- open solver conversations and pass harness prompt files

Monitor must not:

- edit `baselines/harness/` during an eval
- change oracle / metrics / prompt assembly
- ask solver to read local repo / hidden / run files
- inject prior-run gene names, scores, ranks into solver context

## Final read path

Primary:

```text
<run_root>/RUN_SUMMARY.json
```

Debug only:

```text
<run_root>/metrics.json
<run_root>/leakage_audit.json
<run_root>/trace.jsonl
<run_root>/round_*/
```

`run_root` shape:

```text
<output_dir>/<strategy_version>/<run_id>
```
