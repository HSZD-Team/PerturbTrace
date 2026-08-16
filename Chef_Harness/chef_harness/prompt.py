"""Build the monitor launch prompt for /bda."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .skills import SkillPackage, resolve_skill_paths


@dataclass(frozen=True)
class BdaLaunchPlan:
    skill: SkillPackage
    user_text: str
    runtime: str
    package_root: Path
    solver_skill: Path
    task_slug: str
    task_profile: Path
    output_dir: Path
    strategy_version: str
    smoke: bool
    solver_model: str
    solver_effort: str
    prompt: str


def build_bda_plan(
    skill: SkillPackage,
    user_text: str,
    *,
    runtime: str | None = None,
    solver_skill: Path | None = None,
    task_slug: str | None = None,
    smoke: bool | None = None,
) -> BdaLaunchPlan:
    paths = resolve_skill_paths(skill)
    cfg = skill.config
    defaults: dict[str, Any] = dict(cfg.get("defaults") or {})
    solver_defaults: dict[str, Any] = dict(defaults.get("solver") or {})

    resolved_runtime = runtime or str(cfg.get("default_runtime", "codex"))
    supported = list(cfg.get("supported_runtimes") or [resolved_runtime])
    if resolved_runtime not in supported:
        raise ValueError(
            f"Runtime {resolved_runtime!r} not in supported_runtimes={supported}"
        )
    if resolved_runtime != "codex":
        raise ValueError(
            f"MVP only supports runtime 'codex' right now; got {resolved_runtime!r}"
        )

    resolved_solver = solver_skill or paths["solver_skill"]
    if resolved_solver is None or not resolved_solver.exists():
        raise FileNotFoundError(
            "solver_skill is required and must exist. "
            "Pass --solver-skill or set skill.config.yaml solver_skill."
        )
    if not (resolved_solver / "SKILL.md").exists() and resolved_solver.name != "SKILL.md":
        raise FileNotFoundError(f"solver_skill missing SKILL.md: {resolved_solver}")

    resolved_task = task_slug or str(defaults.get("task_slug", ""))
    if not resolved_task:
        raise ValueError("task_slug missing from skill config and CLI")

    # Always derive task_profile from the selected task_slug. Never keep a stale
    # default profile (e.g. cart_crispra) when the user overrides --task.
    task_profile = (
        paths["package_root"]
        / "tasks"
        / resolved_task
        / "task_manifest.yaml"
    ).resolve()
    if not task_profile.exists():
        raise FileNotFoundError(
            f"task_profile not found for task {resolved_task}: {task_profile}"
        )

    if smoke is None:
        # Natural-language smoke cues, else config default.
        lowered = user_text.lower()
        smoke = any(
            token in lowered or token in user_text
            for token in ("smoke", "1-run", "1 run", "一轮", "单轮", "allow-incomplete")
        ) or bool(defaults.get("finalize_allow_incomplete", False))

    strategy_version = str(defaults.get("strategy_version", "bda_skill_v0"))
    solver_model = str(solver_defaults.get("model", "gpt-5.5"))
    solver_effort = str(solver_defaults.get("reasoning_effort", "xhigh"))

    prompt = _render_prompt(
        user_text=user_text,
        skill_md=skill.skill_md,
        package_root=paths["package_root"],
        task_slug=resolved_task,
        task_profile=task_profile,
        solver_skill=resolved_solver,
        output_dir=paths["output_dir"],
        strategy_version=strategy_version,
        smoke=smoke,
        solver_model=solver_model,
        solver_effort=solver_effort,
    )

    return BdaLaunchPlan(
        skill=skill,
        user_text=user_text,
        runtime=resolved_runtime,
        package_root=paths["package_root"],
        solver_skill=resolved_solver,
        task_slug=resolved_task,
        task_profile=task_profile,
        output_dir=paths["output_dir"],
        strategy_version=strategy_version,
        smoke=smoke,
        solver_model=solver_model,
        solver_effort=solver_effort,
        prompt=prompt,
    )


def _render_prompt(
    *,
    user_text: str,
    skill_md: Path,
    package_root: Path,
    task_slug: str,
    task_profile: Path,
    solver_skill: Path,
    output_dir: Path,
    strategy_version: str,
    smoke: bool,
    solver_model: str,
    solver_effort: str,
) -> str:
    smoke_line = (
        "Allow finalize --allow-incomplete (finishing round-1 submission is enough)."
        if smoke
        else "Run all task rounds; do not use --allow-incomplete unless process-response fails and you must stop."
    )
    return f"""$bda

You are the eval monitor. First read the skill file:
{skill_md}

and the references/ in the same directory.

## User request
{user_text.strip()}

## Chef_Harness launch parameters (follow these)
- package_root / cwd: {package_root}
- task: {task_slug}
- task_profile: {task_profile}
- solver_skill: {solver_skill}
- strategy_version: {strategy_version}
- output_dir: {output_dir}
- monitor: must use a local shell to run `PYTHONPATH=. python -m BDAbench.baselines.harness.cli ...`
- solver: open a new Codex thread/task with model {solver_model} and reasoning {solver_effort}; solver must not use a project; solver must not be launched via `codex exec`
- {smoke_line}

## Done criteria
Complete init-run → prepare-round → solver → process-response → finalize-run.
The final reply must include:

```text
run_root: <absolute path>
summary: <absolute path>/RUN_SUMMARY.json
complete: <bool>
primary_metric: <value or n/a>
notes: <one short line>
```
"""
