"""Context management for harness-owned prompt state."""

from __future__ import annotations

import csv
from collections import Counter

from BDAbench.baselines.framework.types import Observation, TaskProfile

from .contracts import MembershipResult

MAX_INLINE_PUBLIC_CANDIDATES = 2000


def _humanize(value: object) -> str:
    return str(value).replace("_", " ")


def _public_candidate_examples(profile: TaskProfile, limit: int | None = None) -> tuple[list[str], int]:
    if not profile.public_candidate_table or not profile.public_candidate_table.exists():
        return [], 0
    values: list[str] = []
    total = 0
    with profile.public_candidate_table.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return [], 0
        column = (
            profile.candidate_id_column
            if profile.candidate_id_column in reader.fieldnames
            else reader.fieldnames[0]
        )
        for row in reader:
            value = row.get(column)
            if not value:
                continue
            total += 1
            if limit is None or len(values) < limit:
                values.append(value)
    return values, total


def _format_public_candidate_block(profile: TaskProfile) -> str:
    delivery = str(profile.candidate_delivery or "artifact_reference").lower()
    visibility = str(profile.action_space_visibility or "public_ids").lower()
    if visibility in {"hidden", "candidate_hidden", "none", "not_visible"}:
        return "\n".join([
            "",
            "Public candidate action space:",
            f"- Visibility: {profile.action_space_visibility}.",
            "- Candidate identifiers are not shown to the solver in this task mode.",
            "- The judge still validates exact membership before oracle submission.",
        ])
    inline_full = delivery in {"inline_full", "full_inline", "inline_public_ids"}
    examples, count = _public_candidate_examples(profile, limit=None if inline_full else 12)
    if not count:
        return ""
    lines = [
        "",
        "Public candidate action space:",
        f"- Visibility: {profile.action_space_visibility}.",
        f"- Delivery: {profile.candidate_delivery}.",
        "- Public artifact: identifiers-only candidate artifact supplied with the task package.",
        f"- Candidate count: {count}.",
        "- Use only action identifiers from this public candidate space.",
        "- The public candidate space contains identifiers only; it does not contain scores, hit labels, hidden ranks, thresholds, or source identity.",
    ]
    if inline_full:
        if count > MAX_INLINE_PUBLIC_CANDIDATES:
            raise ValueError(
                f"Refusing to inline {count} public candidates for {profile.task_id}; "
                f"set candidate_delivery to artifact_reference or raise MAX_INLINE_PUBLIC_CANDIDATES deliberately."
            )
        lines.extend([
            "",
            "Public candidate action identifiers:",
            ", ".join(examples),
        ])
    else:
        example_text = ", ".join(examples)
        lines.append(f"- Identifier examples for format only: {example_text}.")
    return "\n".join(lines)


def build_public_task_brief(profile: TaskProfile) -> str:
    semantics = profile.public_task_semantics
    action_label = _humanize(semantics.get("action_type", "perturbation action"))
    lines = [
        "# Task",
        f"You are selecting {action_label}s for this task: {_humanize(semantics.get('public_task_wording', profile.title))}",
        "",
        "Assay setting:",
        f"- Cell system: {_humanize(semantics.get('cell_system', 'not specified'))}.",
        f"- Perturbation mode: {_humanize(semantics.get('perturbation_mode', 'not specified'))}.",
        f"- Action: {action_label}.",
        f"- Readout: {_humanize(semantics.get('readout', 'not specified'))}.",
        f"- Positive score: {_humanize(semantics.get('score_sign_positive', 'not specified'))}.",
        f"- Negative score: {_humanize(semantics.get('score_sign_negative', 'not specified'))}.",
        "",
        "Objective:",
        f"- In each round, choose {profile.batch_size} previously untested action identifiers.",
        f"- There are {profile.rounds} rounds in this run.",
    ]
    if (
        semantics.get("positive_and_negative_effects_count")
        and semantics.get("prioritize_assay_level_effects_not_generic_ifng_biology")
    ):
        lines.append(
            "- The goal is to select action identifiers whose perturbation is likely to cause large measured changes in the readout; effects in either direction count."
        )
    else:
        lines.append(f"- {profile.objective}")
    candidate_block = _format_public_candidate_block(profile)
    if candidate_block:
        lines.append(candidate_block.rstrip())
    return "\n".join(lines)


def format_observation_feedback(observations: list[Observation], batch_size: int) -> str:
    if not observations:
        return ""
    latest_start = max(0, len(observations) - batch_size)
    latest = observations[latest_start:]
    lines = [
        "# Current-Run Feedback",
        "The following observations are only for actions already tested in this run.",
        f"- Total tested actions: {len(observations)}.",
        f"- Latest round tested actions: {len(latest)}.",
        "",
        "## All Tested Actions",
    ]
    for obs in observations:
        if obs.score is None:
            lines.append(f"- {obs.tested_gene}: feedback=withheld_by_policy")
        else:
            lines.append(
                f"- {obs.tested_gene}: signed_score={obs.score:.6g}; absolute_effect={obs.absolute_effect:.6g}"
            )
    return "\n".join(lines)


def format_no_feedback(observations: list[Observation], batch_size: int) -> str:
    completed_rounds = len(observations) // batch_size
    return "\n".join([
        "# Feedback",
        "Outcome feedback is withheld by the no-feedback policy.",
        f"- Previous submitted rounds: {completed_rounds}.",
        "- No outcomes, scores, effects, ranks, or hit labels are available.",
    ])


def format_round_hit_feedback(observations: list[Observation], batch_size: int, hit_set: set[str]) -> str:
    if not observations:
        return ""
    lines = [
        "# Feedback",
        "Previous submitted round hit counts:",
    ]
    cumulative: set[str] = set()
    for index, start in enumerate(range(0, len(observations), batch_size), start=1):
        round_observations = observations[start:start + batch_size]
        round_genes = {obs.tested_gene for obs in round_observations}
        round_hits = round_genes.intersection(hit_set)
        cumulative.update(round_hits)
        lines.append(
            f"- round {index}: hit_count={len(round_hits)}/{len(round_observations)}; "
            f"cumulative_hit_count={len(cumulative)}"
        )
    return "\n".join(lines)


def build_membership_result(symbols: list[str], candidate_space: set[str], already_submitted: set[str]) -> MembershipResult:
    counts: Counter[str] = Counter()
    statuses: list[dict[str, str]] = []
    seen: set[str] = set()
    valid_reserve: list[str] = []
    for symbol in symbols:
        if symbol in seen:
            status = "duplicate_in_query"
        elif symbol in already_submitted:
            status = "already_tested"
        elif symbol in candidate_space:
            status = "valid_candidate"
            valid_reserve.append(symbol)
        else:
            status = "invalid_symbol"
        seen.add(symbol)
        counts[status] += 1
        statuses.append({"symbol": symbol, "status": status})
    for key in ("valid_candidate", "invalid_symbol", "already_tested", "duplicate_in_query"):
        counts.setdefault(key, 0)
    return MembershipResult(statuses=statuses, counts=dict(counts), valid_reserve=valid_reserve)


def format_membership_for_solver(result: MembershipResult, batch_size: int) -> str:
    issue_rows = [item for item in result.statuses if item["status"] != "valid_candidate"]
    valid_count = result.counts.get("valid_candidate", 0)
    lines = [
        "# Membership Repair",
        "Revise your previous Solution by replacing the action identifiers below.",
    ]
    if issue_rows:
        lines.extend(f"- {item['symbol']}: {item['status']}" for item in issue_rows)
    else:
        lines.append("- none")
    if valid_count != batch_size:
        lines.append(f"- valid_action_count: expected_{batch_size}; received_{valid_count}")
    lines.append(f"Revised Solution must contain exactly {batch_size} valid action identifiers.")
    return "\n".join(lines)
