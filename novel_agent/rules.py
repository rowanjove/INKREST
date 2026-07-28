from pathlib import Path
from typing import Any, Dict

import yaml


class RuleBook:
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)

    def load(self) -> Dict[str, Any]:
        path = self.root_dir / "assets" / "rules.yaml"
        if not path.exists():
            return {
                "commonWords": [],
                "commonSentences": [],
                "forbiddenWords": [],
                "forbiddenSentences": [],
                "writingTechniques": "",
                "referenceAuthors": [],
            }
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        data.setdefault("commonWords", [])
        data.setdefault("commonSentences", [])
        data.setdefault("forbiddenWords", [])
        data.setdefault("forbiddenSentences", [])
        data.setdefault("writingTechniques", "")
        data.setdefault("referenceAuthors", [])
        return data

    def to_prompt_section(self) -> str:
        rules = self.load()
        lines = ["## 结构化写作规则"]
        lines.append("### 常用词")
        lines.extend(self._items(rules["commonWords"]))
        lines.append("### 常用句式")
        lines.extend(self._items(rules["commonSentences"]))
        lines.append("### 禁用词")
        lines.extend(self._items(rules["forbiddenWords"]))
        lines.append("### 禁用句式")
        lines.extend(self._items(rules["forbiddenSentences"]))
        lines.append("### 写作手法")
        lines.append(str(rules["writingTechniques"] or "暂无。"))
        lines.append("### 对标作者与作品气质")
        authors = rules.get("referenceAuthors") or []
        author_lines = []
        for item in authors:
            if isinstance(item, str) and item.strip():
                author_lines.append(f"- {item.strip()}")
        if author_lines:
            lines.extend(author_lines)
            lines.append(
                "- 借鉴对标作品的叙事节奏、人物张力与类型语感；不要照抄剧情、人名或原文句式。"
            )
        else:
            lines.append("- 无")
        return "\n".join(lines)

    @staticmethod
    def _items(items):
        if not items:
            return ["- 无"]
        result = []
        for item in items:
            if isinstance(item, dict):
                content = item.get("content", "")
                description = item.get("description", "")
                result.append(f"- {content}：{description}".rstrip("："))
            else:
                result.append(f"- {item}")
        return result

