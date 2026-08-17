#!/usr/bin/env python3
"""Evaluate completed PerturbTrace harness traces from a user-owned manifest.

This script deliberately has no dependency on Chef's command dispatcher.  It
reads immutable run artifacts and writes every analysis artifact below the
explicit --output-dir supplied by the caller.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import os
import random
import re
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import yaml
from scipy.stats import hypergeom


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
PROTOCOL_DIR = SKILL_DIR / "protocol"
PROMPT_VERSION = "v2"
VALID = {
    "grounding": {"0", "1", "2", "NA"},
    "operation": {"maintain_reinforce", "expand", "narrow_prune", "pivot", "mixed", "none", "unclear"},
    "calibration": {"calibrated", "over_attributed", "unclear", "NA"},
    "uncertainty_update": {"increased", "decreased", "acknowledged", "not_stated", "unclear"},
}
ESTABLISHED = {"calibrated_update", "over_attributed_update"}
OUTCOME_VALID = {"enriched", "expected_range", "depleted"}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def read_json(path: Path) -> Any:
    return json.loads(read_text(path))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in read_text(path).splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str] | None = None) -> None:
    data = list(rows)
    if fields is None:
        fields = list(data[0]) if data else []
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compact(value: str, limit: int) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    return value if len(value) <= limit else value[: limit - 3].rstrip() + "..."


def protocol_hashes() -> dict[str, str]:
    return {path.name: digest_file(path) for path in sorted(PROTOCOL_DIR.iterdir()) if path.is_file()}


def extract_rationale(raw: str) -> str:
    marker = re.search(
        r"Level\s*1\s*[-:\u2013\u2014]?\s*Scientific Evidence and Rationale\s*:\s*",
        raw,
        flags=re.IGNORECASE,
    )
    if not marker:
        return ""
    tail = raw[marker.end() :]
    stop = re.search(r"\n\s*(?:Level\s*2\s*[-:\u2013\u2014]?\s*Executable Action\s*:|Solution\s*:)", tail, flags=re.IGNORECASE)
    return (tail[: stop.start()] if stop else tail).strip().strip("<>").strip()


def feedback_section(prompt: str) -> str:
    normalized = prompt.replace("\r\n", "\n")
    start = normalized.find("# Feedback")
    if start < 0:
        start = normalized.find("# Current-Run Feedback")
    if start < 0:
        return normalized.strip()
    end = normalized.find("# Current Run State", start)
    return normalized[start : end if end >= 0 else None].strip()


def parse_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "run_root" not in reader.fieldnames:
            raise ValueError("Trace manifest must include a run_root column.")
        rows = [{key: (value or "").strip() for key, value in row.items()} for row in reader]
    if not rows:
        raise ValueError("Trace manifest has no rows.")
    seen: set[Path] = set()
    for row in rows:
        if not row["run_root"]:
            raise ValueError("Trace manifest has an empty run_root.")
        root = Path(row["run_root"]).expanduser().resolve()
        if root in seen:
            raise ValueError(f"Duplicate run_root in manifest: {root}")
        seen.add(root)
        row["run_root"] = str(root)
        row.setdefault("case_id", "")
        row.setdefault("group", "")
        row.setdefault("codebook_task_id", "")
    return rows


def find_package_root(task_manifest: Path) -> Path:
    for parent in [task_manifest.parent, *task_manifest.parents]:
        if parent.name == "tasks":
            return parent.parent
    return task_manifest.parent


def resolve_reference(raw_value: str, task_manifest: Path) -> Path:
    raw = Path(raw_value)
    package_root = find_package_root(task_manifest)
    candidates = [raw, package_root / raw, task_manifest.parent / raw, task_manifest.parent / "hidden" / raw.name]
    if raw.parts and raw.parts[0] == "BDAbench":
        candidates.insert(1, package_root / Path(*raw.parts[1:]))
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"Could not resolve declared task artifact {raw_value!r} from {task_manifest}")


def task_artifacts(task_manifest: Path) -> dict[str, Any]:
    document = yaml.safe_load(read_text(task_manifest))
    if not isinstance(document, dict):
        raise ValueError(f"Task manifest is not a mapping: {task_manifest}")
    data = document.get("data") or document.get("paths")
    if not isinstance(data, dict):
        raise ValueError(f"Task manifest has no data/paths mapping: {task_manifest}")
    candidate_ref = data.get("public_candidate_actions") or data.get("candidate_table")
    hit_ref = data.get("hit_set")
    if not candidate_ref or not hit_ref:
        raise ValueError(f"Task manifest lacks candidate or hidden-hit path: {task_manifest}")
    candidate_path = resolve_reference(str(candidate_ref), task_manifest)
    hit_path = resolve_reference(str(hit_ref), task_manifest)
    column = str(data.get("candidate_id_column") or ("action_id" if "data" in document else "Gene"))
    with candidate_path.open(newline="", encoding="utf-8-sig") as handle:
        candidates = {str(row[column]).strip() for row in csv.DictReader(handle) if row.get(column)}
    brief = task_manifest.parent / "public_task_brief.md"
    context = read_text(brief) if brief.exists() else str(document.get("title") or document.get("task_id") or "")
    return {
        "document": document,
        "candidate_path": candidate_path,
        "candidate_set": candidates,
        "hit_path": hit_path,
        "context": context,
        "brief_path": brief if brief.exists() else None,
    }


def accepted_response_paths(run_root: Path) -> dict[int, Path]:
    paths: dict[int, Path] = {}
    events_path = run_root / "trace.jsonl"
    if events_path.exists():
        for event in read_jsonl(events_path):
            if event.get("event_type") != "round_submitted":
                continue
            payload = event.get("payload") or {}
            if "round_index" not in payload or not payload.get("response_path"):
                continue
            path = Path(str(payload["response_path"]))
            if not path.is_absolute():
                path = run_root / path
            if path.exists():
                paths[int(payload["round_index"])] = path.resolve()
    return paths


def run_rounds(run_root: Path, batches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    response_paths = accepted_response_paths(run_root)
    rounds = []
    for index, batch in enumerate(batches):
        round_dir = run_root / f"round_{index + 1}"
        response_path = response_paths.get(index)
        if response_path is None:
            candidates = sorted(round_dir.glob("solver_response_attempt_*.txt"))
            if len(candidates) == 1:
                response_path = candidates[0].resolve()
            elif len(candidates) > 1:
                raise ValueError(
                    f"Cannot identify the accepted solver response for {run_root} round {index + 1}; "
                    "trace.jsonl has no accepted response_path and multiple attempts exist."
                )
        raw = read_text(response_path) if response_path and response_path.exists() else ""
        actions = batch.get("parsed_actions") or batch.get("valid_actions") or batch.get("actions")
        if not isinstance(actions, list) or not actions:
            raise ValueError(f"No accepted action list for {run_root} round {index + 1}")
        feedback_path = round_dir / "feedback_prompt.txt"
        rounds.append(
            {
                "round": index + 1,
                "actions": [str(action) for action in actions],
                "rationale": extract_rationale(raw),
                "rationale_path": str(response_path) if response_path else "",
                "rationale_sha256": digest_file(response_path) if response_path else "",
                "feedback": feedback_section(read_text(feedback_path)) if feedback_path.exists() else "",
                "feedback_path": str(feedback_path.resolve()) if feedback_path.exists() else "",
                "feedback_sha256": digest_file(feedback_path) if feedback_path.exists() else "",
            }
        )
    return rounds


def codebook_modules(codebooks: dict[str, Any], codebook_task_id: str) -> list[dict[str, str]]:
    if not codebook_task_id:
        return []
    task = (codebooks.get("tasks") or {}).get(codebook_task_id)
    if not task:
        available = ", ".join(sorted((codebooks.get("tasks") or {}).keys()))
        raise ValueError(f"Unknown codebook_task_id {codebook_task_id!r}; available keys: {available}")
    return [
        {"id": str(module["id"]), "description": str(module["description"])}
        for module in task.get("modules", [])
        if module.get("id") != "other_uncertain"
    ]


def partition_packets(rows: list[dict[str, Any]], fraction: float) -> tuple[set[str], set[str], set[str]]:
    if not 0 < fraction <= 1:
        raise ValueError("--double-code-fraction must be in (0, 1].")
    by_stratum: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = "|".join([row.get("group", ""), row.get("feedback_policy", ""), str(row["transition_index"])])
        by_stratum[key].append(row)
    selected = {
        min(values, key=lambda row: digest_text(row["packet_id"]))["packet_id"]
        for values in by_stratum.values()
    }
    target = max(len(selected), math.ceil(len(rows) * fraction))
    for row in sorted(rows, key=lambda item: digest_text(item["packet_id"])):
        if len(selected) >= target:
            break
        selected.add(row["packet_id"])
    ordered = sorted(selected, key=digest_text)
    development = set(ordered[::2])
    confirmation = set(ordered[1::2])
    remaining = {row["packet_id"] for row in rows} - selected
    return development, confirmation, remaining


def build_inputs(manifest_rows: list[dict[str, str]], output: Path, fraction: float) -> dict[str, Any]:
    codebooks = read_json(PROTOCOL_DIR / "module_codebooks_v1.json")
    trajectories: list[dict[str, Any]] = []
    state_packets: list[dict[str, Any]] = []
    packet_map: list[dict[str, Any]] = []
    artifacts_cache: dict[Path, dict[str, Any]] = {}
    for row in manifest_rows:
        run_root = Path(row["run_root"])
        required = [run_root / "RUN_SUMMARY.json", run_root / "harness_config.json", run_root / "batches.json"]
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"Run root is not a supported completed harness run: {run_root}; missing {missing}")
        summary = read_json(run_root / "RUN_SUMMARY.json")
        if not summary.get("complete"):
            raise ValueError(f"Trace evaluation accepts completed runs only: {run_root}")
        config = read_json(run_root / "harness_config.json")
        profile_value = config.get("task_profile_path")
        if not profile_value:
            raise ValueError(f"Run config has no task_profile_path: {run_root}")
        task_manifest = Path(str(profile_value)).expanduser().resolve()
        if not task_manifest.exists():
            raise FileNotFoundError(f"Task profile referenced by run is unavailable: {task_manifest}")
        if task_manifest not in artifacts_cache:
            artifacts_cache[task_manifest] = task_artifacts(task_manifest)
        task = artifacts_cache[task_manifest]
        batches = read_json(run_root / "batches.json")
        if not isinstance(batches, list) or len(batches) < 2:
            raise ValueError(f"Trace evaluation needs at least two completed rounds: {run_root}")
        rounds = run_rounds(run_root, batches)
        for round_data in rounds:
            invalid = set(round_data["actions"]) - task["candidate_set"]
            if invalid:
                raise ValueError(f"Accepted actions outside task candidate space in {run_root}: {sorted(invalid)[:5]}")
        case_id = row["case_id"] or str(config.get("run_id") or run_root.name)
        policy = str(config.get("feedback_policy") or "unknown")
        if policy not in {"true_feedback", "random_feedback", "no_feedback"}:
            raise ValueError(f"Unsupported or missing feedback_policy in {run_root}: {policy!r}")
        modules = codebook_modules(codebooks, row["codebook_task_id"])
        trajectory = {
            "case_id": case_id,
            "group": row["group"],
            "codebook_task_id": row["codebook_task_id"],
            "run_root": str(run_root),
            "run_id": str(config.get("run_id") or run_root.name),
            "task_id": str(summary.get("task_id") or task["document"].get("task_id") or ""),
            "feedback_policy": policy,
            "feedback_seed": config.get("feedback_seed"),
            "task_context": task["context"],
            "task_context_path": str(task["brief_path"]) if task["brief_path"] else "",
            "task_manifest": str(task_manifest),
            "candidate_path": str(task["candidate_path"]),
            "candidate_count": len(task["candidate_set"]),
            "hit_path": str(task["hit_path"]),
            "reported_round_hits": summary.get("round_hit_gain") or [],
            "rounds": rounds,
        }
        trajectories.append(trajectory)
        for transition_index in range(1, len(rounds)):
            previous = rounds[transition_index - 1]
            current = rounds[transition_index]
            packet_id = digest_text(f"perturbtrace-trace-v2|{case_id}|{transition_index}")[:24]
            state_packets.append(
                {
                    "packet_id": packet_id,
                    "task_context": task["context"],
                    "module_vocabulary": modules,
                    "previous_externalized_state_text": previous["rationale"],
                    "delivered_feedback_text": current["feedback"],
                    "current_rationale_text": current["rationale"],
                }
            )
            packet_map.append(
                {
                    "packet_id": packet_id,
                    "case_id": case_id,
                    "group": row["group"],
                    "codebook_task_id": row["codebook_task_id"],
                    "run_id": trajectory["run_id"],
                    "task_id": trajectory["task_id"],
                    "feedback_policy": policy,
                    "feedback_seed": trajectory["feedback_seed"],
                    "transition_index": transition_index,
                    "transition": f"F{transition_index}->S{transition_index + 1}->A{transition_index + 1}->O{transition_index + 1}",
                    "run_root": str(run_root),
                    "previous_rationale_path": previous["rationale_path"],
                    "current_rationale_path": current["rationale_path"],
                    "feedback_path": current["feedback_path"],
                }
            )
    if len({row["case_id"] for row in packet_map}) != len(trajectories):
        raise ValueError("case_id values must be unique across the supplied manifest.")
    development, confirmation, remaining = partition_packets(packet_map, fraction)
    for row in packet_map:
        if row["packet_id"] in development:
            row["double_code_partition"] = "development"
        elif row["packet_id"] in confirmation:
            row["double_code_partition"] = "confirmation"
        else:
            row["double_code_partition"] = "remaining"
    serialized = json.dumps(state_packets, ensure_ascii=False)
    forbidden = ["true_feedback", "random_feedback", "no_feedback"]
    hits = [value for value in forbidden if value in serialized]
    if hits:
        raise ValueError(f"Blinded state packets leak condition metadata: {hits}")
    write_jsonl(output / "trajectories.jsonl", trajectories)
    write_jsonl(output / "state_blinded_packets.jsonl", state_packets)
    write_csv(output / "packet_key_map.csv", packet_map)
    report = {
        "trajectory_count": len(trajectories),
        "transition_count": len(state_packets),
        "double_code_development": len(development),
        "double_code_confirmation": len(confirmation),
        "remaining_primary_coding": len(remaining),
        "state_packets_condition_blinded": True,
        "state_packet_forbidden_condition_hits": hits,
        "codebook_unavailable_case_ids": [item["case_id"] for item in trajectories if not item["codebook_task_id"]],
    }
    write_json(output / "input_build_report.json", report)
    return report


def load_api_key(api_key_file: str | None) -> str:
    direct = os.environ.get("BDA_OPENAI_API_KEY", "").strip()
    if direct:
        return direct
    if not api_key_file:
        raise RuntimeError("Set BDA_OPENAI_API_KEY or provide --api-key-file for independent trace judging.")
    path = Path(api_key_file).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Judge API key file does not exist: {path}")
    key = read_text(path).strip().split(":", 1)[-1].strip()
    if not key:
        raise RuntimeError(f"Judge API key file is empty: {path}")
    return key


def parse_response_array(text: str) -> list[dict[str, Any]]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    start, end = cleaned.find("["), cleaned.rfind("]")
    if start < 0 or end < start:
        raise ValueError("Judge response contains no JSON array.")
    value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, list):
        raise ValueError("Judge response is not a JSON array.")
    return value


def validate_labels(rows: list[dict[str, Any]], packets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expected = {item["packet_id"] for item in packets}
    if {str(item.get("packet_id", "")) for item in rows} != expected or len(rows) != len(packets):
        raise ValueError("Judge response does not cover exactly the supplied packet IDs.")
    modules = {item["packet_id"]: {module["id"] for module in item["module_vocabulary"]} for item in packets}
    normalized = []
    for row in rows:
        packet_id = str(row["packet_id"])
        item = {
            "packet_id": packet_id,
            "grounding": str(row.get("grounding", "")),
            "operation": str(row.get("operation", "")),
            "calibration": str(row.get("calibration", "")),
            "priority_up_modules": list(dict.fromkeys(row.get("priority_up_modules") or [])),
            "priority_down_modules": list(dict.fromkeys(row.get("priority_down_modules") or [])),
            "retained_modules": list(dict.fromkeys(row.get("retained_modules") or [])),
            "uncertainty_update": str(row.get("uncertainty_update", "")),
            "feedback_evidence_quote": str(row.get("feedback_evidence_quote", ""))[:500],
            "state_evidence_quote": str(row.get("state_evidence_quote", ""))[:500],
            "annotation_note": str(row.get("annotation_note", ""))[:800],
        }
        for key, allowed in VALID.items():
            if item[key] not in allowed:
                raise ValueError(f"Invalid {key} value for {packet_id}: {item[key]!r}")
        for key in ("priority_up_modules", "priority_down_modules", "retained_modules"):
            invalid = set(item[key]) - modules[packet_id]
            if invalid:
                raise ValueError(f"Unknown module IDs for {packet_id}: {sorted(invalid)}")
        normalized.append(item)
    return sorted(normalized, key=lambda item: item["packet_id"])


def judge_packets(
    packets: list[dict[str, Any]],
    coder: str,
    scope: str,
    model: str,
    api_key: str,
    base_url: str | None,
    workers: int,
    output: Path,
) -> list[dict[str, Any]]:
    from openai import OpenAI

    prompt = read_text(PROTOCOL_DIR / "STATE_CODER_PROMPT_V2.md")
    ordered = sorted(packets, key=lambda item: item["packet_id"], reverse=coder == "B")
    result_path = output / f"state_labels_coder_{coder}_{scope}_{PROMPT_VERSION}.jsonl"
    existing = {row["packet_id"]: row for row in read_jsonl(result_path)} if result_path.exists() else {}
    pending = [item for item in ordered if item["packet_id"] not in existing]
    log_dir = output / "judge_logs" / f"coder_{coder}_{scope}_{PROMPT_VERSION}"
    log_dir.mkdir(parents=True, exist_ok=True)

    def call(index: int, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        client = OpenAI(api_key=api_key, timeout=120, max_retries=0, **({"base_url": base_url} if base_url else {}))
        raw = ""
        for attempt in range(1, 4):
            try:
                response = client.responses.create(
                    model=model,
                    instructions=prompt,
                    input=json.dumps({"records": batch}, ensure_ascii=False),
                    max_output_tokens=12000,
                    reasoning={"effort": "medium"},
                )
                raw = str(response.output_text or "").strip()
                labels = validate_labels(parse_response_array(raw), batch)
                write_json(log_dir / f"batch_{index:04d}.json", {
                    "coder": coder, "scope": scope, "model": model,
                    "packet_ids": [item["packet_id"] for item in batch],
                    "response_id": getattr(response, "id", ""), "raw_output": raw,
                    "api_key_recorded": False,
                })
                return labels
            except Exception as exc:
                write_json(log_dir / f"batch_{index:04d}_attempt_{attempt}_error.json", {
                    "coder": coder, "scope": scope, "model": model,
                    "packet_ids": [item["packet_id"] for item in batch],
                    "error": f"{type(exc).__name__}: {exc}", "raw_output": raw,
                    "api_key_recorded": False,
                })
                if attempt == 3:
                    raise
                time.sleep(min(5 * attempt, 15) + random.random())
        raise RuntimeError("Unreachable judge retry state")

    batches = [pending[index : index + 8] for index in range(0, len(pending), 8)]
    completed = dict(existing)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(call, index, batch): index for index, batch in enumerate(batches)}
        for future in as_completed(futures):
            for label in future.result():
                completed[label["packet_id"]] = label
            write_jsonl(result_path, [completed[key] for key in sorted(completed)])
    if set(completed) != {item["packet_id"] for item in packets}:
        raise RuntimeError(f"Judge {coder} {scope} did not produce complete coverage.")
    write_json(output / f"state_judge_config_{coder}_{scope}_{PROMPT_VERSION}.json", {
        "coder": coder, "scope": scope, "model": model, "packet_count": len(packets),
        "prompt_sha256": digest_file(PROTOCOL_DIR / "STATE_CODER_PROMPT_V2.md"),
        "independent_call_context": True, "reverse_order_for_coder_b": coder == "B", "api_key_recorded": False,
    })
    return [completed[key] for key in sorted(completed)]


def cohen_kappa(left: list[str], right: list[str], weighted: bool = False) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    labels = sorted(set(left) | set(right))
    index = {label: position for position, label in enumerate(labels)}
    observed = np.zeros((len(labels), len(labels)), dtype=float)
    for a, b in zip(left, right):
        observed[index[a], index[b]] += 1
    observed /= len(left)
    left_marginal, right_marginal = observed.sum(axis=1), observed.sum(axis=0)
    expected = np.outer(left_marginal, right_marginal)
    if weighted:
        distance = np.abs(np.subtract.outer(np.arange(len(labels)), np.arange(len(labels))))
        weights = 1 - (distance / max(len(labels) - 1, 1)) ** 2
    else:
        weights = np.eye(len(labels))
    denominator = float((weights * expected).sum())
    return None if denominator == 0 else float((weights * observed).sum() / denominator)


def reliability(a: list[dict[str, Any]], b: list[dict[str, Any]], minimum: int) -> dict[str, Any]:
    left, right = {row["packet_id"]: row for row in a}, {row["packet_id"]: row for row in b}
    shared = sorted(set(left) & set(right))
    values = {
        "grounding_quadratic_weighted_kappa": cohen_kappa([left[key]["grounding"] for key in shared], [right[key]["grounding"] for key in shared], weighted=True),
        "operation_cohen_kappa": cohen_kappa([left[key]["operation"] for key in shared], [right[key]["operation"] for key in shared]),
        "calibration_cohen_kappa": cohen_kappa([left[key]["calibration"] for key in shared], [right[key]["calibration"] for key in shared]),
    }
    estimable = len(shared) >= minimum and all(value is not None for value in values.values())
    gate = estimable and all(float(value) >= 0.70 for value in values.values())
    return {"packet_count": len(shared), "minimum_packets": minimum, "estimable": estimable, "gate_pass": gate if estimable else None, "fields": values,
            "boundary": "Independent judge-judge agreement; not human agreement and not adjudicated consensus."}


def feedback_state_label(policy: str, state: dict[str, Any]) -> str:
    if policy == "no_feedback":
        return "not_applicable_control"
    if state["grounding"] == "0" or state["operation"] == "none":
        return "no_observable_update"
    if state["grounding"] == "1" or state["operation"] == "unclear" or state["calibration"] == "unclear":
        return "indeterminate"
    if state["grounding"] == "2" and state["calibration"] == "over_attributed":
        return "over_attributed_update"
    if state["grounding"] == "2" and state["calibration"] == "calibrated":
        return "calibrated_update"
    return "indeterminate"


def annotation_text(record: dict[str, Any]) -> str:
    return " ".join([str(record.get(key, "")) for key in ("query", "symbol", "name", "summary")] + list(record.get("go_bp_terms") or [])).lower()


def fetch_gene_annotations(genes: set[str], output: Path) -> dict[str, dict[str, Any]]:
    from urllib.parse import quote
    from urllib.request import urlopen

    cache_path = output / "public_gene_annotations.jsonl"
    cached = {str(row.get("query")): row for row in read_jsonl(cache_path)} if cache_path.exists() else {}
    for gene in sorted(genes - set(cached)):
        record: dict[str, Any] = {"query": gene, "notfound": True}
        try:
            url = "https://mygene.info/v3/query?q=" + quote(f"symbol:{gene}") + "&species=human&fields=symbol,name,summary,go.BP&size=1"
            with urlopen(url, timeout=20) as response:  # nosec B310: fixed public HTTPS endpoint
                payload = json.loads(response.read().decode("utf-8"))
            hits = payload.get("hits") or []
            if hits:
                hit = hits[0]
                bp = (hit.get("go") or {}).get("BP") or []
                if isinstance(bp, dict):
                    bp = [bp]
                record = {
                    "query": gene, "symbol": hit.get("symbol", gene), "name": hit.get("name", ""),
                    "summary": hit.get("summary", ""), "go_bp_terms": [str(item.get("term", "")) for item in bp if isinstance(item, dict)],
                    "notfound": False,
                }
        except Exception as exc:  # Annotation loss is handled as other_uncertain coverage.
            record["annotation_error"] = f"{type(exc).__name__}: {exc}"
        cached[gene] = record
        write_jsonl(cache_path, [cached[key] for key in sorted(cached)])
    return cached


def assign_module(action: str, record: dict[str, Any], modules: list[dict[str, Any]]) -> str:
    text = annotation_text(record)
    best_score, best_order, best_id = 0.0, len(modules), "other_uncertain"
    for order, module in enumerate(modules):
        score = 0.0
        for pattern in module.get("symbol_patterns", []):
            if re.search(pattern, action.upper()):
                score += 8.0
        for keyword in module.get("keywords", []):
            if str(keyword).lower() in text:
                score += 2.0 if " " in str(keyword) or len(str(keyword)) >= 8 else 1.0
        if score > best_score or (score == best_score and score > 0 and order < best_order):
            best_score, best_order, best_id = score, order, str(module["id"])
    return best_id if best_score > 0 else "other_uncertain"


def action_compositions(trajectories: list[dict[str, Any]], output: Path) -> tuple[dict[tuple[str, int], dict[str, Any]], dict[str, Any]]:
    codebooks = read_json(PROTOCOL_DIR / "module_codebooks_v1.json")
    by_codebook: dict[str, set[str]] = defaultdict(set)
    for trajectory in trajectories:
        key = trajectory["codebook_task_id"]
        if key:
            by_codebook[key].update(action for round_data in trajectory["rounds"] for action in round_data["actions"])
    annotations = fetch_gene_annotations(set().union(*by_codebook.values()) if by_codebook else set(), output) if by_codebook else {}
    maps: dict[tuple[str, str], str] = {}
    map_rows = []
    for key, genes in sorted(by_codebook.items()):
        modules = (codebooks["tasks"][key].get("modules") or [])
        for gene in sorted(genes):
            module = assign_module(gene, annotations.get(gene, {"query": gene}), modules)
            maps[(key, gene)] = module
            map_rows.append({"codebook_task_id": key, "action": gene, "primary_module": module})
    compositions: dict[tuple[str, int], dict[str, Any]] = {}
    coverage = []
    for trajectory in trajectories:
        key = trajectory["codebook_task_id"]
        modules = (codebooks.get("tasks", {}).get(key, {}).get("modules") or [])
        module_ids = [str(module["id"]) for module in modules]
        for round_data in trajectory["rounds"]:
            actions = round_data["actions"]
            if not module_ids:
                composition = {}
                other_fraction, assessable = 1.0, False
            else:
                counts = Counter(maps.get((key, action), "other_uncertain") for action in actions)
                composition = {
                    module: {
                        "count": counts[module], "proportion": counts[module] / len(actions),
                        "state": "absent" if counts[module] == 0 else "major" if counts[module] / len(actions) >= 0.10 else "minor",
                    }
                    for module in module_ids
                }
                other_fraction = counts["other_uncertain"] / len(actions)
                assessable = other_fraction <= 0.30
            record = {"case_id": trajectory["case_id"], "round": round_data["round"], "assessable": assessable,
                      "other_uncertain_fraction": other_fraction, "composition": composition}
            compositions[(trajectory["case_id"], round_data["round"])] = record
            coverage.append({key: value for key, value in record.items() if key != "composition"})
    write_csv(output / "action_primary_module_map.csv", map_rows)
    write_jsonl(output / "action_module_compositions.jsonl", compositions.values())
    write_csv(output / "action_module_coverage.csv", coverage)
    report = {"mapping_rows": len(map_rows), "batch_rows": len(coverage), "unassessable_batches": sum(not row["assessable"] for row in coverage), "hidden_oracle_used": False}
    write_json(output / "action_module_mapping_report.json", report)
    return compositions, report


def state_action_label(state: dict[str, Any], previous: dict[str, Any], current: dict[str, Any]) -> tuple[str, str]:
    if not previous["assessable"] or not current["assessable"]:
        return "unassessable", "missing codebook or insufficient public action-module coverage"
    operation = state["operation"]
    up, down, retained = state["priority_up_modules"], state["priority_down_modules"], state["retained_modules"]
    if operation in {"none", "unclear"}:
        return "unassessable", "state operation absent or unclear"
    if operation == "maintain_reinforce" and not retained:
        return "unassessable", "maintain has no retained module"
    if operation == "expand" and not up:
        return "unassessable", "expand has no priority-up module"
    if operation == "narrow_prune" and (not down or not retained):
        return "unassessable", "narrow/prune lacks declared directions"
    if operation == "pivot" and (not up or not down):
        return "unassessable", "pivot lacks declared directions"
    if operation == "mixed" and sum(bool(item) for item in (up, down, retained)) < 2:
        return "unassessable", "mixed operation lacks two components"
    old, new = previous["composition"], current["composition"]
    if any(module not in new for module in up + down + retained):
        return "unassessable", "state/action module vocabularies cannot be matched"
    level = {"absent": 0, "minor": 1, "major": 2}
    retain_ok = all(level[new[module]["state"]] >= level[old[module]["state"]] for module in retained)
    up_ok = any(level[new[module]["state"]] > level[old[module]["state"]] for module in up)
    down_ok = any(level[new[module]["state"]] < level[old[module]["state"]] for module in down)
    contradictions = any(new[module]["state"] == "absent" for module in up + retained) or any(new[module]["state"] == "major" for module in down)
    if contradictions:
        return "mismatch", "declared modules contradict current action composition"
    if operation == "maintain_reinforce":
        passed, partial = retain_ok, bool(retained)
    elif operation == "expand":
        passed, partial = retain_ok and up_ok, retain_ok or up_ok
    elif operation == "narrow_prune":
        retained_share = sum(new[m]["proportion"] for m in retained) > sum(old[m]["proportion"] for m in retained)
        passed, partial = down_ok and retained_share, down_ok or retained_share
    elif operation == "pivot":
        pivot_up = any(new[m]["state"] == "major" for m in up)
        pivot_down = any(old[m]["state"] == "major" and new[m]["state"] != "major" for m in down)
        passed, partial = pivot_up and pivot_down, pivot_up or pivot_down
    else:
        parts = ([retain_ok] if retained else []) + ([up_ok] if up else []) + ([down_ok] if down else [])
        passed, partial = bool(parts) and all(parts), any(parts)
    return ("aligned", "operation-direction checks passed") if passed else ("partially_aligned", "partial direction support") if partial else ("mismatch", "declared operation is not reflected in actions")


def outcome(candidate_count: int, hit_set: set[str], prior_actions: set[str], current_actions: list[str]) -> dict[str, Any]:
    remaining_hits = hit_set - prior_actions
    n_remaining, h_remaining, batch_size = candidate_count - len(prior_actions), len(remaining_hits), len(current_actions)
    true_hits = len(set(current_actions) & remaining_hits)
    if not h_remaining:
        return {"n_remaining": n_remaining, "h_remaining": h_remaining, "batch_size": batch_size, "true_hits": true_hits, "random_expected_hits": 0.0, "rhe": None, "upper_tail_p": None, "lower_tail_p": None, "outcome_class": "no_hits_remaining"}
    expectation = batch_size * h_remaining / n_remaining
    upper, lower = float(hypergeom.sf(true_hits - 1, n_remaining, h_remaining, batch_size)), float(hypergeom.cdf(true_hits, n_remaining, h_remaining, batch_size))
    label = "enriched" if upper <= 0.025 else "depleted" if lower <= 0.025 else "expected_range"
    return {"n_remaining": n_remaining, "h_remaining": h_remaining, "batch_size": batch_size, "true_hits": true_hits, "random_expected_hits": expectation,
            "rhe": (true_hits / batch_size) / (h_remaining / n_remaining), "upper_tail_p": upper, "lower_tail_p": lower, "outcome_class": label}


def score(output: Path) -> list[dict[str, Any]]:
    trajectories = {row["case_id"]: row for row in read_jsonl(output / "trajectories.jsonl")}
    with (output / "packet_key_map.csv").open(newline="", encoding="utf-8-sig") as handle:
        packet_map = {row["packet_id"]: row for row in csv.DictReader(handle)}
    labels = {}
    for scope in ("development", "confirmation", "remaining"):
        path = output / f"state_labels_coder_A_{scope}_{PROMPT_VERSION}.jsonl"
        if path.exists():
            labels.update({row["packet_id"]: row for row in read_jsonl(path)})
    if set(labels) != set(packet_map):
        raise RuntimeError("Primary Judge A labels do not cover all extracted packets.")
    compositions, _ = action_compositions(list(trajectories.values()), output)
    rows = []
    for packet_id, meta in sorted(packet_map.items()):
        trajectory = trajectories[meta["case_id"]]
        index = int(meta["transition_index"])
        state = labels[packet_id]
        previous, current = trajectory["rounds"][index - 1], trajectory["rounds"][index]
        prior_actions = {action for round_data in trajectory["rounds"][:index] for action in round_data["actions"]}
        hit_set = set(str(item) for item in np.load(trajectory["hit_path"], allow_pickle=True).tolist())
        result = outcome(trajectory["candidate_count"], hit_set, prior_actions, current["actions"])
        fs = feedback_state_label(trajectory["feedback_policy"], state)
        sa, reason = state_action_label(state, compositions[(trajectory["case_id"], index)], compositions[(trajectory["case_id"], index + 1)])
        full = int(trajectory["feedback_policy"] != "no_feedback" and fs == "calibrated_update" and sa == "aligned" and result["outcome_class"] == "enriched")
        rows.append({**meta, "grounding": state["grounding"], "state_operation": state["operation"], "resolution_calibration": state["calibration"],
                     "feedback_state_label": fs, "state_action_label": sa, "state_action_reason": reason, **result, "full_chain_completion": full,
                     "feedback_evidence_quote": state["feedback_evidence_quote"], "state_evidence_quote": state["state_evidence_quote"],
                     "annotation_note": state["annotation_note"], "feedback_text_snippet": compact(current["feedback"], 700),
                     "current_state_snippet": compact(current["rationale"], 900)})
    write_csv(output / "transition_edge_audit.csv", rows)
    return rows


def rates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {"overall": rows}
    for policy in sorted({row["feedback_policy"] for row in rows}):
        grouped[f"condition:{policy}"] = [row for row in rows if row["feedback_policy"] == policy]
    output = []
    for name, part in grouped.items():
        feedback = [row for row in part if row["feedback_policy"] != "no_feedback"]
        established = [row for row in part if row["feedback_state_label"] in ESTABLISHED and row["state_action_label"] != "unassessable"]
        eligible = [row for row in part if row["outcome_class"] in OUTCOME_VALID]
        full_eligible = [row for row in feedback if row["outcome_class"] in OUTCOME_VALID]
        output.append({"grouping": "overall" if name == "overall" else "condition", "feedback_policy": "" if name == "overall" else name.split(":", 1)[1],
                       "transition_count": len(part), "calibrated_update_numerator": sum(row["feedback_state_label"] == "calibrated_update" for row in feedback), "calibrated_update_denominator": len(feedback),
                       "action_translation_numerator": sum(row["state_action_label"] == "aligned" for row in established), "action_translation_denominator": len(established),
                       "outcome_enrichment_numerator": sum(row["outcome_class"] == "enriched" for row in eligible), "outcome_enrichment_denominator": len(eligible),
                       "full_chain_completion_numerator": sum(row["full_chain_completion"] for row in full_eligible), "full_chain_completion_denominator": len(full_eligible)})
    for row in output:
        for metric in ("calibrated_update", "action_translation", "outcome_enrichment", "full_chain_completion"):
            numerator, denominator = row[f"{metric}_numerator"], row[f"{metric}_denominator"]
            row[f"{metric}_rate"] = numerator / denominator if denominator else None
    return output


def render_figure(rate_rows: list[dict[str, Any]], output: Path) -> Path:
    import matplotlib.pyplot as plt

    conditions = [row for row in rate_rows if row["grouping"] == "condition"]
    metrics = [("calibrated_update_rate", "Feedback-to-State"), ("action_translation_rate", "State-to-Action"), ("outcome_enrichment_rate", "Action-to-Outcome"), ("full_chain_completion_rate", "Full chain")]
    figure, axes = plt.subplots(1, len(metrics), figsize=(12, 3.3), constrained_layout=True)
    for axis, (field, title) in zip(axes, metrics):
        values = [row[field] if row[field] is not None else 0 for row in conditions]
        labels = [row["feedback_policy"] for row in conditions]
        axis.bar(range(len(values)), values, color=["#446B7A", "#B46A45", "#6D8B4E"][: len(values)])
        axis.set_xticks(range(len(values)), labels, rotation=25, ha="right")
        axis.set_ylim(0, 1)
        axis.set_title(title, fontsize=10)
        axis.grid(axis="y", alpha=0.25)
    path = output / "trace_process_rates.png"
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def render_html(rate_rows: list[dict[str, Any]], reliability_rows: dict[str, Any], output: Path, validation: dict[str, Any]) -> Path:
    rows = []
    for row in rate_rows:
        label = row["feedback_policy"] or "overall"
        cells = "".join(f"<td>{html.escape(str(row[f'{metric}_numerator']))}/{html.escape(str(row[f'{metric}_denominator']))}</td>" for metric in ("calibrated_update", "action_translation", "outcome_enrichment", "full_chain_completion"))
        rows.append(f"<tr><th>{html.escape(label)}</th>{cells}</tr>")
    reliability = "".join(f"<li>{html.escape(name)}: {html.escape(json.dumps(value, ensure_ascii=False))}</li>" for name, value in reliability_rows.items())
    document = f"""<!doctype html><html><head><meta charset=\"utf-8\"><title>PerturbTrace trace report</title><style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:36px;color:#1f2933;line-height:1.5}}main{{max-width:1040px;margin:auto}}table{{border-collapse:collapse;width:100%}}th,td{{border-bottom:1px solid #d8dee4;padding:9px;text-align:left}}th{{background:#f4f7f8}}code{{overflow-wrap:anywhere}}.note{{color:#52606d}}</style></head><body><main>
<h1>PerturbTrace Trace Evaluation</h1><p class=\"note\">State labels were generated before hidden outcomes were read. S is an externalized written decision state, not latent belief.</p>
<p>Validation: <strong>{html.escape(validation['status'])}</strong>. Transition rows: {validation['transition_count']}.</p>
<h2>Rates (numerator / eligible denominator)</h2><table><tr><th>Group</th><th>F-to-S</th><th>S-to-A</th><th>A-to-O</th><th>Full chain</th></tr>{''.join(rows)}</table>
<h2>Judge agreement</h2><ul>{reliability}</ul><h2>Artifacts</h2><ul><li><code>transition_edge_audit.csv</code></li><li><code>trace_process_rates.png</code></li><li><code>TRACE_VALIDATION.json</code></li></ul>
</main></body></html>"""
    path = output / "trace_report.html"
    path.write_text(document, encoding="utf-8")
    return path


def validate(output: Path, input_report: dict[str, Any], rows: list[dict[str, Any]], reliability_rows: dict[str, Any], require_gate: bool) -> dict[str, Any]:
    expected = input_report["transition_count"]
    checks = [
        {"check": "transition coverage", "passed": len(rows) == expected, "detail": {"expected": expected, "actual": len(rows)}},
        {"check": "unique packet IDs", "passed": len({row["packet_id"] for row in rows}) == len(rows), "detail": len({row["packet_id"] for row in rows})},
        {"check": "state label domain", "passed": set(row["feedback_state_label"] for row in rows) <= {"not_applicable_control", "no_observable_update", "indeterminate", "over_attributed_update", "calibrated_update"}, "detail": sorted({row["feedback_state_label"] for row in rows})},
        {"check": "state-action label domain", "passed": set(row["state_action_label"] for row in rows) <= {"aligned", "partially_aligned", "mismatch", "unassessable"}, "detail": sorted({row["state_action_label"] for row in rows})},
        {"check": "outcome label domain", "passed": set(row["outcome_class"] for row in rows) <= OUTCOME_VALID | {"no_hits_remaining"}, "detail": sorted({row["outcome_class"] for row in rows})},
    ]
    if require_gate:
        for name, report in reliability_rows.items():
            checks.append({"check": f"{name} reliability gate", "passed": report["gate_pass"] is True, "detail": report})
    status = "PASS" if all(row["passed"] for row in checks) else "FAIL"
    report = {"status": status, "checks": checks, "transition_count": len(rows), "reliability": reliability_rows,
              "source_runs_modified": False, "protocol_hashes": protocol_hashes(), "reliability_boundary": "Independent judge-judge agreement, not human agreement or adjudicated consensus."}
    write_json(output / "TRACE_VALIDATION.json", report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-manifest", required=True, help="CSV with run_root and optional case_id, group, codebook_task_id columns.")
    parser.add_argument("--output-dir", required=True, help="New or empty external analysis output directory.")
    parser.add_argument("--judge-model", default="gpt-5.5", help="Default model for both independent judge passes.")
    parser.add_argument("--judge-a-model", help="Override Judge A only.")
    parser.add_argument("--judge-b-model", help="Override Judge B only.")
    parser.add_argument("--api-key-file", help="Optional runtime API-key file; BDA_OPENAI_API_KEY takes precedence.")
    parser.add_argument("--base-url", default=os.environ.get("BDA_OPENAI_BASE_URL"), help="Optional compatible Responses API base URL.")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--double-code-fraction", type=float, default=0.34)
    parser.add_argument("--minimum-reliability-packets", type=int, default=20)
    parser.add_argument("--prepare-only", action="store_true", help="Build blinded packets and provenance only; do not call judge APIs.")
    args = parser.parse_args(argv)
    manifest = Path(args.run_manifest).expanduser().resolve()
    if not manifest.is_file():
        raise SystemExit(f"Run manifest does not exist: {manifest}")
    output = Path(args.output_dir).expanduser().resolve()
    if output == SKILL_DIR or SKILL_DIR in output.parents:
        raise SystemExit("--output-dir must not be inside the skill source directory.")
    output.mkdir(parents=True, exist_ok=True)
    manifest_rows = parse_manifest(manifest)
    input_report = build_inputs(manifest_rows, output, args.double_code_fraction)
    provenance = {"run_manifest": str(manifest), "run_manifest_sha256": digest_file(manifest), "protocol_files_sha256": protocol_hashes(),
                  "output_dir": str(output), "source_outputs_separated": True, "default_same_model": args.judge_a_model is None and args.judge_b_model is None}
    write_json(output / "trace_evaluation_config.json", provenance)
    if args.prepare_only:
        print(json.dumps({"status": "PREPARED", "output_dir": str(output), **input_report}, ensure_ascii=False))
        return 0
    api_key = load_api_key(args.api_key_file)
    model_a, model_b = args.judge_a_model or args.judge_model, args.judge_b_model or args.judge_model
    packets = {row["packet_id"]: row for row in read_jsonl(output / "state_blinded_packets.jsonl")}
    with (output / "packet_key_map.csv").open(newline="", encoding="utf-8-sig") as handle:
        key_rows = list(csv.DictReader(handle))
    scopes = {scope: [packets[row["packet_id"]] for row in key_rows if row["double_code_partition"] == scope] for scope in ("development", "confirmation", "remaining")}
    reliability_rows: dict[str, Any] = {}
    for scope in ("development", "confirmation"):
        a = judge_packets(scopes[scope], "A", scope, model_a, api_key, args.base_url, args.workers, output)
        b = judge_packets(scopes[scope], "B", scope, model_b, api_key, args.base_url, args.workers, output)
        reliability_rows[scope] = reliability(a, b, args.minimum_reliability_packets)
        write_json(output / f"reliability_{scope}_v2.json", reliability_rows[scope])
    require_gate = any(report["estimable"] for report in reliability_rows.values())
    if require_gate and not all(report["gate_pass"] is True for report in reliability_rows.values() if report["estimable"]):
        validation = validate(output, input_report, [], reliability_rows, require_gate=True)
        raise SystemExit(f"Reliability gate failed; remaining transitions were not labeled. See {output / 'TRACE_VALIDATION.json'} ({validation['status']}).")
    judge_packets(scopes["remaining"], "A", "remaining", model_a, api_key, args.base_url, args.workers, output)
    rows = score(output)
    rate_rows = rates(rows)
    write_csv(output / "process_rates_summary.csv", rate_rows)
    render_figure(rate_rows, output)
    validation = validate(output, input_report, rows, reliability_rows, require_gate=False)
    render_html(rate_rows, reliability_rows, output, validation)
    print(json.dumps({"status": validation["status"], "output_dir": str(output), "report_html": str(output / "trace_report.html")}, ensure_ascii=False))
    return 0 if validation["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
