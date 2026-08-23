"""Regression checks for privacy-sensitive material in published text assets."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_TEXT_ROOTS = (ROOT / "README.md", ROOT / "docs", ROOT / "assets", ROOT / "benchmarks", ROOT / "config")
LOCAL_WINDOWS_PATH = re.compile(
    r"(?i)\b[A-Z]:\\\\(?:Users|AI|Documents|Desktop|AppData|Program Files)\\\\",
)


def _public_text_files() -> list[Path]:
    files: list[Path] = []
    for root in PUBLIC_TEXT_ROOTS:
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            files.extend(
                path
                for path in root.rglob("*")
                if path.is_file() and path.suffix.lower() in {".md", ".txt", ".json", ".jsonl", ".yaml", ".yml"}
            )
    return files


def test_public_text_does_not_expose_local_windows_paths() -> None:
    leaks = []
    for path in _public_text_files():
        text = path.read_text(encoding="utf-8")
        if LOCAL_WINDOWS_PATH.search(text):
            leaks.append(str(path.relative_to(ROOT)))
    assert not leaks, f"published text contains local Windows paths: {leaks}"
