"""Stable contracts for the decoupled restricted-clean harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

from BDAbench.baselines.framework.types import FeedbackPolicy, Observation, TaskProfile


PromptKind = Literal["system", "initial", "feedback", "final_repair"]
RoleName = Literal["harness", "adapter", "oracle", "solver", "skill", "goal_user"]


@dataclass(frozen=True)
class SkillBundle:
    """Solver-facing strategy skill loaded by the harness.

    The source path is internal audit metadata and must not be placed in solver
    prompts.
    """

    name: str
    description: str
    body: str
    source_path: Path
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillAudit:
    clean: bool
    issues: list[dict[str, str]]


@dataclass(frozen=True)
class HarnessConfig:
    task_profile: TaskProfile
    run_id: str
    strategy_version: str
    feedback_policy: FeedbackPolicy
    web_search_enabled: bool = True
    harness_version: str = "decoupled-harness-v0.1"


@dataclass(frozen=True)
class PromptPacket:
    kind: PromptKind
    system_prompt: str
    user_prompt: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RoundState:
    round_index: int
    observations: list[Observation] = field(default_factory=list)
    already_submitted: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MembershipResult:
    statuses: list[dict[str, str]]
    counts: dict[str, int]
    valid_reserve: list[str]
    note: str = "Candidate membership only; no scores, ranks, hit labels, or replacement suggestions."


class AdapterRole(Protocol):
    """Role that sends prompts to a solver model or subagent."""

    def complete(self, packet: PromptPacket, log_file: Path) -> str:
        ...


class OracleRole(Protocol):
    """Role that validates action space and returns allowed current-run feedback."""

    @property
    def candidate_space(self) -> set[str]:
        ...

    def evaluate(
        self,
        actions: list[str],
        feedback_policy: FeedbackPolicy,
        round_index: int,
        stale_observations: list[Observation] | None = None,
    ) -> list[Observation]:
        ...

