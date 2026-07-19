# `/bda` skill (Skill_1)

Eval-monitor skill for BDAbench decoupled harness. Designed to:

1. run inside native Codex skill system (`$bda` / `/skills`)
2. later be launched by Chef_Harness via `/bda ...` with selectable runtime (`codex` default, also `pi` / `opencode`)

## Layout

```text
skills/bda/
  SKILL.md                 # Codex-compatible skill entry
  skill.config.yaml        # Chef defaults (runtime / task / solver transport)
  references/
    monitor-contract.md
    harness-cli.md
  scripts/
    summarize_run.py
```

## Try in Codex first

Step-by-step verification: see [`CODEX_TEST_CHECKLIST.md`](./CODEX_TEST_CHECKLIST.md).

From this repo (or copy the folder):

```bash
mkdir -p .agents/skills
ln -sfn "$(pwd)/skills/bda" .agents/skills/bda
```

Or install into your user skills dir:

```bash
mkdir -p ~/.agents/skills
ln -sfn "$(pwd)/skills/bda" ~/.agents/skills/bda
```

Then in a Codex session, invoke:

Chinese:

```text
$bda 用 decoupled harness 演示一个 1-run 实际评测流程，
task 选 cart_crispra_exhaustion_feedback_decision，
solver 用 codex-xhigh (gpt-5.5，不使用项目，开新线程，不要用 exec)，
并把最终 run_root 和结果文件告诉我。
solver_skill=<path-to-solver-SKILL-dir>
```

English:

```text
$bda Use the decoupled harness to demonstrate a 1-run evaluation.
task: cart_crispra_exhaustion_feedback_decision
solver: Codex xhigh (gpt-5.5; no project; new thread; do not use exec)
When done, report the final run_root and result files.
solver_skill=<path-to-solver-SKILL-dir>
```

`solver_skill` is required: it is the **solver strategy** skill, separate from this monitor skill.

Default solver strategy in this workspace:

```text
solver_skills/restricted-clean-gene-screen
```

## After a run: visualize

Use sibling skill [`../bda-viz`](../bda-viz):

```bash
python skills/bda-viz/scripts/render_report.py /path/to/run_root
open /path/to/run_root/report.html
```

Or in Codex: `$bda-viz run_root=<abs path>`. Chef auto-renders after successful `chef run bda`.

## Launch via Chef_Harness MVP

From `Chef_Harness/`:

```bash
chef run bda --smoke --dry-run
chef run bda --smoke
# or interactive:
chef
```

Interactive prompt — Chinese:

```text
chef> /bda 帮我基于这个文件夹做基因筛选（1-run smoke）
```

Interactive prompt — English:

```text
chef> /bda Help me run a gene-screening evaluation based on files in this folder (1-run smoke)
```

See `../README.md`.

## Not included yet

- runtime adapters for `pi` / `opencode`
