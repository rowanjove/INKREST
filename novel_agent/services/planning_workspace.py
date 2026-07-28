"""Aggregate legacy outline, asset, and SQLite state into planning entities."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

import yaml

from novel_agent.domain.planning import (
    PlanningEntity,
    PlanningRelation,
    PlanningWorkspace,
)
from novel_agent.state.sqlite_store import SQLiteStateStore

RULE_CATEGORY_LABELS = {
    "commonWords": "常用词提醒",
    "commonSentences": "常用句提醒",
    "forbiddenWords": "禁用词",
    "forbiddenSentences": "禁用句",
    "writingTechniques": "写作技巧",
    "referenceAuthors": "参考作者",
}


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _safe_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, yaml.YAMLError):
        return {}


def _slug(value: str) -> str:
    normalized = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value.strip().lower())
    return normalized.strip("-") or "unnamed"


def _as_dict(item: Any, *, name_key: str = "name") -> dict[str, Any]:
    if isinstance(item, dict):
        return dict(item)
    return {name_key: str(item)}


def _items(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            yield _as_dict(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            row = _as_dict(item)
            row.setdefault("name", str(key))
            yield row


def _rule_category_items(value: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for key, rules in value.items():
        label = RULE_CATEGORY_LABELS.get(str(key), str(key))
        summary = "尚未配置"
        if isinstance(rules, list) and rules:
            preview = [
                str(item.get("content") or item.get("name") or "").strip()
                for item in rules
                if isinstance(item, dict)
            ]
            preview = [item for item in preview if item][:2]
            summary = f"{len(rules)} 条规则"
            if preview:
                summary += f" · {'、'.join(preview)}"
        elif isinstance(rules, str) and rules.strip():
            lines = [
                line.strip().removeprefix("-").strip()
                for line in rules.splitlines()
                if line.strip()
            ]
            summary = f"{len(lines)} 条写作原则" if lines else "尚未配置"
        elif isinstance(rules, dict) and rules:
            summary = f"{len(rules)} 项配置"
        yield {
            "id": f"asset-rule:{_slug(str(key))}",
            "name": label,
            "summary": summary,
            "key": str(key),
            "value": rules,
        }


def _entity(
    kind: str,
    item: dict[str, Any],
    *,
    source: str,
    configured: dict[str, Any] | None = None,
    current_state: dict[str, Any] | None = None,
) -> PlanningEntity:
    name = str(
        item.get("name")
        or item.get("title")
        or item.get("arc_name")
        or item.get("id")
        or "未命名"
    )
    entity_id = str(item.get("id") or item.get("arc_id") or f"{kind}:{_slug(name)}")
    summary = str(
        item.get("summary")
        or item.get("description")
        or item.get("goal")
        or item.get("content")
        or ""
    )
    chapters = item.get("related_chapters") or item.get("chapters") or []
    if isinstance(chapters, str):
        chapters = [chapters]
    return PlanningEntity(
        id=entity_id,
        kind=kind,
        name=name,
        summary=summary,
        source=source,
        configured=configured if configured is not None else item,
        current_state=current_state or {},
        related_chapters=[str(chapter) for chapter in chapters if chapter],
    )


def build_planning_workspace(root_dir: Path) -> PlanningWorkspace:
    root = Path(root_dir)
    outline = _safe_json(root / "workspace" / "outline.json")
    cards = _safe_yaml(root / "assets" / "character_cards.yaml")
    rules_asset = _safe_yaml(root / "assets" / "rules.yaml")
    store = SQLiteStateStore(root)
    current_characters = store.list_characters()
    entities: dict[str, PlanningEntity] = {}
    warnings: list[str] = []

    configured_characters: list[dict[str, Any]] = []
    protagonist = outline.get("protagonist")
    if isinstance(protagonist, dict) and protagonist:
        configured_characters.append(protagonist)
    configured_characters.extend(_items(outline.get("main_cast", [])))
    configured_characters.extend(_items(cards.get("characters", [])))

    for item in configured_characters:
        name = str(item.get("name") or item.get("id") or "未命名")
        state = current_characters.get(name, {})
        key = f"character:{_slug(name)}"
        previous = entities.get(key)
        configured = {**(previous.configured if previous else {}), **item}
        entity = _entity(
            "character",
            configured,
            source="outline+assets",
            configured=configured,
            current_state=state if isinstance(state, dict) else {},
        )
        entities[key] = entity

    for name, state in current_characters.items():
        key = f"character:{_slug(str(name))}"
        if key in entities:
            continue
        item = {"name": name}
        entities[key] = _entity(
            "character",
            item,
            source="runtime",
            configured={},
            current_state=state if isinstance(state, dict) else {},
        )

    for arc in _items(outline.get("macro_outline", [])):
        entity = _entity("outline", arc, source="outline")
        entities[f"outline:{entity.id}"] = entity

    category_sources = (
        ("location", outline.get("locations", [])),
        ("organization", outline.get("organizations", [])),
        ("rule", outline.get("world_rules", [])),
    )
    for kind, values in category_sources:
        for item in _items(values):
            entity = _entity(kind, item, source="outline")
            entities[f"{kind}:{entity.id}"] = entity

    rule_values = rules_asset.get("rules", rules_asset)
    rule_items = (
        _rule_category_items(rule_values)
        if isinstance(rule_values, dict)
        else _items(rule_values)
    )
    for item in rule_items:
        entity = _entity("rule", item, source="assets")
        entities.setdefault(f"rule:{entity.id}", entity)

    for item in store.list_objects():
        entity = _entity(
            "object",
            item,
            source="runtime",
            configured={},
            current_state=item,
        )
        entities[f"object:{entity.id}"] = entity

    for item in store.list_foreshadows():
        entity = _entity(
            "foreshadow",
            item,
            source="runtime",
            configured={},
            current_state=item,
        )
        entities[f"foreshadow:{entity.id}"] = entity

    relations = [
        PlanningRelation(
            id=str(row.get("id") or f"relation:{index}"),
            source=str(row.get("source_char") or row.get("source") or ""),
            target=str(row.get("target_char") or row.get("target") or ""),
            label=str(row.get("relation_type") or row.get("type") or ""),
            intensity=float(row.get("intensity") or 0),
            chapter_id=str(row.get("last_updated") or row.get("chapter_id") or ""),
            description=str(row.get("description") or ""),
        )
        for index, row in enumerate(store.list_character_relations())
        if row.get("source_char") or row.get("source")
    ]
    timeline = store.list_events(limit=500)

    if not outline:
        warnings.append("尚未建立完整大纲")
    if not any(entity.kind == "character" for entity in entities.values()):
        warnings.append("尚未建立人物")

    counts: dict[str, int] = {}
    for entity in entities.values():
        counts[entity.kind] = counts.get(entity.kind, 0) + 1
    return PlanningWorkspace(
        entities=list(entities.values()),
        relations=relations,
        timeline=timeline,
        counts=counts,
        warnings=warnings,
    )
