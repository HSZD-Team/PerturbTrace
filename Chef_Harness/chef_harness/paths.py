"""Workspace path helpers."""

from __future__ import annotations

from pathlib import Path


def workspace_root() -> Path:
    """Return the PerturbTrace workspace root (parent of chef_harness/)."""
    return Path(__file__).resolve().parents[1]


def resolve_workspace_path(path: str | Path, *, root: Path | None = None) -> Path:
    p = Path(path).expanduser()
    if p.is_absolute():
        return p.resolve()
    base = root or workspace_root()
    return (base / p).resolve()
