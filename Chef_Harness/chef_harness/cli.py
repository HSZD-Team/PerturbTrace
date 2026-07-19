"""Chef_Harness CLI: interactive /bda launcher MVP."""

from __future__ import annotations

import argparse
import shlex
import sys
import time
from pathlib import Path

from . import __version__
from .paths import resolve_workspace_path, workspace_root
from .prompt import build_bda_plan
from .results import recover_result
from .runtimes.codex import CodexRuntime
from .session import create_session, save_session
from .skills import load_skill
from .viz import render_bda_report, should_auto_viz_after_bda


BANNER = f"""Chef_Harness MVP v{__version__}
Workspace: {workspace_root()}

Commands:
  /bda <request>          Launch BDAbench monitor skill via Codex
  run bda [options]       Same as /bda with flags
  viz <run_root>          Render HTML report via bda-viz skill
  help                    Show help
  exit / quit             Leave

Examples:
  /bda 帮我基于这个文件夹做基因筛选（1-run smoke）
  /bda Help me run a gene-screen eval on this folder (1-run smoke)
  run bda --smoke --solver-skill solver_skills/restricted-clean-gene-screen
  viz <run_root>
"""


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return _repl()

    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return _cmd_run_bda(args)
    if args.command == "viz":
        return _cmd_viz(args)
    if args.command == "repl":
        return _repl()
    parser.print_help()
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chef",
        description="Chef_Harness — local skill launcher for harness evals",
    )
    parser.add_argument("--version", action="version", version=f"Chef_Harness {__version__}")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Run a skill")
    run_sub = run_p.add_subparsers(dest="skill", required=True)
    bda_p = run_sub.add_parser("bda", help="Run /bda monitor skill")
    _add_bda_flags(bda_p)
    bda_p.add_argument("prompt_words", nargs="*", help="User request text")

    viz_p = sub.add_parser("viz", help="Render HTML report for a BDAbench run_root")
    viz_p.add_argument("run_root", type=Path, help="Path to harness run_root")
    viz_p.add_argument("-o", "--output", type=Path, default=None, help="Optional HTML output path")

    sub.add_parser("repl", help="Start interactive prompt")
    return parser


def _add_bda_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--runtime", default=None, help="Monitor runtime (MVP: codex)")
    p.add_argument("--solver-skill", default=None, help="Path to solver strategy skill dir")
    p.add_argument("--task", default=None, help="Task slug override")
    p.add_argument("--smoke", action="store_true", help="1-run smoke; allow incomplete finalize")
    p.add_argument("--full", action="store_true", help="Prefer full rounds (disable smoke)")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Build prompt/session only; do not call Codex",
    )
    p.add_argument(
        "--model",
        default=None,
        help="Codex model for the monitor session (optional)",
    )


def _repl() -> int:
    print(BANNER)
    while True:
        try:
            line = input("chef> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        if line in {"exit", "quit", ":q"}:
            return 0
        if line in {"help", "?"}:
            print(BANNER)
            continue
        if line.startswith("/bda") or line.startswith("$bda"):
            text = line.split(None, 1)[1] if len(line.split(None, 1)) > 1 else ""
            code = _launch_bda(
                user_text=text or "帮我基于这个文件夹里的文件做一次基因筛选评测（1-run smoke）",
                smoke=True,
            )
            if code != 0:
                print(f"[chef] launch exited with code {code}")
            continue
        if line.startswith("viz ") or line.startswith("/bda-viz") or line.startswith("$bda-viz"):
            parts = shlex.split(line)
            if line.startswith("viz"):
                path_args = parts[1:]
            else:
                path_args = parts[1:]
            if not path_args:
                print("Usage: viz <run_root>")
                continue
            code = _cmd_viz(argparse.Namespace(run_root=Path(path_args[0]), output=None))
            if code != 0:
                print(f"[chef] viz exited with code {code}")
            continue
        if line.startswith("run "):
            try:
                args = _build_parser().parse_args(shlex.split(line))
            except SystemExit:
                continue
            if args.command == "run" and args.skill == "bda":
                code = _cmd_run_bda(args)
                if code != 0:
                    print(f"[chef] launch exited with code {code}")
                continue
        print("Unknown command. Type help.")


def _cmd_run_bda(args: argparse.Namespace) -> int:
    user_text = " ".join(args.prompt_words).strip()
    smoke: bool | None
    if args.full:
        smoke = False
    elif args.smoke:
        smoke = True
    else:
        smoke = None
    if not user_text:
        task_label = args.task or "default task"
        if smoke is False:
            user_text = f"请对 task={task_label} 跑完整 BDAbench 评测（全部 rounds）。"
        else:
            user_text = f"请对 task={task_label} 做一次 BDAbench 1-run smoke 评测。"
    solver_skill = (
        resolve_workspace_path(args.solver_skill) if args.solver_skill else None
    )
    return _launch_bda(
        user_text=user_text,
        runtime=args.runtime,
        solver_skill=solver_skill,
        task_slug=args.task,
        smoke=smoke,
        dry_run=args.dry_run,
        model=args.model,
    )


def _launch_bda(
    *,
    user_text: str,
    runtime: str | None = None,
    solver_skill: Path | None = None,
    task_slug: str | None = None,
    smoke: bool | None = None,
    dry_run: bool = False,
    model: str | None = None,
) -> int:
    try:
        skill = load_skill("bda")
        plan = build_bda_plan(
            skill,
            user_text,
            runtime=runtime,
            solver_skill=solver_skill,
            task_slug=task_slug,
            smoke=smoke,
        )
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"[chef] failed to build launch plan: {exc}", file=sys.stderr)
        return 2

    session = create_session(
        skill=plan.skill.name,
        runtime=plan.runtime,
        user_text=plan.user_text,
        package_root=plan.package_root,
        prompt=plan.prompt,
        extra={
            "task_slug": plan.task_slug,
            "solver_skill": str(plan.solver_skill),
            "smoke": plan.smoke,
            "strategy_version": plan.strategy_version,
            "output_dir": str(plan.output_dir),
        },
    )
    print(f"[chef] session: {session.session_id}")
    print(f"[chef] runtime: {plan.runtime}")
    print(f"[chef] package_root: {plan.package_root}")
    print(f"[chef] solver_skill: {plan.solver_skill}")
    print(f"[chef] task: {plan.task_slug}")
    print(f"[chef] smoke: {plan.smoke}")
    print(f"[chef] session_dir: {session.dir}")

    if dry_run:
        session.status = "dry_run"
        save_session(session)
        print("[chef] dry-run only; prompt written to session_dir/prompt.txt")
        print("--- prompt preview (first 40 lines) ---")
        preview = "\n".join(plan.prompt.splitlines()[:40])
        print(preview)
        return 0

    started = time.time()
    session.status = "running"
    save_session(session)

    monitor_cfg = dict(plan.skill.config.get("monitor") or {})
    monitor_model = model or str(monitor_cfg.get("model") or "gpt-5.5")

    runtime_adapter = CodexRuntime()
    print(f"[chef] launching Codex monitor via `codex exec` (model={monitor_model}) ...")
    try:
        result = runtime_adapter.run_monitor(
            prompt=plan.prompt,
            cwd=plan.package_root,
            session_dir=session.dir,
            model=monitor_model,
        )
    except FileNotFoundError:
        session.status = "error"
        session.error = "codex binary not found"
        save_session(session)
        print("[chef] codex not found on PATH", file=sys.stderr)
        return 127
    except Exception as exc:  # noqa: BLE001
        session.status = "error"
        session.error = str(exc)
        save_session(session)
        print(f"[chef] runtime failed: {exc}", file=sys.stderr)
        return 1

    recovered = recover_result(
        last_message=result.last_message,
        output_dir=plan.output_dir,
        since_ts=started,
    )
    task_mismatch = False
    expected_task = plan.task_slug.lower().replace("-", "_")
    actual_task = str(recovered.summary.get("task_id", "")).lower().replace("-", "_")
    if recovered.summary and expected_task and actual_task:
        # Accept either slug or task_id style names containing the slug.
        if expected_task not in actual_task and actual_task not in expected_task:
            task_mismatch = True

    session.exit_code = result.exit_code
    session.run_root = str(recovered.run_root) if recovered.run_root else None
    session.summary_path = str(recovered.summary_path) if recovered.summary_path else None
    session.status = (
        "ok"
        if result.exit_code == 0 and recovered.run_root and not task_mismatch
        else "failed"
    )
    if result.exit_code != 0 or not recovered.run_root:
        session.error = f"codex_exit={result.exit_code}; recover_source={recovered.source}"
    elif task_mismatch:
        session.error = (
            f"task mismatch: requested={plan.task_slug} "
            f"actual={recovered.summary.get('task_id')}"
        )
    session.extra["recover_source"] = recovered.source
    session.extra["codex_stdout"] = str(result.stdout_path)
    session.extra["monitor_model"] = monitor_model
    session.extra["codex_cmd"] = result.command
    session.extra["requested_task"] = plan.task_slug
    session.extra["actual_task"] = recovered.summary.get("task_id")
    save_session(session)

    report_html: Path | None = None
    if session.status == "ok" and recovered.run_root and should_auto_viz_after_bda():
        try:
            report_html = render_bda_report(recovered.run_root)
            session.extra["report_html"] = str(report_html)
            save_session(session)
        except Exception as exc:  # noqa: BLE001
            print(f"[chef] bda-viz failed: {exc}", file=sys.stderr)

    print()
    print("======== Chef result ========")
    print(recovered.display)
    if report_html is not None:
        print(f"report_html: {report_html}")
    print("=============================")
    print(f"[chef] status: {session.status}")
    print(f"[chef] requested_task: {plan.task_slug}")
    if recovered.summary.get("task_id"):
        print(f"[chef] actual_task: {recovered.summary.get('task_id')}")
    print(f"[chef] recover_source: {recovered.source}")
    print(f"[chef] session_dir: {session.dir}")
    if task_mismatch:
        print(
            "[chef] ERROR: recovered run task does not match --task. "
            "Prompt/profile were inconsistent or monitor reused another run.",
            file=sys.stderr,
        )
    if report_html is not None:
        print(f"[chef] open report: open '{report_html}'")
    if result.exit_code != 0:
        errors = CodexRuntime.extract_errors(result.stdout_path)
        print(f"[chef] codex exit: {result.exit_code} (see {result.stdout_path})")
        if errors:
            print("[chef] codex errors:")
            for line in errors:
                print(f"  {line}")
        return result.exit_code
    if task_mismatch:
        return 3
    return 0 if recovered.run_root else 1


def _cmd_viz(args: argparse.Namespace) -> int:
    run_root = Path(args.run_root).expanduser().resolve()
    output = Path(args.output).expanduser().resolve() if getattr(args, "output", None) else None
    try:
        report = render_bda_report(run_root, output=output)
    except Exception as exc:  # noqa: BLE001
        print(f"[chef] viz failed: {exc}", file=sys.stderr)
        return 1
    print(f"report_html: {report}")
    print(f"[chef] open report: open '{report}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
