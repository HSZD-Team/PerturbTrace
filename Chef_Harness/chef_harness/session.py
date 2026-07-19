"""Thin session history for Chef launches."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .paths import workspace_root


@dataclass
class SessionRecord:
    session_id: str
    skill: str
    runtime: str
    created_at: str
    user_text: str
    package_root: str
    status: str = "created"
    run_root: str | None = None
    summary_path: str | None = None
    exit_code: int | None = None
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def dir(self) -> Path:
        return workspace_root() / ".chef" / "sessions" / self.session_id


def create_session(
    *,
    skill: str,
    runtime: str,
    user_text: str,
    package_root: Path,
    prompt: str,
    extra: dict[str, Any] | None = None,
) -> SessionRecord:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    session_id = f"{stamp}_{uuid4().hex[:8]}"
    record = SessionRecord(
        session_id=session_id,
        skill=skill,
        runtime=runtime,
        created_at=datetime.now(timezone.utc).isoformat(),
        user_text=user_text,
        package_root=str(package_root),
        extra=extra or {},
    )
    record.dir.mkdir(parents=True, exist_ok=True)
    (record.dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    save_session(record)
    return record


def save_session(record: SessionRecord) -> None:
    record.dir.mkdir(parents=True, exist_ok=True)
    path = record.dir / "meta.json"
    path.write_text(json.dumps(asdict(record), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
