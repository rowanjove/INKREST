from __future__ import annotations

import json

from novel_agent.retrieval.context_contract import (
    bind_context_role,
    bind_latest_context_role,
    context_pack_id,
    load_context_pack_contract,
    save_context_pack_contract,
)


def test_context_pack_id_is_stable_and_source_bound():
    kwargs = {
        "chapter_id": "12",
        "scene_id": "12-02",
        "context_text": "人物状态\n场景目标",
        "required_memory_ids": ["memory:b", "memory:a"],
        "content_lock_id": "lock:1",
    }
    assert context_pack_id(**kwargs) == context_pack_id(**kwargs)
    assert context_pack_id(**kwargs) != context_pack_id(**{**kwargs, "context_text": "不同上下文"})


def test_context_pack_persists_and_roles_bind_to_immutable_pack(tmp_path):
    pack_id = context_pack_id(chapter_id="12", scene_id="12-02", context_text="ctx")
    save_context_pack_contract(
        tmp_path,
        {"pack_id": pack_id, "chapter_id": "12", "scene_id": "12-02", "context_sha256": "abc"},
    )
    loaded = load_context_pack_contract(tmp_path, "12", "12-02")
    assert loaded["pack_id"] == pack_id
    bind_context_role(tmp_path, "12", role="writer", pack_id=pack_id)
    bind_latest_context_role(tmp_path, "12", role="auditor")
    bindings = json.loads(
        (tmp_path / "workspace" / "chapters" / "chapter_12" / "reports" / "context_bindings.json").read_text(
            encoding="utf-8"
        )
    )
    assert bindings["bindings"]["writer"]["pack_id"] == pack_id
    assert bindings["bindings"]["auditor"]["pack_id"] == pack_id
