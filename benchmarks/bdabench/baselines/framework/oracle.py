"""Hidden-oracle feedback provider for closed-loop perturbation tasks."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .types import FeedbackPolicy, Observation, TaskProfile


@dataclass
class PerturbationOracle:
    profile: TaskProfile

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

    @property
    def candidate_space(self) -> set[str]:
        return set(self._candidate_space)

    @property
    def hit_set(self) -> set[str]:
        return set(self._hit_set)

    def score_of(self, action: str) -> float:
        return float(self._score_by_action[action])

    def evaluate(
        self,
        actions: Iterable[str],
        feedback_policy: FeedbackPolicy,
        round_index: int,
        stale_observations: list[Observation] | None = None,
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
        if feedback_policy == "stale_feedback" and stale_observations:
            stale_by_idx = stale_observations[: len(valid_actions)]
            result = []
            for action, stale in zip(valid_actions, stale_by_idx):
                result.append(
                    Observation(
                        tested_gene=action,
                        score=stale.score,
                        absolute_effect=stale.absolute_effect,
                        score_semantics=stale.score_semantics,
                        feedback_policy=feedback_policy,
                    )
                )
            return result
        scores = [self.score_of(action) for action in valid_actions]
        if feedback_policy == "random_feedback":
            rng = np.random.default_rng(round_index + len(valid_actions))
            scores = list(rng.permutation(scores))

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

