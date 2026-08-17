#!/usr/bin/env python3
"""Render a self-contained HTML report for a PerturbTrace harness run_root."""

from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path
from typing import Any


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return str(value)
        return f"{value:.{digits}f}"
    return str(value)


def _load_run(run_root: Path) -> dict[str, Any]:
    summary = _read_json(run_root / "RUN_SUMMARY.json", {})
    metrics_wrap = _read_json(run_root / "metrics.json", {})
    metrics = metrics_wrap.get("metrics", metrics_wrap) if isinstance(metrics_wrap, dict) else {}
    config = _read_json(run_root / "harness_config.json", {})
    leakage = _read_json(run_root / "leakage_audit.json", {})
    batches = _read_json(run_root / "batches.json", [])
    observations = _read_json(run_root / "observations.json", [])
    skill_audit = _read_json(run_root / "skill_audit.json", {})

    rounds: list[dict[str, Any]] = []
    for round_dir in sorted(run_root.glob("round_*"), key=lambda p: p.name):
        attempts = sorted(round_dir.glob("solver_response_attempt_*.txt"))
        repairs = sorted(round_dir.glob("solver_response_repair_*.txt"))
        memberships = sorted(round_dir.glob("membership_check_attempt_*.json"))
        solver_final = round_dir / "solver_response.txt"
        rationale = ""
        if solver_final.exists():
            text = solver_final.read_text(encoding="utf-8", errors="replace")
            rationale = text.split("Level 2", 1)[0].strip()
            if len(rationale) > 1200:
                rationale = rationale[:1200] + "…"
        rounds.append(
            {
                "name": round_dir.name,
                "attempts": len(attempts),
                "repairs": len(repairs),
                "membership_checks": len(memberships),
                "has_feedback": (round_dir / "feedback_prompt.txt").exists(),
                "has_repair_prompt": (round_dir / "final_repair_prompt.txt").exists(),
                "rationale": rationale,
                "observation_count": len(_read_json(round_dir / "observations.json", [])),
            }
        )

    # Top observations by absolute_effect / score
    ranked = []
    for obs in observations:
        if not isinstance(obs, dict):
            continue
        score = obs.get("absolute_effect")
        if score is None:
            score = obs.get("score")
        try:
            score_f = float(score)
        except (TypeError, ValueError):
            continue
        ranked.append(
            {
                "gene": obs.get("tested_gene") or obs.get("action") or "?",
                "score": score_f,
                "raw_score": obs.get("score"),
                "semantics": obs.get("score_semantics"),
                "policy": obs.get("feedback_policy"),
            }
        )
    ranked.sort(key=lambda x: x["score"], reverse=True)

    gains = summary.get("round_hit_gain") or metrics.get("round_hit_gain") or []
    cumulative = []
    total = 0
    for g in gains:
        total += int(g)
        cumulative.append(total)

    return {
        "run_root": str(run_root.resolve()),
        "summary": summary,
        "metrics": metrics,
        "config": config,
        "leakage": leakage.get("leakage_audit", leakage),
        "skill_audit": skill_audit,
        "batches": batches if isinstance(batches, list) else [],
        "observations": observations if isinstance(observations, list) else [],
        "rounds": rounds,
        "top_observations": ranked[:40],
        "round_hit_gain": gains,
        "cumulative_hits": cumulative,
    }


def _svg_bar_chart(values: list[float], *, width: int = 640, height: int = 220, label_prefix: str = "R") -> str:
    if not values:
        return '<p class="muted">No round data.</p>'
    pad_l, pad_r, pad_t, pad_b = 36, 16, 16, 36
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    max_v = max(values) if max(values) > 0 else 1
    n = len(values)
    gap = 12
    bar_w = max(12, (plot_w - gap * (n - 1)) / n)
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Round hit gains">'
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="transparent"/>'
    ]
    # grid
    for i in range(4):
        y = pad_t + plot_h * i / 3
        parts.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width - pad_r}" y2="{y:.1f}" '
            f'stroke="#E5E5E0" stroke-width="1"/>'
        )
    for i, v in enumerate(values):
        x = pad_l + i * (bar_w + gap)
        h = (float(v) / max_v) * plot_h
        y = pad_t + plot_h - h
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" '
            f'rx="8" fill="url(#barGrad)"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle" '
            f'class="chart-val">{_esc(int(v) if abs(float(v) - int(float(v))) < 1e-9 else v)}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{height - 12}" text-anchor="middle" '
            f'class="chart-label">{label_prefix}{i + 1}</text>'
        )
    parts.append(
        "<defs><linearGradient id='barGrad' x1='0' y1='0' x2='0' y2='1'>"
        "<stop offset='0%' stop-color='#DCE7B9'/>"
        "<stop offset='100%' stop-color='#C5D49A'/>"
        "</linearGradient></defs>"
    )
    parts.append("</svg>")
    return "".join(parts)


def _svg_line_chart(values: list[float], *, width: int = 640, height: int = 220) -> str:
    if not values:
        return '<p class="muted">No cumulative curve.</p>'
    pad_l, pad_r, pad_t, pad_b = 36, 16, 16, 36
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    max_v = max(values) if max(values) > 0 else 1
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        x = pad_l + (plot_w * i / max(n - 1, 1))
        y = pad_t + plot_h - (float(v) / max_v) * plot_h
        pts.append((x, y, v))
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in pts)
    circles = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#5F6B3A"/>'
        f'<text x="{x:.1f}" y="{y - 10:.1f}" text-anchor="middle" class="chart-val">{_esc(int(v))}</text>'
        for x, y, v in pts
    )
    return f"""
<svg viewBox="0 0 {width} {height}" role="img" aria-label="Cumulative hits">
  <polyline fill="none" stroke="#8A9758" stroke-width="2.5" points="{poly}"/>
  {circles}
</svg>
"""


def render_html(data: dict[str, Any]) -> str:
    summary = data["summary"]
    metrics = data["metrics"]
    config = data["config"]
    leakage = data["leakage"]
    complete = bool(summary.get("complete"))
    status_class = "ok" if complete else "warn"
    run_root_path = Path(data["run_root"])
    try:
        run_root_uri = run_root_path.resolve().as_uri()
    except (OSError, ValueError):
        run_root_uri = "file://" + str(run_root_path)

    metric_cards = [
        ("Primary", summary.get("primary_metric", metrics.get("primary_metric_value"))),
        ("Top-effect recall", summary.get("top_effect_recall", metrics.get("top_effect_recall"))),
        ("Precision@budget", summary.get("precision_at_budget", metrics.get("precision_at_budget"))),
        ("AUC-HDC", summary.get("auc_hdc", metrics.get("auc_hdc"))),
        ("Valid unique", summary.get("valid_unique_actions", metrics.get("valid_unique_actions"))),
        ("Submitted", summary.get("total_submitted_actions", metrics.get("total_submitted_actions"))),
        ("Invalid rate", summary.get("invalid_action_rate", metrics.get("invalid_action_rate"))),
        ("Duplicate rate", summary.get("duplicate_action_rate", metrics.get("duplicate_action_rate"))),
        ("Parse failures", summary.get("parse_failure_count", metrics.get("parse_failure_count"))),
        ("Leakage", summary.get("leakage_label", leakage.get("label"))),
    ]
    cards_html = "".join(
        f'<article class="metric"><div class="metric-k">{_esc(k)}</div>'
        f'<div class="metric-v">{_esc(_fmt(v))}</div></article>'
        for k, v in metric_cards
    )

    rounds_html = []
    for idx, rnd in enumerate(data["rounds"]):
        gain = data["round_hit_gain"][idx] if idx < len(data["round_hit_gain"]) else "n/a"
        rationale = _esc(rnd.get("rationale") or "(no solver_response.txt)")
        rounds_html.append(
            f"""
<details class="round" {"open" if idx == 0 else ""}>
  <summary>
    <span>{_esc(rnd["name"])}</span>
    <span class="pill">hit gain: {_esc(gain)}</span>
    <span class="pill">attempts: {_esc(rnd["attempts"])}</span>
    <span class="pill">repairs: {_esc(rnd["repairs"])}</span>
  </summary>
  <div class="round-body">
    <p class="muted">membership checks: {_esc(rnd["membership_checks"])} ·
    feedback prompt: {"yes" if rnd["has_feedback"] else "no"} ·
    repair prompt: {"yes" if rnd["has_repair_prompt"] else "no"} ·
    obs in round folder: {_esc(rnd["observation_count"])}</p>
    <pre>{rationale}</pre>
  </div>
</details>
"""
        )

    top_rows = "".join(
        f"<tr><td>{_esc(i + 1)}</td><td><code>{_esc(item['gene'])}</code></td>"
        f"<td>{_esc(_fmt(item['score']))}</td>"
        f"<td>{_esc(_fmt(item.get('raw_score')))}</td>"
        f"<td>{_esc(item.get('semantics') or '')}</td></tr>"
        for i, item in enumerate(data["top_observations"])
    )
    if not top_rows:
        top_rows = '<tr><td colspan="5" class="muted">No observations.</td></tr>'

    batch_count = len(data["batches"])
    obs_count = len(data["observations"])

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>BDA Run · {_esc(summary.get("run_id", "report"))}</title>
<style>
  :root {{
    --bg: #F7F7F5;
    --surface: #FFFFFF;
    --ink: #1C1C1C;
    --muted: #707070;
    --line: #E0E0DE;
    --accent: #DCE7B9;
    --accent-deep: #5F6B3A;
    --warn: #B86B2C;
    --ok: #5F6B3A;
    --font: "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif;
    --serif: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
    --mono: "SF Mono", "Menlo", ui-monospace, monospace;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: var(--font);
    color: var(--ink);
    background: var(--bg);
    min-height: 100vh;
  }}
  .wrap {{ max-width: 1080px; margin: 0 auto; padding: 40px 24px 72px; }}
  header.hero {{
    display: grid;
    gap: 12px;
    padding: 8px 0 28px;
    margin-bottom: 8px;
  }}
  .eyebrow {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    width: fit-content;
    padding: 4px 10px;
    border-radius: 999px;
    background: var(--accent);
    color: var(--ink);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.02em;
  }}
  h1 {{
    margin: 0;
    font-family: var(--serif);
    font-size: clamp(2rem, 4vw, 2.75rem);
    font-weight: 500;
    letter-spacing: -0.02em;
    line-height: 1.15;
  }}
  .meta-list {{
    display: grid;
    gap: 8px;
    margin: 2px 0 0;
  }}
  .meta-row {{
    display: grid;
    grid-template-columns: 150px minmax(0, 1fr);
    gap: 10px;
    align-items: start;
  }}
  .meta-label {{
    color: var(--muted);
    font-size: 12px;
    font-weight: 650;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    padding-top: 4px;
  }}
  .meta-value code {{
    display: inline-block;
    max-width: 100%;
    background: #F0F0EC;
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 3px 8px;
    font-size: 0.88rem;
    line-height: 1.4;
    overflow-wrap: anywhere;
    word-break: break-word;
  }}
  @media (max-width: 640px) {{
    .meta-row {{ grid-template-columns: 1fr; gap: 4px; }}
  }}
  .status-row {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }}
  .status {{
    display: inline-flex; align-items: center; gap: 8px;
    padding: 5px 10px; border-radius: 999px;
    border: 1px solid var(--line); background: var(--surface);
    font-size: 12px;
  }}
  .status.ok {{ color: var(--ok); }}
  .status.warn {{ color: var(--warn); }}
  .btn-folder {{
    appearance: none;
    border: none;
    background: var(--accent);
    color: var(--ink);
    border-radius: 999px;
    padding: 5px 10px;
    font: inherit;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    line-height: 1.3;
    transition: background 0.15s ease;
  }}
  .btn-folder:hover {{ background: #D0DBAE; }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px;
    margin: 8px 0 28px;
  }}
  .metric {{
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 16px 14px 14px;
    min-width: 0;
    overflow: hidden;
  }}
  .metric-k {{
    color: var(--muted);
    font-size: 11px;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
  }}
  .metric-v {{
    font-family: var(--mono);
    font-size: 0.95rem;
    color: var(--ink);
    line-height: 1.35;
    overflow-wrap: anywhere;
    word-break: break-word;
    hyphens: auto;
  }}
  section {{
    margin: 22px 0;
    padding: 22px;
    border: 1px solid var(--line);
    border-radius: 16px;
    background: var(--surface);
    overflow: hidden;
    min-width: 0;
  }}
  section h2 {{
    margin: 0 0 16px;
    font-family: var(--serif);
    font-size: 1.35rem;
    font-weight: 500;
  }}
  .charts {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }}
  @media (max-width: 860px) {{ .charts {{ grid-template-columns: 1fr; }} }}
  .panel {{
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 14px;
    background: #FBFBFA;
  }}
  .panel h3 {{
    margin: 0 0 10px;
    font-size: 0.78rem;
    color: var(--muted);
    font-weight: 650;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }}
  .chart-val {{ fill: var(--ink); font-size: 11px; font-family: var(--mono); }}
  .chart-label {{ fill: var(--muted); font-size: 11px; }}
  table {{
    width: 100%; border-collapse: collapse; font-size: 0.92rem;
  }}
  th, td {{
    text-align: left; padding: 10px 10px; border-bottom: 1px solid var(--line);
  }}
  th {{
    color: var(--muted);
    font-weight: 650;
    font-size: 11px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }}
  code, pre {{ font-family: var(--mono); }}
  pre {{
    white-space: pre-wrap;
    background: #F7F7F5;
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 14px;
    line-height: 1.5;
    color: var(--ink);
    max-height: 260px;
    overflow: auto;
  }}
  .muted {{ color: var(--muted); }}
  .pill {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    background: var(--accent);
    color: var(--ink);
    font-size: 12px;
    font-weight: 600;
  }}
  details.round {{
    border: 1px solid var(--line);
    border-radius: 14px;
    margin-bottom: 10px;
    background: #FBFBFA;
  }}
  details.round summary {{
    cursor: pointer;
    list-style: none;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    padding: 14px 16px;
    font-weight: 600;
  }}
  details.round summary::-webkit-details-marker {{ display: none; }}
  .round-body {{ padding: 0 16px 16px; }}
  .kv {{ display: grid; gap: 0; }}
  .kv .row {{
    display: grid;
    grid-template-columns: minmax(120px, 160px) minmax(0, 1fr);
    gap: 12px 16px;
    padding: 12px 0;
    border-bottom: 1px solid var(--line);
    align-items: start;
  }}
  .kv .row:last-child {{ border-bottom: none; }}
  .kv b {{
    color: var(--muted);
    font-weight: 600;
    font-size: 0.9rem;
    padding-top: 2px;
  }}
  .kv .val {{
    min-width: 0;
    overflow-wrap: anywhere;
    word-break: break-word;
  }}
  .kv code {{
    display: block;
    width: 100%;
    max-width: 100%;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    word-break: break-all;
    background: #F7F7F5;
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 0.84rem;
    line-height: 1.45;
  }}
  @media (max-width: 640px) {{
    .kv .row {{ grid-template-columns: 1fr; gap: 6px; }}
  }}
  footer {{
    margin-top: 28px; color: var(--muted); font-size: 12px;
  }}
  a {{ color: var(--accent-deep); }}
</style>
</head>
<body>
  <div class="wrap">
    <header class="hero">
      <div class="eyebrow">PerturbTrace · run report</div>
      <h1>{_esc(summary.get("run_id", "PerturbTrace run"))}</h1>
      <div class="meta-list">
        <div class="meta-row">
          <div class="meta-label">Task</div>
          <div class="meta-value"><code>{_esc(summary.get("task_id", "n/a"))}</code></div>
        </div>
        <div class="meta-row">
          <div class="meta-label">Strategy version</div>
          <div class="meta-value"><code>{_esc(summary.get("strategy_version", config.get("strategy_version", "n/a")))}</code></div>
        </div>
        <div class="meta-row">
          <div class="meta-label">Solver strategy skill</div>
          <div class="meta-value"><code>{_esc(config.get("skill_name", "n/a"))}</code></div>
        </div>
      </div>
      <div class="status-row">
        <span class="status {status_class}">
          complete: {_esc(summary.get("complete"))}
          · rounds {_esc(summary.get("rounds_submitted"))}/{_esc(summary.get("expected_rounds"))}
        </span>
        <a class="btn-folder" href="{_esc(run_root_uri)}" title="{_esc(data['run_root'])}" target="_blank" rel="noopener noreferrer">
          Open results folder
        </a>
      </div>
    </header>

    <div class="grid">{cards_html}</div>

    <section>
      <h2>Discovery curve</h2>
      <div class="charts">
        <div class="panel">
          <h3>Round hit gain</h3>
          {_svg_bar_chart([float(x) for x in data["round_hit_gain"]])}
        </div>
        <div class="panel">
          <h3>Cumulative hits</h3>
          {_svg_line_chart([float(x) for x in data["cumulative_hits"]])}
        </div>
      </div>
    </section>

    <section>
      <h2>Run configuration</h2>
      <div class="kv">
        <div class="row"><b>run_root</b><div class="val"><code>{_esc(data["run_root"])}</code></div></div>
        <div class="row"><b>feedback_policy</b><div class="val">{_esc(config.get("feedback_policy", "n/a"))}</div></div>
        <div class="row"><b>harness_version</b><div class="val">{_esc(config.get("harness_version", "n/a"))}</div></div>
        <div class="row"><b>batches</b><div class="val">{_esc(batch_count)}</div></div>
        <div class="row"><b>observations</b><div class="val">{_esc(obs_count)}</div></div>
        <div class="row"><b>skill_audit.clean</b><div class="val">{_esc((data["skill_audit"] or {}).get("clean", "n/a"))}</div></div>
      </div>
    </section>

    <section>
      <h2>Rounds</h2>
      {"".join(rounds_html) or '<p class="muted">No round_* folders found.</p>'}
    </section>

    <section>
      <h2>Top observations (by absolute effect / score)</h2>
      <table>
        <thead>
          <tr><th>#</th><th>Action</th><th>Rank score</th><th>Raw score</th><th>Semantics</th></tr>
        </thead>
        <tbody>{top_rows}</tbody>
      </table>
    </section>

    <section>
      <h2>Leakage audit</h2>
      <div class="kv">
        <div class="row"><b>label</b><div class="val">{_esc(leakage.get("label", summary.get("leakage_label", "n/a")))}</div></div>
        <div class="row"><b>evidence</b><div class="val">{_esc(leakage.get("evidence_summary", "n/a"))}</div></div>
        <div class="row"><b>matched_terms</b><div class="val">{_esc(", ".join(leakage.get("matched_terms") or []) or "(none)")}</div></div>
      </div>
    </section>

    <footer>
      Generated by <code>bda-viz</code> · open this file in any local browser ·
      source artifacts under <code>RUN_SUMMARY.json</code>, <code>metrics.json</code>, <code>observations.json</code>, <code>round_*</code>
    </footer>
  </div>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path, help="Harness run_root directory")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output HTML path (default: <run_root>/report.html)",
    )
    args = parser.parse_args()

    run_root = args.run_root.expanduser().resolve()
    if not run_root.exists():
        raise SystemExit(f"run_root not found: {run_root}")
    if not (run_root / "RUN_SUMMARY.json").exists():
        raise SystemExit(f"Missing RUN_SUMMARY.json in {run_root}")

    data = _load_run(run_root)
    out = (args.output or (run_root / "report.html")).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(data), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
