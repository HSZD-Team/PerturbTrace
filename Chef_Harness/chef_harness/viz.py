"""Invoke skills/bda-viz HTML renderer."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .paths import workspace_root
from .skills import load_skill


def render_bda_report(run_root: Path, *, output: Path | None = None) -> Path:
    skill = load_skill("bda-viz")
    script = skill.skill_dir / "scripts" / "render_report.py"
    if not script.exists():
        raise FileNotFoundError(f"Missing renderer: {script}")

    cmd = [sys.executable, str(script), str(run_root.resolve())]
    if output is not None:
        cmd.extend(["-o", str(output.resolve())])

    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(detail or f"render_report failed with code {proc.returncode}")

    printed = (proc.stdout or "").strip().splitlines()
    if printed:
        return Path(printed[-1]).expanduser().resolve()
    default_name = str(skill.config.get("default_output_name") or "report.html")
    return (run_root / default_name).resolve()


def should_auto_viz_after_bda() -> bool:
    try:
        skill = load_skill("bda-viz")
    except FileNotFoundError:
        return False
    return bool(skill.config.get("auto_after_bda", True))


def default_report_path(run_root: Path) -> Path:
    return (run_root / "report.html").resolve()
