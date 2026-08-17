"""Hidden-oracle feedback provider for closed-loop perturbation tasks."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import hashlib

import numpy as np
import pandas as pd

from .types import FeedbackPolicy, Observation, TaskProfile


FEEDBACK_SEMANTICS_VERSION = "global-outcome-permutation-v1"
FEEDBACK_SEMANTICS = {
    "true_feedback": "True action-outcome mapping from the hidden oracle.",
    "no_feedback": "No outcome, score, rank, hit label, or hit-count feedback is exposed.",
    "random_feedback": (
        "A fixed run-seeded permutation of the complete candidate action-to-outcome mapping; "
        "the global outcome distribution is preserved while action-outcome correspondence is broken."
    ),
}


def derive_feedback_seed(run_id: str) -> int:
    """Derive a stable cross-process seed when the caller does not provide one."""
    digest = hashlib.sha256(run_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


@dataclass
class PerturbationOracle:
    profile: TaskProfile
    random_seed: int = 0

    def __post_init__(self) -> None:
        table = pd.read_csv(self.profile.candidate_table)
        if self.profile.candidate_id_column not in table.columns:
            raise ValueError(f"Missing candidate column: {self.profile.candidate_id_column}")
        if self.profile.score_column not in table.columns:
            raise ValueError(f"Missing score column: {self.profile.score_column}")
        table = table.drop_duplicates(subset=[self.profile.candidate_id_column])
        table = table.set_index(self.profile.candidate_id_column)
        self._score_by_action = table[self.profile.score_column].astype(float).to_dict()
        self._candidate_space = set(self._score_by_action)
        self._hit_set = set(np.load(self.profile.hit_set, allow_pickle=True).tolist())
        candidate_ids = sorted(self._score_by_action, key=str)
        rng = np.random.default_rng(self.random_seed)
        source_ids = list(rng.permutation(candidate_ids))
        self._random_score_by_action = {
            target: self._score_by_action[source]
            for target, source in zip(candidate_ids, source_ids)
        }
        self._random_hit_set = {
            target
            for target, source in zip(candidate_ids, source_ids)
            if source in self._hit_set
        }

    @property
    def candidate_space(self) -> set[str]:
        return set(self._candidate_space)

    @property
    def hit_set(self) -> set[str]:
        return set(self._hit_set)

    @property
    def random_hit_set(self) -> set[str]:
        return set(self._random_hit_set)

    def feedback_hit_set(self, feedback_policy: FeedbackPolicy) -> set[str] | None:
        if feedback_policy == "no_feedback":
            return None
        if feedback_policy == "random_feedback":
            return self.random_hit_set
        return self.hit_set

    def score_of(self, action: str) -> float:
        return float(self._score_by_action[action])

    def evaluate(
        self,
        actions: Iterable[str],
        feedback_policy: FeedbackPolicy,
        round_index: int,
    ) -> list[Observation]:
        valid_actions = [action for action in actions if action in self._score_by_action]
        if feedback_policy == "no_feedback":
            return [
                Observation(
                    tested_gene=action,
                    score=None,
                    absolute_effect=None,
                    score_semantics=None,
                    feedback_policy=feedback_policy,
                )
                for action in valid_actions
            ]
        if feedback_policy == "random_feedback":
            scores = [float(self._random_score_by_action[action]) for action in valid_actions]
        else:
            scores = [self.score_of(action) for action in valid_actions]

        return [
            Observation(
                tested_gene=action,
                score=score,
                absolute_effect=abs(score),
                score_semantics="signed log-fold-change in normalized readout after perturbation",
                feedback_policy=feedback_policy,
            )
            for action, score in zip(valid_actions, scores)
        ]
