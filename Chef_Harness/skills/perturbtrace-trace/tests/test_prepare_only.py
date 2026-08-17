from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_trace_evaluation.py"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("perturbtrace_trace_runner", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load trace runner module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class TracePrepareOnlyTest(unittest.TestCase):
    def test_completed_run_manifest_builds_blinded_packets_without_mutating_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "package"
            task = package / "tasks" / "toy"
            hidden = task / "hidden"
            hidden.mkdir(parents=True)
            candidates = task / "candidates.csv"
            with candidates.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["action_id"])
                writer.writeheader()
                writer.writerows({"action_id": item} for item in ["A", "B", "C", "D"])
            np.save(hidden / "hits.npy", np.asarray(["B", "C"], dtype=object))
            (task / "public_task_brief.md").write_text("Public toy task.", encoding="utf-8")
            task_manifest = task / "task_manifest.yaml"
            task_manifest.write_text(
                "\n".join(
                    [
                        "task_id: toy",
                        "data:",
                        "  candidate_table: tasks/toy/candidates.csv",
                        "  public_candidate_actions: tasks/toy/candidates.csv",
                        "  hit_set: tasks/toy/hidden/hits.npy",
                        "  candidate_id_column: action_id",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            run = root / "completed_run"
            write_json(run / "RUN_SUMMARY.json", {"complete": True, "task_id": "toy", "round_hit_gain": [1, 1]})
            write_json(run / "harness_config.json", {"run_id": "toy_run", "task_profile_path": str(task_manifest), "feedback_policy": "true_feedback", "feedback_seed": 7})
            write_json(run / "batches.json", [{"parsed_actions": ["A", "B"]}, {"parsed_actions": ["C", "D"]}])
            (run / "round_1").mkdir(parents=True)
            (run / "round_2").mkdir(parents=True)
            (run / "round_1" / "solver_response_attempt_1.txt").write_text("Level 1: Scientific Evidence and Rationale: Prior rationale.\nSolution: A, B", encoding="utf-8")
            (run / "round_2" / "solver_response_attempt_1.txt").write_text("Level 1: Scientific Evidence and Rationale: Feedback changes the next plan.\nSolution: C, D", encoding="utf-8")
            (run / "round_2" / "feedback_prompt.txt").write_text("# Feedback\nRound hit count: 1/2\n# Current Run State\n", encoding="utf-8")
            before = {str(path.relative_to(run)): hashlib.sha256(path.read_bytes()).hexdigest() for path in run.rglob("*") if path.is_file()}
            manifest = root / "runs.csv"
            manifest.write_text(f"run_root,case_id,group\n{run},toy_case,smoke\n", encoding="utf-8")
            output = root / "trace_output"
            result = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), "--run-manifest", str(manifest), "--output-dir", str(output), "--prepare-only"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((output / "input_build_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["trajectory_count"], 1)
            self.assertEqual(report["transition_count"], 1)
            packets = (output / "state_blinded_packets.jsonl").read_text(encoding="utf-8")
            self.assertNotIn("true_feedback", packets)
            after = {str(path.relative_to(run)): hashlib.sha256(path.read_bytes()).hexdigest() for path in run.rglob("*") if path.is_file()}
            self.assertEqual(before, after)

            with (output / "packet_key_map.csv").open(newline="", encoding="utf-8-sig") as handle:
                packet_key = next(csv.DictReader(handle))
            label = {
                "packet_id": packet_key["packet_id"],
                "grounding": "2",
                "operation": "expand",
                "calibration": "calibrated",
                "priority_up_modules": [],
                "priority_down_modules": [],
                "retained_modules": [],
                "uncertainty_update": "acknowledged",
                "feedback_evidence_quote": "Round hit count: 1/2",
                "state_evidence_quote": "Feedback changes the next plan.",
                "annotation_note": "synthetic test label",
            }
            (output / f"state_labels_coder_A_{packet_key['double_code_partition']}_v2.jsonl").write_text(
                json.dumps(label) + "\n", encoding="utf-8"
            )
            runner = load_runner_module()
            rows = runner.score(output)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["true_hits"], 1)
            self.assertEqual(rows[0]["state_action_label"], "unassessable")
            rate_rows = runner.rates(rows)
            runner.render_figure(rate_rows, output)
            validation = runner.validate(output, report, rows, {}, require_gate=False)
            runner.render_html(rate_rows, {}, output, validation)
            self.assertTrue((output / "trace_process_rates.png").is_file())
            self.assertTrue((output / "trace_report.html").is_file())
            self.assertEqual(validation["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
