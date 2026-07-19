"""Restricted-clean harness orchestration primitives."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from BDAbench.baselines.framework.actions import parse_actions_from_text, validate_action_batch
from BDAbench.baselines.framework.oracle import PerturbationOracle
from BDAbench.baselines.framework.profile import load_task_profile
from BDAbench.baselines.framework.trace import TraceWriter
from BDAbench.baselines.framework.types import FeedbackPolicy, Observation

from .artifacts import RunArtifacts
from .context import build_membership_result
from .contracts import HarnessConfig, MembershipResult, PromptPacket, RoundState, SkillBundle
from .prompts import build_feedback_prompt, build_final_repair_prompt, build_initial_prompt
from .skill_loader import audit_skill_for_solver, load_skill


def json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return asdict(value)
    return str(value)


def observation_from_dict(data: dict[str, Any]) -> Observation:
    return Observation(
        tested_gene=data["tested_gene"],
        score=data.get("score"),
        absolute_effect=data.get("absolute_effect"),
        score_semantics=data.get("score_semantics"),
        feedback_policy=data.get("feedback_policy", "true_feedback"),
    )


class RestrictedCleanHarness:
    def __init__(
        self,
        *,
        repo_root: Path,
        task_profile_path: Path,
        skill_path: Path,
        run_id: str,
        strategy_version: str,
        feedback_policy: FeedbackPolicy = "true_feedback",
        web_search_enabled: bool = True,
    ) -> None:
        profile = load_task_profile(task_profile_path, repo_root)
        skill = load_skill(skill_path)
        audit = audit_skill_for_solver(skill, profile.forbidden_agent_inputs)
        if not audit.clean:
            raise ValueError(f"Skill failed solver-facing audit: {audit.issues}")
        self.config = HarnessConfig(
            task_profile=profile,
            run_id=run_id,
            strategy_version=strategy_version,
            feedback_policy=feedback_policy,
            web_search_enabled=web_search_enabled,
        )
        self.skill = skill
        self.skill_audit = audit
        self.oracle = PerturbationOracle(profile)

    def round_state(self, round_index: int, observations: list[Observation]) -> RoundState:
        return RoundState(
            round_index=round_index,
            observations=observations,
            already_submitted=[obs.tested_gene for obs in observations],
        )

    def build_round_prompt(self, round_index: int, observations: list[Observation]) -> PromptPacket:
        state = self.round_state(round_index, observations)
        if observations:
            return build_feedback_prompt(self.config, self.skill, state, self.oracle.hit_set)
        return build_initial_prompt(self.config, self.skill, state)

    def membership_check(self, raw_draft: str, observations: list[Observation]) -> MembershipResult:
        symbols = parse_actions_from_text(raw_draft)
        already = {obs.tested_gene for obs in observations}
        return build_membership_result(symbols, self.oracle.candidate_space, already)

    def build_final_prompt(
        self,
        round_index: int,
        observations: list[Observation],
        membership: MembershipResult,
    ) -> PromptPacket:
        return build_final_repair_prompt(self.config, self.round_state(round_index, observations), membership)

    def submit_final(self, raw_final: str, round_index: int, observations: list[Observation]) -> tuple[list[Observation], dict[str, Any]]:
        batch = validate_action_batch(
            raw_text=raw_final,
            candidate_space=self.oracle.candidate_space,
            already_tested=[obs.tested_gene for obs in observations],
            batch_size=self.config.task_profile.batch_size,
        )
        if len(batch.valid_actions) != self.config.task_profile.batch_size:
            raise ValueError(
                f"Final batch has {len(batch.valid_actions)} valid actions; expected {self.config.task_profile.batch_size}."
            )
        new_observations = self.oracle.evaluate(
            batch.valid_actions,
            feedback_policy=self.config.feedback_policy,
            round_index=round_index,
        )
        return new_observations, asdict(batch)


def write_prompt_packet(trace: TraceWriter, packet: PromptPacket, round_index: int) -> dict[str, str]:
    artifacts = RunArtifacts(trace.root)
    paths: dict[str, str] = {}
    if packet.system_prompt.strip():
        system_path = trace.write_text(artifacts.system_prompt_relative_path(round_index), packet.system_prompt)
        paths["system_prompt"] = str(system_path)
    user_path = trace.write_text(artifacts.user_prompt_relative_path(round_index, packet.kind), packet.user_prompt)
    paths["user_prompt"] = str(user_path)
    trace.event("prompt_written", {
        "round_index": round_index,
        "kind": packet.kind,
        "system_prompt": paths.get("system_prompt"),
        "user_prompt": user_path,
    })
    return paths
