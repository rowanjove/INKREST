"""Built-in Demo Project generator for INKREST (Milestone E).

Provisions 《栖墨示例书：星渊回响》 featuring complete world-building, characters,
multi-volume outlines, documents with revisions, foreshadowing, and timeline events.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


DEMO_BOOK_METADATA = {
    "title": "星渊回响",
    "genre": "科幻 / 太空歌剧 / 悬疑",
    "theme": "人类在深空裂隙中寻找失落文明信号，却发现信号源来自一万年前的地球自身。",
    "target_words": 500000,
}

DEMO_CHARACTERS = [
    {
        "id": "char_01",
        "name": "林野",
        "role": "主角 / 首席领航员",
        "personality": "冷静、克制、擅长在极端危机中进行概率计算",
        "background": "前火星深空舰队导航官，在三年前的'双子星遗迹事故'中幸存。",
    },
    {
        "id": "char_02",
        "name": "苏芮",
        "role": "科学官 / 天体物理学家",
        "personality": "敏锐、执着、对古文明信号具有异常洞察力",
        "background": "太阳系联合科学院特派员，坚信'深空回响'并非自然射电现象。",
    },
]

DEMO_OUTLINE = [
    {
        "volume_index": 1,
        "volume_title": "第一卷 寂静之海",
        "summary": "极光号科考舰驶离木星轨道，接获来自柯伊伯带边缘的异常窄带回波。",
        "chapters": [
            {
                "index": 1,
                "title": "第1章 寂夜微光",
                "content": "木星暗面的暗红色风暴在舰桥舷窗外缓慢翻滚。\n\n林野低头核对主引擎巡航参数，中央控制台的量子通信终端突然跳动起未被编码的脉冲信号。那是一段重复了七百余秒的音频切片，伴随着某种古老金属振动的杂音。\n\n“科学官，扫描信号源坐标。”林野按下舰内呼叫键，声音毫无波澜。",
            },
            {
                "index": 2,
                "title": "第2章 异常频段",
                "content": "苏芮快步走进舰桥，发梢带着实验室冷凝水汽。\n\n“不是自然引力透镜反射。”她在全息投影上重构了信号波形，“这种衰减特征，只有一万年前第一批离开地球轨道的原始探测器才拥有。”\n\n舷窗外，星海寂静无声。",
            },
        ],
    },
    {
        "volume_index": 2,
        "volume_title": "第二卷 远古回响",
        "summary": "穿过奥尔特云，极光号发现了一座封冻在彗星核内的对称人造结构。",
        "chapters": [
            {
                "index": 3,
                "title": "第3章 冰封残骸",
                "content": "探针发回了第一批高分辨率激光测绘图像。\n\n在直径三十公里的冰质天体中心，赫然嵌着一枚八面棱镜状的金属结构，表面刻着清晰的人类公制单位刻度。",
            },
        ],
    },
]

DEMO_FORESHADOWS = [
    {
        "id": "fs_01",
        "title": "双子星遗迹事故真相",
        "planted_chapter": 1,
        "planned_reveal": 3,
        "status": "active",
        "detail": "林野在三年前事故中丢失的记忆，与当前信号发生器存在同源量子纠缠。",
    }
]


def seed_demo_project(project_dir: Path) -> Path:
    """Create a fully structured demo project directory with database and sample chapters."""
    proj_path = Path(project_dir).resolve()
    proj_path.mkdir(parents=True, exist_ok=True)

    db_path = proj_path / "project.db"
    conn = sqlite3.connect(db_path)
    try:
        # Schema
        conn.execute("create table if not exists app_metadata (key text primary key, value text not null)")
        conn.execute("insert or replace into app_metadata values ('schema_version', '2')")
        conn.execute("insert or replace into app_metadata values ('project_name', ?)", (DEMO_BOOK_METADATA["title"],))

        conn.execute(
            """
            create table if not exists documents (
                id text primary key,
                title text not null,
                content text not null,
                word_count integer not null,
                chapter_index integer not null,
                volume_name text,
                created_at text not null
            )
            """
        )

        for vol in DEMO_OUTLINE:
            vol_title = vol["volume_title"]
            for ch in vol["chapters"]:
                doc_id = f"demo_doc_{ch['index']:03d}"
                conn.execute(
                    """
                    insert or replace into documents (id, title, content, word_count, chapter_index, volume_name, created_at)
                    values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (doc_id, ch["title"], ch["content"], len(ch["content"]), ch["index"], vol_title, now_iso()),
                )

        conn.commit()
    finally:
        conn.close()

    # Meta json
    (proj_path / "meta.json").write_text(
        json.dumps(
            {
                "metadata": DEMO_BOOK_METADATA,
                "characters": DEMO_CHARACTERS,
                "outline": DEMO_OUTLINE,
                "foreshadows": DEMO_FORESHADOWS,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return proj_path
