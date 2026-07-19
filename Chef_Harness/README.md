# Chef_Harness

Local launcher for SciLoopBench BDAbench evaluations.

Chef starts a **monitor** session (default runtime: Codex), drives the portable BDAbench decoupled harness CLI, then recovers `run_root` and renders an HTML report via `bda-viz`.

## Layout

```text
SciLoopBench/
  benchmarks/bdabench/     # portable BDAbench engine + tasks
  Chef_Harness/            # this folder
    chef_harness/          # Python CLI package
    skills/
      bda/                 # eval-monitor skill
      bda-viz/             # HTML report skill
    solver_skills/
      restricted-clean-gene-screen/
```

## Prerequisites

- Python 3.10+
- BDAbench Python deps (from `../benchmarks/bdabench/requirements.txt`): `numpy`, `pandas`, `pyyaml`
- [Codex CLI](https://github.com/openai/codex) on `PATH` (for real runs; not needed for `--dry-run`)
- Enough Codex usage quota for monitor + solver calls

## Install

From this directory (`SciLoopBench/Chef_Harness`):

```bash
python -m pip install -e .
python -m pip install -r ../benchmarks/bdabench/requirements.txt
```

Check:

```bash
chef --help
# or
python -m chef_harness --help
```

## Quick start

Unless noted otherwise, run these from:

```text
SciLoopBench/Chef_Harness
```

### 1) Dry-run (no Codex call)

Validate that task / task_profile wiring is correct:

```bash
chef run bda --task c3_il2_feedback_decision_v0 --full --dry-run
```

### 2) Smoke (1 round)

```bash
chef run bda --task c3_cart_crispra_exhaustion_feedback_decision_v0 --smoke
```

### 3) Full task (all rounds)

```bash
chef run bda --task c3_il2_feedback_decision_v0 --full
```

### 4) Interactive REPL

```bash
chef
```

Then inside the Chef prompt:

```text
chef> run bda --task c3_gdsc_drug_response_v0 --smoke
```

## What success looks like

At the end of a successful run you should see:

- `[chef] status: ok`
- `requested_task` matching your `--task`
- `actual_task` from `RUN_SUMMARY.json` matching the same task
- `run_root: ...`
- `report_html: .../report.html`

Open the report (any directory; uses an absolute `report_html` path):

```bash
open <report_html>
```

Re-render a report later:

```bash
chef viz <run_root>
```

## Skills

| Skill | Role |
|---|---|
| `bda` | Eval **monitor**: schedules harness CLI, launches solver thread, finalizes run |
| `bda-viz` | Builds local HTML visualization from a finished `run_root` |
| `restricted-clean-gene-screen` | **Solver strategy** skill passed to harness `--skill` |

Notes:

- Chef may use `codex exec` to launch the **monitor**.
- The monitor prompt still requires the **solver** to use a fresh Codex thread/task (no project; prefer not `codex exec` for solver).
- Default monitor model is `skills/bda/skill.config.yaml → monitor.model` (currently `gpt-5.5`).

### Install `bda` in the Codex app

You can run BDAbench without the `chef` CLI by installing the `bda` skill into Codex, then invoking `$bda` inside a Codex session.

#### 1) Link the skill into Codex

From `SciLoopBench/Chef_Harness`:

```bash
# recommended for Codex CLI / app skill discovery
mkdir -p ~/.codex/skills
ln -sfn "$(pwd)/skills/bda" ~/.codex/skills/bda

# optional: also install the HTML visualizer skill
ln -sfn "$(pwd)/skills/bda-viz" ~/.codex/skills/bda-viz
```

Repo-local alternative (useful if you open this folder as a Codex project):

```bash
mkdir -p .agents/skills
ln -sfn "$(pwd)/skills/bda" .agents/skills/bda
ln -sfn "$(pwd)/skills/bda-viz" .agents/skills/bda-viz
```

Then **restart Codex / open a new session** so skills reload.

In Codex, run `/skills` (or the skills picker) and confirm `bda` appears.

#### 2) Invoke `$bda` to run a benchmark

Use absolute paths for `solver_skill` and the BDAbench package root.

Example smoke (1 round) — Chinese:

```text
$bda 用 decoupled harness 演示一个 1-run 实际评测流程。
task 选 c3_cart_crispra_exhaustion_feedback_decision_v0。
monitor 必须用本地 shell，在 /ABS/PATH/to/SciLoopBench/benchmarks/bdabench 下调用 PYTHONPATH=. python -m BDAbench.baselines.harness.cli。
solver 用 Codex 新线程，模型 gpt-5.5，reasoning xhigh；solver 不使用项目；solver 不要用 codex exec 启动。
solver_skill=/ABS/PATH/to/SciLoopBench/Chef_Harness/solver_skills/restricted-clean-gene-screen
允许 finalize --allow-incomplete（完成第 1 轮即可）。
跑完后回报 run_root、RUN_SUMMARY 摘要，并调用 $bda-viz 生成 report.html。
```

Example smoke (1 round) — English:

```text
$bda Use the decoupled harness to demonstrate a 1-run evaluation.
task: c3_cart_crispra_exhaustion_feedback_decision_v0
monitor must use local shell and run PYTHONPATH=. python -m BDAbench.baselines.harness.cli under /ABS/PATH/to/SciLoopBench/benchmarks/bdabench.
solver: open a new Codex thread with model gpt-5.5 and reasoning xhigh; solver must not use project; solver must not be launched via codex exec.
solver_skill=/ABS/PATH/to/SciLoopBench/Chef_Harness/solver_skills/restricted-clean-gene-screen
Allow finalize --allow-incomplete (finishing round 1 is enough).
When done, report run_root, a RUN_SUMMARY summary, and call $bda-viz to generate report.html.
```

Example full run (all rounds) — Chinese:

```text
$bda 对 task=c3_il2_feedback_decision_v0 跑完整 BDAbench 评测（全部 rounds）。
monitor 必须用本地 shell，在 /ABS/PATH/to/SciLoopBench/benchmarks/bdabench 下调用 PYTHONPATH=. python -m BDAbench.baselines.harness.cli。
solver 用 Codex 新线程，模型 gpt-5.5，reasoning xhigh；solver 不使用项目；solver 不要用 codex exec 启动。
solver_skill=/ABS/PATH/to/SciLoopBench/Chef_Harness/solver_skills/restricted-clean-gene-screen
不要使用 --allow-incomplete。
跑完后回报 run_root、RUN_SUMMARY 摘要，并调用 $bda-viz 生成 report.html。
```

Example full run (all rounds) — English:

```text
$bda Run a full BDAbench evaluation for task=c3_il2_feedback_decision_v0 (all rounds).
monitor must use local shell and run PYTHONPATH=. python -m BDAbench.baselines.harness.cli under /ABS/PATH/to/SciLoopBench/benchmarks/bdabench.
solver: open a new Codex thread with model gpt-5.5 and reasoning xhigh; solver must not use project; solver must not be launched via codex exec.
solver_skill=/ABS/PATH/to/SciLoopBench/Chef_Harness/solver_skills/restricted-clean-gene-screen
Do not use --allow-incomplete.
When done, report run_root, a RUN_SUMMARY summary, and call $bda-viz to generate report.html.
```

Replace `/ABS/PATH/to/SciLoopBench/...` with your real absolute paths.

#### 3) What you should get back

A successful Codex `$bda` run should return:

- absolute `run_root`
- `RUN_SUMMARY.json` path / key metrics
- `report_html` (if `$bda-viz` ran), which you can open in a local browser

More detailed Codex checks: `skills/bda/CODEX_TEST_CHECKLIST.md`.
