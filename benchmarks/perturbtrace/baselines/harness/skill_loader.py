"""Load and audit solver-facing strategy skills for the harness."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .contracts import SkillAudit, SkillBundle


_LOCAL_PATH_RE = re.compile(
    r"(?:[A-Z]:[\\/]|\.npy\b|\.csv\b|\.pkl\b|\.jsonl\b|"
    r"BioDiscoveryAgent_repo[\\/]|PerturbTrace[\\/].*(?:runs|task_profiles|framework)[\\/])",
    flags=re.IGNORECASE,
)


class SkillLoadError(ValueError):
    pass


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text.strip()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip()
    raw_metadata = yaml.safe_load(parts[1]) or {}
    if not isinstance(raw_metadata, dict):
        raise SkillLoadError("Skill frontmatter must be a YAML mapping.")
    metadata = {str(key): value for key, value in raw_metadata.items()}
    return metadata, parts[2].strip()


def load_skill(path: Path) -> SkillBundle:
    skill_path = path if path.name == "SKILL.md" else path / "SKILL.md"
    if not skill_path.exists():
        raise SkillLoadError(f"Skill file not found: {skill_path}")
    text = skill_path.read_text(encoding="utf-8")
    metadata, body = _split_frontmatter(text)
    name = metadata.get("name")
    description = metadata.get("description")
    if not name or not description:
        raise SkillLoadError("Skill frontmatter must include name and description.")
    if not body:
        raise SkillLoadError("Skill body is empty.")
    return SkillBundle(
        name=name,
        description=description,
        body=body,
        source_path=skill_path.resolve(),
        metadata=metadata,
    )


def audit_skill_for_solver(skill: SkillBundle, forbidden_terms: list[str]) -> SkillAudit:
    issues: list[dict[str, str]] = []
    text = f"{skill.description}\n{skill.body}"
    for match in sorted({item.group(0) for item in _LOCAL_PATH_RE.finditer(text)}):
        issues.append({"term": match, "reason": "local_or_hidden_artifact_reference"})
    lower = text.lower()
    for term in forbidden_terms:
        if term and term.lower() in lower:
            issues.append({"term": term, "reason": "profile_forbidden_term_in_skill"})
    return SkillAudit(clean=not issues, issues=issues)
