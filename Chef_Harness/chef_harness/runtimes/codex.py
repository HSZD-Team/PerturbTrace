"""Codex runtime adapter for Chef monitor launches."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeResult:
    exit_code: int
    last_message: str
    stdout_path: Path
    last_message_path: Path
    command: list[str]


class CodexRuntime:
    """Launch the monitor skill via `codex exec` (Chef-side automation)."""

    def __init__(self, codex_bin: str | None = None) -> None:
        self.codex_bin = codex_bin or shutil.which("codex") or "codex"

    def run_monitor(
        self,
        *,
        prompt: str,
        cwd: Path,
        session_dir: Path,
        model: str | None = None,
        bypass_sandbox: bool = True,
    ) -> RuntimeResult:
        session_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = session_dir / "prompt.txt"
        prompt_file.write_text(prompt, encoding="utf-8")
        last_message_path = session_dir / "last_message.txt"
        stdout_path = session_dir / "codex_stdout.log"

        cmd = [
            self.codex_bin,
            "exec",
            "--skip-git-repo-check",
            "-C",
            str(cwd),
            "--output-last-message",
            str(last_message_path),
        ]
        if model:
            cmd.extend(["-m", model])
        # Monitor must run harness CLI and write artifacts.
        if bypass_sandbox:
            cmd.append("--dangerously-bypass-approvals-and-sandbox")
        else:
            cmd.extend(["-s", "workspace-write"])
        cmd.append("-")  # read prompt from stdin

        env = os.environ.copy()
        # Ensure PerturbTrace imports resolve when the monitor shells out.
        existing = env.get("PYTHONPATH", "")
        pkg = str(cwd)
        env["PYTHONPATH"] = pkg if not existing else f"{pkg}{os.pathsep}{existing}"

        with stdout_path.open("w", encoding="utf-8") as out:
            proc = subprocess.run(
                cmd,
                input=prompt,
                text=True,
                cwd=str(cwd),
                env=env,
                stdout=out,
                stderr=subprocess.STDOUT,
                check=False,
            )

        last_message = ""
        if last_message_path.exists():
            last_message = last_message_path.read_text(encoding="utf-8").strip()
        # Do not fall back to full stdout for path recovery: it contains the
        # prompt template (e.g. run_root: <absolute path>) and confuses parsers.

        return RuntimeResult(
            exit_code=proc.returncode,
            last_message=last_message,
            stdout_path=stdout_path,
            last_message_path=last_message_path,
            command=cmd,
        )

    @staticmethod
    def extract_errors(stdout_path: Path, *, limit: int = 8) -> list[str]:
        if not stdout_path.exists():
            return []
        lines = []
        for line in stdout_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "ERROR" in line or "invalid_request_error" in line:
                lines.append(line.strip())
        return lines[-limit:]
