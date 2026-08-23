"""Local candidate-set and human-feedback primitives.

Candidate generation remains an explicit caller decision.  This module only
normalises already-produced candidates, enforces a shared source/CONTENT_LOCK
binding and cost/TTL policy, and records human feedback for later calibration.
No model call is made here and an unavailable feedback file never blocks prose.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .render_contract import validate_render_candidate


CANDIDATE_SET_SCHEMA_VERSION = 1
CANDIDATE_TIMELINE_SCHEMA_VERSION = 1
CANDIDATE_PAIRWISE_SCHEMA_VERSION = 1
DEFAULT_MAX_CANDIDATES = 3
DEFAULT_COST_BUDGET = 3
DEFAULT_TTL_DAYS = 7
DEFAULT_TIMELINE_LIMIT = 50


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _parse_time(value: Any) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _text_sha256(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_id(prefix: str, value: Any, *, length: int = 16) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return f"{prefix}:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:length]}"


def _contract_payload(content_lock: Any) -> Dict[str, Any]:
    if hasattr(content_lock, "to_dict"):
        try:
            return dict(content_lock.to_dict())
        except (TypeError, ValueError):
            return {}
    return dict(content_lock) if isinstance(content_lock, Mapping) else {}


def content_lock_id(content_lock: Any) -> str:
    """Return the stable contract binding used by all candidates in a set."""

    payload = _contract_payload(content_lock)
    if payload.get("contract_id"):
        return str(payload["contract_id"])
    lock = payload.get("content_lock") if isinstance(payload.get("content_lock"), Mapping) else payload
    if isinstance(lock, Mapping) and lock.get("lock_digest"):
        return str(lock["lock_digest"])
    return _stable_id("lock", payload) if payload else ""


def candidate_set_path(root_dir: Path, chapter_id: str) -> Path:
    return Path(root_dir) / "workspace" / "chapters" / f"chapter_{chapter_id}" / "reports" / "candidate_set.json"


def candidate_feedback_path(root_dir: Path, chapter_id: str) -> Path:
    return Path(root_dir) / "workspace" / "chapters" / f"chapter_{chapter_id}" / "reports" / "candidate_feedback.jsonl"


def candidate_timeline_path(root_dir: Path, chapter_id: str) -> Path:
    return Path(root_dir) / "workspace" / "chapters" / f"chapter_{chapter_id}" / "reports" / "candidate_timeline.jsonl"


def candidate_pairwise_path(root_dir: Path, chapter_id: str) -> Path:
    return Path(root_dir) / "workspace" / "chapters" / f"chapter_{chapter_id}" / "reports" / "candidate_pairwise.jsonl"


def _normalise_candidate(
    candidate: Mapping[str, Any],
    *,
    chapter_id: str,
    lock_id: str,
    source_sha256: str,
    created_at: str,
) -> Dict[str, Any]:
    text = str(candidate.get("text") or candidate.get("candidate_text") or "").strip()
    candidate_id = str(candidate.get("candidate_id") or candidate.get("id") or "").strip()
    if not candidate_id:
        candidate_id = _stable_id("candidate", {"chapter_id": chapter_id, "text": text})
    try:
        cost_units = max(1, int(candidate.get("cost_units", 1)))
    except (TypeError, ValueError):
        cost_units = 1
    metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), Mapping) else {}
    return {
        "candidate_id": candidate_id,
        "chapter_id": str(chapter_id),
        "text": text,
        "text_sha256": _text_sha256(text),
        "source_sha256": str(candidate.get("source_sha256") or source_sha256),
        "content_lock_id": str(candidate.get("content_lock_id") or lock_id),
        "cost_units": cost_units,
        "status": str(candidate.get("status") or "pending"),
        "created_at": str(candidate.get("created_at") or created_at),
        "metadata": dict(metadata),
    }


def _l0_fact_requirements(content_lock: Any) -> tuple[List[str], List[str]]:
    """Read only explicitly declared literal requirements from CONTENT_LOCK.

    ``required_beats`` can be semantic prose, so it is not treated as a
    literal requirement unless the caller uses the explicit
    ``required_fragments``/``required_text`` fields.  This keeps L0
    deterministic without pretending substring checks understand meaning.
    """

    payload = _contract_payload(content_lock)
    lock = payload.get("content_lock") if isinstance(payload.get("content_lock"), Mapping) else payload
    if not isinstance(lock, Mapping):
        return [], []

    def _strings(value: Any) -> List[str]:
        if value is None:
            return []
        values = value if isinstance(value, (list, tuple, set)) else [value]
        return [str(item).strip() for item in values if item is not None and str(item).strip()]

    required = _strings(lock.get("required_fragments") or lock.get("required_text"))
    forbidden = _strings(lock.get("forbidden_fragments") or lock.get("forbidden_text"))
    return required[:24], forbidden[:24]


def _l0_validation(source_text: str, candidate_text: str, content_lock: Any) -> Dict[str, Any]:
    """Run local format/length and explicitly-declared literal checks."""

    result = validate_render_candidate(source_text, candidate_text, content_lock)
    required, forbidden = _l0_fact_requirements(content_lock)
    reasons = list(result.get("reasons") or [])
    missing = [fragment for fragment in required if fragment not in candidate_text]
    present_forbidden = [fragment for fragment in forbidden if fragment in candidate_text]
    if missing:
        reasons.append("required_fragment_missing")
    if present_forbidden:
        reasons.append("forbidden_fragment_present")
    result["required_fragments"] = required
    result["missing_required_fragments"] = missing
    result["forbidden_fragments"] = forbidden
    result["present_forbidden_fragments"] = present_forbidden
    result["reasons"] = reasons
    result["pass"] = not reasons
    result["blocking"] = bool(reasons)
    if reasons:
        result["status"] = "rejected"
    return result


def _timeline_record(payload: Mapping[str, Any], *, event: str, recorded_at: str) -> Dict[str, Any]:
    snapshot = dict(payload)
    timeline_id = _stable_id(
        "candidate-timeline",
        {
            "candidate_set_id": snapshot.get("candidate_set_id"),
            "revision": snapshot.get("revision", 1),
            "event": event,
            "recorded_at": recorded_at,
        },
    )
    return {
        "schema_version": CANDIDATE_TIMELINE_SCHEMA_VERSION,
        "timeline_id": timeline_id,
        "candidate_set_id": snapshot.get("candidate_set_id"),
        "revision": int(snapshot.get("revision") or 1),
        "event": str(event),
        "recorded_at": recorded_at,
        "snapshot": snapshot,
    }


def _append_candidate_timeline(
    root_dir: Path,
    chapter_id: str,
    payload: Mapping[str, Any],
    *,
    event: str,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    recorded_at = _iso(now or _now())
    record = _timeline_record(payload, event=event, recorded_at=recorded_at)
    path = candidate_timeline_path(root_dir, str(chapter_id))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def build_candidate_set(
    root_dir: Path,
    chapter_id: str,
    *,
    source_text: str,
    content_lock: Any = None,
    candidates: Sequence[Mapping[str, Any]] = (),
    source_revision: Optional[int] = None,
    enabled: bool = False,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
    cost_budget: int = DEFAULT_COST_BUDGET,
    ttl_days: int = DEFAULT_TTL_DAYS,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Build and persist a bounded candidate set from explicit candidates."""

    timestamp = now or _now()
    chapter = str(chapter_id)
    source_sha = _text_sha256(source_text)
    lock_id = content_lock_id(content_lock)
    try:
        max_count = max(1, min(int(max_candidates), 3))
    except (TypeError, ValueError):
        max_count = DEFAULT_MAX_CANDIDATES
    try:
        budget = max(1, int(cost_budget))
    except (TypeError, ValueError):
        budget = DEFAULT_COST_BUDGET
    try:
        ttl = max(1, min(int(ttl_days), 90))
    except (TypeError, ValueError):
        ttl = DEFAULT_TTL_DAYS

    accepted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    used_cost = 0
    created = _iso(timestamp)
    generation = len(list_candidate_timeline(root_dir, chapter, limit=200)) + 1
    for raw in candidates or []:
        if not isinstance(raw, Mapping):
            continue
        item = _normalise_candidate(
            raw,
            chapter_id=chapter,
            lock_id=lock_id,
            source_sha256=source_sha,
            created_at=created,
        )
        validation = _l0_validation(source_text, item["text"], content_lock)
        item["l0_validation"] = validation
        reason = ""
        if not item["text"]:
            reason = "empty_candidate"
        elif item["candidate_id"] in seen_ids:
            reason = "duplicate_candidate_id"
        elif item["source_sha256"] != source_sha:
            reason = "source_sha256_mismatch"
        elif item["content_lock_id"] != lock_id:
            reason = "content_lock_mismatch"
        elif not validation["pass"]:
            reason = "l0_validation_failed"
        elif len(accepted) >= max_count:
            reason = "candidate_count_budget_exceeded"
        elif used_cost + item["cost_units"] > budget:
            reason = "cost_budget_exceeded"
        if reason:
            item["rejected_reason"] = reason
            rejected.append(item)
            continue
        seen_ids.add(item["candidate_id"])
        accepted.append(item)
        used_cost += item["cost_units"]

    expires = _iso(timestamp + timedelta(days=ttl))
    try:
        source_revision_value = int(source_revision) if source_revision is not None else None
    except (TypeError, ValueError):
        source_revision_value = None
    set_payload: Dict[str, Any] = {
        "schema_version": CANDIDATE_SET_SCHEMA_VERSION,
        "candidate_set_id": _stable_id(
            "candidate-set",
            {
                "chapter_id": chapter,
                "source_sha256": source_sha,
                "content_lock_id": lock_id,
                "candidate_ids": [item["candidate_id"] for item in accepted],
                "generation": generation,
            },
        ),
        "chapter_id": chapter,
        "source_revision": source_revision_value,
        "source_sha256": source_sha,
        "content_lock_id": lock_id,
        "enabled": bool(enabled),
        "policy": {
            "mode": "manual_only" if not enabled else "explicit_candidates_only",
            "max_candidates": max_count,
            "cost_budget": budget,
            "ttl_days": ttl,
        },
        "created_at": created,
        "expires_at": expires,
        "revision": 1,
        "status": "ready" if accepted else "empty",
        "candidates": accepted,
        "rejected_candidates": rejected,
        "used_cost_units": used_cost,
        "feedback_count": 0,
    }
    save_candidate_set(root_dir, chapter, set_payload)
    _append_candidate_timeline(root_dir, chapter, set_payload, event="created", now=timestamp)
    return set_payload


def save_candidate_set(root_dir: Path, chapter_id: str, payload: Mapping[str, Any]) -> Path:
    path = candidate_set_path(root_dir, str(chapter_id))
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)
    return path


def load_candidate_set(
    root_dir: Path,
    chapter_id: str,
    *,
    now: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    path = candidate_set_path(root_dir, str(chapter_id))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, Mapping) or payload.get("schema_version") != CANDIDATE_SET_SCHEMA_VERSION:
        return None
    result = dict(payload)
    expires = _parse_time(result.get("expires_at"))
    if expires and (now or _now()) >= expires:
        result["status"] = "expired"
        result["candidates"] = [
            {**item, "status": "expired"}
            for item in result.get("candidates", [])
            if isinstance(item, Mapping)
        ]
    return result


def list_candidate_timeline(
    root_dir: Path,
    chapter_id: str,
    *,
    candidate_set_id: str = "",
    limit: int = DEFAULT_TIMELINE_LIMIT,
) -> List[Dict[str, Any]]:
    """List immutable candidate-set snapshots newest-first."""

    path = candidate_timeline_path(root_dir, str(chapter_id))
    if not path.is_file():
        return []
    try:
        max_items = max(1, min(int(limit), 200))
    except (TypeError, ValueError):
        max_items = DEFAULT_TIMELINE_LIMIT
    records: List[Dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return []
    for line in reversed(lines):
        try:
            item = json.loads(line)
        except (ValueError, json.JSONDecodeError):
            continue
        if not isinstance(item, Mapping) or item.get("schema_version") != CANDIDATE_TIMELINE_SCHEMA_VERSION:
            continue
        if candidate_set_id and str(item.get("candidate_set_id") or "") != str(candidate_set_id):
            continue
        records.append(dict(item))
        if len(records) >= max_items:
            break
    return records


def restore_candidate_set_snapshot(
    root_dir: Path,
    chapter_id: str,
    timeline_id: str,
    *,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Restore a prior candidate-set snapshot as a fresh review revision.

    This never edits the authoritative manuscript.  A restored snapshot gets
    a new set id and TTL so feedback from the superseded set cannot leak into
    the restored ranking.
    """

    records = list_candidate_timeline(root_dir, str(chapter_id), limit=200)
    selected = next((item for item in records if str(item.get("timeline_id")) == str(timeline_id)), None)
    if not selected or not isinstance(selected.get("snapshot"), Mapping):
        raise ValueError("candidate timeline snapshot not found")
    timestamp = now or _now()
    snapshot = dict(selected["snapshot"])
    expires = _parse_time(snapshot.get("expires_at"))
    if expires and timestamp >= expires:
        raise ValueError("candidate timeline snapshot has expired")
    policy = dict(snapshot.get("policy") or {})
    try:
        ttl_days = max(1, min(int(policy.get("ttl_days") or DEFAULT_TTL_DAYS), 90))
    except (TypeError, ValueError):
        ttl_days = DEFAULT_TTL_DAYS
    old_set_id = str(snapshot.get("candidate_set_id") or "")
    restored_at = _iso(timestamp)
    restored = dict(snapshot)
    restored_generation = len(list_candidate_timeline(root_dir, str(chapter_id), limit=200)) + 1
    restored["candidate_set_id"] = _stable_id(
        "candidate-set-restore",
        {
            "old_set_id": old_set_id,
            "timeline_id": str(timeline_id),
            "restored_at": restored_at,
            "generation": restored_generation,
        },
    )
    restored["revision"] = int(snapshot.get("revision") or 1) + 1
    restored["created_at"] = restored_at
    restored["expires_at"] = _iso(timestamp + timedelta(days=ttl_days))
    restored["status"] = "ready" if restored.get("candidates") else "empty"
    restored["feedback_count"] = 0
    restored["restored_from_timeline_id"] = str(timeline_id)
    restored["restored_at"] = restored_at
    save_candidate_set(root_dir, str(chapter_id), restored)
    _append_candidate_timeline(root_dir, str(chapter_id), restored, event="restored", now=timestamp)
    return restored


def _read_pairwise_sessions(root_dir: Path, chapter_id: str) -> Dict[str, Dict[str, Any]]:
    path = candidate_pairwise_path(root_dir, str(chapter_id))
    if not path.is_file():
        return {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return {}
    sessions: Dict[str, Dict[str, Any]] = {}
    for line in lines:
        try:
            item = json.loads(line)
        except (ValueError, json.JSONDecodeError):
            continue
        if not isinstance(item, Mapping) or item.get("schema_version") != CANDIDATE_PAIRWISE_SCHEMA_VERSION:
            continue
        session_id = str(item.get("session_id") or "")
        if session_id:
            sessions[session_id] = dict(item)
    return sessions


def _append_pairwise_record(root_dir: Path, chapter_id: str, record: Mapping[str, Any]) -> None:
    path = candidate_pairwise_path(root_dir, str(chapter_id))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), ensure_ascii=False) + "\n")


def _pairwise_public_session(record: Mapping[str, Any]) -> Dict[str, Any]:
    """Expose only blind labels and prose; never leak candidate IDs."""

    return {
        "schema_version": CANDIDATE_PAIRWISE_SCHEMA_VERSION,
        "session_id": record.get("session_id"),
        "candidate_set_id": record.get("candidate_set_id"),
        "created_at": record.get("created_at"),
        "expires_at": record.get("expires_at"),
        "status": record.get("status", "open"),
        "options": [
            {"label": "A", "text": record.get("candidate_a_text", "")},
            {"label": "B", "text": record.get("candidate_b_text", "")},
        ],
    }


def create_pairwise_session(
    root_dir: Path,
    chapter_id: str,
    *,
    candidate_set_id: str,
    candidate_a: str,
    candidate_b: str,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Create a one-shot blind A/B session for two L0-passing candidates."""

    payload = load_candidate_set(root_dir, str(chapter_id), now=now)
    if not payload:
        raise FileNotFoundError(f"candidate set not found for chapter {chapter_id}")
    if str(payload.get("candidate_set_id") or "") != str(candidate_set_id):
        raise ValueError("candidate set identity mismatch")
    if payload.get("status") == "expired":
        raise ValueError("candidate set has expired")
    candidates = {
        str(item.get("candidate_id")): item
        for item in payload.get("candidates", [])
        if isinstance(item, Mapping)
    }
    if candidate_a not in candidates or candidate_b not in candidates or candidate_a == candidate_b:
        raise ValueError("pairwise candidates must be two distinct candidates in the set")
    for candidate_id in (candidate_a, candidate_b):
        item = candidates[candidate_id]
        if str(item.get("status") or "") in {"rejected", "expired"}:
            raise ValueError("pairwise candidate is unavailable")
        validation = item.get("l0_validation") or {}
        if validation and validation.get("pass") is False:
            raise ValueError("pairwise candidate failed L0 validation")
    timestamp = now or _now()
    # The server-side mapping is intentionally stored separately from the
    # public A/B labels.  A cryptographic nonce keeps repeated sessions from
    # being correlated by a deterministic candidate-id hash.
    if secrets.randbelow(2):
        left_id, right_id = candidate_a, candidate_b
    else:
        left_id, right_id = candidate_b, candidate_a
    session_id = _stable_id(
        "pairwise-session",
        {"candidate_set_id": candidate_set_id, "created_at": timestamp.isoformat(), "nonce": secrets.token_hex(8)},
    )
    expires_at = payload.get("expires_at") or _iso(timestamp + timedelta(days=DEFAULT_TTL_DAYS))
    record = {
        "schema_version": CANDIDATE_PAIRWISE_SCHEMA_VERSION,
        "session_id": session_id,
        "candidate_set_id": str(candidate_set_id),
        "created_at": _iso(timestamp),
        "expires_at": expires_at,
        "status": "open",
        "candidate_a_id": left_id,
        "candidate_b_id": right_id,
        "candidate_a_text": str(candidates[left_id].get("text") or ""),
        "candidate_b_text": str(candidates[right_id].get("text") or ""),
    }
    _append_pairwise_record(root_dir, str(chapter_id), record)
    return _pairwise_public_session(record)


def submit_pairwise_session(
    root_dir: Path,
    chapter_id: str,
    session_id: str,
    *,
    choice: str,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Resolve a blind A/B choice to candidate IDs and record pairwise feedback."""

    sessions = _read_pairwise_sessions(root_dir, str(chapter_id))
    session = sessions.get(str(session_id))
    if not session:
        raise FileNotFoundError("pairwise session not found")
    if session.get("status") != "open":
        raise ValueError("pairwise session is already closed")
    payload = load_candidate_set(root_dir, str(chapter_id), now=now)
    if not payload:
        raise FileNotFoundError(f"candidate set not found for chapter {chapter_id}")
    if str(payload.get("candidate_set_id") or "") != str(session.get("candidate_set_id") or ""):
        raise ValueError("candidate set identity mismatch")
    expires = _parse_time(session.get("expires_at"))
    timestamp = now or _now()
    if expires and timestamp >= expires:
        raise ValueError("pairwise session has expired")
    normalized_choice = str(choice or "").strip().lower()
    if normalized_choice not in {"a", "b", "tie", "neither"}:
        raise ValueError("pairwise choice must be a, b, tie, or neither")
    event = record_candidate_feedback(
        root_dir,
        str(chapter_id),
        {
            "kind": "pairwise",
            "candidate_a": session.get("candidate_a_id"),
            "candidate_b": session.get("candidate_b_id"),
            "choice": normalized_choice,
            "pairwise_session_id": str(session_id),
        },
        now=timestamp,
    )
    submitted = dict(session)
    submitted.update({"status": "submitted", "choice": normalized_choice, "submitted_at": _iso(timestamp)})
    _append_pairwise_record(root_dir, str(chapter_id), submitted)
    return {
        "session_id": str(session_id),
        "status": "recorded",
        "choice": normalized_choice,
        "feedback_id": event.get("feedback_id"),
    }


def _feedback_id(payload: Mapping[str, Any]) -> str:
    return _stable_id(
        "feedback",
        {key: payload.get(key) for key in ("candidate_set_id", "kind", "candidate_a", "candidate_b", "choice", "candidate_id", "edited_text_sha256")},
    )


def record_candidate_feedback(
    root_dir: Path,
    chapter_id: str,
    feedback: Mapping[str, Any],
    *,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Append one validated human feedback event and update lightweight status."""

    payload = load_candidate_set(root_dir, chapter_id, now=now)
    if not payload:
        raise FileNotFoundError(f"candidate set not found for chapter {chapter_id}")
    if payload.get("status") == "expired":
        raise ValueError("candidate set has expired")
    candidates = [item for item in payload.get("candidates", []) if isinstance(item, Mapping)]
    candidate_ids = {str(item.get("candidate_id")) for item in candidates}
    kind = str(feedback.get("kind") or feedback.get("type") or "").strip().lower()
    if kind not in {"pairwise", "accept", "adopt", "edit", "delete", "false_positive", "reject"}:
        raise ValueError("unsupported candidate feedback kind")
    candidate_a = str(feedback.get("candidate_a") or "")
    candidate_b = str(feedback.get("candidate_b") or "")
    candidate_id = str(feedback.get("candidate_id") or "")
    choice = str(feedback.get("choice") or "").lower()
    if kind == "pairwise":
        if candidate_a not in candidate_ids or candidate_b not in candidate_ids or candidate_a == candidate_b:
            raise ValueError("pairwise candidates must be two distinct candidates in the set")
        if choice not in {"a", "b", "tie", "neither"}:
            raise ValueError("pairwise choice must be a, b, tie, or neither")
    elif candidate_id and candidate_id not in candidate_ids:
        raise ValueError("feedback candidate_id is not in the candidate set")

    event = dict(feedback)
    if kind == "edit" and event.get("edited_text") is not None:
        edited_text = str(event.get("edited_text") or "")
        event["edited_text_sha256"] = _text_sha256(edited_text)
        event["edited_text_chars"] = len(edited_text)
    event.update(
        {
            "feedback_id": _feedback_id({**payload, **event}),
            "chapter_id": str(chapter_id),
            "candidate_set_id": payload.get("candidate_set_id"),
            "content_lock_id": payload.get("content_lock_id", ""),
            "source_sha256": payload.get("source_sha256", ""),
            "recorded_at": _iso(now or _now()),
        }
    )
    path = candidate_feedback_path(root_dir, str(chapter_id))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    payload["feedback_count"] = int(payload.get("feedback_count") or 0) + 1
    if kind in {"accept", "adopt"} and candidate_id:
        for item in candidates:
            if str(item.get("candidate_id")) == candidate_id:
                item["status"] = "accepted"
    elif kind in {"delete", "reject"} and candidate_id:
        for item in candidates:
            if str(item.get("candidate_id")) == candidate_id:
                item["status"] = "rejected"
    payload["candidates"] = candidates
    payload["revision"] = int(payload.get("revision") or 1) + 1
    save_candidate_set(root_dir, str(chapter_id), payload)
    _append_candidate_timeline(root_dir, str(chapter_id), payload, event=f"feedback:{kind}", now=now)
    return event


def list_candidate_feedback(
    root_dir: Path,
    chapter_id: str,
    *,
    candidate_set_id: str = "",
) -> List[Dict[str, Any]]:
    path = candidate_feedback_path(root_dir, str(chapter_id))
    if not path.is_file():
        return []
    result: List[Dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return []
    for line in lines:
        try:
            item = json.loads(line)
        except (ValueError, json.JSONDecodeError):
            continue
        if isinstance(item, Mapping):
            if candidate_set_id and str(item.get("candidate_set_id") or "") != str(candidate_set_id):
                continue
            result.append(dict(item))
    return result


def rank_candidates(root_dir: Path, chapter_id: str) -> List[Dict[str, Any]]:
    """Rank candidates from explicit feedback; no rank is returned as calibrated."""

    payload = load_candidate_set(root_dir, str(chapter_id)) or {}
    candidates = [dict(item) for item in payload.get("candidates", []) if isinstance(item, Mapping)]
    stats = {
        str(item.get("candidate_id")): {"wins": 0, "losses": 0, "ties": 0, "accepted": 0, "edits": 0, "deletes": 0}
        for item in candidates
    }
    for event in list_candidate_feedback(
        root_dir,
        str(chapter_id),
        candidate_set_id=str(payload.get("candidate_set_id") or ""),
    ):
        kind = str(event.get("kind") or event.get("type") or "").lower()
        if kind == "pairwise":
            a, b, choice = str(event.get("candidate_a")), str(event.get("candidate_b")), str(event.get("choice"))
            if a not in stats or b not in stats:
                continue
            if choice == "a":
                stats[a]["wins"] += 1
                stats[b]["losses"] += 1
            elif choice == "b":
                stats[b]["wins"] += 1
                stats[a]["losses"] += 1
            else:
                stats[a]["ties"] += 1
                stats[b]["ties"] += 1
        else:
            candidate_id = str(event.get("candidate_id") or "")
            if candidate_id not in stats:
                continue
            if kind in {"accept", "adopt"}:
                stats[candidate_id]["accepted"] += 1
            elif kind == "edit":
                stats[candidate_id]["edits"] += 1
            elif kind in {"delete", "reject"}:
                stats[candidate_id]["deletes"] += 1
    ranked: List[Dict[str, Any]] = []
    for item in candidates:
        candidate_stats = stats[str(item.get("candidate_id"))]
        score = (
            candidate_stats["wins"] * 2
            - candidate_stats["losses"]
            + candidate_stats["accepted"] * 3
            - candidate_stats["edits"]
            - candidate_stats["deletes"] * 2
        )
        ranked.append({**item, "feedback": candidate_stats, "feedback_score": score})
    ranked.sort(key=lambda item: (-int(item["feedback_score"]), str(item.get("candidate_id"))))
    return ranked


def pairwise_calibration_summary(
    root_dir: Path,
    *,
    minimum_samples: int = 20,
    group_by: Sequence[str] = ("user_id", "project_id", "genre", "model"),
) -> Dict[str, Any]:
    """Summarise blind pairwise outcomes without producing an auto-choice.

    Ties/neither are retained but excluded from the directional win-rate
    denominator.  Wilson intervals make small samples visibly ``uncalibrated``
    instead of turning one lucky vote into a global aesthetic score.
    """

    events: list[dict[str, Any]] = []
    chapters_root = Path(root_dir) / "workspace" / "chapters"
    for path in sorted(chapters_root.glob("chapter_*/reports/candidate_feedback.jsonl")):
        chapter_id = path.parent.parent.name.removeprefix("chapter_")
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            continue
        for line in lines:
            try:
                item = json.loads(line)
            except (ValueError, json.JSONDecodeError):
                continue
            if isinstance(item, Mapping) and str(item.get("kind") or "").lower() == "pairwise":
                event = dict(item)
                event.setdefault("chapter_id", chapter_id)
                events.append(event)

    try:
        minimum = max(1, int(minimum_samples))
    except (TypeError, ValueError):
        minimum = 20

    def group_key(event: Mapping[str, Any]) -> str:
        return "|".join(f"{name}={str(event.get(name) or 'unknown')}" for name in group_by)

    grouped: dict[str, dict[str, Any]] = {}
    for event in events:
        key = group_key(event)
        bucket = grouped.setdefault(
            key,
            {
                "group": {name: str(event.get(name) or "unknown") for name in group_by},
                "samples": 0,
                "wins": 0,
                "ties": 0,
                "neither": 0,
                "candidate_outcomes": {},
            },
        )
        choice = str(event.get("choice") or "").lower()
        bucket["samples"] += 1
        if choice in {"a", "b"}:
            bucket["wins"] += 1
            winner = str(event.get("candidate_a") if choice == "a" else event.get("candidate_b") or "")
            loser = str(event.get("candidate_b") if choice == "a" else event.get("candidate_a") or "")
            outcomes = bucket["candidate_outcomes"]
            winner_stats = outcomes.setdefault(winner, {"wins": 0, "losses": 0, "ties": 0})
            loser_stats = outcomes.setdefault(loser, {"wins": 0, "losses": 0, "ties": 0})
            winner_stats["wins"] += 1
            loser_stats["losses"] += 1
        elif choice == "tie":
            bucket["ties"] += 1
            outcomes = bucket["candidate_outcomes"]
            for candidate_id in (str(event.get("candidate_a") or ""), str(event.get("candidate_b") or "")):
                if candidate_id:
                    outcomes.setdefault(candidate_id, {"wins": 0, "losses": 0, "ties": 0})["ties"] += 1
        else:
            bucket["neither"] += 1
    for bucket in grouped.values():
        # A/B labels are randomly swapped per session.  The old aggregate
        # calculation counted both ``choice=a`` and ``choice=b`` as wins,
        # which made every directional sample look like a 100% win rate.
        # Report the leader's candidate-level record instead.
        outcomes = bucket.get("candidate_outcomes") or {}
        for candidate_id, stats in outcomes.items():
            directional = int(stats["wins"]) + int(stats["losses"])
            stats["win_rate"] = round(int(stats["wins"]) / directional, 6) if directional else 0.0
        leader_id, leader_stats = (
            max(
                outcomes.items(),
                key=lambda pair: (int(pair[1]["wins"]) - int(pair[1]["losses"]), int(pair[1]["wins"]), pair[0]),
            )
            if outcomes
            else ("", {"wins": 0, "losses": 0, "ties": 0, "win_rate": 0.0})
        )
        wins = int(leader_stats["wins"])
        losses = int(leader_stats["losses"])
        directional = wins + losses
        rate = float(leader_stats.get("win_rate") or 0.0)
        z = 1.96
        denom = 1 + z * z / max(1, directional)
        centre = (rate + z * z / (2 * max(1, directional))) / denom
        margin = z * math.sqrt((rate * (1 - rate) / max(1, directional)) + z * z / (4 * max(1, directional) ** 2)) / denom
        bucket["wins"] = wins
        bucket["losses"] = losses
        bucket["win_rate"] = round(rate, 6)
        bucket["leader_candidate_id"] = leader_id or None
        bucket["confidence_interval_95"] = [round(max(0.0, centre - margin), 6), round(min(1.0, centre + margin), 6)] if directional else [0.0, 0.0]
        bucket["status"] = "calibrated" if int(bucket["samples"]) >= minimum else "uncalibrated"
        bucket["auto_choice_recommended"] = False
    return {
        "schema_version": 1,
        "status": "calibrated" if events and len(events) >= minimum else "uncalibrated",
        "sample_count": len(events),
        "minimum_samples": minimum,
        "groups": list(grouped.values()),
        "auto_choice_recommended": False,
        "reason": "保守报告模式：需要足够样本和稳定置信区间后才可由产品策略另行启用。" if events else "暂无 pairwise 样本",
    }


build_pairwise_calibration = pairwise_calibration_summary


__all__ = [
    "CANDIDATE_SET_SCHEMA_VERSION",
    "CANDIDATE_PAIRWISE_SCHEMA_VERSION",
    "CANDIDATE_TIMELINE_SCHEMA_VERSION",
    "DEFAULT_COST_BUDGET",
    "DEFAULT_MAX_CANDIDATES",
    "DEFAULT_TTL_DAYS",
    "DEFAULT_TIMELINE_LIMIT",
    "build_candidate_set",
    "build_pairwise_calibration",
    "candidate_feedback_path",
    "candidate_set_path",
    "candidate_pairwise_path",
    "candidate_timeline_path",
    "content_lock_id",
    "create_pairwise_session",
    "list_candidate_feedback",
    "list_candidate_timeline",
    "load_candidate_set",
    "rank_candidates",
    "pairwise_calibration_summary",
    "record_candidate_feedback",
    "restore_candidate_set_snapshot",
    "save_candidate_set",
    "submit_pairwise_session",
]
