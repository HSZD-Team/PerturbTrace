---
name: bda-viz
description: Render a local HTML report for a finished BDAbench harness run_root. Use after /bda or $bda completes, or when the user asks to visualize / open BDAbench results in a browser.
---

# /bda-viz — BDAbench Result Visualizer

You produce a **self-contained HTML report** from an existing harness `run_root`, so the user can open it in a local browser.

## When to run

- Immediately after a successful `/bda` / `$bda` eval that reported a `run_root`
- When the user provides a `run_root` / `RUN_SUMMARY.json` path and asks to visualize results
- When Chef_Harness finishes a bda session and asks you to render the report

## Inputs

Resolve `run_root` from, in order:

1. Explicit path in the user message
2. The latest `/bda` final reply (`run_root: ...`)
3. Ask the user if still missing

`run_root` must contain `RUN_SUMMARY.json`.

## Action

From the workspace (or any cwd), run:

```bash
python "<this_skill_dir>/scripts/render_report.py" "<run_root>"
```

Default output:

```text
<run_root>/report.html
```

Optional:

```bash
python "<this_skill_dir>/scripts/render_report.py" "<run_root>" -o "<custom.html>"
```

Then tell the user the absolute HTML path and that they can open it with a local browser, e.g.:

```bash
open "<run_root>/report.html"   # macOS
```

## Final reply contract

```text
report_html: <absolute path>
run_root: <absolute path>
summary: <absolute path>/RUN_SUMMARY.json
notes: open report_html in a local browser
```

## Boundaries

- Do not re-run the benchmark unless the user asks
- Do not modify harness oracle / metrics code
- Prefer the script above over hand-writing HTML
