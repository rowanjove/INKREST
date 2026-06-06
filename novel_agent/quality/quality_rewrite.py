"""One-shot rewrite driven by quality guard failures."""

from __future__ import annotations

from typing import Any, Dict, TYPE_CHECKING

from novel_agent.logging_config import get_logger
from novel_agent.progress import emit_progress

if TYPE_CHECKING:
    from novel_agent.orchestrator import NovelOrchestrator

logger = get_logger("quality.rewrite")


def build_quality_rewrite_hints(report: Dict[str, Any]) -> str:
    lines = []
    summary = report.get("guard_summary") or {}
    for guard in summary.get("blocked_by") or []:
        lines.append(f"- [硬门禁] {guard}")
    for name, check in (report.get("checks") or {}).items():
        if check.get("pass"):
            continue
        level = check.get("level") or "warning"
        for detail in (check.get("details") or [])[:4]:
            lines.append(f"- [{name}/{level}] {detail}")
    return "\n".join(lines)


async def attempt_quality_rewrite(
    orchestrator: "NovelOrchestrator",
    chapter_id: str,
    final_text: str,
    report: Dict[str, Any],
) -> str:
    hints = build_quality_rewrite_hints(report)
    if not hints.strip() or not (final_text or "").strip():
        return final_text

    emit_progress("quality_rewrite", "running", chapter_id=chapter_id)
    prompt = (
        "你是小说质量修正编辑。根据下列质量门禁反馈修订正文：\n"
        "- 不新增主线剧情与角色\n"
        "- 保持篇幅与段落结构大致相当\n"
        "- 只输出修订后的完整正文\n\n"
        f"## 必须修复\n{hints}\n\n"
        f"## 待修订正文\n{final_text}"
    )
    try:
        editor = orchestrator.style_editor
        if hasattr(editor, "arun"):
            revised = (await editor.arun(prompt)).strip()
        else:
            revised = editor.run(prompt).strip()
        if revised:
            emit_progress("quality_rewrite", "done", {"chars": len(revised)}, chapter_id)
            return revised
    except Exception as exc:
        logger.warning("Quality rewrite failed for chapter %s: %s", chapter_id, exc)
        emit_progress(
            "quality_rewrite",
            "error",
            {"error": str(exc)},
            chapter_id,
        )
    return final_text