"""Human approval gate for chapter outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from novel_agent.scripts.count_chars import count_chinese_chars


class ApprovalGate:
    def __init__(
        self,
        interactive: bool = False,
        plugin_manager: Any = None,
        root_dir: Optional[Path] = None,
    ):
        self.interactive = interactive
        self.plugin_manager = plugin_manager
        self.root_dir = Path(root_dir) if root_dir else None

    def _strict_factory_mode(self) -> bool:
        if not self.root_dir:
            return False
        try:
            from novel_agent.quality.settings import resolve_quality_mode

            return resolve_quality_mode(self.root_dir) == "block_on_fail"
        except Exception:
            return False

    def _chapter_plain_text(self, chapter_id: str, chapter_dir: Path) -> str:
        if self.root_dir:
            try:
                from novel_agent.services.manuscript_workspace import read_chapter_plain_text

                text = read_chapter_plain_text(self.root_dir, chapter_id).strip()
                if text:
                    return text
            except Exception:
                pass
        final_path = Path(chapter_dir) / "chapter_final.txt"
        if final_path.is_file():
            try:
                return final_path.read_text(encoding="utf-8").strip()
            except OSError:
                return ""
        return ""

    def _noninteractive_decision(self, chapter_id: str, chapter_dir: Path) -> bool:
        """Auto-pass unless factory strict mode sees empty text or a bad audit."""
        if not self._strict_factory_mode():
            return True
        if not self._chapter_plain_text(chapter_id, chapter_dir):
            return False
        audit_path = Path(chapter_dir) / "reports" / "audit.json"
        if not audit_path.is_file():
            return True
        try:
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if not isinstance(audit, dict):
            return False
        status = str(audit.get("status") or "ok").strip().lower()
        if status in {"error", "incomplete", "unknown"}:
            return False
        risk = str(audit.get("risk_level") or "").strip().lower()
        if risk in {"高", "high", "critical", "严重"}:
            return False
        return True

    def request_approval(self, chapter_id: str, chapter_dir: Path) -> bool:
        """Request human approval for a chapter.

        Non-interactive report_only still auto-passes (tests / dry runs).
        Strict factory mode refuses empty drafts and incomplete or high-risk audits.
        """
        if self.plugin_manager:
            strategies = self.plugin_manager.get_approval_strategies()
            if strategies:
                strategy = next(iter(strategies.values()))
                return strategy.request_approval(chapter_id, Path(chapter_dir))

        if not self.interactive:
            return self._noninteractive_decision(chapter_id, chapter_dir)

        chapter_dir = Path(chapter_dir)
        final_path = chapter_dir / "chapter_final.txt"
        audit_path = chapter_dir / "reports" / "audit.json"
        wordcount_path = chapter_dir / "reports" / "wordcount.json"

        print(f"\n{'='*60}")
        print(f"章节 {chapter_id} 审批")
        print(f"{'='*60}")

        if final_path.exists():
            text = final_path.read_text(encoding="utf-8")
            char_count = count_chinese_chars(text)
            print(f"终稿字数：{char_count} 汉字")
            preview = text[:200].replace("\n", " ")
            print(f"预览：{preview}...")

        if wordcount_path.exists():
            import json
            wc = json.loads(wordcount_path.read_text(encoding="utf-8"))
            print(f"字数状态：{wc.get('status', '?')}")

        if audit_path.exists():
            import json
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            print(f"风险等级：{audit.get('risk_level', '?')}")
            issues = audit.get("issues", [])
            if issues:
                print(f"审校问题：{len(issues)} 个")
                for issue in issues[:3]:
                    print(f"  - {issue}")

        print(f"{'='*60}")
        while True:
            answer = input("是否通过？(y/n): ").strip().lower()
            if answer in ("y", "yes", "是"):
                return True
            if answer in ("n", "no", "否"):
                return False
            print("请输入 y 或 n")
