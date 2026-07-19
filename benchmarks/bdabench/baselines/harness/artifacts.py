"""Canonical artifact layout for decoupled harness runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROMPT_FILE_BY_KIND = {
    "initial": "initial_prompt.txt",
    "feedback": "feedback_prompt.txt",
    "final_repair": "final_repair_prompt.txt",
}


@dataclass(frozen=True)
class RunArtifacts:
    """All paths owned by one harness run.

    The canonical run root is:

        <output_dir>/<strategy_version>/<run_id>

    Everything below is relative to that root so downstream evaluators only need
    a run_root plus stable filenames such as RUN_SUMMARY.json and metrics.json.
    """

    root: Path

    @classmethod
    def from_output_dir(cls, output_dir: Path | str, strategy_version: str, run_id: str) -> "RunArtifacts":
        return cls(Path(output_dir) / strategy_version / run_id)

    @property
    def harness_config(self) -> Path:
        return self.root / "harness_config.json"

    @property
    def skill_snapshot_dir(self) -> Path:
        return self.root / "skill_snapshot"

    @property
    def skill_snapshot_file(self) -> Path:
        return self.skill_snapshot_dir / "SKILL.md"

    @property
    def skill_audit(self) -> Path:
        return self.root / "skill_audit.json"

    @property
    def observations(self) -> Path:
        return self.root / "observations.json"

    @property
    def batches(self) -> Path:
        return self.root / "batches.json"

    @property
    def membership_checks(self) -> Path:
        return self.root / "membership_checks.json"

    @property
    def trace_events(self) -> Path:
        return self.root / "trace.jsonl"

    @property
    def metrics(self) -> Path:
        return self.root / "metrics.json"

    @property
    def leakage_audit(self) -> Path:
        return self.root / "leakage_audit.json"

    @property
    def run_summary(self) -> Path:
        return self.root / "RUN_SUMMARY.json"

    def round_dir(self, round_index: int) -> Path:
        return self.root / f"round_{round_index + 1}"

    def round_relative_path(self, round_index: int, filename: str) -> str:
        return f"round_{round_index + 1}/{filename}"

    def system_prompt_relative_path(self, round_index: int) -> str:
        return self.round_relative_path(round_index, "system_prompt.txt")

    def user_prompt_relative_path(self, round_index: int, kind: str) -> str:
        filename = PROMPT_FILE_BY_KIND.get(kind, f"{kind}_prompt.txt")
        return self.round_relative_path(round_index, filename)

    def round_observations(self, round_index: int) -> Path:
        return self.round_dir(round_index) / "observations.json"

    def round_membership_check(self, round_index: int) -> Path:
        return self.round_dir(round_index) / "membership_check.json"

    def next_solver_response_attempt(self, round_index: int) -> Path:
        round_dir = self.round_dir(round_index)
        round_dir.mkdir(parents=True, exist_ok=True)
        attempt = len(list(round_dir.glob("solver_response_attempt_*.txt"))) + 1
        return round_dir / f"solver_response_attempt_{attempt}.txt"

    def next_membership_check_attempt(self, round_index: int) -> Path:
        round_dir = self.round_dir(round_index)
        round_dir.mkdir(parents=True, exist_ok=True)
        attempt = len(list(round_dir.glob("membership_check_attempt_*.json"))) + 1
        return round_dir / f"membership_check_attempt_{attempt}.json"
