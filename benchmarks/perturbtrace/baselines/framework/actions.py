"""Action parsing and validation for gene/action batches."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable

from .types import ParsedActionBatch


_GENE_TOKEN = re.compile(r"\b[A-Z][A-Z0-9.&-]{1,40}\b")
_NUMBERED_ACTION = re.compile(
    r"(?:^\s*|[\n,;]\s*)\d+\s*[\.\)]\s*(.*?)(?=(?:[\n,;]\s*)\d+\s*[\.\)]\s*|\Z)",
    flags=re.DOTALL,
)


def _clean_action_token(token: str) -> str:
    token = re.sub(r"\s+", " ", token.strip())
    token = token.strip(" \t\r\n,;")
    token = token.strip("[]{}")
    token = token.strip(" \t\r\n,;")
    return token


def parse_actions_from_text(text: str) -> list[str]:
    """Extract candidate action identifiers from agent output.

    The parser prefers lines after a `Solution:` marker, but falls back to
    numbered/list-style action identifiers so orchestration variants can
    include genes, drugs, numeric ids, and source-native action ids.
    """
    segment = text
    markers = ["Solution:", "DraftPool:", "Final Actions:", "Actions:", '"actions"']
    for marker in markers:
        if marker in text:
            segment = text.split(marker, 1)[1]
            break

    numbered = [_clean_action_token(match.group(1)) for match in _NUMBERED_ACTION.finditer(segment)]
    numbered = [token for token in numbered if token]
    if numbered:
        return numbered

    first_line = segment.strip().splitlines()[0] if segment.strip() else ""
    if "," in first_line or ";" in first_line:
        split_tokens = [_clean_action_token(token) for token in re.split(r"\s*[,;]\s*", first_line)]
        split_tokens = [token for token in split_tokens if token]
        if split_tokens:
            return split_tokens

    tokens = _GENE_TOKEN.findall(segment)
    cleaned: list[str] = []
    for token in tokens:
        token = _clean_action_token(token)
        if token:
            cleaned.append(token)
    return cleaned


def validate_action_batch(
    raw_text: str,
    candidate_space: Iterable[str],
    already_tested: Iterable[str],
    batch_size: int,
) -> ParsedActionBatch:
    candidate_set = set(candidate_space)
    tested_set = set(already_tested)
    parsed = parse_actions_from_text(raw_text)
    counts = Counter(parsed)
    duplicate_actions = sorted({action for action, count in counts.items() if count > 1})
    invalid_actions = sorted(
        action for action in set(parsed)
        if action not in candidate_set or action in tested_set
    )

    valid_actions = []
    seen = set()
    for action in parsed:
        if action in seen:
            continue
        if action not in candidate_set or action in tested_set:
            continue
        valid_actions.append(action)
        seen.add(action)
        if len(valid_actions) >= batch_size:
            break

    return ParsedActionBatch(
        raw_text=raw_text,
        parsed_actions=parsed,
        valid_actions=valid_actions,
        invalid_actions=invalid_actions,
        duplicate_actions=duplicate_actions,
        repaired_actions=[],
    )
