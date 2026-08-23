#!/usr/bin/env python3
"""Capture a reviewable M0 worktree freeze snapshot.

The snapshot is deliberately read-only: it records the commit, dirty paths,
runtime versions, and the active longform flag defaults so later benchmark
results can be compared with the exact source state that produced them.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    from novel_agent.control.longform_flags import as_dict, longform_flags

    status_lines = _git("status", "--short").splitlines()
    tracked_modified = []
    untracked = []
    for line in status_lines:
        path = line[3:] if len(line) >= 4 else ""
        if line.startswith("??"):
            untracked.append(path)
        else:
            tracked_modified.append(path)

    payload = {
        "format": "novel-agent-m0-freeze",
        "version": 1,
        "captured_at": datetime.now(UTC).isoformat(),
        "root": str(ROOT),
        "commit": _git("rev-parse", "HEAD"),
        "dirty": bool(status_lines),
        "status_lines": status_lines,
        "tracked_modified": tracked_modified,
        "untracked": untracked,
        "python": sys.version.split()[0],
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "longform_flags": longform_flags(ROOT),
        "flag_contract": as_dict(),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
