"""Local golden-sample calibration and mutation-test primitives.

Calibration is deliberately explicit and local.  It never generates prose or
silently promotes a detector to a blocking gate.  With too few accepted
chapters the result is ``uncalibrated`` rather than a synthetic quality score.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from .render_contract import validate_render_candidate
from .report import build_quality_report


CALIBRATION_SCHEMA_VERSION = 1
DEFAULT_MINIMUM_SAMPLES = 20
GOLDEN_CHAPTERS_FILENAME = "golden_chapters.json"
CALIBRATION_FILENAME = "quality_calibration.json"
CALIBRATION_FEEDBACK_FILENAME = "quality_calibration_feedback.jsonl"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _sha256(value: Any) -> str:
    return hashlib.sha256(str(value or "").replace("\r\n", "\n").encode("utf-8")).hexdigest()


def golden_chapters_path(root_dir: Path) -> Path:
    return Path(root_dir) / "workspace" / "reports" / GOLDEN_CHAPTERS_FILENAME


def calibration_report_path(root_dir: Path) -> Path:
    return Path(root_dir) / "workspace" / "reports" / CALIBRATION_FILENAME


def calibration_feedback_path(root_dir: Path) -> Path:
    return Path(root_dir) / "workspace" / "reports" / CALIBRATION_FEEDBACK_FILENAME


def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)
    return path


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return None
    return dict(value) if isinstance(value, Mapping) else None


def normalise_golden_chapter(value: Mapping[str, Any], index: int = 0) -> Dict[str, Any]:
    chapter_id = str(value.get("chapter_id") or value.get("id") or f"golden-{index + 1:03d}").strip()
    text = str(value.get("text") or value.get("content") or "").replace("\r\n", "\n").strip()
    if not text:
        raise ValueError("golden chapter text must not be empty")
    expected = value.get("expected_checks") if isinstance(value.get("expected_checks"), Mapping) else {}
    return {
        "chapter_id": chapter_id,
        "text": text,
        "text_sha256": _sha256(text),
        "source": str(value.get("source") or "explicit_local_sample"),
        "accepted": bool(value.get("accepted", True)),
        "tags": [str(item) for item in (value.get("tags") or []) if str(item).strip()][:20],
        "expected_checks": dict(expected),
        "metadata": dict(value.get("metadata") or {}) if isinstance(value.get("metadata"), Mapping) else {},
    }


def save_golden_chapters(root_dir: Path, chapters: Sequence[Mapping[str, Any]]) -> Path:
    """Persist explicitly selected local golden chapters and their digests."""

    normalised: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for index, chapter in enumerate(chapters or []):
        if not isinstance(chapter, Mapping):
            continue
        item = normalise_golden_chapter(chapter, index)
        if item["chapter_id"] in seen:
            raise ValueError(f"duplicate golden chapter id: {item['chapter_id']}")
        seen.add(item["chapter_id"])
        normalised.append(item)
    payload = {
        "schema_version": CALIBRATION_SCHEMA_VERSION,
        "updated_at": _iso(_now()),
        "chapters": normalised,
        "sample_count": len(normalised),
    }
    return _write_json(golden_chapters_path(root_dir), payload)


def load_golden_chapters(root_dir: Path) -> List[Dict[str, Any]]:
    payload = _read_json(golden_chapters_path(root_dir)) or {}
    if payload.get("schema_version") != CALIBRATION_SCHEMA_VERSION:
        return []
    chapters = payload.get("chapters")
    return [dict(item) for item in chapters if isinstance(item, Mapping)] if isinstance(chapters, list) else []


def build_mutation_cases(chapter: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Build deterministic mutations with unambiguous local expectations."""

    chapter_id = str(chapter.get("chapter_id") or chapter.get("id") or "golden")
    text = str(chapter.get("text") or chapter.get("content") or "").strip()
    if not text:
        return []
    cases = [
        {
            "case_id": f"{chapter_id}:wrapper",
            "kind": "format_pollution",
            "text": f"以下是修订后的完整正文：\n{text}",
            "expected_reasons": ["editor_wrapper"],
        },
        {
            "case_id": f"{chapter_id}:markdown",
            "kind": "format_pollution",
            "text": f"# 修订稿\n{text}",
            "expected_reasons": ["markdown_heading"],
        },
        {
            "case_id": f"{chapter_id}:fence",
            "kind": "format_pollution",
            "text": f"```text\n{text}\n```",
            "expected_reasons": ["markdown_code_fence"],
        },
        {
            "case_id": f"{chapter_id}:control",
            "kind": "format_pollution",
            "text": f"{text}\x00",
            "expected_reasons": ["control_character"],
        },
    ]
    if len(text) >= 24:
        cases.append(
            {
                "case_id": f"{chapter_id}:short",
                "kind": "length_drift",
                "text": text[: max(1, len(text) // 5)],
                "expected_reasons": ["candidate_too_short"],
            }
        )
    return cases


def _feedback_counts(root_dir: Path) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    path = calibration_feedback_path(root_dir)
    if not path.is_file():
        return counts
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return counts
    for line in lines:
        try:
            item = json.loads(line)
        except (ValueError, json.JSONDecodeError):
            continue
        if isinstance(item, Mapping):
            kind = str(item.get("kind") or "unknown")
            counts[kind] = counts.get(kind, 0) + 1
    return counts


def run_quality_calibration(
    root_dir: Path,
    *,
    chapters: Optional[Sequence[Mapping[str, Any]]] = None,
    minimum_samples: int = DEFAULT_MINIMUM_SAMPLES,
    persist: bool = True,
) -> Dict[str, Any]:
    """Evaluate explicit golden chapters and mutations without model calls."""

    selected = [normalise_golden_chapter(item, index) for index, item in enumerate(chapters)] if chapters is not None else load_golden_chapters(root_dir)
    minimum = max(1, int(minimum_samples))
    chapter_results: List[Dict[str, Any]] = []
    mutation_results: List[Dict[str, Any]] = []
    errors: List[str] = []
    layer_counts: Dict[str, Dict[str, int]] = {
        "L0": {"pass": 0, "review": 0, "error": 0},
        "L1": {"pass": 0, "review": 0, "error": 0},
        "L2": {"pass": 0, "review": 0, "error": 0},
    }
    for chapter in selected:
        chapter_id = str(chapter["chapter_id"])
        try:
            report = build_quality_report(
                chapter["text"],
                root_dir=Path(root_dir),
                chapter_id=chapter_id,
                mode="report_only",
            )
            expected_results: Dict[str, Any] = {}
            for check_name, expected in (chapter.get("expected_checks") or {}).items():
                actual = (report.get("checks") or {}).get(check_name)
                expected_pass = expected if isinstance(expected, bool) else (expected.get("pass") if isinstance(expected, Mapping) else None)
                expected_results[str(check_name)] = {
                    "expected_pass": expected_pass,
                    "actual_pass": actual.get("pass") if isinstance(actual, Mapping) else None,
                    "matched": expected_pass is None or (isinstance(actual, Mapping) and actual.get("pass") is expected_pass),
                }
            layers = report.get("quality_layers") if isinstance(report.get("quality_layers"), Mapping) else {}
            for layer_name in ("L0", "L1", "L2"):
                layer = layers.get(layer_name) if isinstance(layers, Mapping) else None
                if not isinstance(layer, Mapping):
                    continue
                layer_status = str(layer.get("status") or "pass").lower()
                if layer_status not in {"pass", "review", "error"}:
                    layer_status = "review"
                layer_counts[layer_name][layer_status] += 1
            chapter_results.append(
                {
                    "chapter_id": chapter_id,
                    "text_sha256": chapter["text_sha256"],
                    "overall_pass": bool(report.get("overall_pass")),
                    "overall_score": report.get("overall_score"),
                    "expected_checks": expected_results,
                    "quality_layers": {
                        name: dict(value)
                        for name, value in layers.items()
                        if name in {"L0", "L1", "L2"} and isinstance(value, Mapping)
                    },
                    "error": None,
                }
            )
        except Exception as exc:  # calibration must surface errors, not hide them
            errors.append(f"{chapter_id}: {exc}")
            chapter_results.append({"chapter_id": chapter_id, "error": str(exc)})
        for mutation in build_mutation_cases(chapter):
            try:
                validation = validate_render_candidate(chapter["text"], mutation["text"])
                expected = list(mutation.get("expected_reasons") or [])
                detected = list(validation.get("reasons") or [])
                matched = all(reason in detected for reason in expected)
                mutation_results.append(
                    {
                        "case_id": mutation["case_id"],
                        "kind": mutation["kind"],
                        "expected_reasons": expected,
                        "detected_reasons": detected,
                        "matched": matched,
                        "layer": "L0",
                        "missed": not matched,
                    }
                )
            except Exception as exc:
                errors.append(f"{mutation['case_id']}: {exc}")
                mutation_results.append({"case_id": mutation["case_id"], "matched": False, "error": str(exc)})
    expected_matches = [item.get("matched") for item in mutation_results if "matched" in item]
    mutation_rate = round(sum(bool(item) for item in expected_matches) / len(expected_matches), 4) if expected_matches else 0.0
    feedback = _feedback_counts(root_dir)
    matched_count = sum(1 for item in mutation_results if item.get("matched") is True)
    missed_count = sum(1 for item in mutation_results if item.get("missed") is True)
    false_positive_count = int(feedback.get("false_positive", 0))
    sample_count = sum(1 for item in selected if item.get("accepted", True))
    status = "calibrated" if sample_count >= minimum and mutation_results and mutation_rate >= 0.8 and not errors else "uncalibrated"
    result: Dict[str, Any] = {
        "schema_version": CALIBRATION_SCHEMA_VERSION,
        "status": status,
        "sample_count": sample_count,
        "minimum_samples": minimum,
        "golden_count": len(selected),
        "mutation_count": len(mutation_results),
        "mutation_match_rate": mutation_rate,
        "mutation_summary": {
            "matched_count": matched_count,
            "missed_count": missed_count,
            "false_positive_count": false_positive_count,
        },
        "layer_summary": layer_counts,
        "feedback_counts": feedback,
        "errors": errors,
        "chapters": chapter_results,
        "mutations": mutation_results,
        "updated_at": _iso(_now()),
    }
    if persist:
        _write_json(calibration_report_path(root_dir), result)
    return result


def load_calibration_report(root_dir: Path) -> Dict[str, Any]:
    result = _read_json(calibration_report_path(root_dir))
    if not result or result.get("schema_version") != CALIBRATION_SCHEMA_VERSION:
        return {
            "schema_version": CALIBRATION_SCHEMA_VERSION,
            "status": "uncalibrated",
            "sample_count": 0,
            "minimum_samples": DEFAULT_MINIMUM_SAMPLES,
            "golden_count": 0,
            "mutation_count": 0,
            "mutation_match_rate": 0.0,
            "feedback_counts": {},
            "errors": [],
            "chapters": [],
            "mutations": [],
        }
    return result


def record_calibration_feedback(root_dir: Path, feedback: Mapping[str, Any]) -> Dict[str, Any]:
    kind = str(feedback.get("kind") or "").strip().lower()
    if kind not in {"false_positive", "miss", "valid", "note"}:
        raise ValueError("unsupported calibration feedback kind")
    event = dict(feedback)
    event.update(
        {
            "feedback_id": f"feedback:{_sha256(json.dumps(dict(feedback), ensure_ascii=False, sort_keys=True))[:16]}",
            "kind": kind,
            "recorded_at": _iso(_now()),
        }
    )
    path = calibration_feedback_path(root_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


__all__ = [
    "CALIBRATION_FEEDBACK_FILENAME",
    "CALIBRATION_FILENAME",
    "CALIBRATION_SCHEMA_VERSION",
    "DEFAULT_MINIMUM_SAMPLES",
    "GOLDEN_CHAPTERS_FILENAME",
    "build_mutation_cases",
    "calibration_feedback_path",
    "calibration_report_path",
    "golden_chapters_path",
    "load_calibration_report",
    "load_golden_chapters",
    "normalise_golden_chapter",
    "record_calibration_feedback",
    "run_quality_calibration",
    "save_golden_chapters",
]
