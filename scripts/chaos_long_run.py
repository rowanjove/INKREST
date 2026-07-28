#!/usr/bin/env python3
"""Dry-run chaos: sequential chapter submits with optional abort (local/weekly)."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Novel agent dry-run chaos runner")
    parser.add_argument("--chapters", type=int, default=5)
    parser.add_argument("--report", type=Path, default=Path("logs/chaos_report.json"))
    args = parser.parse_args()

    from tests.test_full_chain_chaos import _seed_ready
    from novel_agent.pipeline import PipelineConfig
    from novel_agent.orchestrator import NovelOrchestrator

    tmp = Path(tempfile.mkdtemp(prefix="novel-chaos-"))
    _seed_ready(tmp)
    config = PipelineConfig.dry_run(tmp)
    orch = NovelOrchestrator(config)
    ok = 0
    errors = []
    for i in range(1, args.chapters + 1):
        cid = f"{i:03d}"
        try:
            orch.run_chapter(cid, f"chaos goal {cid}")
            ok += 1
        except Exception as exc:
            errors.append({"chapter_id": cid, "error": str(exc)})
    report = {"root": str(tmp), "ok": ok, "errors": errors}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())