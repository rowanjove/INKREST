"""Versioned filesystem projection for arc contracts.

SQLite remains the state source for chapter/event data; contracts are small,
append-safe project artifacts so users can inspect and restore revisions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .arc_contract import ArcContract, build_arc_contract, seal_arc_contract, supersede_arc_contract, validate_plan_against_arc


def arc_contract_path(root_dir: Path, arc_id: str) -> Path:
    safe = "".join(char if char.isalnum() or char in "._-" else "_" for char in str(arc_id)) or "arc"
    return Path(root_dir) / "workspace" / "arc_contracts" / f"{safe}.json"


def arc_contract_history_dir(root_dir: Path, arc_id: str) -> Path:
    safe = "".join(char if char.isalnum() or char in "._-" else "_" for char in str(arc_id)) or "arc"
    return Path(root_dir) / "workspace" / "arc_contracts" / "history" / safe


def _contract_from_mapping(value: Mapping[str, Any], arc_id: str) -> ArcContract:
    base = build_arc_contract(
        str(value.get("arc_id") or arc_id),
        chapter_start=int(value.get("chapter_start") or 1),
        chapter_end=int(value.get("chapter_end") or 1),
        objective=str(value.get("objective") or ""),
        required_events=value.get("required_events") or (),
        forbidden_events=value.get("forbidden_events") or (),
        entry_state=value.get("entry_state") or {},
        exit_state=value.get("exit_state") or {},
        character_arc_delta=value.get("character_arc_delta") or {},
        parent_outline_digest=str(value.get("parent_outline_digest") or ""),
        fact_revision=str(value.get("fact_revision") or ""),
        prompt_digest=str(value.get("prompt_digest") or ""),
        version=int(value.get("version") or 1),
    )
    return ArcContract(
        **{
            **base.__dict__,
            "status": str(value.get("status") or "draft"),
            "contract_digest": str(value.get("contract_digest") or base.contract_digest),
        }
    )


def save_arc_contract(root_dir: Path, contract: ArcContract) -> Path:
    path = arc_contract_path(root_dir, contract.arc_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Preserve every prior revision before replacing the live pointer.  The
    # current JSON is a convenient lookup, while history is the audit trail.
    if path.is_file():
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
            previous_version = int(previous.get("version") or 0) if isinstance(previous, Mapping) else 0
            # Sealing is an in-place state transition for the same revision.
            # Do not archive the draft as v1 before the sealed pointer is
            # written; the next supersede operation will archive the sealed
            # revision instead.  A revision must describe the exact contract
            # that was live, not an intermediate write state.
            if previous_version and previous_version != int(contract.version):
                history_dir = arc_contract_history_dir(root_dir, contract.arc_id)
                history_dir.mkdir(parents=True, exist_ok=True)
                history_path = history_dir / f"v{previous_version}.json"
                history_path.write_text(json.dumps(previous, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
            pass
    payload = contract.to_dict()
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def load_arc_contract(root_dir: Path, arc_id: str) -> ArcContract | None:
    path = arc_contract_path(root_dir, arc_id)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(value, Mapping):
        return None
    return _contract_from_mapping(value, arc_id)


def create_arc_contract(root_dir: Path, data: Mapping[str, Any], *, seal: bool = False) -> ArcContract:
    arc_id = str(data.get("arc_id") or "A01")
    if arc_contract_path(root_dir, arc_id).is_file():
        raise FileExistsError(f"arc contract already exists: {arc_id}")
    contract = build_arc_contract(
        arc_id,
        chapter_start=int(data.get("chapter_start") or 1),
        chapter_end=int(data.get("chapter_end") or 1),
        objective=str(data.get("objective") or ""),
        required_events=data.get("required_events") or (),
        forbidden_events=data.get("forbidden_events") or (),
        entry_state=data.get("entry_state") or {},
        exit_state=data.get("exit_state") or {},
        character_arc_delta=data.get("character_arc_delta") or {},
        parent_outline_digest=str(data.get("parent_outline_digest") or ""),
        fact_revision=str(data.get("fact_revision") or ""),
        prompt_digest=str(data.get("prompt_digest") or ""),
        version=int(data.get("version") or 1),
    )
    if seal:
        contract = seal_arc_contract(contract)
    save_arc_contract(root_dir, contract)
    return contract


def seal_saved_arc_contract(root_dir: Path, arc_id: str, *, expected_version: int | None = None) -> ArcContract:
    contract = load_arc_contract(root_dir, arc_id)
    if not contract:
        raise FileNotFoundError(f"arc contract not found: {arc_id}")
    if expected_version is not None and int(expected_version) != int(contract.version):
        raise ValueError(
            f"arc contract version is stale: expected {expected_version}, current {contract.version}"
        )
    sealed = seal_arc_contract(contract)
    save_arc_contract(root_dir, sealed)
    return sealed


def supersede_saved_arc_contract(root_dir: Path, arc_id: str, changes: Mapping[str, Any]) -> ArcContract:
    contract = load_arc_contract(root_dir, arc_id)
    if not contract:
        raise FileNotFoundError(f"arc contract not found: {arc_id}")
    incoming = dict(changes)
    expected_version = incoming.pop("expected_version", None)
    if expected_version is not None and int(expected_version) != int(contract.version):
        raise ValueError(
            f"arc contract version is stale: expected {expected_version}, current {contract.version}"
        )
    incoming.pop("arc_id", None)
    updated = supersede_arc_contract(contract, **incoming)
    save_arc_contract(root_dir, updated)
    return updated


def validate_saved_plan(root_dir: Path, arc_id: str, plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    contract = load_arc_contract(root_dir, arc_id)
    return validate_plan_against_arc(contract, plan) if contract else [{"code": "ARC_CONTRACT_MISSING", "action": "replan"}]


def list_arc_contract_history(root_dir: Path, arc_id: str) -> list[ArcContract]:
    history_dir = arc_contract_history_dir(root_dir, arc_id)
    contracts: list[ArcContract] = []
    for path in sorted(history_dir.glob("v*.json"), key=lambda item: item.name):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, Mapping):
            contracts.append(_contract_from_mapping(value, arc_id))
    current = load_arc_contract(root_dir, arc_id)
    if current and all(item.version != current.version for item in contracts):
        contracts.append(current)
    return sorted(contracts, key=lambda item: item.version)


def restore_saved_arc_contract(
    root_dir: Path,
    arc_id: str,
    version: int,
    *,
    expected_current_version: int | None = None,
) -> ArcContract:
    """Restore a historical revision by creating a new superseding version."""

    source = next((item for item in list_arc_contract_history(root_dir, arc_id) if item.version == int(version)), None)
    current = load_arc_contract(root_dir, arc_id)
    if not source or not current:
        raise FileNotFoundError(f"arc contract revision not found: {arc_id}@v{version}")
    if expected_current_version is not None and int(expected_current_version) != int(current.version):
        raise ValueError(
            f"arc contract version is stale: expected {expected_current_version}, current {current.version}"
        )
    restored = supersede_arc_contract(current, **source.to_dict())
    # supersede_arc_contract receives the source version but always increments
    # from current, so the restore is append-only and never rewrites history.
    save_arc_contract(root_dir, restored)
    return restored


__all__ = [
    "arc_contract_history_dir",
    "arc_contract_path",
    "create_arc_contract",
    "list_arc_contract_history",
    "load_arc_contract",
    "restore_saved_arc_contract",
    "save_arc_contract",
    "seal_saved_arc_contract",
    "supersede_saved_arc_contract",
    "validate_saved_plan",
]
