"""Quality calibration, voice-lab and evidence review APIs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Response

from novel_agent.quality.calibration import (
    load_calibration_report,
    record_calibration_feedback,
    run_quality_calibration,
    save_golden_chapters,
)
from novel_agent.quality.candidate_set import (
    pairwise_calibration_summary,
    list_candidate_feedback,
    list_candidate_timeline,
    load_candidate_set,
    rank_candidates,
)
from novel_agent.quality.candidate_policy import evaluate_candidate_policy
from novel_agent.services.manuscript_workspace import build_manuscript_workspace, text_sha256
from novel_agent.quality.metrics import build_quality_metrics, metrics_csv, save_quality_baseline
from novel_agent.quality.voice_lab import build_voice_lab, record_voice_feedback, set_voice_lab_frozen
from novel_agent.quality.decision import derive_quality_decision
from novel_agent.services.quality_review import quality_issues_from_report
from web.deps import ProjectSession, RequireProjectDep, coerce_project_session, touch_project_activity
from web.helpers import _validate_id


router = APIRouter()


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return {}
    return dict(value) if isinstance(value, dict) else {}


def _evidence_chain(reports: Path, quality: Dict[str, Any], audit: Dict[str, Any], gate: Dict[str, Any]) -> list[Dict[str, Any]]:
    """Flatten report-local evidence while preserving source/span references."""

    evidence: list[Dict[str, Any]] = []
    checks = quality.get("checks") if isinstance(quality.get("checks"), dict) else {}
    for check_name, check in checks.items():
        if not isinstance(check, dict):
            continue
        findings = check.get("findings") if isinstance(check.get("findings"), list) else []
        for index, finding in enumerate(findings[:30]):
            if isinstance(finding, dict):
                evidence.append({
                    "layer": "L1",
                    "kind": "quality_finding",
                    "check": str(check_name),
                    "index": index,
                    "span": finding.get("span") or finding.get("source_span"),
                    "source": finding.get("source") or finding.get("source_ref") or finding.get("chapter_id"),
                    "summary": finding.get("message") or finding.get("reason") or finding.get("type") or str(finding),
                })
        details = check.get("details")
        if isinstance(details, str):
            details = [details]
        if isinstance(details, list):
            for index, detail in enumerate(details[:30]):
                if detail in (None, ""):
                    continue
                item = dict(detail) if isinstance(detail, dict) else {"summary": str(detail)}
                evidence.append({
                    "layer": "L1",
                    "kind": "quality_detail",
                    "check": str(check_name),
                    "index": index,
                    "span": item.get("span") or item.get("source_span"),
                    "source": item.get("source") or item.get("source_ref"),
                    "summary": item.get("message") or item.get("reason") or item.get("summary") or str(item),
                })
    issues = audit.get("issues") if isinstance(audit.get("issues"), list) else []
    for index, issue in enumerate(issues[:30]):
        item = dict(issue) if isinstance(issue, dict) else {"summary": str(issue)}
        evidence.append({
            "layer": "L2",
            "kind": "audit_issue",
            "index": index,
            "span": item.get("span") or item.get("source_span"),
            "source": item.get("source") or item.get("source_ref"),
            "summary": item.get("message") or item.get("reason") or item.get("rule_id") or str(item),
        })
    for name, check in (gate.get("checks") or {}).items() if isinstance(gate.get("checks"), dict) else []:
        if isinstance(check, dict) and check.get("pass") is False:
            evidence.append({"layer": "L0", "kind": "gate_failure", "check": str(name), "summary": check.get("reason") or "统一门禁未通过"})
    gate_quality = gate.get("quality") if isinstance(gate.get("quality"), dict) else {}
    for name in gate_quality.get("blocked_by") or []:
        evidence.append({
            "layer": "L0",
            "kind": "gate_failure",
            "check": str(name),
            "summary": f"统一门禁未通过：{name}",
        })
    for contract_path in sorted(reports.glob("*_render_contract.json"))[:20]:
        contract = _read_json(contract_path)
        lock = contract.get("content_lock") if isinstance(contract.get("content_lock"), dict) else {}
        if lock:
            evidence.append({
                "layer": "L0",
                "kind": "content_lock",
                "path": str(contract_path.name),
                "contract_id": contract.get("contract_id"),
                "lock_digest": lock.get("lock_digest"),
                "scene_id": lock.get("scene_id"),
                "required_beats": lock.get("required_beats") or [],
            })
    return evidence


@router.get("/api/quality/voice-lab")
def get_voice_lab(session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    session = coerce_project_session(session)
    return build_voice_lab(session.root_dir)


@router.post("/api/quality/voice-lab/freeze")
def freeze_voice_lab(body: Dict[str, Any], session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    session = coerce_project_session(session)
    if "frozen" not in body:
        raise HTTPException(422, "frozen is required")
    state = set_voice_lab_frozen(
        session.root_dir,
        frozen=bool(body.get("frozen")),
        reason=str(body.get("reason") or ""),
    )
    touch_project_activity(session)
    return {"status": "updated", "state": state, "voice_lab": build_voice_lab(session.root_dir)}


@router.post("/api/quality/voice-lab/feedback")
def post_voice_feedback(body: Dict[str, Any], session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    session = coerce_project_session(session)
    try:
        event = record_voice_feedback(session.root_dir, body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    touch_project_activity(session)
    return {"status": "recorded", "event": event, "voice_lab": build_voice_lab(session.root_dir)}


@router.get("/api/quality/calibration")
def get_quality_calibration(session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    session = coerce_project_session(session)
    return load_calibration_report(session.root_dir)


@router.post("/api/quality/calibration/golden")
def save_quality_golden(body: Dict[str, Any], session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    session = coerce_project_session(session)
    chapters = body.get("chapters")
    if not isinstance(chapters, list):
        raise HTTPException(422, "chapters must be a list of explicit local samples")
    try:
        path = save_golden_chapters(session.root_dir, chapters)
        report = run_quality_calibration(
            session.root_dir,
            minimum_samples=int(body.get("minimum_samples") or 20),
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    touch_project_activity(session)
    return {"status": "saved", "path": str(path), "calibration": report}


@router.post("/api/quality/calibration/run")
def run_quality_calibration_api(session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    session = coerce_project_session(session)
    return run_quality_calibration(session.root_dir)


@router.post("/api/quality/calibration/feedback")
def post_calibration_feedback(body: Dict[str, Any], session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    session = coerce_project_session(session)
    try:
        event = record_calibration_feedback(session.root_dir, body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    touch_project_activity(session)
    return {"status": "recorded", "event": event, "calibration": load_calibration_report(session.root_dir)}


@router.get("/api/quality/metrics")
def get_quality_metrics(
    minimum_samples: int = Query(default=20, ge=1, le=1000),
    chapter_id: str = Query(default=""),
    since: str = Query(default=""),
    until: str = Query(default=""),
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    session = coerce_project_session(session)
    if chapter_id:
        _validate_id(chapter_id, "chapter_id")
    return build_quality_metrics(
        session.root_dir,
        minimum_samples=minimum_samples,
        chapter_id=chapter_id,
        since=since or None,
        until=until or None,
    )


@router.get("/api/quality/candidates/calibration")
def get_candidate_calibration(
    minimum_samples: int = Query(default=20, ge=1, le=1000),
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    session = coerce_project_session(session)
    return pairwise_calibration_summary(session.root_dir, minimum_samples=minimum_samples)


@router.post("/api/quality/metrics/baseline")
def create_quality_baseline(
    body: Dict[str, Any],
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    session = coerce_project_session(session)
    try:
        minimum_samples = int(body.get("minimum_samples") or 20)
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, "minimum_samples must be an integer") from exc
    if minimum_samples < 1 or minimum_samples > 1000:
        raise HTTPException(422, "minimum_samples must be between 1 and 1000")
    payload = save_quality_baseline(session.root_dir, minimum_samples=minimum_samples)
    touch_project_activity(session)
    return payload


@router.get("/api/quality/metrics/export")
def export_quality_metrics(
    format: str = Query(default="json", pattern=r"^(json|csv)$"),
    chapter_id: str = Query(default=""),
    since: str = Query(default=""),
    until: str = Query(default=""),
    session: ProjectSession = RequireProjectDep,
) -> Response:
    session = coerce_project_session(session)
    if chapter_id:
        _validate_id(chapter_id, "chapter_id")
    payload = build_quality_metrics(
        session.root_dir,
        chapter_id=chapter_id,
        since=since or None,
        until=until or None,
    )
    if format == "csv":
        return Response(content=metrics_csv(payload), media_type="text/csv; charset=utf-8")
    return Response(content=json.dumps(payload, ensure_ascii=False, indent=2), media_type="application/json")


@router.get("/api/quality/review")
def get_quality_review(
    chapter_id: str = Query(default=""),
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    """Aggregate report evidence, candidates and rollback timeline for review UI."""

    session = coerce_project_session(session)
    root = Path(session.root_dir)
    if chapter_id:
        safe_id = _validate_id(chapter_id, "chapter_id")
        reports = root / "workspace" / "chapters" / f"chapter_{safe_id}" / "reports"
        quality = _read_json(reports / "quality.json")
        audit = _read_json(reports / "audit.json")
        gate = _read_json(reports / "unified_gate.json")
        quality_for_review = dict(quality)
        quality_audit = quality_for_review.get("audit")
        quality_audit = quality_audit if isinstance(quality_audit, dict) else {}
        if isinstance(audit.get("issues"), list) and not isinstance(
            quality_audit.get("issues"), list
        ):
            quality_for_review["audit"] = {
                **quality_audit,
                "issues": audit["issues"],
                "status": quality_audit.get("status") or audit.get("status") or "ok",
            }
        candidate_set = load_candidate_set(root, safe_id)
        document_payload: Dict[str, Any] = {}
        try:
            document = build_manuscript_workspace(root, chapter_id=safe_id).document
            if document is not None:
                document_payload = {
                    "revision": int(document.revision),
                    "sha256": text_sha256(document.plain_text),
                    "char_count": len(document.plain_text),
                }
        except Exception:
            document_payload = {}
        return {
            "chapter_id": safe_id,
            "quality_decision": derive_quality_decision(quality_for_review),
            "issues": quality_issues_from_report(quality_for_review),
            "levels": {
                "l0": (quality.get("quality_layers", {}).get("L0") or gate.get("guard_summary") or {}) if isinstance(quality, dict) else {},
                "l1": (quality.get("quality_layers", {}).get("L1") or quality) if isinstance(quality, dict) else {},
                "l2": (quality.get("quality_layers", {}).get("L2") or audit) if isinstance(quality, dict) else audit,
            },
            "quality": quality,
            "audit": audit,
            "unified_gate": gate,
            "document": document_payload,
            "evidence": _evidence_chain(reports, quality, audit, gate),
            "candidate_set": candidate_set,
            "ranked_candidates": rank_candidates(root, safe_id),
            "feedback": list_candidate_feedback(root, safe_id, candidate_set_id=str((candidate_set or {}).get("candidate_set_id") or "")),
            "timeline": list_candidate_timeline(root, safe_id),
            "candidate_policy": evaluate_candidate_policy(
                safe_id,
                chapter_index=int(safe_id) if safe_id.isdigit() else None,
                quality_report=quality,
                recent_metrics=build_quality_metrics(root, chapter_id=safe_id),
            ),
        }
    metrics = build_quality_metrics(root)
    return {"status": metrics.get("status", "uncalibrated"), "metrics": metrics}


__all__ = ["router"]
