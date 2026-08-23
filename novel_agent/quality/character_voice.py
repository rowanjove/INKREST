"""Explainable, local-only character voice profiles.

Profiles describe a character's observable dialogue habits.  They are not
author imitation labels and are diagnostic/contextual hints rather than a hard
quality gate.  The module accepts explicitly selected dialogue samples so the
system never silently harvests arbitrary user documents.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union


CHARACTER_VOICE_SCHEMA_VERSION = 1
CHARACTER_VOICE_FILENAME = "character_voice_profiles.json"
_SENTENCE_SPLIT_RE = re.compile(r"[。！？!?；;]+|\n+")
_DIALOGUE_RE = re.compile(r"[“\"](.*?)[”\"]", re.DOTALL)
_FILLER_WORDS = ("嗯", "啊", "哎", "吧", "呢", "呃", "啧", "呵")


def _normalise_text(value: Any) -> str:
    return str(value or "").replace("\r\n", "\n").strip()


def _sha256(text: str) -> str:
    return hashlib.sha256(_normalise_text(text).encode("utf-8")).hexdigest()


def _distribution(values: Sequence[int]) -> Dict[str, Any]:
    if not values:
        return {"count": 0, "mean": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0, "cv": 0.0}
    ordered = sorted(values)
    mean = sum(values) / len(values)

    def quantile(fraction: float) -> float:
        index = (len(ordered) - 1) * fraction
        lower, upper = math.floor(index), math.ceil(index)
        if lower == upper:
            return float(ordered[lower])
        weight = index - lower
        return ordered[lower] + (ordered[upper] - ordered[lower]) * weight

    variance = sum((item - mean) ** 2 for item in values) / len(values)
    return {
        "count": len(values),
        "mean": round(mean, 4),
        "p25": round(quantile(0.25), 4),
        "p50": round(quantile(0.50), 4),
        "p75": round(quantile(0.75), 4),
        "cv": round(math.sqrt(variance) / mean, 4) if mean else 0.0,
    }


def _coerce_samples(samples: Sequence[Union[str, Mapping[str, Any]]]) -> tuple[List[str], List[Dict[str, Any]]]:
    texts: List[str] = []
    sources: List[Dict[str, Any]] = []
    for index, sample in enumerate(samples or []):
        if isinstance(sample, Mapping):
            text = _normalise_text(sample.get("text"))
            source_id = str(sample.get("id") or f"dialogue-{index + 1}")
            kind = str(sample.get("kind") or "accepted_dialogue")
            source_path = sample.get("path")
        else:
            text = _normalise_text(sample)
            source_id = f"dialogue-{index + 1}"
            kind = "accepted_dialogue"
            source_path = None
        if not text:
            continue
        source = {"id": source_id, "kind": kind, "sha256": _sha256(text), "char_count": len(text)}
        if source_path:
            source["path"] = str(source_path)
        texts.append(text)
        sources.append(source)
    return texts, sources


def _profile_id(profile: Mapping[str, Any]) -> str:
    payload = dict(profile)
    payload.pop("profile_id", None)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def build_character_voice_profile(
    character_id: str,
    samples: Sequence[Union[str, Mapping[str, Any]]],
    *,
    name: str = "",
    profile_version: int = 1,
    human_overrides: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    texts, sources = _coerce_samples(samples)
    utterances: List[str] = []
    for text in texts:
        utterances.extend(part.strip() for part in _SENTENCE_SPLIT_RE.split(text) if part.strip())
    if not utterances:
        utterances = texts[:]
    punctuation = Counter(char for text in texts for char in text if char in "，。！？；：……")
    punctuation_total = sum(punctuation.values()) or 1
    filler_counts = Counter(word for text in texts for word in _FILLER_WORDS if word in text)
    first_tokens = Counter(utterance[:2] for utterance in utterances if len(utterance) >= 2)
    char_count = sum(len(text) for text in texts)
    profile: Dict[str, Any] = {
        "schema_version": CHARACTER_VOICE_SCHEMA_VERSION,
        "profile_version": int(profile_version),
        "status": "calibrated" if sources else "uncalibrated",
        "policy": {"mode": "diagnostic_only", "blocking": False},
        "character_id": str(character_id),
        "name": str(name or character_id),
        "sources": sources,
        "sample_count": len(sources),
        "char_count": char_count,
        "utterance_count": len(utterances),
        "rhythm": {"utterance_length": _distribution([len(item) for item in utterances])},
        "punctuation_profile": {
            mark: round(punctuation.get(mark, 0) / punctuation_total, 6)
            for mark in "，。！？；：……"
        },
        "speech_markers": {
            "filler_counts": dict(filler_counts),
            "question_rate": round(sum(text.count("？") + text.count("?") for text in texts) / max(1, len(utterances)), 4),
            "exclamation_rate": round(sum(text.count("！") + text.count("!") for text in texts) / max(1, len(utterances)), 4),
            "common_openings": [item for item, _ in first_tokens.most_common(8)],
        },
        "human_overrides": dict(human_overrides or {}),
    }
    profile["profile_id"] = _profile_id(profile)
    return profile


def validate_character_voice_profile(profile: Mapping[str, Any]) -> bool:
    return bool(
        isinstance(profile, Mapping)
        and profile.get("schema_version") == CHARACTER_VOICE_SCHEMA_VERSION
        and profile.get("character_id")
        and isinstance(profile.get("sources"), list)
        and isinstance(profile.get("rhythm"), Mapping)
    )


def build_character_voice_profiles(
    samples_by_character: Mapping[str, Sequence[Union[str, Mapping[str, Any]]]],
    *,
    names: Optional[Mapping[str, str]] = None,
) -> Dict[str, Dict[str, Any]]:
    return {
        str(character_id): build_character_voice_profile(
            str(character_id),
            samples,
            name=(names or {}).get(str(character_id), str(character_id)),
        )
        for character_id, samples in samples_by_character.items()
    }


def character_voice_profiles_path(root_dir: Path) -> Path:
    return Path(root_dir) / "assets" / CHARACTER_VOICE_FILENAME


def save_character_voice_profiles(root_dir: Path, profiles: Mapping[str, Mapping[str, Any]]) -> Path:
    valid = {
        str(key): dict(value)
        for key, value in profiles.items()
        if validate_character_voice_profile(value)
    }
    target = character_voice_profiles_path(root_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"schema_version": CHARACTER_VOICE_SCHEMA_VERSION, "profiles": valid}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def load_character_voice_profiles(root_dir: Path) -> Dict[str, Dict[str, Any]]:
    path = character_voice_profiles_path(root_dir)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    profiles = payload.get("profiles") if isinstance(payload, Mapping) else None
    if not isinstance(profiles, Mapping):
        return {}
    return {
        str(key): dict(value)
        for key, value in profiles.items()
        if isinstance(value, Mapping) and validate_character_voice_profile(value)
    }


def compare_character_voice(text: str, profile: Mapping[str, Any]) -> Dict[str, Any]:
    """Compare a dialogue sample to a profile without blocking generation."""

    if not validate_character_voice_profile(profile) or profile.get("status") != "calibrated":
        return {"enabled": False, "status": "uncalibrated", "pass": True, "blocking": False, "score": 100, "deviations": {}}
    utterances = [part.strip() for part in _SENTENCE_SPLIT_RE.split(_normalise_text(text)) if part.strip()]
    actual = _distribution([len(item) for item in utterances])
    expected = ((profile.get("rhythm") or {}).get("utterance_length") or {})
    mean_delta = abs(float(actual.get("mean", 0)) - float(expected.get("mean", 0))) / max(1.0, float(expected.get("mean", 0)))
    question_actual = sum(text.count("？") + text.count("?") for _ in [0]) / max(1, len(utterances))
    question_expected = float((profile.get("speech_markers") or {}).get("question_rate", 0.0))
    deviations = {"utterance_mean": round(mean_delta, 4), "question_rate": round(abs(question_actual - question_expected), 4)}
    score = max(0, min(100, int(round(100 - mean_delta * 70 - deviations["question_rate"] * 20))))
    return {
        "enabled": True,
        "status": "ok" if score >= 70 else "review",
        "pass": True,
        "blocking": False,
        "score": score,
        "level": "none" if score >= 85 else "warning" if score >= 70 else "review",
        "deviations": deviations,
        "profile_id": profile.get("profile_id"),
    }


def build_character_voice_context(root_dir: Path, character_ids: Iterable[str]) -> str:
    profiles = load_character_voice_profiles(root_dir)
    lines: List[str] = []
    for character_id in character_ids:
        profile = profiles.get(str(character_id))
        if not profile:
            continue
        markers = profile.get("speech_markers") or {}
        rhythm = ((profile.get("rhythm") or {}).get("utterance_length") or {})
        overrides = profile.get("human_overrides") or {}
        lines.append(
            f"- {profile.get('name', character_id)}（{character_id}）："
            f"常见句长中位数 {rhythm.get('p50', 0)} 字；"
            f"疑问倾向 {markers.get('question_rate', 0)}；"
            f"常见开头 {', '.join(markers.get('common_openings') or []) or '未校准'}。"
        )
        for key in ("speech_style", "must_not", "lexicon_notes"):
            values = overrides.get(key)
            if values:
                lines.append(f"  - {key}: {', '.join(map(str, values)) if isinstance(values, list) else values}")
    return "\n".join(lines)


def extract_dialogue_samples(text: str, character_names: Iterable[str]) -> Dict[str, List[str]]:
    """Extract only explicit ``角色说：“...”`` style samples."""

    result: Dict[str, List[str]] = {str(name): [] for name in character_names if str(name).strip()}
    for name in result:
        pattern = re.compile(rf"{re.escape(name)}[^。！？\n]{{0,8}}[：:]\s*[“\"]([^”\"]+)[”\"]")
        result[name].extend(match.group(1).strip() for match in pattern.finditer(text or ""))
    return result


__all__ = [
    "CHARACTER_VOICE_FILENAME",
    "CHARACTER_VOICE_SCHEMA_VERSION",
    "build_character_voice_context",
    "build_character_voice_profile",
    "build_character_voice_profiles",
    "character_voice_profiles_path",
    "compare_character_voice",
    "extract_dialogue_samples",
    "load_character_voice_profiles",
    "save_character_voice_profiles",
    "validate_character_voice_profile",
]
