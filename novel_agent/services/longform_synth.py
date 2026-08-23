"""Schema-compliant synthetic novels for longform benchmarks and tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from novel_agent.services.manuscript_documents import plain_text_to_tiptap
from novel_agent.services.rolling_planner import format_chapter_id
from novel_agent.state.sqlite_store import SQLiteStateStore


def seed_synthetic_project(
    root_dir: Path,
    *,
    chapters: int,
    seed: int = 1,
    title: str = "合成长篇",
    scale: str = "infinite",
) -> Dict[str, Any]:
    """Write chapters through the official SQLite repositories. No LLM calls."""

    root = Path(root_dir)
    root.mkdir(parents=True, exist_ok=True)
    (root / "workspace").mkdir(parents=True, exist_ok=True)
    (root / "config").mkdir(parents=True, exist_ok=True)
    count = max(0, int(chapters))
    store = SQLiteStateStore(root)
    items: List[Dict[str, Any]] = []
    for number in range(1, count + 1):
        chapter_id = format_chapter_id(number)
        body = f"第{number}章正文 seed={seed}"
        items.append(
            {
                "chapter_id": chapter_id,
                "title": f"第{number}章",
                "plain_text": body,
                "markdown_text": body,
                "content_json": plain_text_to_tiptap(body),
                "source": "synth",
                "word_count": len(body),
            }
        )
    created = store.bulk_create_manuscript_documents(items)
    if count:
        midpoint = format_chapter_id(max(1, count // 2))
        store.sync_state_update(
            midpoint,
            {
                "events": [
                    {
                        "id": f"E-{seed}",
                        "summary": "合成事件",
                        "characters": ["主角"],
                        "objects": ["信物"],
                        "threads": ["主线"],
                    }
                ],
                "threads": [
                    {
                        "id": f"T-{seed}",
                        "title": "开放主线",
                        "status": "open",
                        "summary": "等待回收",
                    }
                ],
                "characters": {
                    "protagonist": {
                        "name": "主角",
                        "location": "起点",
                        "emotion": "平静",
                    }
                },
                "foreshadows": [
                    {
                        "id": f"F-{seed}",
                        "title": "未揭之谜",
                        "status": "open",
                        "description": "合成伏笔",
                    }
                ],
            },
        )
    outline = {
        "title": title,
        "target_chapters": count,
        "scale_profile": {
            "scale": scale,
            "target_chapters": count,
        },
    }
    (root / "workspace" / "outline.json").write_text(
        json.dumps(outline, ensure_ascii=False),
        encoding="utf-8",
    )
    meta = {"name": title, "target_chapters": count, "scale": scale}
    (root / "config" / "project_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False),
        encoding="utf-8",
    )
    return {
        "root": str(root),
        "chapters": created,
        "seed": int(seed),
        "title": title,
        "llm_called": False,
    }
