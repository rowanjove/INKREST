"""FastAPI router for Human Writing Engine (HWE)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from novel_agent.human_writing.context_compiler import compile_human_writing_prompt
from novel_agent.human_writing.editor.patch_planner import create_patch_plan
from novel_agent.human_writing.editor.patch_runner import run_patch
from novel_agent.human_writing.engine import HumanWritingEngine
from novel_agent.human_writing.memory import (
    analyze_dialogue_voice_drift,
    analyze_sliding_windows,
    detect_chapter_ending_fingerprint_repetition,
    extract_expression_entries_v2,
)
from novel_agent.human_writing.protected_spans import extract_protected_spans
from novel_agent.human_writing.rules.registry import get_rule_registry
from novel_agent.human_writing.schemas import HWEIssue, HWEPatchCandidate, HWEReport, PatchPlanItem
from novel_agent.human_writing.semantic_reviewer import HWESemanticReviewer
from novel_agent.human_writing.preferences import HWEPreferenceManager
from novel_agent.human_writing.eval import HWEEvalRunner, EvalReport
from novel_agent.services.manuscript_workspace import (
    apply_plain_text_to_manuscript,
    read_chapter_plain_text,
    sync_chapter_manuscript_document,
)
from novel_agent.state.sqlite_store import SQLiteStateStore
from web.deps import ProjectSession, RequireProjectDep, get_project_session
from web.helpers import _validate_id

router = APIRouter()
_engine = HumanWritingEngine()
_semantic_reviewer = HWESemanticReviewer()
_latest_eval_report: Optional[EvalReport] = None


class HWEScanRequest(BaseModel):
    text: Optional[str] = Field(default=None, description="Prose text to scan. If omitted, chapter_id will be read from project.")
    chapter_id: Optional[str] = Field(default=None, description="Target chapter ID if applicable")
    revision_id: Optional[str] = Field(default=None, description="Document revision ID if applicable")
    mode: str = Field(default="assist", description="Scan mode: assist, guided, auto")


@router.post("/scan", response_model=HWEReport)
def scan_text(
    payload: HWEScanRequest,
    session: ProjectSession = Depends(get_project_session),
) -> HWEReport:
    """Scan provided text or chapter text for prose slop and template patterns."""
    text_to_scan = payload.text
    if text_to_scan is None:
        if not payload.chapter_id:
            raise HTTPException(status_code=400, detail="必须提供 text 或 chapter_id")
        _validate_id(payload.chapter_id, "chapter_id")
        if not session.has_project:
            raise HTTPException(status_code=400, detail="未选择活跃项目，无法读取章节正文")
        text_to_scan = read_chapter_plain_text(session.root_dir, payload.chapter_id)

    preferences = None
    if session.has_project:
        try:
            store = SQLiteStateStore(session.root_dir)
            preferences = HWEPreferenceManager(store=store, project_id=session.project_id)
        except Exception:
            preferences = None

    report = _engine.scan_text(
        text=text_to_scan,
        chapter_id=payload.chapter_id,
        revision_id=payload.revision_id,
        mode=payload.mode,
        preferences=preferences,
    )
    if session.has_project and payload.chapter_id:
        try:
            store = SQLiteStateStore(session.root_dir)
            store.save_hwe_report(report, chapter_id=payload.chapter_id, document_revision_id=payload.revision_id)
        except Exception:
            pass
    return report


@router.post("/scan/chapter/{chapter_id}", response_model=HWEReport)
def scan_chapter(
    chapter_id: str,
    mode: str = Query(default="assist"),
    session: ProjectSession = RequireProjectDep,
) -> HWEReport:
    """Convenience endpoint to scan an entire chapter manuscript."""
    _validate_id(chapter_id, "chapter_id")
    text = read_chapter_plain_text(session.root_dir, chapter_id)
    if not text:
        raise HTTPException(status_code=404, detail=f"章节 {chapter_id} 暂无正文或内容为空")

    preferences = None
    try:
        store = SQLiteStateStore(session.root_dir)
        preferences = HWEPreferenceManager(store=store, project_id=session.project_id)
    except Exception:
        preferences = None

    report = _engine.scan_text(
        text=text,
        chapter_id=chapter_id,
        mode=mode,
        preferences=preferences,
    )
    try:
        store = SQLiteStateStore(session.root_dir)
        store.save_hwe_report(report, chapter_id=chapter_id)
    except Exception:
        pass
    return report


@router.get("/rules")
def list_rules(
    family: Optional[str] = Query(default=None, description="Filter by rule family"),
    enabled_only: bool = Query(default=True),
) -> Dict[str, Any]:
    """List active HWE rules and metadata."""
    registry = get_rule_registry()
    rules = registry.list_rules(family=family, enabled_only=enabled_only)
    return {
        "ruleset_version": registry.ruleset_version,
        "count": len(rules),
        "rules": [r.model_dump() for r in rules],
    }


@router.get("/reports/{chapter_id}", response_model=HWEReport)
def get_chapter_report(
    chapter_id: str,
    session: ProjectSession = RequireProjectDep,
) -> HWEReport:
    """Get scan report for a specific chapter."""
    _validate_id(chapter_id, "chapter_id")
    text = read_chapter_plain_text(session.root_dir, chapter_id)
    return _engine.scan_text(
        text=text,
        chapter_id=chapter_id,
    )


class HWEPatchPlanRequest(BaseModel):
    text: Optional[str] = None
    chapter_id: Optional[str] = None
    project_characters: Optional[List[str]] = None


class HWEPatchGenerateRequest(BaseModel):
    patch: PatchPlanItem
    max_edit_ratio: float = Field(default=0.55, ge=0.1, le=1.0)


class HWEPatchAcceptRequest(BaseModel):
    chapter_id: str
    patch_id: str
    start: int
    end: int
    candidate_text: str
    rule_ids: List[str] = Field(default_factory=list)
    expected_revision: Optional[int] = None


@router.post("/patch/plan", response_model=List[PatchPlanItem])
def plan_patches(
    payload: HWEPatchPlanRequest,
    session: ProjectSession = Depends(get_project_session),
) -> List[PatchPlanItem]:
    """Analyze issues and produce minimal localized patch plan."""
    text = payload.text
    if text is None:
        if not payload.chapter_id:
            raise HTTPException(status_code=400, detail="必须提供 text 或 chapter_id")
        _validate_id(payload.chapter_id, "chapter_id")
        if not session.has_project:
            raise HTTPException(status_code=400, detail="未选择活跃项目，无法读取章节正文")
        text = read_chapter_plain_text(session.root_dir, payload.chapter_id)

    report = _engine.scan_text(text, chapter_id=payload.chapter_id)
    protected = extract_protected_spans(text, project_characters=payload.project_characters)
    return create_patch_plan(report, text, protected)


@router.post("/patch/generate", response_model=HWEPatchCandidate)
def generate_patch(
    payload: HWEPatchGenerateRequest,
) -> HWEPatchCandidate:
    """Execute localized Three-Pass repair and validate candidate with fidelity checks."""
    return run_patch(payload.patch, engine=_engine, max_edit_ratio=payload.max_edit_ratio)


@router.post("/patches/accept", response_model=HWEReport)
def accept_patch(
    payload: HWEPatchAcceptRequest,
    session: ProjectSession = RequireProjectDep,
) -> HWEReport:
    """Apply accepted localized patch to chapter, create revision, and re-scan."""
    _validate_id(payload.chapter_id, "chapter_id")
    current_text = read_chapter_plain_text(session.root_dir, payload.chapter_id)
    if not current_text:
        raise HTTPException(status_code=404, detail=f"章节 {payload.chapter_id} 暂无正文")

    if payload.start < 0 or payload.end > len(current_text) or payload.start > payload.end:
        raise HTTPException(status_code=400, detail="补丁位置偏移超出当前正文边界")

    # Apply localized replacement
    new_text = current_text[:payload.start] + payload.candidate_text + current_text[payload.end:]

    from novel_agent.state.manuscript_repository import DocumentConflictError

    try:
        apply_plain_text_to_manuscript(
            session.root_dir,
            chapter_id=payload.chapter_id,
            plain_text=new_text,
            expected_revision=payload.expected_revision,
            source="hwe_patch",
        )
    except DocumentConflictError as exc:
        raise HTTPException(
            409,
            {
                "code": "DOCUMENT_CONFLICT",
                "message": "正文已在其他窗口更新，请刷新后重试。",
                "current": exc.current,
            },
        ) from exc

    # Re-scan updated text
    return _engine.scan_text(new_text, chapter_id=payload.chapter_id)


class HWEPromptPreviewRequest(BaseModel):
    chapter_id: Optional[str] = None
    scene_type: Optional[str] = None
    pov: Optional[str] = None
    characters: Optional[List[str]] = None
    user_constraints: Optional[List[str]] = None
    max_budget: int = 1200


class HWESemanticReviewRequest(BaseModel):
    text: Optional[str] = None
    chapter_id: Optional[str] = None
    pov: Optional[str] = None
    characters: Optional[List[str]] = None
    template_risk: float = 0.0
    mode: str = "normal"
    user_requested: bool = True


@router.post("/prompt-preview")
def preview_prompt_constraints(
    payload: HWEPromptPreviewRequest,
    session: ProjectSession = Depends(get_project_session),
) -> Dict[str, Any]:
    """Compile and preview [本章文风与去套路约束] prompt block (PRD §7, §41)."""
    root_dir = session.root_dir if session.has_project else None
    prompt_block = compile_human_writing_prompt(
        root_dir=root_dir,
        scene={"scene_type": payload.scene_type, "characters": payload.characters or []},
        plan={"chapter_id": payload.chapter_id, "pov": payload.pov},
        user_constraints=payload.user_constraints,
        max_budget=payload.max_budget,
    )
    return {
        "prompt_block": prompt_block,
        "char_count": len(prompt_block),
        "budget": payload.max_budget,
        "within_budget": len(prompt_block) <= payload.max_budget,
    }


@router.get("/memory/{chapter_id}")
def get_longform_memory_diagnostics(
    chapter_id: str,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    """Inspect Longform Memory 2.0 sliding windows and opening/ending fingerprints (PRD §19, §58)."""
    _validate_id(chapter_id, "chapter_id")
    current_text = read_chapter_plain_text(session.root_dir, chapter_id)
    if not current_text:
        raise HTTPException(status_code=404, detail=f"章节 {chapter_id} 暂无正文")

    curr_entries = extract_expression_entries_v2(current_text, chapter_id=chapter_id)

    # Load historical chapters for sliding window comparison
    store = SQLiteStateStore(session.root_dir)
    all_docs = store.list_manuscript_documents()
    hist_entries = []
    preceding_texts = []
    for doc in all_docs:
        doc_chap = str(doc.get("chapter_id"))
        if doc_chap != str(chapter_id):
            doc_text = doc.get("plain_text") or doc.get("text") or ""
            if doc_text:
                preceding_texts.append((doc_chap, doc_text))
                for ent in extract_expression_entries_v2(doc_text, chapter_id=doc_chap):
                    hist_entries.append(ent.to_dict())

    # Sliding window diagnostics
    sliding_diagnostics = analyze_sliding_windows(curr_entries, hist_entries, current_chapter_id=chapter_id)

    # Ending repetition diagnostics
    ending_issues = detect_chapter_ending_fingerprint_repetition(current_text, preceding_texts)

    return {
        "chapter_id": chapter_id,
        "total_extracted_entries": len(curr_entries),
        "sliding_windows": [
            {
                "expression": d.expression,
                "kind": d.kind,
                "window_3_count": d.window_3_count,
                "window_10_count": d.window_10_count,
                "whole_book_count": d.whole_book_count,
                "is_saturated": d.is_saturated,
                "evidence_chapters": d.evidence_chapters,
            }
            for d in sliding_diagnostics
        ],
        "saturated_count": sum(1 for d in sliding_diagnostics if d.is_saturated),
        "ending_issues": [i.model_dump() for i in ending_issues],
    }


@router.post("/semantic-review", response_model=List[HWEIssue])
def run_semantic_review(
    payload: HWESemanticReviewRequest,
    session: ProjectSession = Depends(get_project_session),
) -> List[HWEIssue]:
    """Execute Layer 3 on-demand model semantic scan (PRD §8.1, §39)."""
    text = payload.text
    if text is None:
        if not payload.chapter_id:
            raise HTTPException(status_code=400, detail="必须提供 text 或 chapter_id")
        _validate_id(payload.chapter_id, "chapter_id")
        if not session.has_project:
            raise HTTPException(status_code=400, detail="未选择活跃项目，无法读取章节正文")
        text = read_chapter_plain_text(session.root_dir, payload.chapter_id)

    return _semantic_reviewer.review(
        text=text,
        pov=payload.pov,
        characters=payload.characters,
        template_risk=payload.template_risk,
        mode=payload.mode,
        user_requested=payload.user_requested,
    )


class HWEIssueResolveRequest(BaseModel):
    action: str = Field(description="Action: ignore, false_positive, allow_rule, resolved")
    rule_id: str = ""
    note: str = ""


class HWEPreferenceUpdateRequest(BaseModel):
    suppress_rule: Optional[str] = None
    unsuppress_rule: Optional[str] = None
    rule_weights: Optional[Dict[str, float]] = None
    reason: str = ""


@router.get("/reports/{chapter_id}/latest")
def get_latest_chapter_report(
    chapter_id: str,
    session: ProjectSession = RequireProjectDep,
) -> Optional[Dict[str, Any]]:
    """Retrieve the latest persisted HWE quality report for a chapter."""
    _validate_id(chapter_id, "chapter_id")
    store = SQLiteStateStore(session.root_dir)
    return store.get_latest_hwe_report(chapter_id)


@router.post("/issues/{issue_id}/resolve")
def resolve_issue(
    issue_id: str,
    payload: HWEIssueResolveRequest,
    session: ProjectSession = Depends(get_project_session),
) -> Dict[str, Any]:
    """Resolve an issue instance, record false positive, or allow a rule."""
    _validate_id(issue_id, "issue_id")
    store = SQLiteStateStore(session.root_dir) if session.has_project else None
    pm = HWEPreferenceManager(store=store, project_id=session.project_id if session.has_project else "default")
    pm.record_issue_feedback(
        issue_id=issue_id,
        action=payload.action,
        rule_id=payload.rule_id,
        note=payload.note,
    )
    return {"status": "ok", "issue_id": issue_id, "action": payload.action}


@router.get("/preferences")
def get_preferences(
    session: ProjectSession = Depends(get_project_session),
) -> Dict[str, Any]:
    """Get project adaptive writing style preferences and rule suppressions."""
    if session.has_project:
        store = SQLiteStateStore(session.root_dir)
        pm = HWEPreferenceManager(store=store, project_id=session.project_id)
    else:
        pm = HWEPreferenceManager(project_id="default")
    return pm.export_profile()


@router.post("/preferences")
def update_preferences(
    payload: HWEPreferenceUpdateRequest,
    session: ProjectSession = Depends(get_project_session),
) -> Dict[str, Any]:
    """Update adaptive preferences (suppress/unsuppress rule or adjust weights)."""
    if session.has_project:
        store = SQLiteStateStore(session.root_dir)
        pm = HWEPreferenceManager(store=store, project_id=session.project_id)
    else:
        pm = HWEPreferenceManager(project_id="default")
    if payload.suppress_rule:
        pm.suppress_rule(payload.suppress_rule, reason=payload.reason)
    if payload.unsuppress_rule:
        pm.unsuppress_rule(payload.unsuppress_rule)
    if payload.rule_weights:
        for r_id, w in payload.rule_weights.items():
            pm.adjust_rule_weight(r_id, w, reason=payload.reason)
    return pm.export_profile()


@router.post("/eval/run", response_model=EvalReport)
def run_eval_benchmark() -> EvalReport:
    """Execute Eval Lab benchmark suite across positive and negative datasets."""
    global _latest_eval_report
    runner = HWEEvalRunner()
    report = runner.run_eval()
    _latest_eval_report = report
    return report


@router.get("/eval/latest")
def get_latest_eval() -> Optional[Dict[str, Any]]:
    """Retrieve latest Eval Lab report."""
    global _latest_eval_report
    if _latest_eval_report is None:
        return None
    return _latest_eval_report.model_dump()
