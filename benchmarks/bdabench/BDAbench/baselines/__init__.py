"""Compatibility namespace for running BDAbench modules from the repo root."""

from __future__ import annotations

from pathlib import Path

_repo_baselines = Path(__file__).resolve().parents[2] / "baselines"
if _repo_baselines.exists():
    __path__.append(str(_repo_baselines))  # type: ignore[name-defined]
