"""Deterministic canon visibility checks for source-aware narrative events."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class CanonViolation:
    code: str
    memory_id: str
    message: str
    chapter_id: str = ""
    source_revision_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _chapter_number(value: Any) -> int | None:
    digits = "".join(char for char in str(value or "") if char.isdigit())
    return int(digits) if digits else None


def facts_as_of_chapter(
    facts: Iterable[Mapping[str, Any]],
    current_chapter: str,
) -> list[Mapping[str, Any]]:
    """Drop events whose source chapter is later than the chapter being checked."""
    current = _chapter_number(current_chapter)
    if current is None:
        return list(facts)
    visible: list[Mapping[str, Any]] = []
    for fact in facts:
        source = _chapter_number(fact.get("source_chapter") or fact.get("chapter_id"))
        if source is None or source <= current:
            visible.append(fact)
    return visible


def check_canon_visibility(
    facts: Iterable[Mapping[str, Any]],
    *,
    current_chapter: str,
    known_character_ids: set[str] | None = None,
) -> list[CanonViolation]:
    """Reject future, superseded, invalidated, and unknowable fact exposure."""

    current = _chapter_number(current_chapter)
    known = {str(item) for item in (known_character_ids or set())}
    violations: list[CanonViolation] = []
    for fact in facts:
        memory_id = str(fact.get("memory_id") or fact.get("event_id") or fact.get("id") or "")
        chapter_id = str(fact.get("source_chapter") or fact.get("chapter_id") or "")
        revision = str(fact.get("source_revision_id") or "")
        source_number = _chapter_number(chapter_id)
        if current is not None and source_number is not None and source_number > current:
            violations.append(
                CanonViolation("future_fact", memory_id, "事实来源章节晚于当前章节", chapter_id, revision)
            )
            continue
        if fact.get("superseded") or fact.get("superseded_by"):
            violations.append(
                CanonViolation("superseded_fact", memory_id, "事实已被新修订替代", chapter_id, revision)
            )
            continue
        invalidated = str(fact.get("invalidated_at_revision") or "")
        if invalidated:
            violations.append(
                CanonViolation("invalidated_fact", memory_id, "事实已被修订标记为失效", chapter_id, revision)
            )
            continue
        if str(fact.get("truth_scope") or "objective") == "character_belief":
            knowers = {str(item) for item in fact.get("knower_ids") or []}
            if known and not knowers.intersection(known):
                violations.append(
                    CanonViolation("knowledge_boundary", memory_id, "当前人物不具备该主观认知", chapter_id, revision)
                )
    return violations


def filter_visible_canon(
    facts: Iterable[Mapping[str, Any]],
    *,
    current_chapter: str,
    known_character_ids: set[str] | None = None,
) -> tuple[list[Mapping[str, Any]], list[CanonViolation]]:
    facts = list(facts)
    violations = check_canon_visibility(
        facts,
        current_chapter=current_chapter,
        known_character_ids=known_character_ids,
    )
    blocked = {item.memory_id for item in violations}
    visible = [
        fact
        for fact in facts
        if str(fact.get("memory_id") or fact.get("event_id") or fact.get("id") or "") not in blocked
    ]
    return visible, violations
