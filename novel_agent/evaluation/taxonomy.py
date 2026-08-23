"""Chinese long-form consistency taxonomy.

Cases intentionally store compact synthetic text and *expected evidence* so
evaluation can explain why a detector should fire.  They are not a corpus of
published novels and do not become a hidden generation gate.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


CONSISTENCY_TAXONOMY: dict[str, tuple[str, ...]] = {
    "人物": ("personality", "knowledge", "skills", "relationships", "death_absence"),
    "事实": ("name", "appearance", "count", "object_ownership", "location"),
    "时间情节": ("order", "duration", "causality", "open_thread"),
    "世界规则": ("level", "social_norm", "geography", "ability_constraint"),
    "声线表达": ("pov", "tone", "character_voice", "cross_chapter_repetition"),
}
VARIANTS = ("normal", "single_point_mutation", "cross_chapter_mutation", "false_positive")


@dataclass(frozen=True)
class ConsistencyCase:
    case_id: str
    category: str
    subtype: str
    variant: str
    chapters: tuple[dict[str, Any], ...]
    query: str = ""
    expected_label: str = "pass"
    expected_evidence: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["chapters"] = [dict(item) for item in self.chapters]
        payload["expected_evidence"] = [dict(item) for item in self.expected_evidence]
        return payload


def normalise_case(value: Mapping[str, Any], index: int = 0) -> ConsistencyCase:
    category = str(value.get("category") or "事实")
    subtype = str(value.get("subtype") or "unknown")
    variant = str(value.get("variant") or "normal")
    if category not in CONSISTENCY_TAXONOMY:
        raise ValueError(f"unknown consistency category: {category}")
    if subtype not in CONSISTENCY_TAXONOMY[category]:
        raise ValueError(f"unknown subtype {subtype!r} for {category}")
    if variant not in VARIANTS:
        raise ValueError(f"unknown consistency variant: {variant}")
    chapters = value.get("chapters")
    if not isinstance(chapters, (list, tuple)) or not chapters:
        raise ValueError("consistency case requires chapters")
    normalised_chapters = tuple(
        {"chapter_id": str(item.get("chapter_id") or ""), "text": str(item.get("text") or ""), **{
            str(key): item[key] for key in item if str(key) not in {"chapter_id", "text"}
        }}
        for item in chapters if isinstance(item, Mapping)
    )
    if not normalised_chapters or any(not item["text"].strip() for item in normalised_chapters):
        raise ValueError("consistency case chapters must contain text")
    evidence = value.get("expected_evidence")
    expected_evidence = tuple(dict(item) for item in evidence if isinstance(item, Mapping)) if isinstance(evidence, (list, tuple)) else ()
    return ConsistencyCase(
        case_id=str(value.get("case_id") or f"case-{index + 1:04d}"),
        category=category,
        subtype=subtype,
        variant=variant,
        chapters=normalised_chapters,
        query=str(value.get("query") or ""),
        expected_label=str(value.get("expected_label") or ("fail" if variant != "normal" and variant != "false_positive" else "pass")),
        expected_evidence=expected_evidence,
        notes=str(value.get("notes") or ""),
    )


def iter_taxonomy() -> list[tuple[str, str]]:
    return [(category, subtype) for category, subtypes in CONSISTENCY_TAXONOMY.items() for subtype in subtypes]


__all__ = ["CONSISTENCY_TAXONOMY", "ConsistencyCase", "VARIANTS", "iter_taxonomy", "normalise_case"]
