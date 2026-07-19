"""Load Chef-facing skill packages (SKILL.md + skill.config.yaml)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .paths import resolve_workspace_path, workspace_root


@dataclass(frozen=True)
class SkillPackage:
    name: str
    skill_dir: Path
    skill_md: Path
    config: dict[str, Any]
    body: str
    description: str


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text.strip()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip()
    meta = yaml.safe_load(parts[1]) or {}
    if not isinstance(meta, dict):
        raise ValueError("SKILL.md frontmatter must be a YAML mapping")
    return meta, parts[2].strip()


def default_skills_root() -> Path:
    return workspace_root() / "skills"


def load_skill(name: str, *, skills_root: Path | None = None) -> SkillPackage:
    root = skills_root or default_skills_root()
    skill_dir = (root / name).resolve()
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"Skill not found: {skill_md}")

    meta, body = _split_frontmatter(skill_md.read_text(encoding="utf-8"))
    config_path = skill_dir / "skill.config.yaml"
    config: dict[str, Any] = {}
    if config_path.exists():
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Invalid skill config: {config_path}")
        config = loaded

    skill_name = str(config.get("name") or meta.get("name") or name)
    description = str(meta.get("description") or config.get("description") or "")
    return SkillPackage(
        name=skill_name,
        skill_dir=skill_dir,
        skill_md=skill_md,
        config=config,
        body=body,
        description=description,
    )


def resolve_skill_paths(skill: SkillPackage) -> dict[str, Path]:
    """Resolve important absolute paths from skill.config.yaml."""
    cfg = skill.config
    package_root = resolve_workspace_path(cfg.get("package_root", "."))
    solver_skill_raw = cfg.get("solver_skill")
    solver_skill = (
        resolve_workspace_path(solver_skill_raw) if solver_skill_raw else None
    )
    defaults = cfg.get("defaults") or {}
    task_profile = defaults.get("task_profile")
    task_profile_path = (
        (package_root / task_profile).resolve() if task_profile else None
    )
    output_dir = defaults.get("output_dir", "baselines/harness_runs")
    output_dir_path = (package_root / output_dir).resolve()
    return {
        "package_root": package_root,
        "solver_skill": solver_skill,
        "task_profile": task_profile_path,
        "output_dir": output_dir_path,
    }
