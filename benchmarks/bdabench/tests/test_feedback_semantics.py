from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from BDAbench.baselines.framework.oracle import PerturbationOracle
from BDAbench.baselines.framework.profile import load_task_profile
from BDAbench.baselines.framework.types import TaskProfile
from BDAbench.baselines.harness.contracts import HarnessConfig, RoundState, SkillBundle
from BDAbench.baselines.harness.prompts import build_feedback_prompt


REPO_ROOT = Path(__file__).resolve().parents[1]


class FeedbackSemanticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        candidate_table = root / "oracle_scores.csv"
        public_table = root / "candidate_actions.csv"
        hit_set = root / "hit_set.npy"
        actions = list("ABCDEFGH")
        scores = [8.0, 7.0, 1.5, 0.5, -0.5, -1.5, -7.0, -8.0]
        pd.DataFrame({"action_id": actions, "score": scores}).to_csv(candidate_table, index=False)
        pd.DataFrame({"action_id": actions}).to_csv(public_table, index=False)
        np.save(hit_set, np.array(["A", "B"], dtype=object))
        self.profile = TaskProfile(
            task_id="synthetic_feedback",
            title="Synthetic feedback contract",
            data_name="synthetic",
            candidate_table=candidate_table,
            hit_set=hit_set,
            public_candidate_table=public_table,
            candidate_id_column="action_id",
            score_column="score",
            rounds=2,
            batch_size=1,
            objective="Find high-effect actions.",
            public_task_semantics={"feedback_style": "hit_counts"},
            allowed_feedback_fields=[],
            forbidden_agent_inputs=[],
        )
        self.skill = SkillBundle(
            name="test",
            description="test",
            body="Use the current-run evidence.",
            source_path=root / "SKILL.md",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _config(self, policy: str, profile: TaskProfile | None = None) -> HarnessConfig:
        return HarnessConfig(
            task_profile=profile or self.profile,
            run_id=f"run_{policy}",
            strategy_version="test",
            feedback_policy=policy,
            feedback_seed=11,
        )

    def test_random_feedback_is_fixed_global_seeded_permutation(self) -> None:
        oracle_a = PerturbationOracle(self.profile, random_seed=11)
        oracle_b = PerturbationOracle(self.profile, random_seed=11)
        oracle_c = PerturbationOracle(self.profile, random_seed=12)
        actions = sorted(oracle_a.candidate_space)

        values_a = [oracle_a.evaluate([action], "random_feedback", index)[0].score for index, action in enumerate(actions)]
        values_b = [oracle_b.evaluate([action], "random_feedback", 99 - index)[0].score for index, action in enumerate(actions)]
        values_c = [oracle_c.evaluate([action], "random_feedback", index)[0].score for index, action in enumerate(actions)]

        self.assertEqual(values_a, values_b)
        self.assertNotEqual(values_a, values_c)
        self.assertCountEqual(values_a, [oracle_a.score_of(action) for action in actions])
        self.assertEqual(len(oracle_a.random_hit_set), len(oracle_a.hit_set))
        self.assertNotEqual(oracle_a.random_hit_set, oracle_a.hit_set)

    def test_no_feedback_prompt_exposes_no_outcome_signal(self) -> None:
        oracle = PerturbationOracle(self.profile, random_seed=11)
        state = RoundState(
            round_index=1,
            observations=oracle.evaluate(["A"], "no_feedback", round_index=0),
            already_submitted=["A"],
        )
        prompt = build_feedback_prompt(self._config("no_feedback"), self.skill, state, hit_set=None).user_prompt

        self.assertIn("Outcome feedback is withheld", prompt)
        for forbidden in ("hit_count=", "cumulative_hit_count=", "signed_score=", "absolute_effect="):
            self.assertNotIn(forbidden, prompt)

    def test_random_hit_count_uses_permuted_hit_set(self) -> None:
        oracle = PerturbationOracle(self.profile, random_seed=11)
        action = sorted(oracle.hit_set.symmetric_difference(oracle.random_hit_set))[0]
        state = RoundState(
            round_index=1,
            observations=oracle.evaluate([action], "random_feedback", round_index=0),
            already_submitted=[action],
        )
        prompt = build_feedback_prompt(
            self._config("random_feedback"), self.skill, state, hit_set=oracle.random_hit_set
        ).user_prompt

        random_count = int(action in oracle.random_hit_set)
        true_count = int(action in oracle.hit_set)
        self.assertNotEqual(random_count, true_count)
        self.assertIn(f"hit_count={random_count}/1", prompt)
        self.assertNotIn(f"hit_count={true_count}/1", prompt)

    def test_random_tested_score_uses_permuted_mapping(self) -> None:
        score_profile = replace(self.profile, public_task_semantics={"feedback_style": "tested_scores"})
        oracle = PerturbationOracle(score_profile, random_seed=11)
        action = next(
            candidate
            for candidate in sorted(oracle.candidate_space)
            if oracle.evaluate([candidate], "random_feedback", 0)[0].score != oracle.score_of(candidate)
        )
        observation = oracle.evaluate([action], "random_feedback", round_index=0)[0]
        state = RoundState(round_index=1, observations=[observation], already_submitted=[action])
        prompt = build_feedback_prompt(
            self._config("random_feedback", score_profile), self.skill, state, hit_set=oracle.random_hit_set
        ).user_prompt

        self.assertIn(f"signed_score={observation.score:.6g}", prompt)
        self.assertNotIn(f"signed_score={oracle.score_of(action):.6g}", prompt)

    def test_packaged_task_paths_resolve_from_portable_root(self) -> None:
        manifest = REPO_ROOT / "tasks" / "c3_cart_adenosine_feedback_decision_v0" / "task_manifest.yaml"
        profile = load_task_profile(manifest, REPO_ROOT)
        self.assertTrue(profile.candidate_table.is_file())
        self.assertTrue(profile.hit_set.is_file())
        self.assertTrue(profile.public_candidate_table and profile.public_candidate_table.is_file())


if __name__ == "__main__":
    unittest.main()
