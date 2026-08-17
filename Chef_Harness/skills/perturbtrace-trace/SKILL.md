---
name: perturbtrace-trace
description: Audit completed PerturbTrace harness run roots with independent trace labels, outcome scoring, figures, and an HTML report. Use only when the user supplies a manifest of completed runs.
---

# PerturbTrace Trace Evaluation

Evaluate only completed PerturbTrace/PerturbTrace harness runs supplied by the
user. This skill reads the run artifacts without modifying them. It is not a
benchmark launcher and it must never create, resume, or infer a formal run
panel.

## Required input

The user supplies a UTF-8 CSV manifest with a `run_root` column. Every root
must contain a completed `RUN_SUMMARY.json`, `harness_config.json`, and
`batches.json`.

Optional columns are:

| Column | Meaning |
|---|---|
| `case_id` | Stable user-facing identifier; defaults to the run-root name. |
| `group` | User-provided analysis grouping. |
| `codebook_task_id` | One key in `protocol/module_codebooks_v1.json`, such as `T02`. Required for State-to-Action assessment; omission leaves that edge explicitly unassessable. |

Do not guess a `codebook_task_id` from a task name, run name, or biological
description. Do not put a formal experiment manifest, cached labels, judge
logs, figures, reports, or run roots inside this skill directory.

## Invocation

Use an output directory outside this repository. The first form uses the same
judge model for both independent passes. The second form is only for an
explicit heterogeneous-model sensitivity check.

```bash
python "<skill_dir>/scripts/run_trace_evaluation.py" \
  --run-manifest "<absolute-manifest.csv>" \
  --output-dir "<absolute-output-directory>" \
  --judge-model "<model>"
```

```bash
python "<skill_dir>/scripts/run_trace_evaluation.py" \
  --run-manifest "<absolute-manifest.csv>" \
  --output-dir "<absolute-output-directory>" \
  --judge-a-model "<model-a>" \
  --judge-b-model "<model-b>"
```

The runtime supplies credentials through `BDA_OPENAI_API_KEY`, or with
`--api-key-file`. `--base-url` is optional. Never write a credential into a
manifest, report, log, source file, or Git configuration.

The two judges are independent API passes: separate calls, separate contexts,
and reversed packet order for Judge B. Identical models are the default and do
not weaken that operational independence.

## Outputs and interpretation

The output directory contains blinded packets, judge labels and logs,
transition-level scoring, a PNG summary figure, `trace_report.html`, and
`TRACE_VALIDATION.json`. The output is local analysis material and must not be
committed to this repository.

For a small manifest, agreement can be reported as not estimable. This is not
a reliability pass and must not be presented as one. A one-run analysis is a
case-level audit only: it does not justify condition-level comparisons.

The report treats `S` as an externalized written decision state, not latent
belief. It retains the protocol distinction between Feedback-to-State,
State-to-Action, and Action-to-Outcome. Hidden hit sets are read only after
blinded state coding, for Action-to-Outcome scoring.
