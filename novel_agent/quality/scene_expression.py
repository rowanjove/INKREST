"""Per-scene expression contracts.

The planner owns scene intent, while the writer needs a compact, stable
expression brief.  This module normalises optional scene-card fields and
combines them with the existing local expression memory and character voice
profiles.  It is deliberately prompt-only and report-safe: missing fields
remain explicit instead of being guessed, and no content fact is rewritten.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


SCENE_EXPRESSION_CONTRACT_SCHEMA_VERSION = 1
MAX_CONTRACT_CHARS = 2400


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [value]


def _compact(value: Any, *, limit: int = 180) -> str:
    if isinstance(value, Mapping):
        character = str(value.get("character") or value.get("speaker") or "").strip()
        intent = str(value.get("intent") or value.get("goal") or value.get("wants") or "").strip()
        subtext = str(value.get("subtext") or value.get("hidden_pressure") or "").strip()
        parts = [item for item in (character, intent, f"潜台词：{subtext}" if subtext else "") if item]
        text = "；".join(parts) or str(dict(value))
    else:
        text = str(value or "").strip()
    return text[:limit]


def _compact_list(value: Any, *, limit: int = 6) -> List[str]:
    result: List[str] = []
    for item in _as_list(value):
        text = _compact(item)
        if text and text not in result:
            result.append(text)
        if len(result) >= limit:
            break
    return result


def _first(scene: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = scene.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:180]
        if isinstance(value, (list, tuple, set, Mapping)):
            compact = _compact(value)
            if compact and compact not in {"{}", "[]"}:
                return compact
        if value not in (None, "") and not isinstance(value, (list, tuple, set, Mapping)):
            return str(value).strip()[:180]
    return ""


def _scene_characters(scene: Mapping[str, Any]) -> List[str]:
    values = _as_list(scene.get("characters")) + _as_list(scene.get("pov"))
    result: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def normalise_scene_expression_contract(
    scene: Mapping[str, Any],
    *,
    chapter_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Normalise planner aliases into a versioned, JSON-safe scene contract."""

    source = dict(scene) if isinstance(scene, Mapping) else {}
    rhythm = source.get("rhythm_targets") or source.get("rhythm") or {}
    return {
        "schema_version": SCENE_EXPRESSION_CONTRACT_SCHEMA_VERSION,
        "chapter_id": str(chapter_id or source.get("chapter_id") or ""),
        "scene_id": str(source.get("scene_id") or source.get("id") or ""),
        "pov": _first(source, "pov", "point_of_view", "narrator"),
        "narrative_distance": _first(source, "narrative_distance", "distance", "default_distance"),
        "pressure_curve": _first(source, "pressure_curve", "pressure", "tension_curve", "emotional_curve"),
        "dialogue_intents": _compact_list(
            source.get("dialogue_intents")
            or source.get("dialogue_intent")
            or source.get("character_intents")
        ),
        "subtext": _compact_list(source.get("subtext") or source.get("dialogue_subtext")),
        "allowed_motifs": _compact_list(
            source.get("allowed_motifs") or source.get("motifs") or source.get("imagery")
        ),
        "rhythm_targets": dict(rhythm) if isinstance(rhythm, Mapping) else {},
        "characters": _scene_characters(source),
        "policy": {
            "mode": "diagnostic_only",
            "blocking": False,
            "content_lock": "表达合同不得新增或改写剧情事实、状态和因果关系。",
        },
    }


def build_scene_expression_contract(
    root_dir: Path,
    chapter_id: Optional[str],
    scene: Mapping[str, Any],
    *,
    limit: int = 8,
) -> str:
    """Render one bounded scene expression contract for writer prompts."""

    payload = normalise_scene_expression_contract(scene, chapter_id=chapter_id)
    lines = [
        "[SCENE_EXPRESSION_CONTRACT v1]",
        f"POV：{payload['pov'] or '未显式指定，沿用项目叙述 profile'}",
        f"叙事距离：{payload['narrative_distance'] or '未显式指定，保持当前场景稳定'}",
        f"压力曲线：{payload['pressure_curve'] or '未显式指定，不擅自制造高潮或反转'}",
    ]
    if payload["dialogue_intents"]:
        lines.append("对白意图：" + "；".join(payload["dialogue_intents"]))
    if payload["subtext"]:
        lines.append("对白潜台词：" + "；".join(payload["subtext"]))
    if payload["allowed_motifs"]:
        lines.append("允许母题：" + "；".join(payload["allowed_motifs"]))
    if payload["rhythm_targets"]:
        lines.append(f"局部节奏目标：{_compact(payload['rhythm_targets'], limit=240)}")

    try:
        from novel_agent.quality.expression_memory import build_expression_contract

        expression_contract = build_expression_contract(root_dir, chapter_id, limit=limit)
    except Exception:
        expression_contract = ""
    if expression_contract:
        lines.append(expression_contract)

    try:
        from novel_agent.quality.character_voice import build_character_voice_context

        voice_context = build_character_voice_context(root_dir, payload["characters"])
    except Exception:
        voice_context = ""
    if voice_context:
        lines.append("角色声口参考：\n" + voice_context[:800])

    lines.append("合同策略：只在不改变 CONTENT_LOCK 的前提下调整句法、节拍、意象和对白表面表达。")
    lines.append("[/SCENE_EXPRESSION_CONTRACT]")
    rendered = "\n".join(lines)
    if len(rendered) <= MAX_CONTRACT_CHARS:
        return rendered
    closing = "\n[/SCENE_EXPRESSION_CONTRACT]"
    return rendered[: max(0, MAX_CONTRACT_CHARS - len(closing))].rstrip() + closing


__all__ = [
    "MAX_CONTRACT_CHARS",
    "SCENE_EXPRESSION_CONTRACT_SCHEMA_VERSION",
    "build_scene_expression_contract",
    "normalise_scene_expression_contract",
]
