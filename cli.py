"""Novel Agent CLI Interface.

Supports offline tasks:
  1. run-chapter: Runs the generation pipeline for a single chapter.
  2. dashboard: Rebuilds the HTML dashboard.
  3. query-events: Searches events in SQLite.
  4. query-timeline: Searches timeline items.
  5. compress-assets: Compresses project assets.
  6. calibrate-prose: Builds a local prose identity profile from explicit files.
  7. agent: Read-only status / logs for external AI agents (JSON stdout).
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional

from novel_agent.agents.asset_compressor import compress_assets
from novel_agent.dashboard import write_dashboard
from novel_agent.exceptions import AgentError, FatalPipelineError, TaskAbortedError
from novel_agent.logging_config import setup_logging
from novel_agent.orchestrator import NovelOrchestrator
from novel_agent.pipeline import PipelineConfig
from novel_agent.progress import enable_json_output, emit_complete, emit_error
from novel_agent.prompts import PromptRepository
from novel_agent.state.sqlite_store import SQLiteStateStore


def _handle_cli_error(exc: Exception, chapter_id: str, step: str = "", json_output: bool = False) -> None:
    """Centralised error handling for CLI commands.

    Exits with distinct codes:
        2  – FatalPipelineError (unrecoverable config / setup issue)
        130 – TaskAbortedError (user cancelled)
        1  – Other agent / pipeline errors
    """
    if isinstance(exc, FatalPipelineError):
        emit_error(chapter_id, str(exc), step)
        if not json_output:
            print(f"Fatal error: {exc}", file=sys.stderr)
        sys.exit(2)
    if isinstance(exc, TaskAbortedError):
        emit_error(chapter_id, "Task aborted by user", step)
        if not json_output:
            print("Aborted.", file=sys.stderr)
        sys.exit(130)
    if isinstance(exc, AgentError):
        emit_error(chapter_id, str(exc), step)
        if not json_output:
            print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    # Truly unexpected – keep traceback out of user-facing output
    emit_error(chapter_id, f"Unexpected error: {exc}", step)
    if not json_output:
        print(f"Unexpected error: {exc}", file=sys.stderr)
    sys.exit(1)


def run_chapter_cmd(args: argparse.Namespace) -> None:
    """Execute the run-chapter CLI command."""
    root_dir = Path(getattr(args, "root_dir", None) or getattr(args, "root", None) or ".")
    setup_logging(root_dir / "logs")

    if getattr(args, "json_output", False):
        enable_json_output()

    if getattr(args, "dry_run", False):
        config = PipelineConfig.dry_run(root_dir)
    else:
        config = PipelineConfig.from_config(root_dir)

    if getattr(args, "interactive", False):
        config.interactive = True

    orchestrator = NovelOrchestrator(config)

    try:
        result = orchestrator.run_chapter(args.chapter_id, args.goal)
        payload = {
            "chapter_id": result.chapter_id,
            "final_path": str(result.final_path),
            "risk_level": result.audit.get("risk_level", "unknown"),
        }
        emit_complete(args.chapter_id, payload)
        if not args.json_output:
            print(f"Chapter {result.chapter_id} completed: {result.final_path}")
            print(f"Risk level: {result.audit.get('risk_level', 'unknown')}")
            print(f"chapter_id={result.chapter_id}")
            print(f"final_path={result.final_path}")
            print(f"risk_level={result.audit.get('risk_level')}")
    except Exception as exc:
        _handle_cli_error(exc, args.chapter_id, json_output=getattr(args, "json_output", False))


def dashboard_cmd(args: argparse.Namespace) -> None:
    """Execute the dashboard generation CLI command."""
    root_dir = Path(getattr(args, "root_dir", None) or getattr(args, "root", None) or ".")
    path = write_dashboard(root_dir)
    print(f"dashboard_path={path}")


def query_events_cmd(args: argparse.Namespace) -> None:
    """Execute the query-events search CLI command."""
    root_dir = Path(getattr(args, "root_dir", None) or getattr(args, "root", None) or ".")
    events = SQLiteStateStore(root_dir).search_events(args.query, args.limit)
    for event in events:
        print(f"{event['chapter_id']} {event['id']} {event['summary']}")


def query_timeline_cmd(args: argparse.Namespace) -> None:
    """Execute the query-timeline search CLI command."""
    root_dir = Path(getattr(args, "root_dir", None) or getattr(args, "root", None) or ".")
    items = SQLiteStateStore(root_dir).search_timeline(args.query, args.limit)
    for item in items:
        label = item.get("title") or item.get("name") or item.get("description", "")
        print(f"{item.get('chapter_id', '')} {item['kind']} {item['id']} {label}")


def run_arc_cmd(args: argparse.Namespace) -> None:
    root_dir = Path(getattr(args, "root_dir", None) or getattr(args, "root", None) or ".")
    setup_logging(root_dir / "logs")
    if getattr(args, "json_output", False):
        enable_json_output()

    config = PipelineConfig.dry_run(root_dir) if getattr(args, "dry_run", False) else PipelineConfig.from_config(root_dir)
    orchestrator = NovelOrchestrator(config)
    arc_ids: Optional[List[str]] = None
    if getattr(args, "arc_ids", None):
        arc_ids = [s.strip() for s in args.arc_ids.split(",") if s.strip()]

    try:
        results = asyncio.run(
            orchestrator.arun_arcs(
                arc_id=getattr(args, "arc_id", None) or None,
                arc_ids=arc_ids,
                start_arc_id=getattr(args, "start_arc_id", None) or None,
                resume=not getattr(args, "no_resume", False),
            )
        )
        payload = {"chapters_completed": len(results)}
        if args.json_output:
            print(json.dumps(payload, ensure_ascii=False))
        else:
            print(f"Arc batch completed: {len(results)} chapters")
    except Exception as exc:
        _handle_cli_error(exc, "", step="run_arc", json_output=getattr(args, "json_output", False))


def continue_novel_cmd(args: argparse.Namespace) -> None:
    root_dir = Path(getattr(args, "root_dir", None) or getattr(args, "root", None) or ".")
    setup_logging(root_dir / "logs")
    if getattr(args, "json_output", False):
        enable_json_output()

    config = PipelineConfig.dry_run(root_dir) if getattr(args, "dry_run", False) else PipelineConfig.from_config(root_dir)
    orchestrator = NovelOrchestrator(config)
    try:
        results = asyncio.run(
            orchestrator.arun_novel_continue(resume=not getattr(args, "no_resume", False))
        )
        payload = {"chapters_completed": len(results)}
        if args.json_output:
            print(json.dumps(payload, ensure_ascii=False))
        else:
            print(f"Novel continue completed: {len(results)} chapters")
    except Exception as exc:
        _handle_cli_error(exc, "", step="continue_novel", json_output=getattr(args, "json_output", False))


def rebuild_index_cmd(args: argparse.Namespace) -> None:
    root_dir = Path(getattr(args, "root_dir", None) or getattr(args, "root", None) or ".")
    setup_logging(root_dir / "logs")
    config = PipelineConfig.from_config(root_dir)
    orchestrator = NovelOrchestrator(config)
    store = orchestrator.vector_store
    if not hasattr(store, "rebuild_hnsw_indices"):
        print("Vector backend does not support HNSW rebuild", file=sys.stderr)
        sys.exit(1)
    counts = store.rebuild_hnsw_indices()
    if args.json_output:
        print(json.dumps({"dimensions": counts}, ensure_ascii=False))
    else:
        print(f"rebuilt_hnsw={counts}")


def _print_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _resolve_agent_root(args: argparse.Namespace) -> Path:
    if getattr(args, "root_dir", None) or getattr(args, "root", None):
        return Path(args.root_dir or args.root).resolve()
    from novel_agent.integrations.agent_bridge import resolve_project_root

    return resolve_project_root(
        project_id=(getattr(args, "project_id", None) or "").strip() or None
    )


def agent_projects_cmd(args: argparse.Namespace) -> None:
    from novel_agent.integrations.agent_bridge import list_projects, set_default_base_dir

    if getattr(args, "novel_root", None):
        set_default_base_dir(Path(args.novel_root).resolve())
    _print_json(list_projects())


def agent_snapshot_cmd(args: argparse.Namespace) -> None:
    from novel_agent.integrations.agent_bridge import build_agent_snapshot, set_default_base_dir
    from novel_agent.integrations import http_client

    if getattr(args, "novel_root", None):
        set_default_base_dir(Path(args.novel_root).resolve())

    if getattr(args, "http", False):
        params = {}
        if getattr(args, "project_id", None):
            params["project_id"] = args.project_id
        _print_json(http_client.api_get("/api/agent/snapshot", params=params or None))
        return

    root = _resolve_agent_root(args)
    pid = (getattr(args, "project_id", None) or "").strip()
    _print_json(build_agent_snapshot(root, project_id=pid))


def agent_logs_cmd(args: argparse.Namespace) -> None:
    from novel_agent.integrations.agent_bridge import set_default_base_dir, tail_project_logs
    from novel_agent.integrations import http_client

    if getattr(args, "novel_root", None):
        set_default_base_dir(Path(args.novel_root).resolve())

    if getattr(args, "runtime", False):
        _print_json(
            http_client.fetch_runtime_logs(
                since_id=int(getattr(args, "since_id", 0) or 0),
                limit=int(args.lines),
            )
        )
        return

    root = _resolve_agent_root(args)
    _print_json(tail_project_logs(root, max_lines=int(args.lines)))


def agent_alerts_cmd(args: argparse.Namespace) -> None:
    from novel_agent.integrations import http_client

    _print_json(http_client.api_get("/api/pipeline-alerts"))


def agent_health_cmd(args: argparse.Namespace) -> None:
    from novel_agent.integrations import http_client

    _print_json(http_client.fetch_health())


def compress_assets_cmd(args: argparse.Namespace) -> None:
    """Execute the asset compression CLI command."""
    root_dir = Path(getattr(args, "root_dir", None) or getattr(args, "root", None) or ".")
    config = PipelineConfig.from_config(root_dir)
    llm = config.get_llm("asset_compressor")
    prompts = PromptRepository(root_dir)
    result = compress_assets(root_dir, llm, prompts)
    print(f"compressed={result.get('compressed', False)}")
    print(f"archived_threads={len(result.get('archived_threads', []))}")
    print(f"removed_events={len(result.get('removed_events', []))}")


def calibrate_prose_cmd(args: argparse.Namespace) -> None:
    """Build a prose identity profile from explicitly selected local files."""

    from novel_agent.quality.prose_identity import (
        build_prose_identity_profile,
        list_prose_identity_profile_versions,
        restore_prose_identity_profile,
        save_prose_identity_profile,
    )

    root_dir = Path(getattr(args, "root_dir", None) or getattr(args, "root", None) or ".").resolve()
    if getattr(args, "list_versions", False):
        payload = {"versions": list_prose_identity_profile_versions(root_dir)}
        if getattr(args, "json_output", False):
            print(json.dumps(payload, ensure_ascii=False))
        else:
            for item in payload["versions"]:
                marker = "*" if item.get("is_active") else " "
                print(f"{marker} revision={item.get('revision')} profile_id={item.get('profile_id')} samples={item.get('sample_count')}")
        return

    restore_revision = getattr(args, "restore_revision", None)
    if restore_revision is not None:
        try:
            target = restore_prose_identity_profile(root_dir, revision=int(restore_revision))
        except ValueError as exc:
            print(f"无法恢复文风档案: {exc}", file=sys.stderr)
            raise SystemExit(2)
        payload = {"path": str(target), "restored_revision": int(restore_revision)}
        if getattr(args, "json_output", False):
            print(json.dumps(payload, ensure_ascii=False))
        else:
            print(f"prose_profile={target}")
            print(f"restored_revision={restore_revision}")
        return

    sample_paths = [(str(raw), "user_sample") for raw in (getattr(args, "sample", None) or [])]
    accepted_paths = [(str(raw), "accepted_chapter") for raw in (getattr(args, "accepted_chapter", None) or [])]
    inputs = sample_paths + accepted_paths
    if not inputs:
        print("至少指定一个 --sample 或 --accepted-chapter", file=sys.stderr)
        raise SystemExit(2)

    samples = []
    for raw_path, kind in inputs:
        path = Path(raw_path)
        if not path.is_absolute():
            path = root_dir / path
        if not path.is_file():
            print(f"输入文件不存在: {path}", file=sys.stderr)
            raise SystemExit(2)
        try:
            relative_path = str(path.resolve().relative_to(root_dir))
        except ValueError:
            relative_path = str(path.resolve())
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            print(f"无法读取输入文件 {path}: {exc}", file=sys.stderr)
            raise SystemExit(2)
        samples.append(
            {
                "id": relative_path,
                "kind": kind,
                "path": relative_path,
                "text": text,
            }
        )

    profile = build_prose_identity_profile(samples)
    target = Path(getattr(args, "output", None) or "assets/prose_identity_profile.json")
    if not target.is_absolute():
        target = root_dir / target
    if target.exists() and not getattr(args, "force", False):
        print(f"档案已存在，使用 --force 覆盖: {target}", file=sys.stderr)
        raise SystemExit(2)
    save_prose_identity_profile(root_dir, profile, path=target)
    payload = {
        "path": str(target),
        "profile_id": profile.get("profile_id"),
        "status": profile.get("status"),
        "sample_count": profile.get("sample_count"),
        "char_count": profile.get("char_count"),
    }
    if getattr(args, "json_output", False):
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"prose_profile={target}")
        print(f"profile_id={profile.get('profile_id')}")
        print(f"sample_count={profile.get('sample_count')}")


def hwe_scan_cmd(args: argparse.Namespace) -> None:
    """Execute HWE local prose scan from text or file."""
    from novel_agent.human_writing.engine import HumanWritingEngine

    text = ""
    if getattr(args, "text", None):
        text = args.text
    elif getattr(args, "file", None):
        path = Path(args.file)
        if not path.exists():
            print(f"Error: file not found: {path}", file=sys.stderr)
            sys.exit(1)
        text = path.read_text(encoding="utf-8")
    else:
        print("Error: either --text or --file must be specified", file=sys.stderr)
        sys.exit(1)

    engine = HumanWritingEngine()
    chapter_id = getattr(args, "chapter", None)
    report = engine.scan_text(text, chapter_id=chapter_id)

    root_dir = Path(getattr(args, "root_dir", None) or getattr(args, "root", None) or ".")
    if getattr(args, "save", False) and (root_dir / "data").exists():
        store = SQLiteStateStore(root_dir)
        store.save_hwe_report(report, chapter_id=chapter_id or "cli_scan")

    fmt = getattr(args, "format", "table")
    if fmt == "json":
        print(json.dumps(report.model_dump(), ensure_ascii=False, indent=2))
    else:
        print("=== HWE 1.0 Prose Quality Scan Report ===")
        print(f"Characters: {report.char_count} | Issues: {len(report.issues)}")
        print(f"Overall Score: {report.scores.overall_score}/100 | Template Risk: {report.scores.template_risk}/100")
        print(
            f"Dimensions: 自然度={report.scores.naturalness} | 句式节奏={report.scores.rhythm} | "
            f"描写新鲜度={report.scores.freshness} | 对白声线={report.scores.voice} | "
            f"叙事克制={report.scores.narrative_trust}"
        )
        print(f"Summary: {report.summary}")
        if report.issues:
            print("\nIssues:")
            for idx, issue in enumerate(report.issues, start=1):
                print(f"  {idx}. [{issue.hwe.rule_id}] ({issue.severity}) @ {issue.hwe.start}-{issue.hwe.end}: {issue.hwe.matched_text}")
                print(f"     Why: {issue.why}")
                print(f"     Fix: {issue.fix}")


def hwe_eval_cmd(args: argparse.Namespace) -> None:
    """Execute HWE Eval Lab benchmark suite."""
    from novel_agent.human_writing.eval import HWEEvalRunner

    fixtures_dir = Path(args.fixtures_dir) if getattr(args, "fixtures_dir", None) else None
    runner = HWEEvalRunner(fixtures_dir=fixtures_dir)
    report = runner.run_eval()

    fmt = getattr(args, "format", "table")
    if fmt == "json":
        print(json.dumps(report.model_dump(), ensure_ascii=False, indent=2))
    else:
        print("=== HWE 1.0 Benchmark Suite Results ===")
        print(f"Total Cases: {report.metrics.total_cases} (Pos: {report.metrics.positive_cases}, Neg: {report.metrics.negative_cases})")
        print(f"Precision: {report.metrics.precision:.4f} | Recall: {report.metrics.recall:.4f} | F1: {report.metrics.f1_score:.4f}")
        print(f"False Positive Rate (FPR): {report.metrics.false_positive_rate * 100:.2f}% (Target < 5%: {'PASS' if report.fpr_target_met else 'FAIL'})")
        print(f"Average Latency: {report.metrics.avg_latency_ms:.2f} ms")

    if getattr(args, "assert_fpr", False) and not report.fpr_target_met:
        print(f"Error: FPR target failed ({report.metrics.false_positive_rate * 100:.2f}% >= 5.0%)", file=sys.stderr)
        sys.exit(1)


def hwe_rebuild_memory_cmd(args: argparse.Namespace) -> None:
    """Rebuild longform expression saturation and sliding window diagnostics."""
    from novel_agent.human_writing.memory import (
        extract_expression_entries_v2,
        analyze_sliding_windows,
        detect_chapter_ending_fingerprint_repetition,
    )

    root_dir = Path(getattr(args, "novel_root", None) or getattr(args, "root_dir", None) or getattr(args, "root", None) or ".")
    chapters_dir = root_dir / "workspace" / "chapters"

    chapter_texts: List[str] = []
    if chapters_dir.exists():
        for ch_dir in sorted(chapters_dir.glob("chapter_*")):
            final_file = ch_dir / "chapter_final.txt"
            if final_file.exists():
                chapter_texts.append(final_file.read_text(encoding="utf-8"))

    if not chapter_texts and (root_dir / "data" / "novel.sqlite").exists():
        try:
            store = SQLiteStateStore(root_dir)
            if hasattr(store, "list_manuscript_documents"):
                docs = store.list_manuscript_documents()
                chapter_texts = [d["plain_text"] for d in docs if d.get("plain_text")]
        except Exception:
            pass

    all_entries = []
    for idx, text in enumerate(chapter_texts, start=1):
        entries = extract_expression_entries_v2(text, chapter_id=str(idx))
        all_entries.append(entries)

    history_mappings = []
    for entries in (all_entries[:-1] if len(all_entries) > 1 else all_entries):
        for e in entries:
            history_mappings.append(e.to_dict())

    curr_entries = all_entries[-1] if all_entries else []
    diagnostics = analyze_sliding_windows(
        curr_entries,
        history_mappings,
        current_chapter_id=str(len(chapter_texts)) if chapter_texts else "1",
    )
    curr_text = chapter_texts[-1] if chapter_texts else ""
    preceding = [(str(i), txt) for i, txt in enumerate(chapter_texts[:-1], start=1)]
    ending_repeats = [i.text for i in detect_chapter_ending_fingerprint_repetition(curr_text, preceding)]

    saturated = [d for d in diagnostics if d.is_saturated]

    fmt = getattr(args, "format", "table")
    payload = {
        "total_chapters": len(chapter_texts),
        "saturation_warning_count": len(saturated),
        "ending_repeats": ending_repeats,
        "diagnostics": [
            {
                "expression": d.expression,
                "kind": d.kind,
                "window_3_count": d.window_3_count,
                "window_10_count": d.window_10_count,
                "whole_book_count": d.whole_book_count,
                "is_saturated": d.is_saturated,
                "evidence_chapters": d.evidence_chapters,
            }
            for d in diagnostics
        ],
    }

    if fmt == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("=== HWE Longform Expression Memory Analysis ===")
        print(f"Analyzed {len(chapter_texts)} chapters across sliding windows (3 / 10 / Whole).")
        print(f"Saturation Warnings: {len(saturated)}")
        for d in saturated[:5]:
            print(f"  - [{d.kind}] '{d.expression}' (w3: {d.window_3_count}, w10: {d.window_10_count}, whole: {d.whole_book_count}) chapters: {d.evidence_chapters}")
        if ending_repeats:
            print(f"Ending Fingerprint Repeats: {len(ending_repeats)}")


def plugin_cmd(args: argparse.Namespace) -> None:
    from novel_agent.plugins.cli import plugin_init, plugin_validate, plugin_pack, plugin_test

    sub = getattr(args, "plugin_subcommand", "")
    if sub == "init":
        p = plugin_init(args.name, ptype=args.ptype, dest_dir=Path(args.dest))
        print(f"Created plugin scaffold at: {p.resolve()}")
    elif sub == "validate":
        res = plugin_validate(Path(args.target))
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif sub == "pack":
        out = Path(args.output) if args.output else None
        p = plugin_pack(Path(args.source), output_zip=out)
        print(f"Packaged plugin archive at: {p.resolve()}")
    elif sub == "test":
        res = plugin_test(Path(args.source))
        print(json.dumps(res, indent=2, ensure_ascii=False))


def _normalize_argv(argv):
    if not argv:
        return ["--help"]
    commands = {
        "run-chapter",
        "run-arc",
        "continue-novel",
        "rebuild-index",
        "dashboard",
        "query-events",
        "query-timeline",
        "compress-assets",
        "calibrate-prose",
        "agent",
        "hwe-scan",
        "hwe-eval",
        "hwe-rebuild-memory",
        "plugin",
    }
    if argv[0] in commands:
        return argv
    if any(arg.startswith("--chapter-id") or arg == "--goal" for arg in argv):
        return ["run-chapter"] + argv
    return argv


def main() -> None:
    argv = _normalize_argv(sys.argv[1:])
    parser = argparse.ArgumentParser(description="Novel Agent CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # 1. run-chapter
    run_parser = subparsers.add_parser("run-chapter", help="Run chapter generation pipeline")
    run_parser.add_argument("--chapter-id", default="001", help="Chapter ID")
    run_parser.add_argument("--goal", required=True, help="Chapter generation goal description")
    run_parser.add_argument("--root-dir", default=None, help="Project root directory (alternative)")
    run_parser.add_argument("--root", default=None, help="Project root directory")
    run_parser.add_argument("--dry-run", action="store_true", help="Use dry-run static LLM responses")
    run_parser.add_argument("--interactive", action="store_true", help="Enable approval gate interaction")
    run_parser.add_argument("--json-output", action="store_true", help="Emit JSON logs to stdout for Electron IPC")

    arc_parser = subparsers.add_parser("run-arc", help="Run arc batch from workspace/arc_*.json")
    arc_parser.add_argument("--arc-id", default="", help="Single arc id")
    arc_parser.add_argument("--arc-ids", default="", help="Comma-separated arc ids")
    arc_parser.add_argument("--start-arc-id", default="", help="Start from this arc through end")
    arc_parser.add_argument("--no-resume", action="store_true", help="Do not skip completed chapters")
    arc_parser.add_argument("--root-dir", default=None)
    arc_parser.add_argument("--root", default=None)
    arc_parser.add_argument("--dry-run", action="store_true")
    arc_parser.add_argument("--json-output", action="store_true")

    cont_parser = subparsers.add_parser("continue-novel", help="Resume arc batch from progress file")
    cont_parser.add_argument("--no-resume", action="store_true")
    cont_parser.add_argument("--root-dir", default=None)
    cont_parser.add_argument("--root", default=None)
    cont_parser.add_argument("--dry-run", action="store_true")
    cont_parser.add_argument("--json-output", action="store_true")

    rebuild_parser = subparsers.add_parser("rebuild-index", help="Rebuild HNSW vector indices")
    rebuild_parser.add_argument("--root-dir", default=None)
    rebuild_parser.add_argument("--root", default=None)
    rebuild_parser.add_argument("--json-output", action="store_true")

    # 2. dashboard
    dash_parser = subparsers.add_parser("dashboard", help="Regenerate HTML dashboard")
    dash_parser.add_argument("--root-dir", default=None)
    dash_parser.add_argument("--root", default=None)

    # 3. query-events
    events_parser = subparsers.add_parser("query-events", help="Search SQLite event history")
    events_parser.add_argument("--query", required=True, help="Text query to search for")
    events_parser.add_argument("--root-dir", default=None)
    events_parser.add_argument("--root", default=None)
    events_parser.add_argument("--limit", type=int, default=8, help="Max results count")

    # 4. query-timeline
    timeline_parser = subparsers.add_parser("query-timeline", help="Search timeline nodes, edges, foreshadows, hooks")
    timeline_parser.add_argument("--query", required=True, help="Text query to search for")
    timeline_parser.add_argument("--root-dir", default=None)
    timeline_parser.add_argument("--root", default=None)
    timeline_parser.add_argument("--limit", type=int, default=8, help="Max results count")

    # 5. compress-assets
    compress_parser = subparsers.add_parser("compress-assets", help="Compress timeline, events and assets")
    compress_parser.add_argument("--root-dir", default=None)
    compress_parser.add_argument("--root", default=None)

    calibrate_parser = subparsers.add_parser(
        "calibrate-prose",
        help="Build a local prose identity profile from explicit sample files",
    )
    calibrate_parser.add_argument("--sample", action="append", default=[], help="User-provided prose sample (repeatable)")
    calibrate_parser.add_argument(
        "--accepted-chapter",
        action="append",
        default=[],
        help="Accepted chapter text to include (repeatable)",
    )
    calibrate_parser.add_argument("--root-dir", default=None)
    calibrate_parser.add_argument("--root", default=None)
    calibrate_parser.add_argument("--output", default=None, help="Profile output path (default: assets/prose_identity_profile.json)")
    calibrate_parser.add_argument("--force", action="store_true", help="Overwrite an existing profile")
    calibrate_parser.add_argument("--list-versions", action="store_true", help="List saved profile revisions")
    calibrate_parser.add_argument("--restore-revision", type=int, default=None, help="Restore a prior revision as a new active revision")
    calibrate_parser.add_argument("--json-output", action="store_true")

    agent_parser = subparsers.add_parser(
        "agent",
        help="Agent bridge: status, logs, alerts (JSON; use with Cursor MCP / skills)",
    )
    agent_sub = agent_parser.add_subparsers(dest="agent_command", required=True)

    ap = agent_sub.add_parser("projects", help="List projects from projects.json")
    ap.add_argument("--novel-root", default=None, help="Workspace root (parent of projects/)")
    ap.set_defaults(func=agent_projects_cmd)

    snap = agent_sub.add_parser("snapshot", help="Progress, pending, readiness bundle")
    snap.add_argument("--project-id", default="", help="Project id (default: active)")
    snap.add_argument("--novel-root", default=None)
    snap.add_argument("--root-dir", default=None)
    snap.add_argument("--root", default=None)
    snap.add_argument(
        "--http",
        action="store_true",
        help="Fetch from running API (NOVEL_AGENT_API_URL)",
    )
    snap.set_defaults(func=agent_snapshot_cmd)

    logs = agent_sub.add_parser("logs", help="Tail file logs or runtime buffer (--runtime)")
    logs.add_argument("--project-id", default="")
    logs.add_argument("--novel-root", default=None)
    logs.add_argument("--root-dir", default=None)
    logs.add_argument("--root", default=None)
    logs.add_argument("--lines", type=int, default=80)
    logs.add_argument("--since-id", type=int, default=0, help="Runtime log cursor (--runtime)")
    logs.add_argument(
        "--runtime",
        action="store_true",
        help="Use GET /api/runtime-logs (requires running server)",
    )
    logs.set_defaults(func=agent_logs_cmd)

    alerts = agent_sub.add_parser("alerts", help="Pipeline alerts (HTTP only)")
    alerts.set_defaults(func=agent_alerts_cmd)

    health = agent_sub.add_parser("health", help="API health (HTTP only)")
    health.set_defaults(func=agent_health_cmd)

    hwe_scan_parser = subparsers.add_parser("hwe-scan", help="Scan prose for AI writing slop and style issues")
    hwe_scan_parser.add_argument("--file", default=None, help="File path to scan")
    hwe_scan_parser.add_argument("--text", default=None, help="Prose text string to scan")
    hwe_scan_parser.add_argument("--chapter", default=None, help="Chapter ID")
    hwe_scan_parser.add_argument("--root-dir", default=None, help="Project root directory")
    hwe_scan_parser.add_argument("--root", default=None, help="Project root directory")
    hwe_scan_parser.add_argument("--format", choices=["table", "json"], default="table", help="Output format")
    hwe_scan_parser.add_argument("--save", action="store_true", help="Save scan report to SQLite database")

    hwe_eval_parser = subparsers.add_parser("hwe-eval", help="Run Eval Lab benchmark suite")
    hwe_eval_parser.add_argument("--fixtures-dir", default=None, help="Custom fixtures directory")
    hwe_eval_parser.add_argument("--format", choices=["table", "json"], default="table", help="Output format")
    hwe_eval_parser.add_argument("--assert-fpr", action="store_true", help="Fail if False Positive Rate >= 5%")

    hwe_mem_parser = subparsers.add_parser("hwe-rebuild-memory", help="Rebuild longform expression memory and diagnostics")
    hwe_mem_parser.add_argument("--novel-root", default=None, help="Workspace root")
    hwe_mem_parser.add_argument("--root-dir", default=None, help="Workspace root")
    hwe_mem_parser.add_argument("--root", default=None, help="Workspace root")
    hwe_mem_parser.add_argument("--format", choices=["table", "json"], default="table", help="Output format")
    hwe_mem_parser.add_argument("--save", action="store_true", help="Save memory state")

    plugin_parser = subparsers.add_parser("plugin", help="Inkrest plugin developer suite")
    plugin_sub = plugin_parser.add_subparsers(dest="plugin_subcommand", required=True)

    # plugin init
    init_p = plugin_sub.add_parser("init", help="Scaffold a new plugin")
    init_p.add_argument("name", help="Plugin identifier/name")
    init_p.add_argument("--type", dest="ptype", choices=["pipeline_hook", "command", "web_extension"], default="pipeline_hook", help="Plugin type")
    init_p.add_argument("--dest", default="plugins", help="Destination parent directory")

    # plugin validate
    val_p = plugin_sub.add_parser("validate", help="Validate plugin manifest")
    val_p.add_argument("target", help="Plugin directory or .zip file path")

    # plugin pack
    pack_p = plugin_sub.add_parser("pack", help="Package a plugin into a zip archive")
    pack_p.add_argument("source", help="Plugin directory")
    pack_p.add_argument("--output", default=None, help="Output zip file path")

    # plugin test
    test_p = plugin_sub.add_parser("test", help="Test plugin contract using Mock Test Host")
    test_p.add_argument("source", help="Plugin directory")

    args = parser.parse_args(argv)

    if args.command == "run-chapter":
        run_chapter_cmd(args)
    elif args.command == "run-arc":
        run_arc_cmd(args)
    elif args.command == "continue-novel":
        continue_novel_cmd(args)
    elif args.command == "rebuild-index":
        rebuild_index_cmd(args)
    elif args.command == "dashboard":
        dashboard_cmd(args)
    elif args.command == "query-events":
        query_events_cmd(args)
    elif args.command == "query-timeline":
        query_timeline_cmd(args)
    elif args.command == "compress-assets":
        compress_assets_cmd(args)
    elif args.command == "calibrate-prose":
        calibrate_prose_cmd(args)
    elif args.command == "agent":
        args.func(args)
    elif args.command == "hwe-scan":
        hwe_scan_cmd(args)
    elif args.command == "hwe-eval":
        hwe_eval_cmd(args)
    elif args.command == "hwe-rebuild-memory":
        hwe_rebuild_memory_cmd(args)
    elif args.command == "plugin":
        plugin_cmd(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
