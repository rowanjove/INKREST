"""Unified guard result registry for chapter quality checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping


STATUS_PASS = "PASS"
STATUS_WARN = "WARN"
STATUS_FAIL = "FAIL"


@dataclass
class GuardFinding:
    guard: str
    severity: str
    code: str
    message: str
    evidence: List[str] = field(default_factory=list)
    suggestion: str = ""
    confidence: float = 1.0
    location: str = "chapter"


@dataclass
class GuardResult:
    guard: str
    status: str
    level: int
    title: str
    findings: List[GuardFinding] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["findings"] = [asdict(finding) for finding in self.findings]
        return data


def _non_empty_final_text(text: str) -> GuardResult:
    stripped = (text or "").strip()
    if stripped:
        return GuardResult(
            guard="non_empty_final_text",
            status=STATUS_PASS,
            level=1,
            title="正文非空",
            metrics={"chars": len(stripped)},
        )
    return GuardResult(
        guard="non_empty_final_text",
        status=STATUS_FAIL,
        level=1,
        title="正文非空",
        findings=[
            GuardFinding(
                guard="non_empty_final_text",
                severity=STATUS_FAIL,
                code="EMPTY_FINAL_TEXT",
                message="章节正文为空，不能标记为符合要求。",
                evidence=[],
                suggestion="重新生成本章，或先补写正文后再审核。",
                confidence=1.0,
                location="chapter_final.txt",
            )
        ],
        metrics={"chars": 0},
    )


def _status_from_check(check: Mapping[str, Any]) -> str:
    level = str(check.get("level") or "none")
    if level == "fail":
        return STATUS_WARN
    if level in {"warning", "review"}:
        return STATUS_WARN
    if check.get("pass", False):
        return STATUS_PASS
    return STATUS_WARN


def _result_from_quality_check(name: str, check: Mapping[str, Any]) -> GuardResult:
    status = _status_from_check(check)
    details = [str(item) for item in check.get("details", []) if item]
    findings = []
    if status != STATUS_PASS:
        findings.append(
            GuardFinding(
                guard=name,
                severity=status,
                code=f"{name.upper()}_CHECK",
                message=f"{name} 需要审阅。",
                evidence=details[:5],
                suggestion="查看质量报告详情，按提示局部重写。",
                confidence=0.8,
                location="chapter",
            )
        )
    return GuardResult(
        guard=name,
        status=status,
        level=2,
        title=str(check.get("title") or name),
        findings=findings,
        metrics={key: value for key, value in check.items() if key not in {"details"}},
    )


def build_guard_summary(text: str, checks: Mapping[str, Mapping[str, Any]] | None = None) -> Dict[str, Any]:
    """Build a single serializable guard summary for one chapter."""
    results: List[GuardResult] = [_non_empty_final_text(text)]
    for name, check in (checks or {}).items():
        results.append(_result_from_quality_check(str(name), check))

    blocked_by = [result.guard for result in results if result.level == 1 and result.status == STATUS_FAIL]
    if blocked_by:
        overall_status = STATUS_FAIL
    elif any(result.status == STATUS_WARN for result in results):
        overall_status = STATUS_WARN
    else:
        overall_status = STATUS_PASS

    return {
        "overall_status": overall_status,
        "blocked_by": blocked_by,
        "results": [result.to_dict() for result in results],
    }

