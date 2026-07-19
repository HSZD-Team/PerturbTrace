#!/usr/bin/env python3
"""Print a short /bda final report from a harness run_root."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SUMMARY_KEYS = (
    "run_id",
    "strategy_version",
    "task_id",
    "rounds_submitted",
    "expected_rounds",
    "complete",
    "primary_metric",
    "top_effect_recall",
    "precision_at_budget",
    "auc_hdc",
    "leakage_label",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path, help="Harness run root directory")
    args = parser.parse_args()

    run_root = args.run_root.expanduser().resolve()
    summary_path = run_root / "RUN_SUMMARY.json"
    if not summary_path.exists():
        print(f"run_root: {run_root}", file=sys.stderr)
        print(f"error: missing {summary_path}", file=sys.stderr)
        return 1

    data = json.loads(summary_path.read_text(encoding="utf-8"))
    print(f"run_root: {run_root}")
    print(f"summary: {summary_path}")
    for key in SUMMARY_KEYS:
        if key in data:
            print(f"{key}: {data[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
