"""Conservative, source-aware continuity diagnostics for long-form state.

This layer does not replace the existing auditor hard rules.  It adds a
report-only explanation path that connects a suspicious span to the persisted
character/object/secret state and the NarrativeEvent projection.  Until a
project has enough calibrated data, these findings remain review signals and
never silently rewrite a chapter.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from novel_agent.state.sqlite_store import SQLiteStateStore


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _chapter_number(value: Any) -> Optional[int]:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else None


def _paragraph_spans(text: str) -> Iterable[tuple[str, int, int]]:
    for match in re.finditer(r"[^\n]+(?:\n|$)", text or ""):
        value = match.group(0).strip()
        if value:
            start = match.start() + len(match.group(0)) - len(match.group(0).lstrip())
            yield value, start, start + len(value)


def _state_update_character(state_update: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    updates = state_update.get("characters") or {}
    item = updates.get(name) if isinstance(updates, Mapping) else None
    return item if isinstance(item, Mapping) else {}


def _state_update_object(state_update: Mapping[str, Any], object_id: str, object_name: str) -> Mapping[str, Any]:
    updates = state_update.get("objects") or []
    for item in updates if isinstance(updates, list) else []:
        if not isinstance(item, Mapping):
            continue
        if str(item.get("id") or "") == object_id or str(item.get("name") or "") == object_name:
            return item
    return {}


_INJURY_RE = re.compile(r"(受伤|伤口|流血|骨折|中毒|昏迷|虚弱|发热|疼痛|透支|内伤)")
_HEALTHY_RE = re.compile(r"(毫发无伤|没有受伤|伤势痊愈|伤口消失|完好无损|恢复如初)")
# These are deliberately explicit narrative turn markers.  A generic
# surprise word is not enough: the detector also requires an event projection
# with no causal/foreshadowing anchor and no overlap with recent entities.
_ABRUPT_TURN_RE = re.compile(r"(突然|原来|竟然|意外(?:地|的是)?|没想到|就在这时|下一刻|猛地|谁也没想到|不料|猝然)")


def _event_entities(event: Mapping[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in ("actors", "characters", "objects", "items", "threads", "clues"):
        for item in _as_list(event.get(key)):
            value = str(item).strip()
            if value:
                values.add(value)
    location = str(event.get("location") or "").strip()
    if location:
        values.add(location)
    return values


def _event_has_anchor(event: Mapping[str, Any]) -> bool:
    """Return whether the extractor supplied an explicit setup/causal anchor."""

    for key in (
        "causes",
        "predecessors",
        "cause",
        "predecessor",
        "foreshadow",
        "foreshadow_ids",
        "setup",
        "setup_ids",
        "anchor",
        "anchored_to",
        "source_evidence",
        "evidence",
    ):
        if _as_list(event.get(key)):
            return True
    source_span = event.get("source_span")
    return isinstance(source_span, Mapping) and bool(source_span)


def _parse_story_time(value: Any) -> Optional[int]:
    """Parse only explicit ordinal day markers; do not guess calendar dates."""

    match = re.search(r"(?:第\s*)?(\d+)\s*(?:天|日)|day\s*(\d+)", str(value or ""), re.IGNORECASE)
    if not match:
        return None
    return int(next(item for item in match.groups() if item is not None))


def _finding(
    issue_type: str,
    text: str,
    *,
    start: int,
    end: int,
    severity: str,
    message: str,
    evidence: Sequence[Mapping[str, Any]],
    fix: str,
) -> Dict[str, Any]:
    return {
        "issue_id": f"event_consistency:{issue_type}:{start}:{end}",
        "type": issue_type,
        "category": "event_consistency",
        "text": text,
        "start": int(start),
        "end": int(end),
        "severity": severity,
        "audit_class": "CRITICAL" if severity == "high" else "WARNING",
        "message": message,
        "why": message,
        "fix": fix,
        "action": "review",
        "blocking": False,
        "evidence": [dict(item) for item in evidence],
    }


def _load_plan(root_dir: Path, chapter_id: Optional[str], plan: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if isinstance(plan, Mapping):
        return dict(plan)
    if not chapter_id:
        return {}
    path = Path(root_dir) / "workspace" / "chapters" / f"chapter_{chapter_id}" / "plan.json"
    try:
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def check_event_consistency(
    final_text: str,
    root_dir: Path,
    *,
    chapter_id: Optional[str] = None,
    state_update: Optional[Mapping[str, Any]] = None,
    plan: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Check conservative state conflicts with source-labelled evidence."""

    text = str(final_text or "")
    update = state_update if isinstance(state_update, Mapping) else {}
    store = SQLiteStateStore(Path(root_dir))
    state = store.get_continuity_state()
    findings: List[Dict[str, Any]] = []
    paragraphs = list(_paragraph_spans(text))
    plan_data = _load_plan(Path(root_dir), chapter_id, plan)

    known_locations = {
        str(item.get("location") or "").strip()
        for item in (state.get("characters") or {}).values()
        if isinstance(item, Mapping) and str(item.get("location") or "").strip()
    }
    for scene in plan_data.get("scenes") or []:
        if isinstance(scene, Mapping):
            location = str(scene.get("location") or scene.get("scene_location") or "").strip()
            if location:
                known_locations.add(location)

    # Location conflict: a character is co-mentioned with a known alternate
    # location, but no corresponding state update is present.
    for name, character in (state.get("characters") or {}).items():
        if not isinstance(character, Mapping) or not str(character.get("location") or "").strip():
            continue
        old_location = str(character.get("location"))
        updated_location = str(_state_update_character(update, str(name)).get("location") or "")
        if updated_location:
            continue
        for paragraph, start, end in paragraphs:
            if str(name) not in paragraph:
                continue
            for location in known_locations:
                if location == old_location or location not in paragraph:
                    continue
                evidence = [
                    {
                        "kind": "character_state",
                        "entity_id": str(name),
                        "field": "location",
                        "value": old_location,
                    }
                ]
                evidence.extend(
                    {
                        "kind": "narrative_event",
                        "event_id": item.get("event_id"),
                        "chapter_id": item.get("chapter_id"),
                        "source_revision_id": item.get("source_revision_id"),
                    }
                    for item in store.list_narrative_events(actor=str(name), limit=3)
                )
                findings.append(
                    _finding(
                        "character_location_conflict",
                        paragraph,
                        start=start,
                        end=end,
                        severity="high",
                        message=f"{name} 的历史地点为“{old_location}”，但本段同时出现“{location}”，未发现位置变更证据。",
                        evidence=evidence,
                        fix=f"补充 {name} 前往“{location}”的状态更新，或在正文中交代这只是回忆/转述。",
                    )
                )
                break

    # Object ownership conflict: another named character appears next to an
    # object whose persisted holder has not changed in state_update.
    characters = [str(name) for name in (state.get("characters") or {}).keys()]
    for obj in state.get("objects") or []:
        if not isinstance(obj, Mapping):
            continue
        object_id = str(obj.get("id") or "")
        object_name = str(obj.get("name") or object_id)
        holder = str(obj.get("holder") or "").strip()
        if not object_id or not object_name or not holder:
            continue
        update_obj = _state_update_object(update, object_id, object_name)
        updated_holder = str(update_obj.get("holder") or update_obj.get("owner") or "")
        if updated_holder:
            continue
        for paragraph, start, end in paragraphs:
            if object_name not in paragraph:
                continue
            other = next((name for name in characters if name != holder and name in paragraph), None)
            if not other:
                continue
            evidence = [
                {
                    "kind": "object_state",
                    "entity_id": object_id,
                    "field": "holder",
                    "value": holder,
                }
            ]
            evidence.extend(
                {
                    "kind": "narrative_event",
                    "event_id": item.get("event_id"),
                    "chapter_id": item.get("chapter_id"),
                    "source_revision_id": item.get("source_revision_id"),
                }
                for item in store.list_narrative_events(object_name=object_name, limit=3)
            )
            findings.append(
                _finding(
                    "object_holder_conflict",
                    paragraph,
                    start=start,
                    end=end,
                    severity="high",
                    message=f"“{object_name}”登记持有者为“{holder}”，但本段出现“{other}”使用/持有迹象。",
                    evidence=evidence,
                    fix=f"补充“{object_name}”转移给 {other} 的状态证据，或明确 {other} 只是看见它。",
                )
            )
            break

    # Hidden-secret leak: only flag exact, user-authored secret titles or
    # descriptions, never infer secrets from generic vocabulary.
    updated_secret_ids = {
        str(item.get("id"))
        for item in _as_list(update.get("secrets"))
        if isinstance(item, Mapping) and str(item.get("id") or "")
    }
    for secret in state.get("secrets") or []:
        if not isinstance(secret, Mapping) or str(secret.get("status") or "").lower() not in {"hidden", "secret"}:
            continue
        secret_id = str(secret.get("id") or "")
        if secret_id in updated_secret_ids:
            continue
        candidates = [str(secret.get("title") or "").strip(), str(secret.get("description") or "").strip()]
        marker = next((item for item in candidates if len(item) >= 4 and item in text), None)
        if not marker:
            continue
        start = text.find(marker)
        findings.append(
            _finding(
                "hidden_secret_knowledge_leak",
                marker,
                start=start,
                end=start + len(marker),
                severity="high",
                message=f"正文出现尚未解除隐藏状态的秘密标记“{marker}”。",
                evidence=[
                    {
                        "kind": "secret_state",
                        "entity_id": secret_id,
                        "field": "status",
                        "value": secret.get("status"),
                    }
                ],
                fix=f"确认本章是否应揭示“{marker}”；若应揭示，请在 state_update 中记录揭示。",
            )
        )

    # Injury/health conflict: only use explicit state markers and explicit
    # denial/injury language.  Generic fatigue or a single pain word is not a
    # contradiction by itself.
    for name, character in (state.get("characters") or {}).items():
        if not isinstance(character, Mapping):
            continue
        physical = " ".join(
            str(character.get(key) or "")
            for key in ("physical_state", "health", "injury", "status")
        )
        character_update = _state_update_character(state_update if isinstance(state_update, Mapping) else {}, str(name))
        if any(str(character_update.get(key) or "").strip() for key in ("physical_state", "health", "injury", "status")):
            continue
        prior_injured = bool(_INJURY_RE.search(physical))
        prior_healthy = bool(physical) and bool(re.search(r"(健康|正常|完好|无伤)", physical)) and not prior_injured
        for paragraph, start, end in paragraphs:
            if str(name) not in paragraph:
                continue
            if prior_injured and _HEALTHY_RE.search(paragraph):
                findings.append(
                    _finding(
                        "character_injury_conflict",
                        paragraph,
                        start=start,
                        end=end,
                        severity="high",
                        message=f"{name} 的状态记录包含“{physical}”，但本段使用了明确的无伤/痊愈表述。",
                        evidence=[
                            {"kind": "character_state", "entity_id": str(name), "field": "physical_state", "value": physical}
                        ],
                        fix=f"补充 {name} 伤势恢复的状态变化，或改为与既有伤势一致的描写。",
                    )
                )
            elif prior_healthy and _INJURY_RE.search(paragraph):
                findings.append(
                    _finding(
                        "character_injury_conflict",
                        paragraph,
                        start=start,
                        end=end,
                        severity="high",
                        message=f"{name} 的状态记录为“{physical}”，但本段出现明确伤势表述，未发现伤势变化证据。",
                        evidence=[
                            {"kind": "character_state", "entity_id": str(name), "field": "physical_state", "value": physical}
                        ],
                        fix=f"在状态更新中记录 {name} 的受伤，或明确这不是当前时间线的事实。",
                    )
                )
            break

    # Story-time regression: compare explicit ordinal markers only, and only
    # when the new event identifies a related actor.  Relative prose such as
    # “后来” is intentionally left to the model auditor.
    prior_events = store.list_narrative_events(limit=200)
    current_events = [item for item in _as_list(update.get("events")) if isinstance(item, Mapping)]
    for current_event in current_events:
        current_time = _parse_story_time(current_event.get("story_time") or current_event.get("time"))
        if current_time is None:
            continue
        actors = {str(item) for item in _as_list(current_event.get("actors") or current_event.get("characters"))}
        related = [
            item for item in prior_events
            if actors.intersection({str(actor) for actor in _as_list(item.get("actors"))})
            and _parse_story_time(item.get("story_time")) is not None
        ]
        if not related:
            continue
        latest = max(related, key=lambda item: _parse_story_time(item.get("story_time")) or -1)
        previous_time = _parse_story_time(latest.get("story_time"))
        if previous_time is None or current_time >= previous_time:
            continue
        findings.append(
            _finding(
                "story_time_regression",
                str(current_event.get("summary") or current_event.get("action") or ""),
                start=0,
                end=max(1, len(str(current_event.get("summary") or current_event.get("action") or ""))),
                severity="high",
                message=f"事件时间从第 {previous_time} 天回退到第 {current_time} 天，且涉及同一人物。",
                evidence=[
                    {
                        "kind": "narrative_event",
                        "event_id": latest.get("event_id"),
                        "chapter_id": latest.get("chapter_id"),
                        "story_time": latest.get("story_time"),
                        "source_revision_id": latest.get("source_revision_id"),
                    },
                    {
                        "kind": "current_event",
                        "event_id": current_event.get("id"),
                        "story_time": current_event.get("story_time") or current_event.get("time"),
                    },
                ],
                fix="确认这是闪回/非线性叙事；若不是，请修正 story_time 或补充时间跳转说明。",
            )
        )

    # Unanchored turn: deterministic first pass for the common "突然/原来/"
    # packaging of a new twist.  It is intentionally report-only and only
    # fires when all three conservative signals agree: an explicit marker,
    # no extractor-provided setup/causes, and no shared actor/object/thread or
    # location with the ten most recent prior events.  This lets ordinary
    # reversals involving an established character continue without noise.
    current_chapter_number = _chapter_number(chapter_id)
    recent_prior_events: List[Mapping[str, Any]] = []
    for item in prior_events:
        if not isinstance(item, Mapping):
            continue
        if str(item.get("id") or item.get("event_id") or "") in {
            str(current.get("id") or "") for current in current_events
        }:
            continue
        item_chapter_number = _chapter_number(item.get("chapter_id"))
        if (
            current_chapter_number is not None
            and item_chapter_number is not None
            and item_chapter_number >= current_chapter_number
        ):
            continue
        recent_prior_events.append(item)
        if len(recent_prior_events) >= 10:
            break

    for current_event in current_events:
        event_text = "；".join(
            str(current_event.get(key) or "").strip()
            for key in ("summary", "action", "outcome")
            if str(current_event.get(key) or "").strip()
        )
        marker_match = _ABRUPT_TURN_RE.search(event_text)
        if not marker_match or _event_has_anchor(current_event):
            continue
        current_entities = _event_entities(current_event)
        overlap_events = [
            item
            for item in recent_prior_events
            if current_entities.intersection(_event_entities(item))
        ]
        if overlap_events:
            continue

        marker = marker_match.group(0)
        evidence_text = event_text or marker
        evidence_start = 0
        evidence_end = max(1, len(evidence_text))
        # Prefer the actual paragraph span when the extractor summary is
        # present in the chapter; otherwise the event summary remains useful
        # evidence for the review panel.
        for paragraph, start, end in paragraphs:
            if marker in paragraph or (event_text and event_text in paragraph):
                evidence_text = paragraph
                evidence_start = start
                evidence_end = end
                break
        findings.append(
            _finding(
                "unanchored_turn",
                evidence_text,
                start=evidence_start,
                end=evidence_end,
                severity="medium",
                message=f"事件使用“{marker}”突转标记，但未提供因果、前置伏笔或近期既有实体关联证据。",
                evidence=[
                    {
                        "kind": "current_event",
                        "event_id": current_event.get("id") or current_event.get("event_id"),
                        "chapter_id": chapter_id,
                        "marker": marker,
                        "actors": list(_as_list(current_event.get("actors") or current_event.get("characters"))),
                        "objects": list(_as_list(current_event.get("objects") or current_event.get("items"))),
                        "threads": list(_as_list(current_event.get("threads") or current_event.get("clues"))),
                    },
                    {
                        "kind": "anchor_check",
                        "route": "recent_events",
                        "checked_event_ids": [
                            item.get("event_id") or item.get("id") for item in recent_prior_events
                        ],
                        "entity_overlap": [],
                        "causes": list(_as_list(current_event.get("causes") or current_event.get("predecessors"))),
                    },
                ],
                fix="补充 causes/predecessors、前置伏笔或已建立角色/物品/线索关联；若并非新转折，请去掉突转包装并明确场景铺垫。",
            )
        )

    # Deduplicate by issue type and span so the report remains readable.
    unique: Dict[str, Dict[str, Any]] = {}
    for item in findings:
        unique.setdefault(item["issue_id"], item)
    findings = list(unique.values())
    score = max(0, 100 - min(60, len(findings) * 20))
    return {
        "enabled": True,
        "pass": True,
        "blocking": False,
        "level": "none" if not findings else ("warning" if score >= 60 else "review"),
        "score": score,
        "details": [f"发现 {len(findings)} 个来源化状态冲突候选（仅供审阅）" if findings else "未发现来源化状态冲突候选"],
        "findings": findings,
        "conflict_count": len(findings),
    }


__all__ = ["check_event_consistency"]
