#!/usr/bin/env python3
"""Fail if portable bundle paths include dev-only directories."""

from __future__ import annotations

import sys
from pathlib import Path

FORBIDDEN_PARTS = frozenset(
    {
        "scratch",
        "tests",
        ".git",
        "__pycache__",
        "node_modules",
        "dist-portable",
        "terminals",
    }
)
SENSITIVE_FILENAMES = frozenset(
    {
        ".env",
        ".local_access_token",
        "models.json",
        "plugins.yaml",
        "pipeline.yaml",
    }
)
RUNTIME_FILE_SUFFIXES = frozenset({".db", ".sqlite", ".sqlite3", ".log"})
RUNTIME_ROOTS = frozenset({"projects", "workspace", "logs", "data"})


def _is_runtime_root(rel: Path) -> bool:
    parts = rel.parts
    if not parts:
        return False
    if parts[0] in RUNTIME_ROOTS:
        return True
    return len(parts) > 1 and parts[0] == "resources" and parts[1] in RUNTIME_ROOTS


def _is_sensitive_file(rel: Path) -> bool:
    name = rel.name.casefold()
    if name == ".env" or name.startswith(".env."):
        return True
    if name in SENSITIVE_FILENAMES:
        return True
    return rel.suffix.casefold() in RUNTIME_FILE_SUFFIXES


def check_tree(root: Path) -> list[str]:
    issues: list[str] = []
    if not root.is_dir():
        return [f"missing bundle root: {root}"]
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        for part in rel.parts:
            if part in FORBIDDEN_PARTS:
                issues.append(str(rel))
                break
        else:
            if _is_runtime_root(rel) or (path.is_file() and _is_sensitive_file(rel)):
                issues.append(str(rel))
    return issues


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "bundle_root",
        nargs="?",
        default=str(Path(__file__).resolve().parents[1] / "dist"),
    )
    args = parser.parse_args()
    root = Path(args.bundle_root)
    issues = check_tree(root)
    if issues:
        print("Forbidden paths in bundle:", file=sys.stderr)
        for item in issues[:50]:
            print(f"  - {item}", file=sys.stderr)
        return 1
    print(f"OK: no forbidden dev paths under {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
