"""Novel Agent CLI Interface.

Supports offline tasks:
  1. run-chapter: Runs the generation pipeline for a single chapter.
  2. dashboard: Rebuilds the HTML dashboard.
  3. query-events: Searches events in SQLite.
  4. query-timeline: Searches timeline items.
  5. compress-assets: Compresses project assets.
  6. agent: Read-only status / logs for external AI agents (JSON stdout).
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional

from novel_agent.agents.asset_compressor import compress_assets
from novel_agent.dashboard import write_dashboard
from novel_agent.logging_config import setup_logging
from novel_agent.orchestrator import NovelOrchestrator
from novel_agent.pipeline import PipelineConfig
from novel_agent.progress import enable_json_output, emit_complete, emit_error
from novel_agent.prompts import PromptRepository
from novel_agent.state.sqlite_store import SQLiteStateStore


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
        emit_error(args.chapter_id, str(exc))
        if not args.json_output:
            print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


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
        emit_error("", str(exc), "run_arc")
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


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
        emit_error("", str(exc), "continue_novel")
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


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
    elif args.command == "agent":
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
