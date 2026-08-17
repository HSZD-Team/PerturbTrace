"""Task profile loading for closed-loop perturbation baseline runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .types import TaskProfile


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None"}:
        return None
    if value.startswith("[") and value.endswith("]"):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value.strip('"').strip("'")


def _simple_yaml_load(path: Path) -> dict[str, Any]:
    """Load the small YAML subset used by task profiles without extra deps."""
    lines = path.read_text(encoding="utf-8").splitlines()

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        container: dict[str, Any] | list[Any] | None = None
        while index < len(lines):
            raw_line = lines[index]
            if not raw_line.strip() or raw_line.lstrip().startswith("#"):
                index += 1
                continue
            current_indent = len(raw_line) - len(raw_line.lstrip(" "))
            if current_indent < indent:
                break
            if current_indent > indent:
                raise ValueError(f"Unexpected indentation in {path}: {raw_line}")

            line = raw_line.strip()
            if line.startswith("- "):
                if container is None:
                    container = []
                if not isinstance(container, list):
                    raise ValueError(f"Mixed mapping/list block in {path}: {raw_line}")
                container.append(_parse_scalar(line[2:]))
                index += 1
                continue

            if ":" not in line:
                raise ValueError(f"Unsupported profile line in {path}: {raw_line}")
            if container is None:
                container = {}
            if not isinstance(container, dict):
                raise ValueError(f"Mixed list/mapping block in {path}: {raw_line}")
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            index += 1
            if value:
                container[key] = _parse_scalar(value)
                continue
            child, index = parse_block(index, indent + 2)
            container[key] = child

        return (container if container is not None else {}), index

    parsed, final_index = parse_block(0, 0)
    if final_index < len(lines):
        raise ValueError(f"Could not parse full profile {path}")
    if not isinstance(parsed, dict):
        raise ValueError(f"Profile root must be a mapping: {path}")
    return parsed


def _load_profile_dict(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore

        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return _simple_yaml_load(path)


def _agent_safe_wording(data: dict[str, Any], semantics: dict[str, Any]) -> str:
    wording = str(semantics.get("agent_safe_brief") or "").strip()
    if wording:
        return wording
    return f"Select perturbation actions for private task {data['task_id']}."


def _agent_safe_objective(data: dict[str, Any], semantics: dict[str, Any]) -> str:
    wording = _agent_safe_wording(data, semantics).rstrip(".")
    if wording:
        return f"{wording} under the task budget."
    return "Select perturbation actions that maximize private-task performance under the task budget."


def _public_action_space_contract(data: dict[str, Any]) -> tuple[str, str]:
    contract = data.get("public_action_space", {})
    if not isinstance(contract, dict):
        contract = {}
    visibility = str(contract.get("visibility") or data.get("action_space_visibility") or "public_ids")
    delivery = str(contract.get("delivery") or data.get("candidate_delivery") or "artifact_reference")
    return visibility, delivery


def _resolve_declared_path(repo_root: Path, raw_path: str) -> Path:
    raw = Path(raw_path)
    if raw.is_absolute():
        return raw.resolve()
    candidates = [repo_root / raw]
    if raw.parts and raw.parts[0] == "PerturbTrace":
        candidates.append(repo_root / Path(*raw.parts[1:]))
    candidates.append(repo_root.parent / raw)
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def load_task_profile(path: Path, repo_root: Path) -> TaskProfile:
    data = _load_profile_dict(path)
    if "paths" not in data and "data" in data:
        task_data = data["data"]
        semantics = data.get("task_semantics", {})
        action_space_visibility, candidate_delivery = _public_action_space_contract(data)
        public_task_semantics = {
            **semantics,
            "public_task_wording": _agent_safe_wording(data, semantics),
            "cell_system": semantics.get("biological_system", "not specified"),
            "perturbation_mode": semantics.get("perturbation_operation", "not specified"),
            "action_type": semantics.get("action_type", "one perturbation action per submitted identifier"),
            "readout": semantics.get("readout", "not specified"),
            "score_sign_positive": semantics.get("score_sign_positive", "higher hidden score"),
            "score_sign_negative": semantics.get("score_sign_negative", "lower hidden score"),
            "positive_and_negative_effects_count": True,
        }
        feedback_fields = [
            "tested_action",
            "score",
            "absolute_effect",
            "score_semantics",
        ]
        leakage = data.get("leakage_controls", {})
        forbidden_inputs = list(
            leakage.get("forbidden_agent_inputs")
            or leakage.get("forbidden_to_agent")
            or []
        )
        return TaskProfile(
            task_id=data["task_id"],
            title=data.get("title", data["task_id"]),
            data_name=task_data["data_name"],
            candidate_table=_resolve_declared_path(repo_root, task_data["candidate_table"]),
            hit_set=_resolve_declared_path(repo_root, task_data["hit_set"]),
            public_candidate_table=(
                _resolve_declared_path(repo_root, task_data["public_candidate_actions"])
                if task_data.get("public_candidate_actions")
                else None
            ),
            candidate_id_column=task_data.get("candidate_id_column", "action_id"),
            score_column=task_data.get("score_column", "score"),
            rounds=int(data["budget"]["rounds"]),
            batch_size=int(data["budget"]["batch_size"]),
            objective=_agent_safe_objective(data, semantics),
            public_task_semantics=public_task_semantics,
            allowed_feedback_fields=feedback_fields,
            forbidden_agent_inputs=forbidden_inputs,
            action_space_visibility=action_space_visibility,
            candidate_delivery=candidate_delivery,
        )

    paths = data["paths"]
    budget = data["budget"]
    task_semantics = data.get("task_semantics", {})
    feedback = data.get("feedback", {})
    leakage = data.get("leakage_controls", {})
    action_space_visibility, candidate_delivery = _public_action_space_contract(data)

    return TaskProfile(
        task_id=data["task_id"],
        title=data.get("title", data["task_id"]),
        data_name=data["data_name"],
        candidate_table=_resolve_declared_path(repo_root, paths["candidate_table"]),
        hit_set=_resolve_declared_path(repo_root, paths["hit_set"]),
        public_candidate_table=(
            _resolve_declared_path(repo_root, paths["public_candidate_actions"])
            if paths.get("public_candidate_actions")
            else None
        ),
        candidate_id_column=data.get("candidate_id_column", "Gene"),
        score_column=data.get("score_column", "Score"),
        rounds=int(budget["rounds"]),
        batch_size=int(budget["batch_size"]),
        objective=data["objective"],
        public_task_semantics=task_semantics,
        allowed_feedback_fields=list(feedback.get("allowed_fields", [])),
        forbidden_agent_inputs=list(leakage.get("forbidden_agent_inputs", [])),
        action_space_visibility=action_space_visibility,
        candidate_delivery=candidate_delivery,
    )
