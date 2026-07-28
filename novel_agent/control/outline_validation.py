"""Validate and normalize outline.json before save / queue sync."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from novel_agent.control.outline_structure import _parse_chapter_range, normalize_macro_outline


def validate_macro_outline(
    macro: List[Dict[str, Any]],
    *,
    target_chapters: int,
) -> Tuple[List[str], List[str]]:
    """Return (errors, warnings)."""
    errors: List[str] = []
    warnings: List[str] = []
    if not macro:
        errors.append("macro_outline 为空，至少需要一个卷/阶段。")
        return errors, warnings

    spans: List[Tuple[int, int, str]] = []
    for arc in macro:
        if not isinstance(arc, dict):
            errors.append("macro_outline 含非对象条目。")
            continue
        if not str(arc.get("arc_id") or "").strip():
            warnings.append("某卷缺少 arc_id，保存时将自动补全。")
        if not str(arc.get("goal") or "").strip():
            warnings.append(f"卷 {arc.get('arc_id', '?')} 缺少 goal。")
        start, end = _parse_chapter_range(arc.get("chapters", "1-1"))
        if end < start:
            errors.append(f"卷 {arc.get('arc_id', '?')} 章号范围无效：{arc.get('chapters')}")
        spans.append((start, end, str(arc.get("arc_id") or "")))

    spans.sort(key=lambda x: x[0])
    for i in range(1, len(spans)):
        prev_end = spans[i - 1][1]
        curr_start = spans[i][0]
        if curr_start <= prev_end:
            warnings.append(
                f"卷 {spans[i][2]} 起始章 {curr_start} 与前一卷结束 {prev_end} 重叠或倒序。"
            )

    if spans:
        last_end = spans[-1][1]
        if target_chapters > 0 and last_end > target_chapters + 50:
            warnings.append(
                f"末卷结束章 {last_end} 明显大于目标章数 {target_chapters}，请核对体量。"
            )
    return errors, warnings


def validate_outline_document(
    outline: Dict[str, Any],
    *,
    require_chosen_title: bool = False,
    strict_macro: bool = True,
) -> Dict[str, Any]:
    """Validate outline; return {valid, errors, warnings, outline}."""
    errors: List[str] = []
    warnings: List[str] = []

    if not str(outline.get("core_theme") or "").strip():
        warnings.append("缺少 core_theme。")
    if require_chosen_title and not str(outline.get("chosen_title") or "").strip():
        errors.append("请先确定最终书名 chosen_title。")

    proto = outline.get("protagonist") or {}
    if not isinstance(proto, dict) or not str(proto.get("name") or "").strip():
        errors.append("protagonist.name 必填。")

    target = int(outline.get("target_chapters") or 0)
    sp = outline.get("scale_profile") or {}
    scale = str(sp.get("scale") or "")
    if strict_macro:
        macro = outline.get("macro_outline") or []
        me, mw = validate_macro_outline(macro, target_chapters=target)
        errors.extend(me)
        warnings.extend(mw)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def finalize_outline_for_save(outline: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize macro arcs and attach layer implementation notes."""
    from novel_agent.control.genre_genes import ensure_genre_genes

    doc = ensure_genre_genes(dict(outline))
    target = int(doc.get("target_chapters") or 20)
    sp = doc.get("scale_profile") or {}
    scale = str(sp.get("scale") or "")
    doc["macro_outline"] = normalize_macro_outline(
        doc.get("macro_outline") or [],
        target_chapters=target,
        scale=scale,
    )
    doc["outline_layer_impl"] = {
        "L0": "outline.json：genre_genes、核心设定、禁止项",
        "L1_L2": "未单独落盘；卷级 goal/turning_point 写在 macro_outline",
        "L3": "macro_outline + workspace/arc_*.json 章 brief",
        "L4": "chapter_*/expanded_plan.json",
        "configured_layers": list(sp.get("outline_layers") or []),
    }
    return doc