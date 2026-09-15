import json
from pathlib import Path
import pytest

from novel_agent.assistant.models import PatchStatus
from novel_agent.assistant.patch.service import PatchService


def test_patch_lifecycle_create_apply_revert(tmp_path: Path):
    ch_dir = tmp_path / "workspace" / "chapters" / "chapter_001"
    ch_dir.mkdir(parents=True)
    orig_text = "江炘靠在门边，看着窗外的大雨。"
    (ch_dir / "chapter.txt").write_text(orig_text, encoding="utf-8")
    (ch_dir / "chapter.json").write_text(
        json.dumps({"content": orig_text}, ensure_ascii=False), encoding="utf-8"
    )

    service = PatchService(tmp_path)

    proposed = "江炘斜倚着门框。雨水沿玻璃一道道滑下来，街灯被切成细长的光斑。"
    patch = service.create_patch(
        project_id="test_proj",
        chapter_id="001",
        original_text=orig_text,
        proposed_text=proposed,
        reason="增强画面感",
        skill_id="polish",
    )

    assert patch.id.startswith("patch_")
    assert patch.status == PatchStatus.PROPOSED

    # Test apply
    apply_res = service.apply_patch(patch.id)
    assert apply_res["success"] is True
    assert (ch_dir / "chapter.txt").read_text(encoding="utf-8") == proposed

    fetched = service.get_patch(patch.id)
    assert fetched is not None
    assert fetched.status == PatchStatus.ACCEPTED

    # Test revert
    revert_res = service.revert_patch(patch.id)
    assert revert_res["success"] is True
    assert (ch_dir / "chapter.txt").read_text(encoding="utf-8") == orig_text

    fetched_after_revert = service.get_patch(patch.id)
    assert fetched_after_revert is not None
    assert fetched_after_revert.status == PatchStatus.REVERTED


def test_patch_reject(tmp_path: Path):
    service = PatchService(tmp_path)
    patch = service.create_patch(
        project_id="test_proj",
        chapter_id="002",
        original_text="旧文本",
        proposed_text="新文本",
    )
    rejected = service.reject_patch(patch.id)
    assert rejected is not None
    assert rejected.status == PatchStatus.REJECTED
