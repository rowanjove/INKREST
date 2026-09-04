"""Deterministic safety checks for model-produced prose rewrite candidates.

The quality editor is allowed to suggest a revision, but the editor output is
still untrusted text.  This module deliberately contains no model calls and no
project-specific state.  It only compares a candidate with the source text and
rejects changes that would make it unsafe to put back into the chapter file.
"""

from __future__ import annotations

import json
import hashlib
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

from novel_agent.quality.fact_ledger import audit_fact_consistency


DEFAULT_MIN_LENGTH_RATIO = 0.55
DEFAULT_MAX_LENGTH_RATIO = 1.45
CONTENT_LOCK_SCHEMA_VERSION = 1

_CODE_FENCE_RE = re.compile(r"```|~~~")
_MARKDOWN_HEADING_RE = re.compile(r"(?m)^\s{0,3}#{1,6}\s+\S")
_MARKDOWN_BULLET_RE = re.compile(r"(?m)^\s{0,3}(?:[-*+] |\d+[.)] )\S")
_HTML_BLOCK_RE = re.compile(r"(?is)<\/?(?:p|div|section|article|html|body|pre|code)(?:\s[^>]*)?>")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WRAPPER_LINE_RE = re.compile(
    r"(?i)^\s*(?:以下是|下面是|这是|现将)?\s*"
    r"(?:修订|修改|润色|重写)(?:后的)?(?:完整)?正文\s*[:：]?\s*$"
)
_EXPLANATION_LINE_RE = re.compile(
    r"(?i)^\s*(?:修改说明|修订说明|改写说明|说明|注：|备注：)\s*[:：]?\s*$"
)


@dataclass(frozen=True)
class RenderContract:
    """The source-derived bounds a rewrite candidate must satisfy."""

    original_chars: int
    original_paragraphs: int
    min_chars: int
    max_chars: int
    min_length_ratio: float = DEFAULT_MIN_LENGTH_RATIO
    max_length_ratio: float = DEFAULT_MAX_LENGTH_RATIO
    # Optional scene binding fields.  Legacy callers can keep using the
    # length-only contract; the extra fields are populated by
    # ``build_scene_render_contract`` and remain report-only.
    content_lock: Dict[str, Any] = field(default_factory=dict)
    expression_contract: str = ""
    bindings: Dict[str, Any] = field(default_factory=dict)
    contract_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _normalise(text: Any) -> str:
    return str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def text_sha256(text: Any) -> str:
    return hashlib.sha256(_normalise(text).encode("utf-8")).hexdigest()


def _paragraph_count(text: str) -> int:
    return len([part for part in re.split(r"\n\s*\n+", text) if part.strip()])


def _stable_digest(value: Any, *, length: int = 24) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def _bounded_values(value: Any, *, limit: int = 12) -> List[str]:
    if value is None:
        return []
    values = value if isinstance(value, (list, tuple, set)) else [value]
    result: List[str] = []
    for item in values:
        if isinstance(item, Mapping):
            text = str(
                item.get("summary")
                or item.get("content")
                or item.get("text")
                or item.get("goal")
                or item.get("intent")
                or item
            )
        else:
            text = str(item)
        text = text.strip()
        if text and text not in result:
            result.append(text[:240])
        if len(result) >= limit:
            break
    return result


def build_content_lock(
    *,
    chapter_id: str = "",
    scene: Optional[Mapping[str, Any]] = None,
    plan: Optional[Mapping[str, Any]] = None,
    state_snapshot: Optional[Mapping[str, Any]] = None,
    prose_profile: Optional[Mapping[str, Any]] = None,
    prompt_template_version: str = "",
    source_memory_ids: Optional[Sequence[str]] = None,
    required_memory_ids: Optional[Sequence[str]] = None,
    candidate_id: str = "",
    revision_id: str = "",
) -> Dict[str, Any]:
    """Compile an explainable, immutable-by-digest CONTENT_LOCK payload."""

    scene_data = dict(scene) if isinstance(scene, Mapping) else {}
    plan_data = dict(plan) if isinstance(plan, Mapping) else {}
    state_data = dict(state_snapshot) if isinstance(state_snapshot, Mapping) else {}
    profile_data = dict(prose_profile) if isinstance(prose_profile, Mapping) else {}
    scene_id = str(scene_data.get("scene_id") or scene_data.get("id") or "")
    required_beats = _bounded_values(
        scene_data.get("required_beats")
        or scene_data.get("must_include")
        or scene_data.get("beats")
        or plan_data.get("beats")
    )
    immutable_facts = _bounded_values(
        scene_data.get("immutable_facts")
        or scene_data.get("canon_facts")
        or plan_data.get("immutable_facts")
        or plan_data.get("canon_facts")
    )
    character_goals = _bounded_values(
        scene_data.get("character_goals")
        or scene_data.get("character_intents")
        or plan_data.get("character_intents")
    )
    knowledge_boundaries = _bounded_values(
        scene_data.get("knowledge_boundaries") or scene_data.get("must_not_include")
    )
    causal_predecessors = _bounded_values(
        scene_data.get("causal_predecessors")
        or scene_data.get("predecessors")
        or scene_data.get("causes")
    )
    raw_deltas = scene_data.get("state_deltas") or scene_data.get("state_delta") or {}
    if not raw_deltas:
        raw_deltas = plan_data.get("state_expectations") or {}
    state_deltas = dict(raw_deltas) if isinstance(raw_deltas, Mapping) else _bounded_values(raw_deltas)
    profile_version = str(
        profile_data.get("profile_id")
        or profile_data.get("revision")
        or profile_data.get("version")
        or ""
    )
    raw_memory_ids: Sequence[Any]
    if isinstance(source_memory_ids, str):
        raw_memory_ids = [source_memory_ids]
    else:
        raw_memory_ids = source_memory_ids or []
    memory_ids = [str(item) for item in raw_memory_ids if str(item).strip()]
    raw_required_ids = required_memory_ids if required_memory_ids is not None else []
    required_ids = [str(item) for item in raw_required_ids if str(item).strip()]
    bindings = {
        "chapter_plan_digest": _stable_digest(plan_data),
        "state_snapshot_digest": _stable_digest(state_data),
        "prose_profile_version": profile_version,
        "prompt_template_version": str(prompt_template_version or ""),
        "source_memory_ids": memory_ids[:32],
        "required_memory_ids": required_ids[:32],
        "candidate_id": str(candidate_id or ""),
        "revision_id": str(revision_id or ""),
    }
    lock = {
        "schema_version": CONTENT_LOCK_SCHEMA_VERSION,
        "chapter_id": str(chapter_id or ""),
        "scene_id": scene_id,
        "entry": str(scene_data.get("entry") or "")[:240],
        "exit": str(scene_data.get("exit") or "")[:240],
        "required_beats": required_beats,
        "immutable_canon_facts": immutable_facts,
        "character_goals": character_goals,
        "knowledge_boundaries": knowledge_boundaries,
        "causal_predecessors": causal_predecessors,
        "state_deltas": state_deltas,
        "bindings": bindings,
    }
    lock["lock_digest"] = _stable_digest(lock)
    return lock


def build_scene_render_contract(
    original_text: str = "",
    *,
    chapter_id: str = "",
    scene: Optional[Mapping[str, Any]] = None,
    plan: Optional[Mapping[str, Any]] = None,
    state_snapshot: Optional[Mapping[str, Any]] = None,
    prose_profile: Optional[Mapping[str, Any]] = None,
    prompt_template_version: str = "",
    source_memory_ids: Optional[Sequence[str]] = None,
    required_memory_ids: Optional[Sequence[str]] = None,
    expression_contract: str = "",
    candidate_id: str = "",
    revision_id: str = "",
    min_length_ratio: float = DEFAULT_MIN_LENGTH_RATIO,
    max_length_ratio: float = DEFAULT_MAX_LENGTH_RATIO,
) -> RenderContract:
    """Build one scene contract while preserving legacy length validation."""

    base = build_render_contract(
        original_text,
        min_length_ratio=min_length_ratio,
        max_length_ratio=max_length_ratio,
    )
    lock = build_content_lock(
        chapter_id=chapter_id,
        scene=scene,
        plan=plan,
        state_snapshot=state_snapshot,
        prose_profile=prose_profile,
        prompt_template_version=prompt_template_version,
        source_memory_ids=source_memory_ids,
        required_memory_ids=required_memory_ids,
        candidate_id=candidate_id,
        revision_id=revision_id,
    )
    bindings = dict(lock.get("bindings") or {})
    contract_id = _stable_digest(
        {
            "base": base.to_dict(),
            "content_lock": lock,
            "expression_contract": str(expression_contract or ""),
        }
    )
    contract_data = base.to_dict()
    contract_data.update(
        {
            "content_lock": lock,
            "expression_contract": str(expression_contract or ""),
            "bindings": bindings,
            "contract_id": contract_id,
        }
    )
    return RenderContract(**contract_data)


def build_render_contract(
    original_text: str,
    *,
    min_length_ratio: float = DEFAULT_MIN_LENGTH_RATIO,
    max_length_ratio: float = DEFAULT_MAX_LENGTH_RATIO,
) -> RenderContract:
    """Build a source-only contract for a prose rewrite.

    Length is measured in Unicode code points after trimming outer whitespace.
    This is intentionally conservative: it is a loss-prevention bound, not a
    literary quality score.
    """

    original = _normalise(original_text)
    min_ratio = max(0.0, float(min_length_ratio))
    max_ratio = max(min_ratio, float(max_length_ratio))
    original_chars = len(original)
    min_chars = max(1, int(round(original_chars * min_ratio))) if original_chars else 0
    max_chars = max(min_chars, int(round(original_chars * max_ratio)))
    return RenderContract(
        original_chars=original_chars,
        original_paragraphs=_paragraph_count(original),
        min_chars=min_chars,
        max_chars=max_chars,
        min_length_ratio=min_ratio,
        max_length_ratio=max_ratio,
    )


def _coerce_contract(
    original_text: str,
    contract: Optional[Union[RenderContract, Mapping[str, Any]]],
) -> RenderContract:
    if isinstance(contract, RenderContract):
        return contract
    if isinstance(contract, Mapping):
        try:
            return RenderContract(
                original_chars=int(contract["original_chars"]),
                original_paragraphs=int(contract.get("original_paragraphs", 0)),
                min_chars=int(contract["min_chars"]),
                max_chars=int(contract["max_chars"]),
                min_length_ratio=float(contract.get("min_length_ratio", DEFAULT_MIN_LENGTH_RATIO)),
                max_length_ratio=float(contract.get("max_length_ratio", DEFAULT_MAX_LENGTH_RATIO)),
                content_lock=dict(contract.get("content_lock") or {}),
                expression_contract=str(contract.get("expression_contract") or ""),
                bindings=dict(contract.get("bindings") or {}),
                contract_id=str(contract.get("contract_id") or ""),
            )
        except (KeyError, TypeError, ValueError):
            pass
    return build_render_contract(original_text)


def _format_pollution(candidate: str) -> List[str]:
    reasons: List[str] = []
    if _CODE_FENCE_RE.search(candidate):
        reasons.append("markdown_code_fence")
    if _MARKDOWN_HEADING_RE.search(candidate):
        reasons.append("markdown_heading")
    if len(_MARKDOWN_BULLET_RE.findall(candidate)) >= 2:
        reasons.append("markdown_list")
    if _HTML_BLOCK_RE.search(candidate):
        reasons.append("html_block")
    lines = [line.strip() for line in candidate.splitlines() if line.strip()]
    if lines and (_WRAPPER_LINE_RE.match(lines[0]) or _EXPLANATION_LINE_RE.match(lines[0])):
        reasons.append("editor_wrapper")
    if lines and lines[0] in {"正文：", "正文如下：", "修订稿：", "修改稿："}:
        reasons.append("editor_wrapper")
    if _CONTROL_RE.search(candidate):
        reasons.append("control_character")
    if not reasons and lines and lines[0].startswith("{"):
        try:
            parsed = json.loads(candidate)
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed = None
        if isinstance(parsed, (dict, list)):
            reasons.append("json_payload")
    return reasons


def validate_render_candidate(
    original_text: str,
    candidate_text: str,
    contract: Optional[Union[RenderContract, Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    """Validate a candidate and return a stable, JSON-serialisable result.

    ``pass`` means the candidate may proceed to the existing rewrite path.
    Rejections are deliberately hard and local; no LLM is called to explain or
    repair them.  Paragraph drift is reported as a metric but is not a hard
    failure because a legitimate prose edit may merge or split paragraphs.
    """

    original = _normalise(original_text)
    candidate = _normalise(candidate_text)
    resolved = _coerce_contract(original, contract)
    reasons: List[str] = []
    if not candidate:
        reasons.append("empty_candidate")

    candidate_chars = len(candidate)
    ratio = (candidate_chars / resolved.original_chars) if resolved.original_chars else None
    if candidate and resolved.original_chars:
        if candidate_chars < resolved.min_chars:
            reasons.append("candidate_too_short")
        elif candidate_chars > resolved.max_chars:
            reasons.append("candidate_too_long")
    reasons.extend(_format_pollution(candidate))

    fact_audit = audit_fact_consistency(original, candidate) if candidate and original else {"pass": True, "missing_items": [], "missing_states": [], "details": []}
    if not fact_audit.get("pass", True):
        reasons.append("fact_drift_violation")

    unchanged = bool(candidate) and candidate == original
    status = "unchanged" if unchanged and not reasons else ("rejected" if reasons else "accepted")
    return {
        "status": status,
        "pass": not reasons,
        "blocking": bool(reasons),
        "reasons": reasons,
        "metrics": {
            "original_chars": resolved.original_chars,
            "candidate_chars": candidate_chars,
            "length_ratio": round(ratio, 4) if ratio is not None else None,
            "original_paragraphs": resolved.original_paragraphs,
            "candidate_paragraphs": _paragraph_count(candidate),
            "min_chars": resolved.min_chars,
            "max_chars": resolved.max_chars,
            "fact_ledger": {
                "missing_items": fact_audit.get("missing_items", []),
                "missing_states": fact_audit.get("missing_states", []),
                "pass": fact_audit.get("pass", True),
                "details": fact_audit.get("details", []),
            },
        },
        "contract": resolved.to_dict(),
    }


def persist_render_contract(
    contract_path: Optional[Path],
    contract: Union[RenderContract, Mapping[str, Any]],
    *,
    metadata: Optional[Mapping[str, Any]] = None,
) -> None:
    """Persist a compiled contract atomically without touching chapter prose."""

    if contract_path is None:
        return
    try:
        payload = contract.to_dict() if isinstance(contract, RenderContract) else dict(contract)
        if metadata:
            payload.update(dict(metadata))
        path = Path(contract_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(path)
    except (OSError, TypeError, ValueError):
        # Contract persistence is diagnostic; an unavailable reports folder
        # must not stop an otherwise valid generation attempt.
        return


def persist_render_candidate(
    candidate_path: Optional[Path],
    candidate_text: str,
    validation: Mapping[str, Any],
    *,
    metadata: Optional[Mapping[str, Any]] = None,
) -> None:
    """Persist a candidate and its local validation metadata when requested.

    Candidate artifacts are diagnostic and isolated from authoritative chapter
    files.  Persistence is best-effort so an unavailable reports directory
    cannot turn an otherwise recoverable rewrite into a pipeline failure.
    """

    if candidate_path is None:
        return
    try:
        path = Path(candidate_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(candidate_text or ""), encoding="utf-8")
        payload: Dict[str, Any] = {
            "accepted": bool(validation.get("pass")),
            "status": validation.get("status"),
            "candidate_sha256": text_sha256(candidate_text),
            "reasons": list(validation.get("reasons") or []),
            "metrics": dict(validation.get("metrics") or {}),
            "contract": dict(validation.get("contract") or {}),
        }
        if metadata:
            payload.update(dict(metadata))
        path.with_name(f"{path.stem}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        # Candidate persistence must never make a rewrite path fail closed.
        return


__all__ = [
    "CONTENT_LOCK_SCHEMA_VERSION",
    "RenderContract",
    "build_content_lock",
    "build_render_contract",
    "build_scene_render_contract",
    "persist_render_contract",
    "persist_render_candidate",
    "text_sha256",
    "validate_render_candidate",
]
