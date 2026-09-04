"""Story knowledge base & editorial context extractor for the ShanShan pet assistant."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_story_overview(root_dir: Optional[Path]) -> Dict[str, Any]:
    """Retrieve high-level novel information (title, premise, target chapters, arcs)."""
    if not root_dir:
        return {}
    
    outline = _read_json(root_dir / "workspace" / "outline.json")
    meta = _read_json(root_dir / "config" / "project_meta.json")

    title = outline.get("chosen_title") or meta.get("title") or meta.get("name") or "未命名作品"
    premise = outline.get("premise") or meta.get("premise") or meta.get("description") or ""
    genre = outline.get("genre") or meta.get("genre") or ""

    macro_outline = outline.get("macro_outline") or []
    arcs_summary: List[Dict[str, Any]] = []
    for arc in macro_outline[:5]:
        if isinstance(arc, dict):
            arcs_summary.append({
                "arc_id": arc.get("arc_id", ""),
                "title": arc.get("title") or arc.get("arc_title", ""),
                "goal": arc.get("goal") or arc.get("main_conflict", ""),
                "chapters": arc.get("chapters", ""),
            })

    return {
        "title": title,
        "genre": genre,
        "premise": premise,
        "target_chapters": outline.get("target_chapters") or meta.get("target_chapters") or 0,
        "macro_arcs": arcs_summary,
    }


def get_character_snapshots(root_dir: Optional[Path], limit: int = 5) -> List[Dict[str, Any]]:
    """Extract character cards snapshot (protagonist and key characters)."""
    if not root_dir:
        return []

    cards_path = root_dir / "assets" / "character_cards.yaml"
    if not cards_path.is_file():
        cards_path = root_dir / "templates" / "assets" / "character_cards.yaml"
    
    doc = _read_yaml(cards_path)
    char_list = doc.get("characters") if isinstance(doc.get("characters"), list) else []
    
    results: List[Dict[str, Any]] = []
    for item in char_list[:limit]:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("id") or "未命名角色"
        profile = item.get("fixed_profile") or {}
        role = profile.get("role") or item.get("role") or "主要角色"
        motivation = profile.get("core_motivation") or item.get("motivation") or ""
        constraints = item.get("personality_constraints") or []
        must_not = item.get("must_not") or []

        results.append({
            "name": name,
            "role": role,
            "motivation": motivation,
            "personality": constraints[:3] if isinstance(constraints, list) else [],
            "taboos": must_not[:2] if isinstance(must_not, list) else [],
        })
    return results


def get_gate_diagnostic_detail(root_dir: Optional[Path], chapter_id: str) -> Optional[Dict[str, Any]]:
    """Extract in-depth gate failure reasons and rewrite hints for a chapter."""
    if not root_dir or not chapter_id:
        return None

    safe_id = str(chapter_id).replace("/", "").replace("\\", "").strip()
    reports_dir = root_dir / "workspace" / "chapters" / f"chapter_{safe_id}" / "reports"
    gate_path = reports_dir / "unified_gate.json"
    if not gate_path.is_file():
        return None

    doc = _read_json(gate_path)
    if not doc:
        return None

    overall_pass = doc.get("overall_pass", False)
    quality = doc.get("quality") if isinstance(doc.get("quality"), dict) else {}
    audit = doc.get("audit") if isinstance(doc.get("audit"), dict) else {}

    blocked_by = quality.get("blocked_by") or []
    rewrite_hints = quality.get("rewrite_hints") or ""
    score = quality.get("overall_score")
    risk_level = audit.get("risk_level") or "正常"
    
    audit_issues: List[str] = []
    raw_issues = audit.get("issues") or []
    if isinstance(raw_issues, list):
        for iss in raw_issues[:4]:
            if isinstance(iss, dict) and iss.get("message"):
                audit_issues.append(f"[{iss.get('severity', '提示')}] {iss.get('message')}")

    return {
        "chapter_id": safe_id,
        "overall_pass": overall_pass,
        "score": score,
        "blocked_by": blocked_by,
        "rewrite_hints": rewrite_hints,
        "risk_level": risk_level,
        "audit_issues": audit_issues,
    }


def format_story_context_for_shanshan(root_dir: Optional[Path]) -> str:
    """Format compact story & editorial context for injection into ShanShan's prompt."""
    if not root_dir:
        return "【作品设定档案】未选定项目"

    overview = get_story_overview(root_dir)
    title = overview.get("title") or "未命名作品"
    genre = overview.get("genre") or "通用"
    premise = (overview.get("premise") or "无简介")[:120]
    
    characters = get_character_snapshots(root_dir, limit=4)
    char_lines = []
    for c in characters:
        parts = [f"- {c['name']}（{c['role']}）"]
        if c.get("motivation") and c["motivation"] != "待填写":
            parts.append(f"目标: {c['motivation']}")
        if c.get("personality"):
            parts.append(f"特质: {', '.join(str(p) for p in c['personality'])}")
        char_lines.append(" | ".join(parts))
    chars_str = "\n".join(char_lines) if char_lines else "暂无角色卡（默认使用主角设定）"

    arcs = overview.get("macro_arcs") or []
    arc_lines = []
    for arc in arcs[:3]:
        arc_lines.append(f"- {arc.get('arc_id')}: {arc.get('title') or arc.get('goal') or '卷推进'}")
    arcs_str = "\n".join(arc_lines) if arc_lines else "卷纲待完善"

    return f"""【作品设定与主要角色档案】
- 作品名: 《{title}》 | 题材: {genre}
- 核心立意: {premise}
- 卷纲要览:
{arcs_str}
- 登场角色简卡:
{chars_str}
"""
