"""Unit tests for ImportWizard text parsing and project commit."""

import sqlite3
from pathlib import Path
from novel_agent.importers.import_wizard import ImportWizard


SAMPLE_NOVEL_RAW = """
第一卷 风起青萍

第一章 少年出山
山风拂过石桥，少年背负木剑，回头望了最后一眼道观。
这是他第一次离开终南山。

第二章 驿路风云
暮色降临，官道旁的茶摊燃起昏暗的油灯。
三名带刀汉子悄然围拢过来。

第二卷 潜龙在渊

第三章 金陵夜雨
金陵城的夜雨连绵了三日。
秦淮河上的画舫依旧笙歌曼舞。
"""


def test_import_wizard_parsing_and_commit(tmp_path: Path):
    tree = ImportWizard.parse_text(SAMPLE_NOVEL_RAW)

    assert tree.total_chapters == 3
    assert len(tree.volumes) == 2
    assert tree.total_words > 50

    vol1 = tree.volumes[0]
    assert "第一卷" in vol1.title
    assert len(vol1.chapters) == 2
    assert "第一章" in vol1.chapters[0].title
    assert "第二章" in vol1.chapters[1].title

    vol2 = tree.volumes[1]
    assert "第二卷" in vol2.title
    assert len(vol2.chapters) == 1
    assert "第三章" in vol2.chapters[0].title

    # Commit to project.db
    proj_dir = tmp_path / "imported_novel"
    inserted = ImportWizard.commit_to_project(tree, proj_dir)
    assert inserted == 3

    db_path = proj_dir / "project.db"
    assert db_path.is_file()

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("select id, title, chapter_index, volume_name from documents order by chapter_index").fetchall()
        assert len(rows) == 3
        assert rows[0][2] == 1
        assert "风起青萍" in rows[0][3]
        assert rows[2][2] == 3
        assert "潜龙在渊" in rows[2][3]
    finally:
        conn.close()
