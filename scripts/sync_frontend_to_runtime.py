#!/usr/bin/env python3
"""Copy built web/frontend/dist into PyInstaller bundles and Electron resources."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "web" / "frontend" / "dist"

TARGET_DIRS = [
    ROOT / "build" / "python-runtime" / "novel-agent-backend" / "_internal" / "web" / "frontend" / "dist",
    ROOT / "build" / "python-runtime" / "novel-agent-backend" / "web" / "frontend" / "dist",
    ROOT / "web" / "frontend" / "dist-desktop" / "win-unpacked" / "resources" / "python-runtime" / "novel-agent-backend" / "_internal" / "web" / "frontend" / "dist",
    ROOT / "web" / "frontend" / "dist-desktop" / "win-unpacked" / "resources" / "python-runtime" / "novel-agent-backend" / "web" / "frontend" / "dist",
]


def sync_to(dst: Path) -> bool:
    try:
        backend_dir = dst.parents[3]  # novel-agent-backend directory
        if not backend_dir.is_dir():
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(SRC, dst)
        if not (dst / "index.html").is_file():
            print(f"Error: index.html missing after copy to {dst}", file=sys.stderr)
            return False
        index_js = sorted((dst / "assets").glob("index-*.js"))
        label = index_js[0].name if index_js else "(no index chunk)"
        print(f"Synced frontend dist -> {dst} ({label})")

        manifest_src = ROOT / "web" / "factory_modes.json"
        manifest_dst = dst.parents[1] / "factory_modes.json"
        if manifest_src.is_file():
            manifest_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(manifest_src, manifest_dst)
            print(f"Synced factory manifest -> {manifest_dst}")
        return True
    except Exception as exc:
        print(f"Warning: failed syncing to {dst}: {exc}", file=sys.stderr)
        return False


def main() -> int:
    if not SRC.is_dir() or not (SRC / "index.html").is_file():
        print(
            f"Error: Missing frontend build or index.html at: {SRC}\n"
            "Run: cd web/frontend && npm run build",
            file=sys.stderr,
        )
        return 1

    synced_count = 0
    for target in TARGET_DIRS:
        if sync_to(target):
            synced_count += 1

    if synced_count == 0:
        # Fallback: ensure at least the build/python-runtime target is populated if python-runtime exists
        runtime_base = ROOT / "build" / "python-runtime"
        if runtime_base.is_dir():
            primary = TARGET_DIRS[0]
            if sync_to(primary):
                synced_count += 1

    print(f"Successfully synced frontend assets to {synced_count} runtime target(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())