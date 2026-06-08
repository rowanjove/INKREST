"""Novel Agent — Single entry point.

Supports two modes:
  1. Server mode (default): Starts FastAPI and opens browser.
  2. Run chapter mode: python main.py run-chapter --chapter-id X --goal Y [--json-output]
"""

import argparse
import os
import sys
import threading
import time
import webbrowser
import secrets
from pathlib import Path

# Add dynamic dependencies directory to sys.path
if os.environ.get("NOVEL_AGENT_ROOT"):
    base_dir = Path(os.environ["NOVEL_AGENT_ROOT"]).resolve()
elif getattr(sys, "frozen", False):
    base_dir = Path(sys.executable).resolve().parent
else:
    base_dir = Path(__file__).resolve().parent

py_deps_dir = base_dir / "data" / "py_deps"
py_deps_dir.mkdir(parents=True, exist_ok=True)
if str(py_deps_dir) not in sys.path:
    sys.path.insert(0, str(py_deps_dir))

# ---- Python Interpreter Stub Interceptor ----
if len(sys.argv) > 1:
    clean_args = []
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ("-u", "-E", "-s", "-I", "-O"):
            i += 1
            continue
        clean_args.append(arg)
        i += 1

    if clean_args and getattr(sys, "frozen", False):
        if clean_args[0] in ("pip", "-m", "-c"):
            print(
                f"Error: `{clean_args[0]}` stub is disabled in packaged builds.",
                file=sys.stderr,
            )
            sys.exit(2)

    if clean_args:
        if clean_args[0] == "pip":
            try:
                sys.argv = [sys.argv[0]] + clean_args[1:]
                try:
                    from pip._internal import main as pipmain
                except ImportError:
                    from pip import main as pipmain
                sys.exit(pipmain())
            except Exception as e:
                print(f"Error running pip via stub: {e}", file=sys.stderr)
                sys.exit(1)

        elif clean_args[0] == "-m" and len(clean_args) > 1:
            module_name = clean_args[1]
            module_args = clean_args[2:]
            try:
                sys.argv = [module_name] + module_args
                import runpy
                runpy.run_module(module_name, run_name="__main__", alter_sys=True)
                sys.exit(0)
            except Exception as e:
                print(f"Error running module {module_name} via stub: {e}", file=sys.stderr)
                sys.exit(1)

        elif clean_args[0] == "-c" and len(clean_args) > 1:
            print(
                "Error: -c / exec is disabled in packaged builds (security). "
                "Use `python main.py serve` or `run-chapter`.",
                file=sys.stderr,
            )
            sys.exit(2)



def open_browser(host: str, port: int, delay: float = 1.5) -> None:
    """Open the default browser after a short delay."""
    time.sleep(delay)
    url = f"http://{host}:{port}"
    webbrowser.open(url)


def _prepare_remote_access(host: str, allow_remote: bool) -> None:
    from web.security import (
        ACCESS_TOKEN_ENV,
        ALLOW_REMOTE_ENV,
        BIND_HOST_ENV,
        is_loopback_host,
        require_remote_token,
    )

    os.environ[BIND_HOST_ENV] = host
    if allow_remote:
        os.environ[ALLOW_REMOTE_ENV] = "1"
    from web.security import bootstrap_loopback_access_token, LOCAL_TOKEN_FILENAME

    root = Path(os.environ.get("NOVEL_AGENT_ROOT", str(base_dir)))
    if is_loopback_host(host):
        token = bootstrap_loopback_access_token(root)
        if token and not os.environ.get("NOVEL_AGENT_QUIET_TOKEN"):
            print(
                f"Local access token ({ACCESS_TOKEN_ENV}) persisted under data/{LOCAL_TOKEN_FILENAME}; "
                "fetch via GET /api/auth/local-setup from loopback clients."
            )
    elif allow_remote and not os.environ.get(ACCESS_TOKEN_ENV):
        os.environ[ACCESS_TOKEN_ENV] = secrets.token_urlsafe(32)
        print(f"Remote access token ({ACCESS_TOKEN_ENV}): {os.environ[ACCESS_TOKEN_ENV]}")
    require_remote_token(host, allow_remote, os.environ.get(ACCESS_TOKEN_ENV, ""))


def cmd_serve(args: argparse.Namespace) -> None:
    """Start the FastAPI server."""
    if getattr(args, "root_dir", None):
        os.environ["NOVEL_AGENT_ROOT"] = str(Path(args.root_dir).resolve())
    _prepare_remote_access(args.host, getattr(args, "allow_remote", False))

    import uvicorn
    from web.app import app

    if not args.no_browser:
        threading.Thread(target=open_browser, args=(args.host, args.port), daemon=True).start()

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


def cmd_run_chapter(args: argparse.Namespace) -> None:
    """Run a single chapter generation pipeline (delegated to cli.py)."""
    import cli
    cli.run_chapter_cmd(args)


def main() -> None:
    # Legacy: `python main.py --no-browser` (pre-subcommand CLI)
    import sys

    if len(sys.argv) > 1 and sys.argv[1] not in ("serve", "run-chapter", "-h", "--help"):
        sys.argv.insert(1, "serve")

    parser = argparse.ArgumentParser(description="Novel Agent")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # serve subcommand
    serve_parser = subparsers.add_parser("serve", help="Start the web server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    serve_parser.add_argument("--port", type=int, default=8000, help="Bind port")
    serve_parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload (dev mode)")
    serve_parser.add_argument("--allow-remote", action="store_true", help="Allow non-loopback binding with token protection")
    serve_parser.add_argument("--root-dir", default=None, help="Project data root directory")

    # run-chapter subcommand
    run_parser = subparsers.add_parser("run-chapter", help="Run a chapter generation")
    run_parser.add_argument("--chapter-id", required=True, help="Chapter ID (e.g. 001)")
    run_parser.add_argument("--goal", required=True, help="Chapter goal description")
    run_parser.add_argument("--json-output", action="store_true", help="Emit JSON progress to stdout (for Electron IPC)")
    run_parser.add_argument("--root-dir", default=None, help="Project root directory")
    run_parser.add_argument("--dry-run", action="store_true", help="Use static LLM responses")

    args = parser.parse_args()

    if args.command == "run-chapter":
        cmd_run_chapter(args)
    elif args.command == "serve":
        cmd_serve(args)
    else:
        # Default: serve mode (backward compatible)
        args.host = "127.0.0.1"
        args.port = 8000
        args.no_browser = False
        args.reload = False
        args.allow_remote = False
        cmd_serve(args)


if __name__ == "__main__":
    main()
