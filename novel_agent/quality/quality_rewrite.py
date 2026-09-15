"""One-shot rewrite driven by quality guard failures."""

from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, TYPE_CHECKING

from novel_agent.logging_config import get_logger
from novel_agent.progress import emit_progress
from novel_agent.quality.render_contract import (
    persist_render_candidate,
    text_sha256,
    validate_render_candidate,
)

if TYPE_CHECKING:
    from novel_agent.orchestrator import NovelOrchestrator

logger = get_logger("quality.rewrite")


def _load_persisted_content_lock(candidate_path: Optional[Path]) -> Optional[Dict[str, Any]]:
    """Load chapter scene locks for a chapter-level Style Editor pass."""

    if candidate_path is None:
        return None
    root = Path(candidate_path).parent
    locks: List[Mapping[str, Any]] = []
    for path in sorted(root.glob("scene_*_render_contract.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
            continue
        lock = payload.get("content_lock") if isinstance(payload, Mapping) else None
        if isinstance(lock, Mapping):
            locks.append(lock)
    if not locks:
        return None
    if len(locks) == 1:
        return {"content_lock": dict(locks[0]), "contract_id": "scene:" + str(locks[0].get("lock_digest") or "")}

    merged: Dict[str, Any] = {
        "schema_version": 1,
        "chapter_id": str(locks[0].get("chapter_id") or ""),
        "scene_id": "chapter",
        "required_beats": [],
        "immutable_canon_facts": [],
        "character_goals": [],
        "knowledge_boundaries": [],
        "causal_predecessors": [],
        "state_deltas": {},
        "lock_digest": ",".join(str(lock.get("lock_digest") or "") for lock in locks if lock.get("lock_digest")),
    }
    for lock in locks:
        for key in ("required_beats", "immutable_canon_facts", "character_goals", "knowledge_boundaries", "causal_predecessors"):
            for value in lock.get(key) or []:
                if value not in merged[key]:
                    merged[key].append(value)
        state_deltas = lock.get("state_deltas")
        if isinstance(state_deltas, Mapping):
            merged["state_deltas"].update(state_deltas)
    return {"content_lock": merged, "contract_id": "chapter:" + merged["lock_digest"]}


def _contract_payload(contract: Any) -> Dict[str, Any]:
    if hasattr(contract, "to_dict"):
        try:
            return dict(contract.to_dict())
        except (TypeError, ValueError):
            return {}
    return dict(contract) if isinstance(contract, Mapping) else {}


def _patch_findings(report: Mapping[str, Any], final_text: str, *, limit: int = 8) -> List[Dict[str, Any]]:
    """Collect source-anchored failing findings without asking the model to rediscover them."""

    candidates: List[Dict[str, Any]] = []
    for check_name, check in (report.get("checks") or {}).items():
        if not isinstance(check, Mapping):
            continue
        # Report-only diagnostics remain review signals; an automatic rewrite
        # should only receive checks that actually failed or were explicitly
        # marked for patching.
        if check.get("pass") and not check.get("force_patch"):
            continue
        for finding in check.get("findings") or []:
            if not isinstance(finding, Mapping):
                continue
            try:
                start = max(0, int(finding.get("start", 0)))
                end = min(len(final_text), max(start, int(finding.get("end", start))))
            except (TypeError, ValueError):
                start, end = 0, 0
            target = final_text[start:end].strip() if end > start else str(finding.get("text") or "").strip()
            if not target:
                continue
            candidates.append(
                {
                    "check": str(check_name),
                    "issue_id": str(finding.get("issue_id") or finding.get("id") or f"{check_name}:{start}:{end}"),
                    "type": str(finding.get("type") or finding.get("rule_id") or finding.get("category") or "review"),
                    "severity": str(finding.get("severity") or check.get("level") or "warning"),
                    "start": start,
                    "end": end,
                    "target": target[:360],
                    "why": str(
                        finding.get("why")
                        or finding.get("message")
                        or finding.get("description")
                        or "局部表达需要修正"
                    )[:360],
                    "fix": str(finding.get("fix") or finding.get("suggestion") or "只修改该证据范围")[:360],
                }
            )

    audit = report.get("audit") if isinstance(report.get("audit"), Mapping) else {}
    for issue in audit.get("issues") or []:
        if not isinstance(issue, Mapping):
            continue
        issue_type = str(issue.get("type") or "")
        severity = str(issue.get("severity") or issue.get("level") or "").lower()
        critical = str(issue.get("audit_class") or "").upper() == "CRITICAL"
        if issue_type not in {"sensitive_word_hit", "word_count_out_of_bounds"} and not critical:
            if severity not in {"high", "critical", "高", "fail"}:
                continue
        target = str(issue.get("target_text") or "").strip() or str(issue.get("text") or "").strip()
        if not target:
            continue
        start = final_text.find(target)
        end = start + len(target) if start >= 0 else 0
        if start < 0:
            start = 0
            end = 0
        candidates.append(
            {
                "check": "audit",
                "issue_id": str(issue.get("issue_id") or issue.get("id") or f"audit:{issue_type}:{start}"),
                "type": issue_type or "audit",
                "severity": severity or "high",
                "start": start,
                "end": end,
                "target": target[:360],
                "why": str(issue.get("why") or issue.get("text") or "审校指出需要修正")[:360],
                "fix": str(issue.get("fix") or issue.get("suggestion") or "只修改该证据范围")[:360],
            }
        )

    severity_order = {"high": 0, "critical": 0, "review": 1, "warning": 2, "medium": 2, "low": 3}
    candidates.sort(key=lambda item: (severity_order.get(str(item.get("severity")), 2), item["start"], item["end"]))
    selected: List[Dict[str, Any]] = []
    for item in candidates:
        if any(item["start"] < existing["end"] and existing["start"] < item["end"] for existing in selected):
            continue
        selected.append(item)
        if len(selected) >= max(1, int(limit)):
            break
    return selected


def build_issue_driven_patch_prompt(
    report: Mapping[str, Any],
    final_text: str,
    *,
    expression_contract: str = "",
    content_lock: Optional[Mapping[str, Any]] = None,
) -> str:
    """Build a bounded patch prompt while keeping the editor's plain-text API."""

    findings = _patch_findings(report, final_text)
    hints = build_quality_rewrite_hints(dict(report))
    lines = [
        "你是小说质量修正编辑，请执行 issue-driven patch，而不是全文泛化润色。",
        "- 只修改下列已定位的证据片段及其必要的相邻语句。",
        "- 不新增角色、事件、设定、知识或因果；不改变 CONTENT_LOCK。",
        "- 未被问题覆盖的正文尽量逐字保留。",
        "- 只输出修订后的完整正文，不要输出说明、JSON 或 Markdown。",
    ]
    if findings:
        lines.append("\n## 已定位问题（按证据修补）")
        for index, finding in enumerate(findings, start=1):
            lines.extend(
                [
                    f"### Patch {index} [{finding['check']}/{finding['type']}] {finding['issue_id']}",
                    f"范围：字符 {finding['start']}–{finding['end']}",
                    f"原文证据：{finding['target']}",
                    f"问题：{finding['why']}",
                    f"修补目标：{finding['fix']}",
                ]
            )
    elif hints.strip():
        lines.extend(["\n## 质量反馈（没有可定位 span，只做最小范围修正）", hints])
    if content_lock:
        lock = dict(content_lock)
        lines.extend(
            [
                "\n## CONTENT_LOCK 摘要",
                json.dumps(
                    {
                        "scene_id": lock.get("scene_id"),
                        "required_beats": lock.get("required_beats") or [],
                        "immutable_canon_facts": lock.get("immutable_canon_facts") or [],
                        "knowledge_boundaries": lock.get("knowledge_boundaries") or [],
                        "causal_predecessors": lock.get("causal_predecessors") or [],
                    },
                    ensure_ascii=False,
                ),
            ]
        )
    if expression_contract:
        lines.extend(["\n## 表达合同", expression_contract])
    lines.extend(["\n## 待修订正文", final_text])
    return "\n".join(lines)


def analyse_content_delta(
    original: str,
    candidate: str,
    contract: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Return deterministic patch metadata for UI review and rollback."""

    original_text = str(original or "")
    candidate_text = str(candidate or "")
    operations: List[Dict[str, Any]] = []
    matcher = difflib.SequenceMatcher(None, original_text, candidate_text, autojunk=True)
    changed_original = 0
    changed_candidate = 0
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag == "equal":
            continue
        changed_original += old_end - old_start
        changed_candidate += new_end - new_start
        operations.append(
            {
                "op": tag,
                "original_range": [old_start, old_end],
                "candidate_range": [new_start, new_end],
                "original": original_text[old_start:old_end][:180],
                "candidate": candidate_text[new_start:new_end][:180],
            }
        )
        if len(operations) >= 24:
            break

    if hasattr(contract, "to_dict"):
        contract_data = contract.to_dict()
    else:
        contract_data = contract if isinstance(contract, Mapping) else {}
    lock = dict(contract_data.get("content_lock") or {})
    preserved_facts: List[Dict[str, Any]] = []
    for key in ("required_beats", "immutable_canon_facts", "character_goals", "causal_predecessors"):
        for fact in lock.get(key) or []:
            value = str(fact).strip()
            if not value:
                continue
            preserved_facts.append(
                {
                    "kind": key,
                    "text": value,
                    "preserved": value in candidate_text,
                }
            )
    return {
        "changed": original_text != candidate_text,
        "changed_original_chars": changed_original,
        "changed_candidate_chars": changed_candidate,
        "changed_ratio": round(changed_original / max(1, len(original_text)), 4),
        "operation_count": len(operations),
        "operations": operations,
        "preserved_facts": preserved_facts,
        "content_lock_digest": lock.get("lock_digest", ""),
    }


def build_quality_rewrite_hints(report: Dict[str, Any]) -> str:
    lines = []
    summary = report.get("guard_summary") or {}
    for guard in summary.get("blocked_by") or []:
        lines.append(f"- [硬门禁] {guard}")
    for name, check in (report.get("checks") or {}).items():
        if name == "prose_identity" and check.get("status") in {"warning", "review"}:
            level = check.get("level") or "warning"
            for detail in (check.get("details") or [])[:4]:
                lines.append(f"- [文风档案/{level}] {detail}")
            continue
        if check.get("pass"):
            continue
        level = check.get("level") or "warning"
        for detail in (check.get("details") or [])[:4]:
            lines.append(f"- [{name}/{level}] {detail}")
    return "\n".join(lines)


async def attempt_quality_rewrite(
    orchestrator: "NovelOrchestrator",
    chapter_id: str,
    final_text: str,
    report: Dict[str, Any],
    *,
    candidate_path: Optional[Path] = None,
    contract: Optional[Mapping[str, Any]] = None,
) -> str:
    hints = build_quality_rewrite_hints(report)
    if not hints.strip() or not (final_text or "").strip():
        return final_text

    expression_contract = ""
    try:
        from novel_agent.quality.expression_memory import build_expression_contract

        project_root = getattr(orchestrator, "root_dir", None)
        if project_root:
            expression_contract = build_expression_contract(Path(project_root), chapter_id, limit=8)
    except Exception as exc:
        logger.debug("Expression contract unavailable for quality rewrite: %s", exc)

    resolved_content_contract = (
        _contract_payload(contract)
        if contract is not None
        else (_load_persisted_content_lock(candidate_path) or {})
    )

    emit_progress("quality_rewrite", "running", chapter_id=chapter_id)
    prompt = build_issue_driven_patch_prompt(
        report,
        final_text,
        expression_contract=expression_contract,
        content_lock=resolved_content_contract.get("content_lock") or None,
    )
    try:
        editor = orchestrator.style_editor
        if hasattr(editor, "arun"):
            revised = (await editor.arun(prompt)).strip()
        else:
            revised = editor.run(prompt).strip()
        validation = validate_render_candidate(final_text, revised, contract)
        delta = analyse_content_delta(final_text, revised, resolved_content_contract)
        persist_render_candidate(
            candidate_path,
            revised,
            validation,
            metadata={
                "chapter_id": chapter_id,
                "stage": "quality_rewrite",
                "source_sha256": text_sha256(final_text),
                "patch_mode": "issue_driven",
                "content_delta": delta,
                "preserved_facts": delta.get("preserved_facts", []),
                "content_contract_id": resolved_content_contract.get("contract_id", ""),
            },
        )
        if validation["blocking"]:
            logger.warning(
                "Quality rewrite candidate rejected for chapter %s: %s",
                chapter_id,
                ", ".join(validation["reasons"]),
            )
            emit_progress(
                "quality_rewrite",
                "rejected",
                {
                    "chars": len(revised),
                    "reasons": validation["reasons"],
                    "metrics": validation["metrics"],
                    "content_delta": delta,
                },
                chapter_id,
            )
            return final_text
        if validation["status"] == "unchanged":
            emit_progress("quality_rewrite", "skipped", {"reason": "unchanged"}, chapter_id)
            return final_text
        emit_progress(
            "quality_rewrite",
            "done",
            {"chars": len(revised), "metrics": validation["metrics"], "content_delta": delta},
            chapter_id,
        )
        return revised
    except Exception as exc:
        logger.warning("Quality rewrite failed for chapter %s: %s", chapter_id, exc)
        emit_progress(
            "quality_rewrite",
            "error",
            {"error": str(exc)},
            chapter_id,
        )
    return final_text
