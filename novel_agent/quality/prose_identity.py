"""Local, explainable prose-identity calibration.

``ProseIdentityProfile`` deliberately stores aggregate signals rather than a
copy of the user's prose.  It is a diagnostic profile for rhythm and register
drift, not an author imitation model and not an automatic quality gate.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union


PROFILE_SCHEMA_VERSION = 1
PROFILE_FILENAME = "prose_identity_profile.json"
PROFILE_HISTORY_DIRNAME = "prose_identity_history"
PUNCTUATIONS = "，。！？；：、“”‘’（）——……"
_SENTENCE_SPLIT_RE = re.compile(r"[。！？!?；;]+|\n+")
_DIALOGUE_RE = re.compile(r"[“\"](.*?)[”\"]", re.DOTALL)


def _normalise_text(text: Any) -> str:
    return str(text or "").replace("\r\n", "\n").strip()


def text_sha256(text: str) -> str:
    return hashlib.sha256(_normalise_text(text).encode("utf-8")).hexdigest()


def _quantile(values: Sequence[int], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return float(ordered[lower])
    weight = position - lower
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * weight)


def _distribution(values: Sequence[int]) -> Dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "min": 0,
            "max": 0,
            "mean": 0.0,
            "p25": 0.0,
            "p50": 0.0,
            "p75": 0.0,
            "cv": 0.0,
        }
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return {
        "count": len(values),
        "min": int(min(values)),
        "max": int(max(values)),
        "mean": round(mean, 4),
        "p25": round(_quantile(values, 0.25), 4),
        "p50": round(_quantile(values, 0.50), 4),
        "p75": round(_quantile(values, 0.75), 4),
        "cv": round(math.sqrt(variance) / mean, 4) if mean else 0.0,
    }


def _sentence_lengths(text: str) -> List[int]:
    return [len(part.strip()) for part in _SENTENCE_SPLIT_RE.split(text) if part.strip()]


def _paragraph_lengths(text: str) -> List[int]:
    return [len(part.strip()) for part in re.split(r"\n+", text) if part.strip()]


def _punctuation_counts(text: str) -> Counter:
    return Counter(char for char in text if char in PUNCTUATIONS)


def _quoted_char_count(text: str) -> int:
    return sum(len(match.group(1)) for match in _DIALOGUE_RE.finditer(text))


def _coerce_sample(sample: Union[str, Mapping[str, Any]], index: int) -> Tuple[str, Dict[str, Any]]:
    if isinstance(sample, Mapping):
        text = _normalise_text(sample.get("text"))
        kind = str(sample.get("kind") or "user_sample")
        source_id = str(sample.get("id") or f"{kind}-{index + 1}")
        source_path = sample.get("path")
    else:
        text = _normalise_text(sample)
        kind = "user_sample"
        source_id = f"{kind}-{index + 1}"
        source_path = None

    source = {
        "id": source_id,
        "kind": kind,
        "sha256": text_sha256(text),
        "char_count": len(text),
    }
    if source_path:
        source["path"] = str(source_path)
    return text, source


def _profile_id(profile: Mapping[str, Any]) -> str:
    payload = dict(profile)
    payload.pop("profile_id", None)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def build_prose_identity_profile(
    samples: Sequence[Union[str, Mapping[str, Any]]],
    *,
    profile_version: int = 1,
    human_overrides: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a deterministic profile from user samples/accepted chapters.

    Sample contents are used only during local computation; the returned profile
    keeps source digests and aggregate measurements, not the original text.
    """

    sentence_values: List[int] = []
    paragraph_values: List[int] = []
    punctuation_counts: Counter = Counter()
    sources: List[Dict[str, Any]] = []
    char_count = 0
    dialogue_chars = 0

    for index, raw_sample in enumerate(samples or []):
        text, source = _coerce_sample(raw_sample, index)
        if not text:
            continue
        sources.append(source)
        char_count += len(text)
        sentence_values.extend(_sentence_lengths(text))
        paragraph_values.extend(_paragraph_lengths(text))
        punctuation_counts.update(_punctuation_counts(text))
        dialogue_chars += _quoted_char_count(text)

    punctuation_total = sum(punctuation_counts.values())
    punctuation_profile = {
        mark: round(punctuation_counts.get(mark, 0) / punctuation_total, 6) if punctuation_total else 0.0
        for mark in PUNCTUATIONS
    }
    profile: Dict[str, Any] = {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "profile_version": int(profile_version),
        "status": "calibrated" if sources else "uncalibrated",
        "policy": {"mode": "diagnostic_only", "blocking": False},
        "sources": sources,
        "sample_count": len(sources),
        "char_count": char_count,
        "sentence_count": len(sentence_values),
        "paragraph_count": len(paragraph_values),
        "rhythm": {
            "sentence_length": _distribution(sentence_values),
            "paragraph_length": _distribution(paragraph_values),
        },
        "punctuation_profile": punctuation_profile,
        "dialogue": {
            "quoted_char_ratio": round(dialogue_chars / char_count, 6) if char_count else 0.0,
            "quoted_char_count": dialogue_chars,
        },
        "human_overrides": dict(human_overrides or {}),
    }
    profile["profile_id"] = _profile_id(profile)
    return profile


def build_prose_identity_profile_from_paths(
    paths: Iterable[Path],
    *,
    kind: str = "user_sample",
    root_dir: Optional[Path] = None,
    profile_version: int = 1,
    human_overrides: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Read explicitly selected local files and build a profile."""

    samples: List[Dict[str, Any]] = []
    for path in paths:
        path = Path(path)
        text = path.read_text(encoding="utf-8")
        display_path: str
        if root_dir is not None:
            try:
                display_path = str(path.resolve().relative_to(Path(root_dir).resolve()))
            except ValueError:
                display_path = str(path)
        else:
            display_path = str(path)
        samples.append({"id": display_path, "kind": kind, "path": display_path, "text": text})
    return build_prose_identity_profile(
        samples,
        profile_version=profile_version,
        human_overrides=human_overrides,
    )


def validate_prose_identity_profile(profile: Mapping[str, Any]) -> bool:
    if not isinstance(profile, Mapping):
        return False
    if profile.get("schema_version") != PROFILE_SCHEMA_VERSION:
        return False
    if not isinstance(profile.get("sources"), list):
        return False
    rhythm = profile.get("rhythm")
    if not isinstance(rhythm, Mapping):
        return False
    return all(isinstance(rhythm.get(key), Mapping) for key in ("sentence_length", "paragraph_length"))


def prose_identity_profile_path(root_dir: Path, filename: str = PROFILE_FILENAME) -> Path:
    return Path(root_dir) / "assets" / filename


def prose_identity_profile_history_dir(
    root_dir: Path,
    *,
    path: Optional[Path] = None,
) -> Path:
    """Return the explicit, local-only directory used for profile revisions."""

    target = Path(path) if path is not None else prose_identity_profile_path(root_dir)
    if path is None or target.name == PROFILE_FILENAME:
        return Path(root_dir) / "assets" / PROFILE_HISTORY_DIRNAME
    return target.parent / f"{target.stem}_history"


def _read_profile_file(path: Path) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return dict(data) if isinstance(data, dict) and validate_prose_identity_profile(data) else None


def _history_revision(path: Path) -> int:
    match = re.match(r"revision-(\d+)-", path.name)
    return int(match.group(1)) if match else 0


def save_prose_identity_profile(
    root_dir: Path,
    profile: Mapping[str, Any],
    *,
    path: Optional[Path] = None,
    record_history: bool = True,
) -> Path:
    if not validate_prose_identity_profile(profile):
        raise ValueError("invalid prose identity profile")
    target = Path(path) if path is not None else prose_identity_profile_path(root_dir)
    history_dir = prose_identity_profile_history_dir(root_dir, path=path)
    previous = _read_profile_file(target) if target.is_file() else None
    revision = int((previous or {}).get("revision") or 0)
    if record_history and history_dir.is_dir():
        revision = max(revision, *(_history_revision(item) for item in history_dir.glob("revision-*.json")))
    revision += 1
    payload = dict(profile)
    if not payload.get("profile_id"):
        payload["profile_id"] = _profile_id(payload)
    payload["revision"] = revision
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    target.write_text(encoded, encoding="utf-8")
    if record_history:
        history_dir.mkdir(parents=True, exist_ok=True)
        snapshot = history_dir / f"revision-{revision:04d}-{payload['profile_id']}.json"
        snapshot.write_text(encoded, encoding="utf-8")
    return target


def load_prose_identity_profile(root_dir: Path, *, path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    target = Path(path) if path is not None else prose_identity_profile_path(root_dir)
    if not target.is_file():
        return None
    return _read_profile_file(target)


def list_prose_identity_profile_versions(
    root_dir: Path,
    *,
    path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """List profile revisions newest-first without returning sample text."""

    target = Path(path) if path is not None else prose_identity_profile_path(root_dir)
    history_dir = prose_identity_profile_history_dir(root_dir, path=path)
    versions: List[Dict[str, Any]] = []
    if history_dir.is_dir():
        for snapshot in history_dir.glob("revision-*.json"):
            data = _read_profile_file(snapshot)
            if not data:
                continue
            versions.append(
                {
                    "revision": int(data.get("revision") or _history_revision(snapshot)),
                    "profile_id": data.get("profile_id"),
                    "status": data.get("status"),
                    "sample_count": data.get("sample_count", 0),
                    "char_count": data.get("char_count", 0),
                    "path": str(snapshot),
                    "is_active": target.is_file() and snapshot.read_bytes() == target.read_bytes(),
                }
            )
    if not versions and target.is_file():
        data = _read_profile_file(target)
        if data:
            versions.append(
                {
                    "revision": int(data.get("revision") or 1),
                    "profile_id": data.get("profile_id"),
                    "status": data.get("status"),
                    "sample_count": data.get("sample_count", 0),
                    "char_count": data.get("char_count", 0),
                    "path": str(target),
                    "is_active": True,
                }
            )
    return sorted(versions, key=lambda item: int(item.get("revision") or 0), reverse=True)


def restore_prose_identity_profile(
    root_dir: Path,
    *,
    revision: Optional[int] = None,
    profile_id: Optional[str] = None,
    path: Optional[Path] = None,
) -> Path:
    """Restore a prior revision as a new active revision."""

    target = Path(path) if path is not None else prose_identity_profile_path(root_dir)
    versions = list_prose_identity_profile_versions(root_dir, path=path)
    selected = next(
        (
            item
            for item in versions
            if (revision is None or int(item.get("revision") or 0) == int(revision))
            and (profile_id is None or item.get("profile_id") == profile_id)
        ),
        None,
    )
    if not selected:
        raise ValueError("profile revision not found")
    restored = _read_profile_file(Path(selected["path"]))
    if not restored:
        raise ValueError("profile revision is invalid")
    restored["restored_from_revision"] = int(selected.get("revision") or 0)
    return save_prose_identity_profile(root_dir, restored, path=target, record_history=True)


def _relative_delta(actual: float, expected: float) -> float:
    return abs(actual - expected) / max(1.0, abs(expected))


def compare_prose_identity(text: str, profile: Mapping[str, Any]) -> Dict[str, Any]:
    """Compare text to a profile without turning deviation into a hard failure."""

    if not validate_prose_identity_profile(profile) or profile.get("status") != "calibrated":
        return {
            "enabled": False,
            "status": "uncalibrated",
            "pass": True,
            "blocking": False,
            "level": "none",
            "score": 100,
            "details": ["文风身份档案尚未校准"],
            "deviations": {},
        }

    current_text = _normalise_text(text)
    if not current_text:
        return {
            "enabled": True,
            "status": "empty",
            "pass": True,
            "blocking": False,
            "level": "none",
            "score": 100,
            "details": [],
            "deviations": {},
        }

    current = build_prose_identity_profile([current_text])
    expected_rhythm = profile.get("rhythm") or {}
    actual_rhythm = current.get("rhythm") or {}
    sentence_expected = expected_rhythm.get("sentence_length") or {}
    paragraph_expected = expected_rhythm.get("paragraph_length") or {}
    sentence_actual = actual_rhythm.get("sentence_length") or {}
    paragraph_actual = actual_rhythm.get("paragraph_length") or {}
    punctuation_expected = profile.get("punctuation_profile") or {}
    punctuation_actual = current.get("punctuation_profile") or {}
    punctuation_distance = sum(
        abs(float(punctuation_actual.get(mark, 0.0)) - float(punctuation_expected.get(mark, 0.0)))
        for mark in PUNCTUATIONS
    ) / 2.0
    dialogue_expected = float((profile.get("dialogue") or {}).get("quoted_char_ratio", 0.0))
    dialogue_actual = float((current.get("dialogue") or {}).get("quoted_char_ratio", 0.0))
    deviations = {
        "sentence_mean": round(_relative_delta(float(sentence_actual.get("mean", 0.0)), float(sentence_expected.get("mean", 0.0))), 4),
        "sentence_cv": round(abs(float(sentence_actual.get("cv", 0.0)) - float(sentence_expected.get("cv", 0.0))), 4),
        "paragraph_mean": round(_relative_delta(float(paragraph_actual.get("mean", 0.0)), float(paragraph_expected.get("mean", 0.0))), 4),
        "punctuation": round(punctuation_distance, 4),
        "dialogue_ratio": round(abs(dialogue_actual - dialogue_expected), 4),
    }
    penalty = (
        deviations["sentence_mean"] * 35
        + deviations["sentence_cv"] * 20
        + deviations["paragraph_mean"] * 20
        + deviations["punctuation"] * 15
        + deviations["dialogue_ratio"] * 10
    )
    score = max(0, min(100, int(round(100 - penalty))))
    if score >= 85:
        level = "none"
    elif score >= 70:
        level = "warning"
    else:
        level = "review"
    details = []
    if deviations["sentence_mean"] > 0.35:
        details.append("句长均值明显偏离参考档案")
    if deviations["sentence_cv"] > 0.25:
        details.append("句长变化度明显偏离参考档案")
    if deviations["paragraph_mean"] > 0.45:
        details.append("段落长度明显偏离参考档案")
    if deviations["punctuation"] > 0.35:
        details.append("标点分布明显偏离参考档案")
    if deviations["dialogue_ratio"] > 0.25:
        details.append("对白占比明显偏离参考档案")
    return {
        "enabled": True,
        "status": "ok" if not details else "review",
        "pass": True,
        "blocking": False,
        "level": level,
        "score": score,
        "details": details,
        "deviations": deviations,
        "profile_id": profile.get("profile_id"),
    }


__all__ = [
    "PROFILE_FILENAME",
    "PROFILE_HISTORY_DIRNAME",
    "PROFILE_SCHEMA_VERSION",
    "build_prose_identity_profile",
    "build_prose_identity_profile_from_paths",
    "compare_prose_identity",
    "load_prose_identity_profile",
    "list_prose_identity_profile_versions",
    "prose_identity_profile_path",
    "prose_identity_profile_history_dir",
    "restore_prose_identity_profile",
    "save_prose_identity_profile",
    "text_sha256",
    "validate_prose_identity_profile",
]
