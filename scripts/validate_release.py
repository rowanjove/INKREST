#!/usr/bin/env python3
"""Release validation: version alignment + optional bundle manifest check."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_version() -> str:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError(f"Invalid VERSION: {version!r}")
    return version


def check_version_alignment() -> list[str]:
    issues: list[str] = []
    version = read_version()
    package = json.loads((ROOT / "web" / "frontend" / "package.json").read_text(encoding="utf-8"))
    if str(package.get("version")) != version:
        issues.append(
            f"package.json version {package.get('version')!r} != VERSION {version!r}; run python scripts/sync_version.py",
        )
    app_text = (ROOT / "web" / "app.py").read_text(encoding="utf-8")
    match = re.search(r'FastAPI\(title="Novel Agent API", version="([^"]+)"', app_text)
    if not match or match.group(1) != version:
        issues.append(
            f"web/app.py FastAPI version {match.group(1) if match else None!r} != VERSION {version!r}",
        )
    return issues


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check-bundle",
        action="store_true",
        help="Also validate dist-desktop/win-unpacked when present",
    )
    args = parser.parse_args()

    issues = check_version_alignment()
    if issues:
        print("Release validation failed:", file=sys.stderr)
        for item in issues:
            print(f"  - {item}", file=sys.stderr)
        return 1

    bundle_root = ROOT / "web" / "frontend" / "dist-desktop" / "win-unpacked"
    if args.check_bundle and bundle_root.is_dir():
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "verify_bundle_manifest.py"), str(bundle_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout, file=sys.stderr)
            return proc.returncode

    print("Release validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())