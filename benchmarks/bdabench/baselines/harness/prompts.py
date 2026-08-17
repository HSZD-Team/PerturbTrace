"""Harness-owned prompt templates.

Strategy skills are inserted as content blocks. They do not own role boundaries,
context access, oracle access, or output contracts.
"""

from __future__ import annotations

from .context import (
    build_public_task_brief,
    format_membership_for_solver,
    format_no_feedback,
    format_observation_feedback,
    format_round_hit_feedback,
)
from .contracts import HarnessConfig, MembershipResult, PromptPacket, RoundState, SkillBundle


def build_system_prompt(config: HarnessConfig) -> str:
    return """You are a biomedical discovery agent selecting perturbation actions for an iterative perturbation-screen discovery task.
Use the provided task context and any current-run feedback to choose candidate actions.
Follow the current step's output contract exactly.
"""


def _skill_block(skill: SkillBundle) -> str:
    return f"""# Strategy

{skill.body.strip()}
"""


def build_initial_prompt(config: HarnessConfig, skill: SkillBundle, state: RoundState) -> PromptPacket:
    candidate_artifact = ""
    if str(config.task_profile.candidate_delivery).lower() == "artifact_reference":
        candidate_artifact = """# Candidate Artifact
The identifiers-only public candidate artifact is available as `candidate_actions.csv` in the solver task directory.

"""
    user_prompt = f"""# Initial Solver Prompt

{build_public_task_brief(config.task_profile)}

{candidate_artifact}{_skill_block(skill)}

# Current Run State
- This is round {state.round_index + 1} of {config.task_profile.rounds}.
- No actions have been tested yet in this run.

# Output Contract
Return two sections:

Level 1 - Scientific Evidence and Rationale:
Briefly state the evidence, hypotheses, and selection logic behind your choices.

Level 2 - Executable Action:
Solution: 1. ACTION1, 2. ACTION2, ..., {config.task_profile.batch_size}. ACTION{config.task_profile.batch_size}

The `Solution:` line must contain exactly {config.task_profile.batch_size} unique previously untested action identifiers from the task action space. Do not include prose after the `Solution:` line.
"""
    return PromptPacket(kind="initial", system_prompt=build_system_prompt(config), user_prompt=user_prompt)


def build_feedback_prompt(
    config: HarnessConfig,
    skill: SkillBundle,
    state: RoundState,
    hit_set: set[str] | None,
) -> PromptPacket:
    feedback_style = str(config.task_profile.public_task_semantics.get("feedback_style", "hit_counts"))
    if config.feedback_policy == "no_feedback":
        feedback = format_no_feedback(state.observations, config.task_profile.batch_size)
    elif feedback_style == "tested_scores":
        feedback = format_observation_feedback(state.observations, config.task_profile.batch_size)
    else:
        if hit_set is None:
            raise ValueError("Hit-count feedback requires an explicit feedback hit set.")
        feedback = format_round_hit_feedback(state.observations, config.task_profile.batch_size, hit_set)
    user_prompt = f"""# Feedback Solver Prompt

{feedback}

# Current Run State
- This is round {state.round_index + 1} of {config.task_profile.rounds}.
- {len(state.already_submitted)} actions have already been tested in this run.

# Output Contract
Return two sections:

Level 1 - Scientific Evidence and Rationale:
Briefly state the evidence, hypotheses, and selection logic behind your choices.

Level 2 - Executable Action:
Solution: 1. ACTION1, 2. ACTION2, ..., {config.task_profile.batch_size}. ACTION{config.task_profile.batch_size}

The `Solution:` line must contain exactly {config.task_profile.batch_size} unique previously untested action identifiers from the task action space. Do not include prose after the `Solution:` line.
"""
    return PromptPacket(kind="feedback", system_prompt="", user_prompt=user_prompt)


def build_final_repair_prompt(
    config: HarnessConfig,
    state: RoundState,
    membership: MembershipResult,
) -> PromptPacket:
    user_prompt = f"""# Final Repair Prompt

Round: {state.round_index + 1} of {config.task_profile.rounds}

{format_membership_for_solver(membership, config.task_profile.batch_size)}

# Output Contract
Return one complete revised Solution line and no prose:

Solution: <exactly {config.task_profile.batch_size} unique valid previously untested action identifiers>

Do not include bullets, explanations, or any text before or after the `Solution:` line.
"""
    return PromptPacket(kind="final_repair", system_prompt="", user_prompt=user_prompt)
