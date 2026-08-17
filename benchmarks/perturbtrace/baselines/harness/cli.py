"""CLI for the decoupled restricted-clean harness."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from PerturbTrace.baselines.framework.leakage import LeakageAuditor
from PerturbTrace.baselines.framework.metrics import compute_run_metrics
from PerturbTrace.baselines.framework.oracle import FEEDBACK_SEMANTICS, FEEDBACK_SEMANTICS_VERSION
from PerturbTrace.baselines.framework.trace import TraceWriter
from PerturbTrace.baselines.framework.types import ParsedActionBatch

from .artifacts import RunArtifacts
from .contracts import MembershipResult
from .runner import RestrictedCleanHarness, json_default, observation_from_dict, write_prompt_packet


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TASK_PROFILE = REPO_ROOT / "PerturbTrace" / "baselines" / "task_profiles" / "IFNG.yaml"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "PerturbTrace" / "baselines" / "harness_runs"


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=json_default) + "\n", encoding="utf-8")


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _load_harness(run_root: Path) -> RestrictedCleanHarness:
    artifacts = RunArtifacts(run_root)
    config = _read_json(artifacts.harness_config, {})
    if not config:
        raise SystemExit(f"Missing harness_config.json in {run_root}")
    if config.get("harness_version") != "decoupled-harness-v0.2":
        raise SystemExit(
            f"Run uses incompatible harness_version={config.get('harness_version')!r}; "
            "initialize a new run root with decoupled-harness-v0.2."
        )
    if config.get("feedback_semantics_version") != FEEDBACK_SEMANTICS_VERSION:
        raise SystemExit(
            f"Run uses incompatible feedback semantics; initialize a new run root with "
            f"{FEEDBACK_SEMANTICS_VERSION}."
        )
    if "feedback_seed" not in config:
        raise SystemExit("Run has no persisted feedback_seed; initialize a new run root.")
    return RestrictedCleanHarness(
        repo_root=REPO_ROOT,
        task_profile_path=Path(config["task_profile_path"]),
        skill_path=artifacts.skill_snapshot_dir,
        run_id=config["run_id"],
        strategy_version=config["strategy_version"],
        feedback_policy=config.get("feedback_policy", "true_feedback"),
        feedback_seed=config.get("feedback_seed"),
        web_search_enabled=config.get("web_search_enabled", True),
    )


def _load_observations(run_root: Path):
    return [observation_from_dict(item) for item in _read_json(RunArtifacts(run_root).observations, [])]


def _batch_from_dict(data: dict[str, Any]) -> ParsedActionBatch:
    return ParsedActionBatch(
        raw_text=data.get("raw_text", ""),
        parsed_actions=list(data.get("parsed_actions", [])),
        valid_actions=list(data.get("valid_actions", [])),
        invalid_actions=list(data.get("invalid_actions", [])),
        duplicate_actions=list(data.get("duplicate_actions", [])),
        repaired_actions=list(data.get("repaired_actions", [])),
    )


def _assert_current_round(harness: RestrictedCleanHarness, observations: list, round_index: int) -> None:
    batch_size = harness.config.task_profile.batch_size
    if len(observations) % batch_size != 0:
        raise SystemExit(
            f"Observation count {len(observations)} is not divisible by batch size {batch_size}; run state is inconsistent."
        )
    expected_round = len(observations) // batch_size
    if round_index != expected_round:
        raise SystemExit(
            f"Refusing round_index={round_index}; current run state expects round_index={expected_round}."
        )
    if round_index >= harness.config.task_profile.rounds:
        raise SystemExit(f"All {harness.config.task_profile.rounds} rounds are already complete.")


def _record_solver_response(run_root: Path, round_index: int, raw_text: str) -> Path:
    path = RunArtifacts(run_root).next_solver_response_attempt(round_index)
    path.write_text(raw_text, encoding="utf-8")
    return path


def init_run(args: argparse.Namespace) -> None:
    artifacts = RunArtifacts.from_output_dir(args.output_dir, args.strategy_version, args.run_id)
    run_root = artifacts.root
    if run_root.exists() and any(run_root.iterdir()) and not args.force:
        raise SystemExit(f"Run root already exists; pass --force to overwrite config files: {run_root}")
    trace = TraceWriter(run_root)
    harness = RestrictedCleanHarness(
        repo_root=REPO_ROOT,
        task_profile_path=Path(args.task_profile),
        skill_path=Path(args.skill),
        run_id=args.run_id,
        strategy_version=args.strategy_version,
        feedback_policy=args.feedback_policy,
        feedback_seed=args.feedback_seed,
        web_search_enabled=not args.no_web_search,
    )
    skill_snapshot = artifacts.skill_snapshot_dir
    skill_snapshot.mkdir(parents=True, exist_ok=True)
    artifacts.skill_snapshot_file.write_text(
        Path(args.skill).joinpath("SKILL.md").read_text(encoding="utf-8")
        if Path(args.skill).is_dir()
        else Path(args.skill).read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    _write_json(artifacts.harness_config, {
        "run_id": args.run_id,
        "strategy_version": args.strategy_version,
        "task_profile_path": str(Path(args.task_profile).resolve()),
        "feedback_policy": args.feedback_policy,
        "feedback_seed": harness.config.feedback_seed,
        "feedback_semantics_version": FEEDBACK_SEMANTICS_VERSION,
        "feedback_semantics": FEEDBACK_SEMANTICS[args.feedback_policy],
        "web_search_enabled": not args.no_web_search,
        "harness_version": harness.config.harness_version,
        "skill_name": harness.skill.name,
        "skill_description": harness.skill.description,
    })
    _write_json(artifacts.skill_audit, asdict(harness.skill_audit))
    _write_json(artifacts.observations, [])
    _write_json(artifacts.batches, [])
    _write_json(artifacts.membership_checks, [])
    trace.event("run_initialized", {"run_root": run_root, "run_id": args.run_id})
    print(run_root)


def prepare_round(args: argparse.Namespace) -> None:
    run_root = Path(args.run_root)
    trace = TraceWriter(run_root)
    harness = _load_harness(run_root)
    observations = _load_observations(run_root)
    _assert_current_round(harness, observations, args.round_index)
    packet = harness.build_round_prompt(args.round_index, observations)
    paths = write_prompt_packet(trace, packet, args.round_index)
    print(json.dumps(paths, ensure_ascii=False, indent=2))


def prepare_final(args: argparse.Namespace) -> None:
    run_root = Path(args.run_root)
    artifacts = RunArtifacts(run_root)
    trace = TraceWriter(run_root)
    harness = _load_harness(run_root)
    observations = _load_observations(run_root)
    _assert_current_round(harness, observations, args.round_index)
    raw_draft = Path(args.raw_draft).read_text(encoding="utf-8")
    membership = harness.membership_check(raw_draft, observations)
    checks = _read_json(artifacts.membership_checks, [])
    checks.append(asdict(membership))
    _write_json(artifacts.membership_checks, checks)
    _write_json(artifacts.round_membership_check(args.round_index), asdict(membership))
    packet = harness.build_final_prompt(args.round_index, observations, membership)
    paths = write_prompt_packet(trace, packet, args.round_index)
    trace.event("membership_checked", {"round_index": args.round_index, "counts": membership.counts})
    print(json.dumps(paths, ensure_ascii=False, indent=2))


def submit_final(args: argparse.Namespace) -> None:
    run_root = Path(args.run_root)
    artifacts = RunArtifacts(run_root)
    trace = TraceWriter(run_root)
    harness = _load_harness(run_root)
    observations = _load_observations(run_root)
    _assert_current_round(harness, observations, args.round_index)
    raw_final = Path(args.raw_final).read_text(encoding="utf-8")
    new_observations, batch = harness.submit_final(raw_final, args.round_index, observations)
    all_observations = observations + new_observations
    batches = _read_json(artifacts.batches, [])
    batches.append(batch)
    _write_json(artifacts.observations, [asdict(item) for item in all_observations])
    _write_json(artifacts.batches, batches)
    _write_json(artifacts.round_observations(args.round_index), [asdict(item) for item in new_observations])
    trace.event("round_submitted", {"round_index": args.round_index, "submitted_count": len(new_observations)})
    print(json.dumps({"submitted_count": len(new_observations)}, ensure_ascii=False, indent=2))


def process_response(args: argparse.Namespace) -> None:
    run_root = Path(args.run_root)
    artifacts = RunArtifacts(run_root)
    trace = TraceWriter(run_root)
    harness = _load_harness(run_root)
    observations = _load_observations(run_root)
    _assert_current_round(harness, observations, args.round_index)

    raw_text = Path(args.raw_response).read_text(encoding="utf-8")
    recorded_response = _record_solver_response(run_root, args.round_index, raw_text)
    membership = harness.membership_check(raw_text, observations)
    _write_json(artifacts.next_membership_check_attempt(args.round_index), asdict(membership))
    checks = _read_json(artifacts.membership_checks, [])
    checks.append(asdict(membership))
    _write_json(artifacts.membership_checks, checks)

    counts = membership.counts
    expected = harness.config.task_profile.batch_size
    is_complete = (
        counts.get("valid_candidate", 0) == expected
        and counts.get("invalid_symbol", 0) == 0
        and counts.get("already_tested", 0) == 0
        and counts.get("duplicate_in_query", 0) == 0
    )

    if not is_complete:
        packet = harness.build_final_prompt(args.round_index, observations, membership)
        paths = write_prompt_packet(trace, packet, args.round_index)
        trace.event("repair_required", {
            "round_index": args.round_index,
            "response_path": recorded_response,
            "counts": membership.counts,
            "repair_prompt": paths["user_prompt"],
        })
        print(json.dumps({
            "status": "needs_repair",
            "response_path": str(recorded_response),
            "counts": membership.counts,
            "repair_prompt": paths["user_prompt"],
            "system_prompt": paths.get("system_prompt"),
        }, ensure_ascii=False, indent=2, default=json_default))
        return

    new_observations, batch = harness.submit_final(raw_text, args.round_index, observations)
    all_observations = observations + new_observations
    batches = _read_json(artifacts.batches, [])
    batches.append(batch)
    _write_json(artifacts.observations, [asdict(item) for item in all_observations])
    _write_json(artifacts.batches, batches)
    _write_json(artifacts.round_observations(args.round_index), [asdict(item) for item in new_observations])
    trace.event("round_submitted", {
        "round_index": args.round_index,
        "response_path": recorded_response,
        "submitted_count": len(new_observations),
    })
    print(json.dumps({
        "status": "submitted",
        "response_path": str(recorded_response),
        "submitted_count": len(new_observations),
    }, ensure_ascii=False, indent=2, default=json_default))


def finalize_run(args: argparse.Namespace) -> None:
    run_root = Path(args.run_root)
    artifacts = RunArtifacts(run_root)
    trace = TraceWriter(run_root)
    harness = _load_harness(run_root)
    batches = [_batch_from_dict(item) for item in _read_json(artifacts.batches, [])]
    expected_rounds = harness.config.task_profile.rounds
    if len(batches) != expected_rounds and not args.allow_incomplete:
        raise SystemExit(f"Cannot finalize {len(batches)} rounds; expected {expected_rounds}.")

    metrics = compute_run_metrics(
        batches,
        harness.oracle.hit_set,
        harness.config.task_profile.batch_size,
    )
    raw_paths = sorted(run_root.glob("round_*/*.txt"))
    texts = [path.read_text(encoding="utf-8", errors="replace") for path in raw_paths]
    leakage = LeakageAuditor.for_terms(harness.config.task_profile.forbidden_agent_inputs).audit_texts(
        texts,
        raw_trace_paths=raw_paths,
    )
    metrics_path = trace.write_json(artifacts.metrics.relative_to(run_root).as_posix(), {"metrics": metrics})
    leakage_path = trace.write_json(artifacts.leakage_audit.relative_to(run_root).as_posix(), {"leakage_audit": leakage})
    summary = {
        "run_id": harness.config.run_id,
        "strategy_version": harness.config.strategy_version,
        "task_id": harness.config.task_profile.task_id,
        "harness_version": harness.config.harness_version,
        "feedback_policy": harness.config.feedback_policy,
        "feedback_seed": harness.config.feedback_seed,
        "feedback_semantics_version": FEEDBACK_SEMANTICS_VERSION,
        "feedback_semantics": FEEDBACK_SEMANTICS[harness.config.feedback_policy],
        "rounds_submitted": len(batches),
        "expected_rounds": expected_rounds,
        "complete": len(batches) == expected_rounds,
        "primary_metric": metrics.primary_metric_value,
        "top_effect_recall": metrics.top_effect_recall,
        "precision_at_budget": metrics.precision_at_budget,
        "auc_hdc": metrics.auc_hdc,
        "round_hit_gain": metrics.round_hit_gain,
        "valid_unique_actions": metrics.valid_unique_actions,
        "total_submitted_actions": metrics.total_submitted_actions,
        "invalid_action_rate": metrics.invalid_action_rate,
        "duplicate_action_rate": metrics.duplicate_action_rate,
        "parse_failure_count": metrics.parse_failure_count,
        "batch_fill_failure_rate": metrics.batch_fill_failure_rate,
        "leakage_label": leakage.label,
        "metrics_path": str(metrics_path),
        "leakage_audit_path": str(leakage_path),
    }
    summary_path = trace.write_json(artifacts.run_summary.relative_to(run_root).as_posix(), summary)
    trace.event("run_finalized", summary)
    print(json.dumps({
        "status": "finalized",
        "run_root": str(run_root),
        "metrics_path": str(metrics_path),
        "leakage_audit_path": str(leakage_path),
        "summary_path": str(summary_path),
        "rounds_submitted": len(batches),
        "top_effect_recall": metrics.top_effect_recall,
        "leakage_label": leakage.label,
    }, ensure_ascii=False, indent=2, default=json_default))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_p = subparsers.add_parser("init-run")
    init_p.add_argument("--run-id", required=True)
    init_p.add_argument("--strategy-version", required=True)
    init_p.add_argument("--task-profile", default=str(DEFAULT_TASK_PROFILE))
    init_p.add_argument("--skill", required=True)
    init_p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    init_p.add_argument("--feedback-policy", choices=["true_feedback", "no_feedback", "random_feedback"], default="true_feedback")
    init_p.add_argument("--feedback-seed", type=int)
    init_p.add_argument("--no-web-search", action="store_true")
    init_p.add_argument("--force", action="store_true")
    init_p.set_defaults(func=init_run)

    prep_p = subparsers.add_parser("prepare-round")
    prep_p.add_argument("--run-root", required=True)
    prep_p.add_argument("--round-index", type=int, required=True)
    prep_p.set_defaults(func=prepare_round)

    final_p = subparsers.add_parser("prepare-final")
    final_p.add_argument("--run-root", required=True)
    final_p.add_argument("--round-index", type=int, required=True)
    final_p.add_argument("--raw-draft", required=True)
    final_p.set_defaults(func=prepare_final)

    submit_p = subparsers.add_parser("submit-final")
    submit_p.add_argument("--run-root", required=True)
    submit_p.add_argument("--round-index", type=int, required=True)
    submit_p.add_argument("--raw-final", required=True)
    submit_p.set_defaults(func=submit_final)

    process_p = subparsers.add_parser("process-response")
    process_p.add_argument("--run-root", required=True)
    process_p.add_argument("--round-index", type=int, required=True)
    process_p.add_argument("--raw-response", required=True)
    process_p.set_defaults(func=process_response)

    finalize_p = subparsers.add_parser("finalize-run")
    finalize_p.add_argument("--run-root", required=True)
    finalize_p.add_argument("--allow-incomplete", action="store_true")
    finalize_p.set_defaults(func=finalize_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
