"""Local voice-lab view model built from prose profile evidence and reports."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping

from .prose_identity import list_prose_identity_profile_versions, load_prose_identity_profile


VOICE_LAB_SCHEMA_VERSION = 1
VOICE_LAB_STATE_FILENAME = "voice_lab_state.json"
VOICE_LAB_FEEDBACK_FILENAME = "voice_lab_feedback.jsonl"


def voice_lab_state_path(root_dir: Path) -> Path:
    return Path(root_dir) / "workspace" / "reports" / VOICE_LAB_STATE_FILENAME


def voice_lab_feedback_path(root_dir: Path) -> Path:
    return Path(root_dir) / "workspace" / "reports" / VOICE_LAB_FEEDBACK_FILENAME


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return {}
    return dict(value) if isinstance(value, Mapping) else {}


def _profile_evidence(root_dir: Path, profile: Mapping[str, Any]) -> List[Dict[str, Any]]:
    evidence: List[Dict[str, Any]] = []
    root = Path(root_dir).resolve()
    for source in profile.get("sources", []) if isinstance(profile.get("sources"), list) else []:
        if not isinstance(source, Mapping):
            continue
        item = {
            "id": source.get("id"),
            "kind": source.get("kind"),
            "sha256": source.get("sha256"),
            "char_count": source.get("char_count", 0),
        }
        raw_path = source.get("path")
        if raw_path:
            path = Path(str(raw_path))
            if not path.is_absolute():
                path = root / path
            try:
                resolved = path.resolve()
                resolved.relative_to(root)
            except (OSError, ValueError):
                resolved = None
            if resolved and resolved.is_file():
                try:
                    text = resolved.read_text(encoding="utf-8").strip()
                    item["path"] = str(resolved.relative_to(root))
                    item["preview"] = text[:180]
                    item["preview_truncated"] = len(text) > 180
                except (OSError, UnicodeError):
                    pass
        evidence.append(item)
    return evidence[:50]


def _drift_trend(root_dir: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    chapters_root = Path(root_dir) / "workspace" / "chapters"
    if not chapters_root.is_dir():
        return rows
    for report_path in sorted(chapters_root.glob("chapter_*/reports/quality.json")):
        report = _read_json(report_path)
        check = report.get("checks", {}).get("prose_identity") if isinstance(report.get("checks"), Mapping) else None
        if not isinstance(check, Mapping):
            continue
        rows.append(
            {
                "chapter_id": report_path.parent.parent.name.removeprefix("chapter_"),
                "status": check.get("status", "unknown"),
                "score": check.get("score"),
                "deviations": dict(check.get("deviations") or {}) if isinstance(check.get("deviations"), Mapping) else {},
            }
        )
    return rows


def _feedback(root_dir: Path) -> List[Dict[str, Any]]:
    path = voice_lab_feedback_path(root_dir)
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return []
    result: List[Dict[str, Any]] = []
    for line in lines:
        try:
            item = json.loads(line)
        except (ValueError, json.JSONDecodeError):
            continue
        if isinstance(item, Mapping):
            result.append(dict(item))
    return result[-100:]


def build_voice_lab(root_dir: Path) -> Dict[str, Any]:
    root = Path(root_dir)
    profile = load_prose_identity_profile(root)
    state = _read_json(voice_lab_state_path(root))
    feedback = _feedback(root)
    profile_data = profile or {"status": "uncalibrated", "sample_count": 0, "sources": []}
    return {
        "schema_version": VOICE_LAB_SCHEMA_VERSION,
        "status": "calibrated" if profile_data.get("status") == "calibrated" else "uncalibrated",
        "frozen": bool(state.get("frozen", False)),
        "freeze_reason": state.get("reason", ""),
        "state_revision": int(state.get("revision") or 0),
        "profile": profile_data,
        "versions": list_prose_identity_profile_versions(root),
        "evidence": _profile_evidence(root, profile_data),
        "drift_trend": _drift_trend(root),
        "feedback": feedback,
        "feedback_count": len(feedback),
    }


def is_voice_lab_frozen(root_dir: Path) -> bool:
    return bool(_read_json(voice_lab_state_path(root_dir)).get("frozen", False))


def set_voice_lab_frozen(root_dir: Path, *, frozen: bool, reason: str = "") -> Dict[str, Any]:
    current = _read_json(voice_lab_state_path(root_dir))
    payload = {
        "schema_version": VOICE_LAB_SCHEMA_VERSION,
        "frozen": bool(frozen),
        "reason": str(reason or "")[:240],
        "revision": int(current.get("revision") or 0) + 1,
        "updated_at": _iso_now(),
    }
    path = voice_lab_state_path(root_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def record_voice_feedback(root_dir: Path, feedback: Mapping[str, Any]) -> Dict[str, Any]:
    kind = str(feedback.get("kind") or "").strip().lower()
    if kind not in {"false_positive", "valid", "drift", "note"}:
        raise ValueError("unsupported voice feedback kind")
    raw = json.dumps(dict(feedback), ensure_ascii=False, sort_keys=True)
    event = dict(feedback)
    event.update(
        {
            "feedback_id": f"voice-feedback:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}",
            "kind": kind,
            "recorded_at": _iso_now(),
        }
    )
    path = voice_lab_feedback_path(root_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


__all__ = [
    "VOICE_LAB_FEEDBACK_FILENAME",
    "VOICE_LAB_SCHEMA_VERSION",
    "VOICE_LAB_STATE_FILENAME",
    "build_voice_lab",
    "is_voice_lab_frozen",
    "record_voice_feedback",
    "set_voice_lab_frozen",
    "voice_lab_feedback_path",
    "voice_lab_state_path",
]
