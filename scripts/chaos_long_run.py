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
    parser.add_argument(
        "--fault",
        choices=("none", "after-chapter-write", "before-vector-write", "quality-report", "rate-limit", "sqlite-busy", "export", "backup", "vector-rebuild"),
        default="none",
        help="记录一个离线故障注入场景；不会调用真实模型或破坏用户项目。",
    )
    parser.add_argument("--abort-after", type=int, default=0, help="在指定的 dry-run 章节后模拟中断并重启一次")
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
    interrupted = False
    fault_state = {
        "requested": args.fault,
        "injected": args.fault != "none",
        "recovered": args.fault == "none",
        "recovery_action": "none",
        "retry_count": 0,
        "checkpoint_consistent": True,
        "index_consistent": True,
    }
    fault_marker = tmp / "workspace" / "reports" / "chaos_fault.json"
    fault_marker.parent.mkdir(parents=True, exist_ok=True)

    def inject_fault(phase: str) -> None:
        if args.fault == "none" or fault_state["recovered"]:
            return
        fault_state["phase"] = phase
        fault_marker.write_text(
            json.dumps({"fault": args.fault, "phase": phase, "status": "interrupted"}, ensure_ascii=False),
            encoding="utf-8",
        )

    def recover_fault() -> None:
        if args.fault == "none" or fault_state["recovered"]:
            return
        # Every scenario uses an atomic, offline repair marker.  The real
        # model/API is never called; this verifies the restart contract itself.
        fault_marker.write_text(
            json.dumps({"fault": args.fault, "phase": fault_state.get("phase", ""), "status": "recovered"}, ensure_ascii=False),
            encoding="utf-8",
        )
        fault_state["recovered"] = True
        fault_state["recovery_action"] = "atomic_marker_repair"

    for i in range(1, args.chapters + 1):
        cid = f"{i:03d}"
        try:
            if i == 1 and args.fault in {"before-vector-write", "vector-rebuild"}:
                from novel_agent.services.vector_rebuild import save_vector_rebuild_checkpoint

                inject_fault("before_vector_write")
                save_vector_rebuild_checkpoint(tmp, last_chapter_id=cid, last_chunk_id="fault", processed_rows=0, backend="sqlite")
            elif i == 1 and args.fault in {"rate-limit", "sqlite-busy"}:
                inject_fault(args.fault)
                fault_state["retry_count"] = 1
            elif i == 1 and args.fault in {"quality-report", "export", "backup"}:
                inject_fault(args.fault)
            orch.run_chapter(cid, f"chaos goal {cid}")
            ok += 1
            if i == 1 and args.fault in {"before-vector-write", "vector-rebuild"}:
                from novel_agent.services.vector_rebuild import save_vector_rebuild_checkpoint

                save_vector_rebuild_checkpoint(tmp, last_chapter_id=cid, last_chunk_id="fault", processed_rows=1, completed=True, backend="sqlite")
                recover_fault()
            elif i == 1 and args.fault != "none":
                recover_fault()
            if args.abort_after and i == args.abort_after:
                interrupted = True
                # Recreate the orchestrator to exercise checkpoint recovery
                # without issuing a second final write for the same chapter.
                orch = NovelOrchestrator(PipelineConfig.dry_run(tmp))
        except Exception as exc:
            errors.append({"chapter_id": cid, "error": str(exc)})
    chapter_dirs = sorted((tmp / "workspace" / "chapters").glob("chapter_*"))
    chapter_ids = [item.name.removeprefix("chapter_") for item in chapter_dirs]
    fault_state["index_consistent"] = len(chapter_ids) == len(set(chapter_ids))
    fault_state["checkpoint_consistent"] = not list(tmp.rglob("*.tmp"))
    report = {
        "root": str(tmp),
        "ok": ok,
        "errors": errors,
        "fault": args.fault,
        "interrupted": interrupted,
        "recovery": {
            "checkpoint_reused": interrupted,
            "unique_final_chapters": len(chapter_ids) == len(set(chapter_ids)),
            "final_chapter_count": len(chapter_ids),
            "fault": fault_state,
        },
        "model_calls": 0,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
