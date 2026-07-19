"""Shared data contracts for closed-loop perturbation baseline runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


FeedbackPolicy = Literal["true_feedback", "no_feedback", "random_feedback", "stale_feedback"]
LeakageLabel = Literal[
    "clean_general_knowledge",
    "web_supported_but_not_answer_table",
    "suspected_answer_seeking",
    "confirmed_answer_leakage",
]
RunPhase = Literal["exploration", "confirmation", "maintenance"]
LedgerState = Literal["candidate", "promoted", "rejected", "stale", "pruned"]


@dataclass(frozen=True)
class TaskProfile:
    task_id: str
    title: str
    data_name: str
    candidate_table: Path
    hit_set: Path
    public_candidate_table: Path | None
    candidate_id_column: str
    score_column: str
    rounds: int
    batch_size: int
    objective: str
    public_task_semantics: dict[str, Any]
    allowed_feedback_fields: list[str]
    forbidden_agent_inputs: list[str]
    action_space_visibility: str = "public_ids"
    candidate_delivery: str = "artifact_reference"


@dataclass(frozen=True)
class AgentRunConfig:
    task_profile: TaskProfile
    run_id: str
    strategy_version: str
    phase: RunPhase
    feedback_policy: FeedbackPolicy
    model_name: str
    reasoning_level: str | None = None
    prompt_version: str = "v0.1"
    orchestration_version: str = "v0.1"
    web_search_enabled: bool = True
    evidence_cache_version: str | None = None
    generation_params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParsedActionBatch:
    raw_text: str
    parsed_actions: list[str]
    valid_actions: list[str]
    invalid_actions: list[str]
    duplicate_actions: list[str]
    repaired_actions: list[str]


@dataclass(frozen=True)
class Observation:
    tested_gene: str
    score: float | None
    absolute_effect: float | None
    score_semantics: str | None
    feedback_policy: FeedbackPolicy


@dataclass(frozen=True)
class RoundMemory:
    round_index: int
    hypothesis_pool: list[str]
    selection_policy: str
    selected_action_summary: str
    rejected_or_deprioritized: list[str]
    feedback_interpretation: str
    next_strategy_delta: str

    @classmethod
    def empty(cls, round_index: int) -> "RoundMemory":
        return cls(
            round_index=round_index,
            hypothesis_pool=[],
            selection_policy="Not recorded by agent.",
            selected_action_summary="Not recorded by agent.",
            rejected_or_deprioritized=[],
            feedback_interpretation="Not recorded by agent.",
            next_strategy_delta="Not recorded by agent.",
        )


@dataclass(frozen=True)
class LeakageAudit:
    label: LeakageLabel
    evidence_summary: str
    matched_terms: list[str] = field(default_factory=list)
    query_log_paths: list[str] = field(default_factory=list)
    raw_trace_paths: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RunMetrics:
    primary_metric_name: str
    primary_metric_value: float | None
    top_effect_recall: float | None
    precision_at_budget: float | None
    auc_hdc: float | None
    round_hit_gain: list[int]
    invalid_action_rate: float | None
    duplicate_action_rate: float | None
    parse_failure_count: int
    batch_fill_failure_rate: float | None
    valid_unique_actions: int
    total_submitted_actions: int
