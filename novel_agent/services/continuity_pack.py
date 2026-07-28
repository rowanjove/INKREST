"""Build cross-chapter continuity blocks for planner and scene enrichment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set

import yaml

from novel_agent.services.writing_context import (
    format_context_for_managing_editor,
    gather_recent_writing_context,
)
from novel_agent.state.sqlite_store import SQLiteStateStore


def _chapter_num(chapter_id: str) -> int:
    raw = str(chapter_id or "").strip()
    return int(raw) if raw.isdigit() else 0


def load_cast_roster(root_dir: Path) -> List[str]:
    """Names from character_cards.yaml and SQLite character_state."""
    names: List[str] = []
    cards_path = root_dir / "assets" / "character_cards.yaml"
    if cards_path.is_file():
        try:
            data = yaml.safe_load(cards_path.read_text(encoding="utf-8")) or {}
            for item in data.get("characters") or []:
                if not isinstance(item, dict):
                    continue
                for key in ("name", "id"):
                    val = str(item.get(key) or "").strip()
                    if val and val not in ("待填写", "主角"):
                        names.append(val)
                    elif key == "name" and val == "主角":
                        names.append(val)
                if item.get("id") == "protagonist":
                    pname = str(item.get("name") or "主角").strip()
                    if pname and pname not in names:
                        names.insert(0, pname)
        except Exception:
            pass

    try:
        store = SQLiteStateStore(root_dir)
        for cid, info in (store.list_characters() or {}).items():
            for val in (cid, (info or {}).get("name")):
                s = str(val or "").strip()
                if s:
                    names.append(s)
    except Exception:
        pass

    seen: Set[str] = set()
    ordered: List[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            ordered.append(n)
    return ordered


def prev_chapter_cast(root_dir: Path, chapter_id: str) -> List[str]:
    """Characters from previous chapter plan or tail text."""
    num = _chapter_num(chapter_id)
    if num <= 1:
        return []
    prev_id = f"{num - 1:03d}"
    plan_path = root_dir / "workspace" / "chapters" / f"chapter_{prev_id}" / "plan.json"
    cast: List[str] = []
    if plan_path.is_file():
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            for scene in plan.get("scenes") or []:
                if not isinstance(scene, dict):
                    continue
                for key in ("characters", "pov"):
                    val = scene.get(key)
                    if isinstance(val, list):
                        cast.extend(str(c).strip() for c in val if str(c).strip())
                    elif isinstance(val, str) and val.strip():
                        cast.append(val.strip())
            for name in (plan.get("state_expectations") or {}).get("characters") or []:
                if str(name).strip():
                    cast.append(str(name).strip())
        except Exception:
            pass

    if not cast:
        final_path = root_dir / "workspace" / "chapters" / f"chapter_{prev_id}" / "chapter_final.txt"
        if final_path.is_file():
            try:
                text = final_path.read_text(encoding="utf-8")
                roster = load_cast_roster(root_dir)
                tail = text[-400:] if len(text) > 400 else text
                for name in roster:
                    if name in tail:
                        cast.append(name)
            except Exception:
                pass

    seen: Set[str] = set()
    out: List[str] = []
    for c in cast:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def build_planner_continuity_block(root_dir: Path, chapter_id: str, chapter_goal: str) -> str:
    """Markdown section injected into PlannerAgent prompt."""
    root_dir = Path(root_dir)
    parts: List[str] = []
    roster = load_cast_roster(root_dir)
    if roster:
        parts.append(
            "## 全书角色名册（禁止擅自改名或替换主角）\n"
            + "、".join(roster)
            + "\n规划场景时 `pov` 与 `characters` 只能使用上述姓名；"
            "如需新配角，须在 `must_include` 中写明「新角色：姓名（身份）」且不得替换已有主角。"
        )
    else:
        parts.append(
            "## 全书角色名册\n"
            "当前 `assets/character_cards.yaml` 为空或仅有占位。"
            "请先在设定页填写主角姓名与核心配角，否则各章容易生成互无关联网名。"
        )

    num = _chapter_num(chapter_id)
    if num > 1:
        prev_cast = prev_chapter_cast(root_dir, chapter_id)
        if prev_cast:
            parts.append(
                "## 上一章登场人物（本章必须延续）\n" + "、".join(prev_cast)
            )
        ctx = gather_recent_writing_context(root_dir, before_chapter=num, max_chapters=2)
        formatted = format_context_for_managing_editor(ctx)
        if formatted.strip():
            parts.append(formatted)
        parts.append(
            f"## 本章衔接要求\n"
            f"- 本章 ID：{chapter_id}，叙事目标：{chapter_goal}\n"
            "- 默认与上一章同一世界观、同一时间线延续；不得无故更换主角姓名。\n"
            "- 每个场景的 `characters` 须列出本场景登场人物；`pov` 须为已登场角色之一。"
        )
    return "\n\n".join(parts).strip()


def scene_cast_from_scene(scene: Dict[str, Any]) -> List[str]:
    """Normalize characters + pov into a list of names."""
    names: List[str] = []
    raw = scene.get("characters")
    if isinstance(raw, list):
        names.extend(str(c).strip() for c in raw if str(c).strip())
    elif isinstance(raw, str) and raw.strip():
        names.append(raw.strip())
    pov = scene.get("pov")
    if isinstance(pov, str) and pov.strip():
        names.append(pov.strip())
    seen: Set[str] = set()
    out: List[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def enrich_plan_characters(plan: Dict[str, Any], root_dir: Path, chapter_id: str) -> Dict[str, Any]:
    """Ensure every scene has characters[] from roster / prev chapter / pov."""
    root_dir = Path(root_dir)
    roster = load_cast_roster(root_dir)
    prev_cast = prev_chapter_cast(root_dir, chapter_id)
    core = list(roster[:3]) or list(prev_cast[:3])
    if not core and roster:
        core = [roster[0]]
    if not core and prev_cast:
        core = [prev_cast[0]]

    scenes = plan.get("scenes") or []
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        existing = scene_cast_from_scene(scene)
        merged: List[str] = []
        seen: Set[str] = set()
        for name in existing + core + prev_cast[:2]:
            n = str(name).strip()
            if not n or n in seen:
                continue
            seen.add(n)
            merged.append(n)
        if not merged and core:
            merged = list(core)
        scene["characters"] = merged
        if not scene.get("pov") and merged:
            scene["pov"] = merged[0]
        must = scene.get("must_not_include")
        if not isinstance(must, list):
            must = [str(must)] if must else []
        rule = "禁止更换主角或主要配角姓名；禁止与已写章节无关的独立短篇"
        if rule not in must:
            must.append(rule)
        scene["must_not_include"] = must

    expectations = plan.get("state_expectations")
    if not isinstance(expectations, dict):
        expectations = {}
    exp_chars = expectations.get("characters")
    if not isinstance(exp_chars, list):
        exp_chars = []
    for name in core + prev_cast:
        if name and name not in exp_chars:
            exp_chars.append(name)
    expectations["characters"] = exp_chars
    plan["state_expectations"] = expectations
    plan["scenes"] = scenes
    return plan