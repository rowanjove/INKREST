"""Longform Memory 2.0 and cross-chapter pattern diagnostics (PRD §19, §58)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from novel_agent.human_writing.schemas import HWEIssue, HWEIssueDetail


# Regular expressions for expanded Longform Memory 2.0 categories
_SENTENCE_RE = re.compile(r"[^。！？!?；;\n]+[。！？!?；;]?")
_BODY_REACTION_RE = re.compile(
    r"(?:手指|指尖|肩膀|喉结|呼吸|心脏|胸口|脚步|嘴角|眼底|眼神|目光|拳头|身形)"
    r"[^，,。！？!?；;\n]{0,10}"
)
_EMOTION_REACTION_RE = re.compile(
    r"(?:心中一震|倒吸一口凉气|浑身冰冷|后背发凉|头皮发麻|瞳孔微缩|心头一紧|莫名一颤|如坠冰窟)"
)
_IMAGERY_RE = re.compile(r"(?:仿佛|如同|宛如|好似|像是|犹如|如)[^，,。！？!?；;\n]{1,20}")
_TRANSITION_RE = re.compile(
    r"^(?:然而|只是|直到|就在这时|与此同时|下一刻|此时|随后|最终|终于|原来|可就在)"
)
_SYNTAX_BINARY_RE = re.compile(r"(?:不是|不只是|并非)[^，。！？]{2,20}，?(?:而是|更是)[^，。！？]{2,20}")
_DIALOGUE_TAG_RE = re.compile(r"(?:冷笑|淡淡|轻声|低沉|咬牙|沉吟|失声|脱口)(?:道|说|问)")
_AUTHOR_SUMMARY_RE = re.compile(r"(?:这意味着|换句话说|他终于明白|显而易见|毋庸置疑|在某种程度上)")


def normalise_text(value: Any) -> str:
    """Normalize text by stripping whitespace and standardizing newlines."""
    return re.sub(r"\s+", "", str(value or "").replace("\r\n", "\n")).strip()


def normalise_expression(value: str) -> str:
    """Strip punctuation and digits to generate matching canonical expression."""
    val = normalise_text(value)
    val = re.sub(r"[“”\"'‘’【】《》]", "", val)
    val = re.sub(r"[，。！？!?；;：:、,.\-]+", "", val)
    val = re.sub(r"\d+", "#", val)
    return val[:80]


def extract_chapter_number(chapter_id: Any) -> Optional[int]:
    """Parse numeric chapter index from chapter_id."""
    match = re.search(r"\d+", str(chapter_id or ""))
    return int(match.group(0)) if match else None


@dataclass
class ExpressionEntry:
    """Single expression fingerprint entry."""

    id: str
    kind: str
    text: str
    normalized: str
    fingerprint: str
    chapter_id: Optional[str] = None
    start: int = 0
    end: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "text": self.text,
            "normalized": self.normalized,
            "fingerprint": self.fingerprint,
            "chapter_id": self.chapter_id,
            "start": self.start,
            "end": self.end,
        }


def extract_expression_entries_v2(
    text: str,
    *,
    chapter_id: Optional[str] = None,
) -> List[ExpressionEntry]:
    """Extract Longform Memory 2.0 expression entries across all expanded categories."""
    entries: List[ExpressionEntry] = []
    norm_text = normalise_text(text)
    if not norm_text:
        return entries

    ch_id_str = str(chapter_id) if chapter_id is not None else None

    # Helper to add entry
    def add_entry(kind: str, raw_val: str, st: int, en: int) -> None:
        norm = normalise_expression(raw_val)
        if len(norm) < 3:
            return
        fp = hashlib.sha256(f"{kind}:{norm}".encode("utf-8")).hexdigest()[:16]
        eid = f"expr2:{kind}:{fp}:{st}"
        entries.append(
            ExpressionEntry(
                id=eid,
                kind=kind,
                text=raw_val[:120],
                normalized=norm,
                fingerprint=fp,
                chapter_id=ch_id_str,
                start=st,
                end=en,
            )
        )

    # 1. Sentences scan
    for match in _SENTENCE_RE.finditer(norm_text):
        s_text = match.group(0).strip()
        st = match.start()
        en = match.end()
        if not s_text:
            continue

        # Sentence opening
        add_entry("sentence_opening", s_text[:8], st, min(en, st + 8))

        # Body reaction
        for m in _BODY_REACTION_RE.finditer(s_text):
            add_entry("body_reaction", m.group(0), st + m.start(), st + m.end())

        # Emotion shock reaction
        for m in _EMOTION_REACTION_RE.finditer(s_text):
            add_entry("emotion_reaction", m.group(0), st + m.start(), st + m.end())

        # Imagery / simile
        for m in _IMAGERY_RE.finditer(s_text):
            add_entry("imagery", m.group(0), st + m.start(), st + m.end())

        # Transition
        if _TRANSITION_RE.search(s_text):
            add_entry("transition", s_text[:12], st, min(en, st + 12))

        # Binary contrast syntax
        for m in _SYNTAX_BINARY_RE.finditer(s_text):
            add_entry("syntax_pattern", m.group(0), st + m.start(), st + m.end())

        # Dialogue tag
        for m in _DIALOGUE_TAG_RE.finditer(s_text):
            add_entry("dialogue_tag", m.group(0), st + m.start(), st + m.end())

        # Author summary
        for m in _AUTHOR_SUMMARY_RE.finditer(s_text):
            add_entry("author_summary", m.group(0), st + m.start(), st + m.end())

    # 2. Chapter opening & closing fingerprints
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        first_line = lines[0]
        add_entry("chapter_opening", first_line[:40], 0, min(len(text), len(first_line)))

        last_line = lines[-1]
        add_entry(
            "chapter_closing",
            last_line[-40:],
            max(0, len(text) - len(last_line)),
            len(text),
        )

    return entries


@dataclass
class WindowDiagnostics:
    """Sliding window statistics for repeated expressions."""

    expression: str
    kind: str
    window_3_count: int = 0
    window_10_count: int = 0
    whole_book_count: int = 0
    is_saturated: bool = False
    evidence_chapters: List[str] = field(default_factory=list)


def analyze_sliding_windows(
    current_entries: Sequence[ExpressionEntry],
    historical_entries: Sequence[Mapping[str, Any]],
    current_chapter_id: Optional[str] = None,
) -> List[WindowDiagnostics]:
    """Calculate multi-window frequencies (3-chapter, 10-chapter, whole book) according to PRD §19.1."""
    curr_num = extract_chapter_number(current_chapter_id)

    # Group historical entries by (kind, normalized)
    history_by_key: Dict[Tuple[str, str], List[Mapping[str, Any]]] = {}
    for h in historical_entries:
        h_chap = str(h.get("chapter_id"))
        if current_chapter_id and h_chap == str(current_chapter_id):
            continue
        k = (str(h.get("kind")), str(h.get("normalized")))
        history_by_key.setdefault(k, []).append(h)

    # Deduplicate current entries by key
    diagnostics: List[WindowDiagnostics] = []
    seen_keys: Set[Tuple[str, str]] = set()

    for e in current_entries:
        key = (e.kind, e.normalized)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        matches = history_by_key.get(key, [])
        if not matches:
            continue

        w3_cnt = 0
        w10_cnt = 0
        whole_cnt = len(matches)
        evidence_chaps: List[str] = []

        for m in matches:
            m_chap = str(m.get("chapter_id"))
            if m_chap and m_chap not in evidence_chaps:
                evidence_chaps.append(m_chap)

            m_num = extract_chapter_number(m_chap)
            if curr_num is not None and m_num is not None:
                dist = curr_num - m_num
                if 0 < dist <= 3:
                    w3_cnt += 1
                if 0 < dist <= 10:
                    w10_cnt += 1

        # Saturation criteria (PRD §19.1): >=2 in window_3 OR >=4 in window_10
        is_sat = (w3_cnt >= 2) or (w10_cnt >= 4)
        diagnostics.append(
            WindowDiagnostics(
                expression=e.text,
                kind=e.kind,
                window_3_count=w3_cnt,
                window_10_count=w10_cnt,
                whole_book_count=whole_cnt,
                is_saturated=is_sat,
                evidence_chapters=evidence_chaps[:5],
            )
        )

    # Sort saturated items first, then by window_3 count descending
    diagnostics.sort(key=lambda d: (d.is_saturated, d.window_3_count, d.window_10_count), reverse=True)
    return diagnostics


def detect_chapter_ending_fingerprint_repetition(
    current_text: str,
    preceding_chapters_texts: Sequence[Tuple[str, str]],  # List of (chapter_id, text)
) -> List[HWEIssue]:
    """Detect repetitive chapter ending archetypes across consecutive chapters (PRD §58.3)."""
    issues: List[HWEIssue] = []
    curr_lines = [l.strip() for l in current_text.splitlines() if l.strip()]
    if not curr_lines:
        return issues

    curr_ending = curr_lines[-1]

    # Check for ending hook patterns e.g. "等待着他", "悄然拉开序幕", "新的风暴", "深渊"
    ending_patterns = [
        r"(?:悄然拉开|拉开|开启|等待着|属于他的).{0,15}(?:序幕|深渊|风暴|时代)",
        r"(?:直到这一刻|夜幕下|黑夜中).{0,20}(?:他才明白|注定|无可挽回)",
        r"(?:游戏|较量|杀戮|狩猎).{0,10}(?:才刚刚开始)",
    ]

    matched_pattern: Optional[str] = None
    for p in ending_patterns:
        if re.search(p, curr_ending):
            matched_pattern = p
            break

    if not matched_pattern:
        return issues

    # Compare with last 1-3 chapters
    repetitive_in_recent = []
    for prev_id, prev_text in preceding_chapters_texts[-3:]:
        prev_lines = [l.strip() for l in prev_text.splitlines() if l.strip()]
        if prev_lines and re.search(matched_pattern, prev_lines[-1]):
            repetitive_in_recent.append(prev_id)

    if repetitive_in_recent:
        start_pos = max(0, len(current_text) - len(curr_ending))
        issues.append(
            HWEIssue(
                type="HWE.LONGFORM.CHAPTER_ENDING_REPEAT",
                issue_layer="text",
                severity="high",
                audit_class="WARNING",
                text=curr_ending[:80],
                why=f"跨章节连续以‘{curr_ending[:30]}’等类似悬念套路作结（前序第 {', '.join(repetitive_in_recent)} 章已使用相似句式），读者极易产生审美疲劳。",
                fix="改用截然不同的章尾形式（如中断在一句未说完的台词、一声突兀的撞击、或一个客观物品的状态变化）。",
                hwe=HWEIssueDetail(
                    rule_id="HWE.LONGFORM.CHAPTER_ENDING_REPEAT",
                    family="longform",
                    confidence=0.92,
                    start=start_pos,
                    end=len(current_text),
                    line=len(current_text.splitlines()),
                    paragraph=len(curr_lines),
                    matched_text=curr_ending[:80],
                    autofix="model_patch",
                ),
            )
        )

    return issues


def analyze_dialogue_voice_drift(
    current_text: str,
    character_name: str,
    baseline_profile: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Calculate character dialogue statistics and detect voice collapse/drift (PRD §58.5)."""
    # Extract dialogue utterances attributed to character
    pattern = re.compile(
        rf"(?:{re.escape(character_name)}[^\n]{{0,10}}[：:说问道]|“(?P<quote>[^”]{{1,200}})”[^\n]{{0,10}}{re.escape(character_name)})"
    )

    quotes: List[str] = []
    # Also simple extraction of dialogue lines if character is in scene
    for line in current_text.splitlines():
        if character_name in line:
            for m in re.finditer(r"“([^”]+)”", line):
                quotes.append(m.group(1))

    if not quotes:
        return {"character": character_name, "utterances_count": 0, "status": "insufficient_data"}

    total_chars = sum(len(q) for q in quotes)
    avg_len = total_chars / len(quotes)
    question_count = sum(1 for q in quotes if "？" in q or "?" in q)
    exclamation_count = sum(1 for q in quotes if "！" in q or "!" in q)

    q_ratio = question_count / len(quotes)
    e_ratio = exclamation_count / len(quotes)

    drift_detected = False
    drift_reasons: List[str] = []

    if baseline_profile:
        # Check expected sentence length
        exp_style = str(baseline_profile.get("style") or baseline_profile.get("tone") or "")
        if "短句" in exp_style or "精炼" in exp_style:
            if avg_len > 35:
                drift_detected = True
                drift_reasons.append(f"角色设定偏好短句精炼，但当前平均句长达 {avg_len:.1f} 字，台词明显拖沓。")
        elif "长句" in exp_style or "严密" in exp_style:
            if avg_len < 8:
                drift_detected = True
                drift_reasons.append(f"角色设定偏好长句严密，但当前平均句长仅 {avg_len:.1f} 字。")

        # Check question ratio
        if "反问" not in exp_style and q_ratio > 0.4:
            drift_detected = True
            drift_reasons.append(f"角色无反问习惯，但反问句占比达 {q_ratio*100:.0f}%，出现机械设问漂移。")

    return {
        "character": character_name,
        "utterances_count": len(quotes),
        "avg_sentence_length": round(avg_len, 1),
        "question_ratio": round(q_ratio, 2),
        "exclamation_ratio": round(e_ratio, 2),
        "drift_detected": drift_detected,
        "drift_reasons": drift_reasons,
    }
