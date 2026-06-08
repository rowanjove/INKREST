#!/usr/bin/env python3
"""Copy built web/frontend/dist into the PyInstaller python-runtime bundle."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "web" / "frontend" / "dist"
DST = (
    ROOT
    / "build"
    / "python-runtime"
    / "novel-agent-backend"
    / "_internal"
    / "web"
    / "frontend"
    / "dist"
)


def main() -> int:
    if not SRC.is_dir():
        print(f"Missing frontend build: {SRC}\nRun: cd web/frontend && npm run build", file=sys.stderr)
        return 1
    if not (ROOT / "build" / "python-runtime").is_dir():
        print(
            "Missing python-runtime bundle. Run: cd web/frontend && npm run build:backend",
            file=sys.stderr,
        )
        return 1
    DST.parent.mkdir(parents=True, exist_ok=True)
    if DST.exists():
        shutil.rmtree(DST)
    shutil.copytree(SRC, DST)
    index_js = sorted((DST / "assets").glob("index-*.js"))
    label = index_js[0].name if index_js else "(no index chunk)"
    print(f"Synced frontend dist -> {DST} ({label})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())