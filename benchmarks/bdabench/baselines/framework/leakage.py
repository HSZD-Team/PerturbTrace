"""Leakage audit helpers for unrestricted baseline traces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .types import LeakageAudit, LeakageLabel


DEFAULT_FORBIDDEN_TERMS = [
    "ground_truth_IFNG.csv",
    "topmovers_IFNG.npy",
    "topmovers",
    "ground_truth",
    "hit table",
    "score table",
    "supplementary table",
    "screen id",
    "screen accession",
    "Schmidt",
]


@dataclass(frozen=True)
class LeakageAuditor:
    forbidden_terms: list[str]

    @classmethod
    def for_terms(cls, terms: list[str] | None = None) -> "LeakageAuditor":
        return cls(forbidden_terms=terms or DEFAULT_FORBIDDEN_TERMS)

    def audit_texts(self, texts: list[str], raw_trace_paths: list[Path] | None = None) -> LeakageAudit:
        joined = "\n".join(texts)
        lower = joined.lower()
        matches = sorted({term for term in self.forbidden_terms if term.lower() in lower})
        label: LeakageLabel
        if any(term.lower() in lower for term in ["ground_truth_ifng.csv", "topmovers_ifng.npy"]):
            label = "confirmed_answer_leakage"
        elif matches:
            label = "suspected_answer_seeking"
        elif "http" in lower or "pubmed" in lower or "doi" in lower:
            label = "web_supported_but_not_answer_table"
        else:
            label = "clean_general_knowledge"
        summary = "No leakage indicators matched."
        if matches:
            summary = "Matched possible answer-seeking terms: " + ", ".join(matches)
        return LeakageAudit(
            label=label,
            evidence_summary=summary,
            matched_terms=matches,
            raw_trace_paths=[str(path) for path in raw_trace_paths or []],
        )

