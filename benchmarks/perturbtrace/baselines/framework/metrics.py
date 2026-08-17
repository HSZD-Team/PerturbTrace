"""Metric computation for closed-loop perturbation baselines."""

from __future__ import annotations

from collections.abc import Iterable

from .types import ParsedActionBatch, RunMetrics


def _safe_div(num: float, den: float) -> float | None:
    if den == 0:
        return None
    return num / den


def compute_run_metrics(
    batches: list[ParsedActionBatch],
    hit_set: Iterable[str],
    batch_size: int,
    primary_metric_name: str = "final_top_effect_recall",
) -> RunMetrics:
    hits = set(hit_set)
    cumulative_valid: list[str] = []
    total_invalid = 0
    total_duplicates = 0
    parse_failures = 0
    underfilled_rounds = 0
    round_hit_gain: list[int] = []
    last_hit_count = 0

    for batch in batches:
        total_invalid += len(batch.invalid_actions)
        total_duplicates += len(batch.duplicate_actions)
        if not batch.parsed_actions:
            parse_failures += 1
        if len(batch.valid_actions) < batch_size:
            underfilled_rounds += 1
        cumulative_valid.extend(batch.valid_actions)
        current_hit_count = len(set(cumulative_valid).intersection(hits))
        round_hit_gain.append(current_hit_count - last_hit_count)
        last_hit_count = current_hit_count

    unique_valid = set(cumulative_valid)
    total_submitted = sum(len(batch.parsed_actions) for batch in batches)
    hit_count = len(unique_valid.intersection(hits))
    top_effect_recall = _safe_div(hit_count, len(hits))
    precision_at_budget = _safe_div(hit_count, len(unique_valid))

    curve = []
    cumulative = 0
    for gain in round_hit_gain:
        cumulative += gain
        curve.append(_safe_div(cumulative, len(hits)) or 0.0)
    auc_hdc = sum(curve) / len(curve) if curve else None

    return RunMetrics(
        primary_metric_name=primary_metric_name,
        primary_metric_value=top_effect_recall,
        top_effect_recall=top_effect_recall,
        precision_at_budget=precision_at_budget,
        auc_hdc=auc_hdc,
        round_hit_gain=round_hit_gain,
        invalid_action_rate=_safe_div(total_invalid, total_submitted),
        duplicate_action_rate=_safe_div(total_duplicates, total_submitted),
        parse_failure_count=parse_failures,
        batch_fill_failure_rate=_safe_div(underfilled_rounds, len(batches)),
        valid_unique_actions=len(unique_valid),
        total_submitted_actions=total_submitted,
    )

