"""Tiptap document conversion and manuscript projection helpers."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple


def _text_content(node: Dict[str, Any]) -> str:
    node_type = node.get("type")
    if node_type == "text":
        return str(node.get("text") or "")
    if node_type == "hardBreak":
        return "\n"
    return "".join(
        _text_content(child)
        for child in node.get("content", [])
        if isinstance(child, dict)
    )


def _markdown_blocks(node: Dict[str, Any]) -> Iterable[str]:
    node_type = str(node.get("type") or "")
    children = [
        child for child in node.get("content", []) if isinstance(child, dict)
    ]
    if node_type == "heading":
        level = max(1, min(int((node.get("attrs") or {}).get("level") or 1), 6))
        yield "{} {}".format("#" * level, _text_content(node).replace("\n", "  \n"))
        return
    if node_type == "paragraph":
        yield _text_content(node).replace("\n", "  \n")
        return
    if node_type == "blockquote":
        for block in children:
            for line in _markdown_blocks(block):
                yield "\n".join("> " + part for part in line.splitlines())
        return
    if node_type in ("bulletList", "orderedList"):
        ordered = node_type == "orderedList"
        for index, item in enumerate(children, start=1):
            prefix = "{}. ".format(index) if ordered else "- "
            text = _text_content(item).replace("\n", " ")
            yield prefix + text
        return
    if node_type == "codeBlock":
        yield "```\n{}\n```".format(_text_content(node))
        return
    for child in children:
        yield from _markdown_blocks(child)


def validate_tiptap_document(content_json: Dict[str, Any]) -> None:
    if not isinstance(content_json, dict) or content_json.get("type") != "doc":
        raise ValueError("content_json must be a Tiptap doc")
    content = content_json.get("content", [])
    if not isinstance(content, list):
        raise ValueError("content_json.content must be a list")


def derive_document_text(content_json: Dict[str, Any]) -> Tuple[str, str]:
    validate_tiptap_document(content_json)
    blocks = [
        block for block in _markdown_blocks(content_json) if block.strip()
    ]
    markdown_text = "\n\n".join(blocks)
    plain_text = markdown_text
    plain_lines: List[str] = []
    for child in content_json.get("content", []):
        if isinstance(child, dict):
            value = _text_content(child).strip()
            if value:
                plain_lines.append(value)
    plain_text = "\n".join(plain_lines)
    return plain_text, markdown_text


def plain_text_to_tiptap(text: str) -> Dict[str, Any]:
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = normalized.split("\n\n") if normalized else [""]
    content = []
    for paragraph in paragraphs:
        node: Dict[str, Any] = {"type": "paragraph"}
        if paragraph:
            node["content"] = [{"type": "text", "text": paragraph}]
        content.append(node)
    return {"type": "doc", "content": content}
