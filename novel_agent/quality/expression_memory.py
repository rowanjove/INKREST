"""Local expression memory and cross-chapter repetition diagnostics.

This module deliberately stays deterministic and report-only.  It stores small
expression fingerprints rather than embeddings or prose samples, so a project
can explain *where* a repeated expression came from without making a style
detector the source of truth for publication.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


EXPRESSION_MEMORY_SCHEMA_VERSION = 1
EXPRESSION_MEMORY_RELATIVE_PATH = Path("workspace/reports/expression_memory.json")
EXPRESSION_RULES_SCHEMA_VERSION = 1
EXPRESSION_RULES_RELATIVE_PATH = Path("assets/expression_memory_rules.json")
_SENTENCE_RE = re.compile(r"[^。！？!?；;\n]+[。！？!?；;]?")
_BODY_REACTION_RE = re.compile(
    r"(?:手指|指尖|肩膀|喉结|呼吸|心脏|胸口|脚步|嘴角|眼底|眼神|目光)"
    r"[^。！？!?；;\n]{0,20}"
)
_IMAGERY_RE = re.compile(r"(?:仿佛|如同|宛如|好似|像是|像)[^。！？!?；;\n]{1,24}")
_TRANSITION_RE = re.compile(
    r"^(?:然而|只是|直到|就在这时|与此同时|下一刻|此时|随后|最终|终于|原来|可就在)"
)


def _normalise_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").replace("\r\n", "\n")).strip()


def _normalise_expression(value: str) -> str:
    value = _normalise_text(value)
    value = re.sub(r"[“”\"'‘’]", "", value)
    value = re.sub(r"[，。！？!?；;：:、,]+", "", value)
    value = re.sub(r"\d+", "#", value)
    return value[:80]


def _text_sha256(text: str) -> str:
    return hashlib.sha256(_normalise_text(text).encode("utf-8")).hexdigest()


def _chapter_sort_value(chapter_id: Any) -> Optional[int]:
    match = re.search(r"\d+", str(chapter_id or ""))
    return int(match.group(0)) if match else None


def _sentence_spans(text: str) -> Iterable[Tuple[str, int, int]]:
    for match in _SENTENCE_RE.finditer(text or ""):
        value = match.group(0).strip()
        if value:
            start = match.start() + len(match.group(0)) - len(match.group(0).lstrip())
            yield value, start, start + len(value)


def _entry(
    kind: str,
    value: str,
    start: int,
    end: int,
    *,
    chapter_id: Optional[str],
    source: str,
    source_sha256: str,
) -> Optional[Dict[str, Any]]:
    text = _normalise_text(value)
    normalised = _normalise_expression(text)
    if len(normalised) < 4:
        return None
    fingerprint = hashlib.sha256(f"{kind}:{normalised}".encode("utf-8")).hexdigest()[:16]
    return {
        "id": f"expr:{fingerprint}:{start}",
        "kind": kind,
        "text": text[:120],
        "normalized": normalised,
        "fingerprint": fingerprint,
        "chapter_id": str(chapter_id) if chapter_id is not None else None,
        "source": source,
        "source_sha256": source_sha256,
        "start": int(start),
        "end": int(end),
    }


def extract_expression_entries(
    text: str,
    *,
    chapter_id: Optional[str] = None,
    source: str = "chapter_final",
) -> List[Dict[str, Any]]:
    """Extract explainable expression fingerprints from one chapter.

    The extractor intentionally uses a small set of high-signal categories.  A
    single entry is never a failure; repetition diagnostics decide whether a
    cluster is worth reviewing.
    """

    normalised_text = _normalise_text(text)
    if not normalised_text:
        return []
    source_sha256 = _text_sha256(normalised_text)
    entries: List[Dict[str, Any]] = []
    sentences = list(_sentence_spans(normalised_text))
    for sentence, start, end in sentences:
        opening = sentence[:8]
        item = _entry(
            "sentence_opening",
            opening,
            start,
            min(end, start + len(opening)),
            chapter_id=chapter_id,
            source=source,
            source_sha256=source_sha256,
        )
        if item:
            entries.append(item)

        for match in _BODY_REACTION_RE.finditer(sentence):
            item = _entry(
                "body_reaction",
                match.group(0),
                start + match.start(),
                start + match.end(),
                chapter_id=chapter_id,
                source=source,
                source_sha256=source_sha256,
            )
            if item:
                entries.append(item)

        for match in _IMAGERY_RE.finditer(sentence):
            item = _entry(
                "imagery",
                match.group(0),
                start + match.start(),
                start + match.end(),
                chapter_id=chapter_id,
                source=source,
                source_sha256=source_sha256,
            )
            if item:
                entries.append(item)

        if _TRANSITION_RE.search(sentence):
            item = _entry(
                "transition",
                sentence[:20],
                start,
                min(end, start + 20),
                chapter_id=chapter_id,
                source=source,
                source_sha256=source_sha256,
            )
            if item:
                entries.append(item)

    if sentences:
        sentence, start, end = sentences[-1]
        item = _entry(
            "ending_hook",
            sentence[-32:],
            max(start, end - 32),
            end,
            chapter_id=chapter_id,
            source=source,
            source_sha256=source_sha256,
        )
        if item:
            entries.append(item)
    return entries


def build_expression_memory_index(
    documents: Sequence[Mapping[str, Any]],
    *,
    max_entries: int = 6000,
) -> Dict[str, Any]:
    """Build a bounded project-local index from explicit chapter documents."""

    entries: List[Dict[str, Any]] = []
    sources: List[Dict[str, Any]] = []
    for document in documents:
        text = _normalise_text(document.get("text"))
        if not text:
            continue
        chapter_id = document.get("chapter_id")
        source = str(document.get("source") or "chapter_final")
        extracted = extract_expression_entries(text, chapter_id=chapter_id, source=source)
        entries.extend(extracted)
        sources.append(
            {
                "chapter_id": str(chapter_id) if chapter_id is not None else None,
                "source": source,
                "sha256": _text_sha256(text),
                "entry_count": len(extracted),
            }
        )
    if len(entries) > max_entries:
        entries = entries[-max_entries:]
    return {
        "schema_version": EXPRESSION_MEMORY_SCHEMA_VERSION,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_count": len(sources),
        "entry_count": len(entries),
        "sources": sources,
        "entries": entries,
    }


def expression_memory_path(root_dir: Path) -> Path:
    return Path(root_dir) / EXPRESSION_MEMORY_RELATIVE_PATH


def expression_memory_rules_path(root_dir: Path) -> Path:
    return Path(root_dir) / EXPRESSION_RULES_RELATIVE_PATH


def _default_expression_rules() -> Dict[str, Any]:
    return {
        "schema_version": EXPRESSION_RULES_SCHEMA_VERSION,
        "allowlist": [],
        "functional_recurrence": [],
    }


def load_expression_memory_rules(root_dir: Path) -> Dict[str, Any]:
    """Load optional local exceptions without making the checker fail closed."""

    path = expression_memory_rules_path(root_dir)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return _default_expression_rules()
    if not isinstance(payload, Mapping):
        return _default_expression_rules()
    if payload.get("schema_version") not in (None, EXPRESSION_RULES_SCHEMA_VERSION):
        return _default_expression_rules()
    result = _default_expression_rules()
    for key in ("allowlist", "whitelist", "functional_recurrence", "functional_recurrences"):
        value = payload.get(key)
        if not isinstance(value, list):
            continue
        target = "allowlist" if key in {"allowlist", "whitelist"} else "functional_recurrence"
        result[target].extend(item for item in value if isinstance(item, (str, Mapping)))
    return result


def save_expression_memory_rules(root_dir: Path, rules: Mapping[str, Any]) -> Path:
    """Persist a small, human-editable local exception file atomically."""

    payload = _default_expression_rules()
    for key in ("allowlist", "functional_recurrence"):
        value = rules.get(key) if isinstance(rules, Mapping) else None
        if isinstance(value, list):
            payload[key] = [item for item in value if isinstance(item, (str, Mapping))]
    target = expression_memory_rules_path(root_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(target)
    return target


def _rule_matches(entry: Mapping[str, Any], rule: Any) -> bool:
    if isinstance(rule, str):
        return _normalise_expression(rule) == str(entry.get("normalized") or "")
    if not isinstance(rule, Mapping):
        return False
    kind = str(rule.get("kind") or rule.get("category") or "").strip()
    if kind and kind != str(entry.get("kind") or ""):
        return False
    fingerprint = str(rule.get("fingerprint") or "").strip()
    if fingerprint and fingerprint == str(entry.get("fingerprint") or ""):
        return True
    candidate = rule.get("normalized") or rule.get("text") or rule.get("expression")
    return bool(candidate) and _normalise_expression(str(candidate)) == str(entry.get("normalized") or "")


def _expression_rule_kind(entry: Mapping[str, Any], rules: Mapping[str, Any]) -> str:
    for rule in rules.get("allowlist", []) if isinstance(rules, Mapping) else []:
        if _rule_matches(entry, rule):
            return "allowlist"
    for rule in rules.get("functional_recurrence", []) if isinstance(rules, Mapping) else []:
        if _rule_matches(entry, rule):
            return "functional_recurrence"
    return ""


def save_expression_memory(root_dir: Path, index: Mapping[str, Any]) -> Path:
    target = expression_memory_path(root_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(dict(index), ensure_ascii=False, indent=2) + "\n"
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_text(payload, encoding="utf-8")
    temp.replace(target)
    return target


def load_expression_memory(root_dir: Path) -> Optional[Dict[str, Any]]:
    path = expression_memory_path(root_dir)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("schema_version") != EXPRESSION_MEMORY_SCHEMA_VERSION:
        return None
    if not isinstance(payload.get("entries"), list):
        return None
    return payload


def refresh_expression_memory(root_dir: Path) -> Dict[str, Any]:
    """Rebuild the index from authoritative chapter_final.txt files."""

    root = Path(root_dir)
    documents: List[Dict[str, Any]] = []
    chapters_root = root / "workspace" / "chapters"
    for chapter_dir in sorted(chapters_root.glob("chapter_*")):
        final_path = chapter_dir / "chapter_final.txt"
        if not final_path.is_file():
            continue
        try:
            text = final_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        documents.append(
            {
                "chapter_id": chapter_dir.name.removeprefix("chapter_"),
                "source": "chapter_final",
                "text": text,
            }
        )
    index = build_expression_memory_index(documents)
    try:
        save_expression_memory(root, index)
    except OSError:
        # Diagnostics should never make quality reporting fail closed by accident.
        pass
    return index


def _entry_key(entry: Mapping[str, Any]) -> Tuple[str, str]:
    return str(entry.get("kind") or "unknown"), str(entry.get("normalized") or "")


def check_expression_repetition(
    text: str,
    root_dir: Path,
    *,
    chapter_id: Optional[str] = None,
    index: Optional[Mapping[str, Any]] = None,
    rules: Optional[Mapping[str, Any]] = None,
    max_findings: int = 40,
) -> Dict[str, Any]:
    """Return report-only cross-chapter and local expression repetition findings."""

    current_entries = extract_expression_entries(text, chapter_id=chapter_id, source="current")
    if not current_entries:
        return {
            "enabled": True,
            "pass": True,
            "blocking": False,
            "level": "none",
            "score": 100,
            "details": [],
            "findings": [],
            "clusters": [],
            "memory_source_count": 0,
        }

    memory = dict(index) if isinstance(index, Mapping) else load_expression_memory(root_dir)
    if not memory:
        memory = refresh_expression_memory(root_dir)
    expression_rules = dict(rules) if isinstance(rules, Mapping) else load_expression_memory_rules(root_dir)
    historical_entries = [item for item in memory.get("entries", []) if isinstance(item, Mapping)]
    current_hash = _text_sha256(text)
    current_chapters = {
        str(item.get("chapter_id"))
        for item in historical_entries
        if item.get("source_sha256") == current_hash and item.get("chapter_id") is not None
    }
    by_key: Dict[Tuple[str, str], List[Mapping[str, Any]]] = {}
    for item in historical_entries:
        if item.get("source_sha256") == current_hash or (
            chapter_id is not None and str(item.get("chapter_id")) == str(chapter_id)
        ):
            continue
        by_key.setdefault(_entry_key(item), []).append(item)

    local_counts: Dict[Tuple[str, str], int] = {}
    for item in current_entries:
        local_counts[_entry_key(item)] = local_counts.get(_entry_key(item), 0) + 1

    findings: List[Dict[str, Any]] = []
    allowlist_count = 0
    functional_count = 0
    for current in current_entries:
        rule_kind = _expression_rule_kind(current, expression_rules)
        if rule_kind == "allowlist":
            allowlist_count += 1
            continue
        is_functional = rule_kind == "functional_recurrence"
        if is_functional:
            functional_count += 1
        key = _entry_key(current)
        matches = by_key.get(key, [])
        local_count = local_counts.get(key, 1)
        if not matches and local_count < 2:
            continue
        chapter_ids = sorted({str(item.get("chapter_id")) for item in matches if item.get("chapter_id") is not None})
        distances = []
        current_number = _chapter_sort_value(chapter_id)
        for item in matches:
            previous_number = _chapter_sort_value(item.get("chapter_id"))
            if current_number is not None and previous_number is not None:
                distances.append(abs(current_number - previous_number))
        distance = min(distances) if distances else None
        if distance is not None and distance <= 3:
            window = "near_3"
        elif distance is not None and distance <= 10:
            window = "recent_10"
        elif distance is not None and distance <= 30:
            window = "long_30"
        else:
            window = "unknown_distance"
        count_historical = len(matches)
        confidence = min(0.96, 0.58 + (0.12 if count_historical >= 2 else 0) + (0.12 if local_count >= 2 else 0))
        evidence = [
            {
                "chapter_id": item.get("chapter_id"),
                "start": item.get("start"),
                "end": item.get("end"),
                "text": item.get("text"),
            }
            for item in matches[:4]
        ]
        issue_id = f"expression_reuse:{current.get('id')}"
        findings.append(
            {
                "issue_id": issue_id,
                "id": issue_id,
                "kind": current.get("kind"),
                "text": current.get("text"),
                "normalized": current.get("normalized"),
                "start": current.get("start"),
                "end": current.get("end"),
                "count_local": local_count,
                "count_historical": count_historical,
                "chapter_ids": chapter_ids,
                "distance": distance,
                "window": window,
                "confidence": round(confidence, 3),
                "severity": "info" if is_functional else ("review" if confidence >= 0.7 else "warning"),
                "action": "keep" if is_functional else "review",
                "functional_recurrence": is_functional,
                "evidence": evidence,
            }
        )
        if len(findings) >= max_findings:
            break

    clusters: List[Dict[str, Any]] = []
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for finding in findings:
        grouped.setdefault((str(finding.get("kind")), str(finding.get("normalized"))), []).append(finding)
    for number, ((kind, normalized), items) in enumerate(grouped.items(), start=1):
        clusters.append(
            {
                "id": f"expression-cluster-{number}",
                "kind": kind,
                "normalized": normalized,
                "finding_ids": [item["issue_id"] for item in items],
                "count": len(items),
                "reviewable": not all(item.get("functional_recurrence") for item in items),
            }
        )

    reviewable_findings = [item for item in findings if not item.get("functional_recurrence")]
    score = max(
        0,
        100 - min(60, len(reviewable_findings) * 8) - min(20, len([item for item in clusters if item.get("reviewable", True)]) * 4),
    )
    level = "none" if not findings else ("warning" if score >= 70 else "review")
    return {
        "enabled": True,
        "pass": True,
        "blocking": False,
        "level": level,
        "score": score,
        "details": [
            f"发现 {len(findings)} 处表达复用候选（仅供审阅）" if findings else "未发现跨章表达复用候选",
        ],
        "findings": findings,
        "clusters": clusters,
        "memory_source_count": int(memory.get("source_count") or 0),
        "memory_entry_count": int(memory.get("entry_count") or len(historical_entries)),
        "current_chapter_ids": sorted(current_chapters),
        "allowlist_count": allowlist_count,
        "functional_recurrence_count": functional_count,
    }


def build_expression_avoidance_context(
    root_dir: Path,
    chapter_id: Optional[str],
    *,
    limit: int = 12,
) -> str:
    """Build a short high-priority avoidance block for a scene writer."""

    memory = load_expression_memory(root_dir)
    if not memory:
        memory = refresh_expression_memory(root_dir)
    expression_rules = load_expression_memory_rules(root_dir)
    current_number = _chapter_sort_value(chapter_id)
    candidates: List[Mapping[str, Any]] = []
    seen: set[Tuple[str, str]] = set()
    entries = [entry for entry in memory.get("entries", []) if isinstance(entry, Mapping)]
    preferred = [
        entry for entry in entries
        if str(entry.get("kind")) in {"body_reaction", "imagery", "transition", "ending_hook"}
    ]
    fallback = [entry for entry in entries if entry not in preferred]
    for item in reversed(preferred + fallback):
        item_number = _chapter_sort_value(item.get("chapter_id"))
        if current_number is not None and item_number is not None and item_number >= current_number:
            continue
        if _expression_rule_kind(item, expression_rules) in {"allowlist", "functional_recurrence"}:
            continue
        key = _entry_key(item)
        if key in seen or len(str(item.get("normalized") or "")) < 5:
            continue
        seen.add(key)
        candidates.append(item)
        if len(candidates) >= max(1, int(limit)):
            break
    if not candidates:
        return ""
    lines = [
        "以下是近期已采用的表达，仅用于避免无必要的原样复用；角色口头禅和必要母题可保留："
    ]
    for item in candidates:
        lines.append(
            f"- [避免复读][expr:{item.get('fingerprint', '?')}][第{item.get('chapter_id', '?')}章] "
            f"{item.get('text', '')}（{item.get('kind', 'expression')}）"
        )
    return "\n".join(lines)


def build_expression_contract(
    root_dir: Path,
    chapter_id: Optional[str],
    *,
    limit: int = 12,
) -> str:
    """Compile the bounded recall into a writer/style-editor contract.

    The contract is deliberately plain text so existing prompt agents can
    consume it without a schema migration.  It states the policy (avoid
    accidental reuse, preserve functional recurrence) next to the
    source-labelled examples and remains empty when no memory exists.
    """

    avoidance = build_expression_avoidance_context(root_dir, chapter_id, limit=limit)
    if not avoidance:
        return ""
    return (
        "[EXPRESSION_CONTRACT]\n"
        "只改写无功能必要的表达复用；不得为了去重改变事实、角色口头禅、专名或已标记的功能性回环。\n"
        f"{avoidance}\n"
        "[/EXPRESSION_CONTRACT]"
    )


__all__ = [
    "EXPRESSION_MEMORY_RELATIVE_PATH",
    "EXPRESSION_MEMORY_SCHEMA_VERSION",
    "EXPRESSION_RULES_RELATIVE_PATH",
    "EXPRESSION_RULES_SCHEMA_VERSION",
    "build_expression_memory_index",
    "build_expression_avoidance_context",
    "build_expression_contract",
    "check_expression_repetition",
    "expression_memory_path",
    "expression_memory_rules_path",
    "extract_expression_entries",
    "load_expression_memory",
    "load_expression_memory_rules",
    "refresh_expression_memory",
    "save_expression_memory",
    "save_expression_memory_rules",
]
