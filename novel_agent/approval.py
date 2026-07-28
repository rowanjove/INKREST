"""Human approval gate for chapter outputs."""

from pathlib import Path
from typing import Any, Dict

from novel_agent.scripts.count_chars import count_chinese_chars


class ApprovalGate:
    def __init__(self, interactive: bool = False, plugin_manager: Any = None):
        self.interactive = interactive
        self.plugin_manager = plugin_manager

    def request_approval(self, chapter_id: str, chapter_dir: Path) -> bool:
        """Request human approval for a chapter.

        In non-interactive mode (tests, dry runs), always returns True.
        In interactive mode, prints a summary and waits for y/n input.
        """
        if self.plugin_manager:
            strategies = self.plugin_manager.get_approval_strategies()
            if strategies:
                strategy = next(iter(strategies.values()))
                return strategy.request_approval(chapter_id, Path(chapter_dir))

        if not self.interactive:
            return True

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
