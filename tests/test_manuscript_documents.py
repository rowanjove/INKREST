import json

import pytest

from novel_agent.services.manuscript_documents import (
    derive_document_text,
    plain_text_to_tiptap,
)
from novel_agent.state.manuscript_repository import DocumentConflictError
from novel_agent.state.sqlite_store import SQLiteStateStore


def _doc(*paragraphs: str) -> dict:
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": paragraph}],
            }
            for paragraph in paragraphs
        ],
    }


def test_derives_plain_text_and_markdown_from_tiptap_json():
    content = {
        "type": "doc",
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "雨夜"}],
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "林越"},
                    {"type": "hardBreak"},
                    {"type": "text", "text": "推门而入。"},
                ],
            },
            {
                "type": "blockquote",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "别回头。"}],
                    }
                ],
            },
        ],
    }

    plain_text, markdown_text = derive_document_text(content)

    assert plain_text == "雨夜\n林越\n推门而入。\n别回头。"
    assert markdown_text == "## 雨夜\n\n林越  \n推门而入。\n\n> 别回头。"


def test_plain_text_import_creates_stable_tiptap_paragraphs():
    content = plain_text_to_tiptap("第一段。\n\n第二段。\n仍是第二段。")

    assert content["type"] == "doc"
    assert len(content["content"]) == 2
    assert content["content"][1]["content"][0]["text"] == "第二段。\n仍是第二段。"


def test_repository_uses_revision_for_optimistic_concurrency(tmp_path):
    store = SQLiteStateStore(tmp_path)
    created = store.create_manuscript_document(
        chapter_id="001",
        title="第一章",
        content_json=_doc("初稿"),
        plain_text="初稿",
        markdown_text="初稿",
        source="import",
    )

    updated = store.save_manuscript_document(
        chapter_id="001",
        title="第一章 雨夜",
        content_json=_doc("第二稿"),
        plain_text="第二稿",
        markdown_text="第二稿",
        expected_revision=created["revision"],
        source="autosave",
    )

    assert updated["revision"] == 2
    assert store.get_manuscript_document("001")["plain_text"] == "第二稿"

    with pytest.raises(DocumentConflictError) as conflict:
        store.save_manuscript_document(
            chapter_id="001",
            title="过期客户端",
            content_json=_doc("不应覆盖"),
            plain_text="不应覆盖",
            markdown_text="不应覆盖",
            expected_revision=1,
            source="autosave",
        )

    assert conflict.value.current["revision"] == 2
    assert store.get_manuscript_document("001")["plain_text"] == "第二稿"


def test_repository_skips_unchanged_save_and_restores_as_new_revision(tmp_path):
    store = SQLiteStateStore(tmp_path)
    first = store.create_manuscript_document(
        chapter_id="008",
        title="旧标题",
        content_json=_doc("旧正文"),
        plain_text="旧正文",
        markdown_text="旧正文",
        source="import",
    )
    unchanged = store.save_manuscript_document(
        chapter_id="008",
        title="旧标题",
        content_json=_doc("旧正文"),
        plain_text="旧正文",
        markdown_text="旧正文",
        expected_revision=first["revision"],
        source="autosave",
    )
    second = store.save_manuscript_document(
        chapter_id="008",
        title="新标题",
        content_json=_doc("新正文"),
        plain_text="新正文",
        markdown_text="新正文",
        expected_revision=unchanged["revision"],
        source="manual",
    )

    assert unchanged["revision"] == 1
    history = store.list_manuscript_revisions("008")
    assert [item["revision"] for item in history] == [2, 1]

    restored = store.restore_manuscript_revision(
        chapter_id="008",
        revision_id=history[-1]["revision_id"],
        expected_revision=second["revision"],
    )

    assert restored["revision"] == 3
    assert restored["plain_text"] == "旧正文"
    assert restored["source"] == "restore"


def test_document_payload_is_stored_as_json_not_python_repr(tmp_path):
    store = SQLiteStateStore(tmp_path)
    content = _doc("含“中文”与 emoji 🌧️")
    store.create_manuscript_document(
        chapter_id="010",
        title="编码",
        content_json=content,
        plain_text="含“中文”与 emoji 🌧️",
        markdown_text="含“中文”与 emoji 🌧️",
        source="manual",
    )

    document = store.get_manuscript_document("010")

    assert document["content_json"] == content
    assert json.loads(json.dumps(document["content_json"], ensure_ascii=False)) == content
