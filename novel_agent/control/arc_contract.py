"""Versioned volume/arc contracts that prevent silent outline drift."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from typing import Any, Mapping, Sequence


def _digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True)
class ArcContract:
    arc_id: str
    version: int
    chapter_start: int
    chapter_end: int
    objective: str
    required_events: tuple[str, ...] = ()
    forbidden_events: tuple[str, ...] = ()
    entry_state: Mapping[str, Any] = None  # type: ignore[assignment]
    exit_state: Mapping[str, Any] = None  # type: ignore[assignment]
    character_arc_delta: Mapping[str, Any] = None  # type: ignore[assignment]
    parent_outline_digest: str = ""
    fact_revision: str = ""
    prompt_digest: str = ""
    status: str = "draft"
    contract_digest: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("required_events", "forbidden_events"):
            payload[key] = list(payload[key])
        for key in ("entry_state", "exit_state", "character_arc_delta"):
            payload[key] = dict(payload[key] or {})
        return payload


def build_arc_contract(
    arc_id: str,
    *,
    chapter_start: int,
    chapter_end: int,
    objective: str,
    required_events: Sequence[str] = (),
    forbidden_events: Sequence[str] = (),
    entry_state: Mapping[str, Any] | None = None,
    exit_state: Mapping[str, Any] | None = None,
    character_arc_delta: Mapping[str, Any] | None = None,
    parent_outline_digest: str = "",
    fact_revision: str = "",
    prompt_digest: str = "",
    version: int = 1,
) -> ArcContract:
    if int(chapter_start) < 1 or int(chapter_end) < int(chapter_start):
        raise ValueError("arc chapter range is invalid")
    raw = {
        "arc_id": str(arc_id),
        "version": int(version),
        "chapter_start": int(chapter_start),
        "chapter_end": int(chapter_end),
        "objective": str(objective),
        "required_events": sorted({str(item) for item in required_events if str(item)}),
        "forbidden_events": sorted({str(item) for item in forbidden_events if str(item)}),
        "entry_state": dict(entry_state or {}),
        "exit_state": dict(exit_state or {}),
        "character_arc_delta": dict(character_arc_delta or {}),
        "parent_outline_digest": str(parent_outline_digest),
        "fact_revision": str(fact_revision),
        "prompt_digest": str(prompt_digest),
    }
    return ArcContract(
        **raw,
        contract_digest=_digest(raw),
    )


def seal_arc_contract(contract: ArcContract) -> ArcContract:
    if contract.status not in {"draft", "sealed"}:
        raise ValueError("only draft contracts can be sealed")
    return replace(contract, status="sealed")


def supersede_arc_contract(contract: ArcContract, **changes: Any) -> ArcContract:
    payload = contract.to_dict()
    payload.update(changes)
    payload.pop("contract_digest", None)
    payload.pop("status", None)
    payload["version"] = int(contract.version) + 1
    return build_arc_contract(**payload)


def validate_plan_against_arc(
    contract: ArcContract,
    plan: Mapping[str, Any],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if contract.status != "sealed":
        issues.append({"code": "ARC_NOT_SEALED", "action": "replan"})
    if str(plan.get("arc_id") or "") != contract.arc_id:
        issues.append({"code": "ARC_ID_MISMATCH", "action": "replan"})
    if int(plan.get("arc_contract_version") or 0) != contract.version:
        issues.append({"code": "ARC_VERSION_MISMATCH", "action": "replan"})
    return issues
