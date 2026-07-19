"""Recover and summarize harness run artifacts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


RUN_ROOT_RE = re.compile(
    r"^\s*run_root\s*[:=]\s*(.+?)\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)
SUMMARY_RE = re.compile(
    r"^\s*summary\s*[:=]\s*(.+?)\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class RunResult:
    run_root: Path | None
    summary_path: Path | None
    summary: dict[str, Any]
    source: str
    display: str


def _looks_like_real_path(value: str) -> bool:
    text = value.strip().strip('`"')
    if not text:
        return False
    # Reject prompt-template placeholders such as "<absolute path>".
    if "<" in text or ">" in text:
        return False
    if "absolute path" in text.lower():
        return False
    return text.startswith("/") or text.startswith("~") or ":\\" in text[:3]


def parse_paths_from_text(text: str) -> tuple[Path | None, Path | None]:
    run_root = None
    summary = None
    for m in RUN_ROOT_RE.finditer(text or ""):
        candidate = m.group(1).strip().strip('`"')
        if _looks_like_real_path(candidate):
            run_root = Path(candidate).expanduser()
    for m in SUMMARY_RE.finditer(text or ""):
        candidate = m.group(1).strip().strip('`"')
        if _looks_like_real_path(candidate):
            summary = Path(candidate).expanduser()
    return run_root, summary


def find_newest_run_root(output_dir: Path, *, since_ts: float | None = None) -> Path | None:
    if not output_dir.exists():
        return None
    candidates: list[Path] = []
    for summary in output_dir.rglob("RUN_SUMMARY.json"):
        if since_ts is not None and summary.stat().st_mtime < since_ts - 2:
            continue
        candidates.append(summary.parent)
    if not candidates:
        return None
    return max(candidates, key=lambda p: (p / "RUN_SUMMARY.json").stat().st_mtime)


def load_summary(summary_path: Path) -> dict[str, Any]:
    if not summary_path.exists():
        return {}
    return json.loads(summary_path.read_text(encoding="utf-8"))


def format_summary(run_root: Path, summary: dict[str, Any], summary_path: Path) -> str:
    keys = (
        "run_id",
        "task_id",
        "rounds_submitted",
        "expected_rounds",
        "complete",
        "primary_metric",
        "top_effect_recall",
        "precision_at_budget",
        "auc_hdc",
        "leakage_label",
    )
    lines = [
        f"run_root: {run_root}",
        f"summary: {summary_path}",
    ]
    for key in keys:
        if key in summary:
            lines.append(f"{key}: {summary[key]}")
    if not summary:
        lines.append("notes: RUN_SUMMARY.json missing or empty")
    return "\n".join(lines)


def recover_result(
    *,
    last_message: str,
    output_dir: Path,
    since_ts: float | None,
) -> RunResult:
    run_root, summary_path = parse_paths_from_text(last_message)
    source = "monitor_message"

    if run_root is None:
        run_root = find_newest_run_root(output_dir, since_ts=since_ts)
        source = "filesystem_scan" if run_root else "none"

    if run_root is not None:
        run_root = run_root.resolve()
        if summary_path is None:
            summary_path = run_root / "RUN_SUMMARY.json"
        else:
            summary_path = summary_path.resolve()

    summary: dict[str, Any] = {}
    if summary_path and summary_path.exists():
        summary = load_summary(summary_path)

    display = (
        format_summary(run_root, summary, summary_path)
        if run_root and summary_path
        else (last_message.strip() or "No run_root recovered.")
    )
    return RunResult(
        run_root=run_root,
        summary_path=summary_path,
        summary=summary,
        source=source,
        display=display,
    )
