# Portable PerturbTrace Decoupled Harness

This package intentionally excludes solver skills and historical run artifacts.

Use from the package root, with an externally supplied solver skill:

```powershell
python -m PerturbTrace.baselines.harness.cli init-run `
  --run-id <run_id> `
  --strategy-version <strategy_version> `
  --task-profile tasks/<task_slug>/task_manifest.yaml `
  --skill <external_solver_skill_dir> `
  --output-dir baselines/harness_runs/<experiment_name> `
  --feedback-policy true_feedback
```

Then follow `baselines/agent.md` and `baselines/harness/README.md` as the monitor contract.
