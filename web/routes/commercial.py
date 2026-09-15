"""Commercial readiness, licensing, recovery, and budget endpoints."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from web.context import get_root_dir
from novel_agent.vault.manager import VaultManager
from novel_agent.vault.migration import migrate_legacy_workspace
from novel_agent.licensing.license_service import LicenseService
from novel_agent.licensing.models import LicenseTier
from novel_agent.recovery.health_check import ProjectHealthChecker
from novel_agent.recovery.backup import BackupManager
from novel_agent.recovery.diagnostics import DiagnosticManager
from novel_agent.recovery.crash_recovery import CrashRecoveryManager
from novel_agent.budget.budget_guard import BudgetGuard

router = APIRouter(prefix="/api/commercial", tags=["commercial"])

# Global singletons for runtime
_budget_guard = BudgetGuard(daily_budget_cny=50.0, task_budget_cny=15.0)


class ActivateLicenseRequest(BaseModel):
    license_json: str


class EstimateCostRequest(BaseModel):
    num_chapters: int = 10
    avg_input_tokens: int = 4000
    avg_output_tokens: int = 1500
    model: str = "deepseek-chat"


def _get_managers() -> tuple[VaultManager, LicenseService, Path]:
    root_dir = get_root_dir() or Path(".").resolve()
    vault_mgr = VaultManager(root_dir)
    # Ensure default vault exists
    migrate_legacy_workspace(root_dir, vault_mgr)
    lic_service = LicenseService(root_dir / "global")
    return vault_mgr, lic_service, root_dir


@router.get("/status")
def get_commercial_status() -> Dict[str, Any]:
    """Return overall commercial status: license, entitlements, vault, recovery, budget."""
    vault_mgr, lic_service, root_dir = _get_managers()

    # License & Entitlements
    curr_license = lic_service.get_current_license()
    ent_service = lic_service.get_entitlement_service()
    tier = ent_service.get_active_tier()
    is_valid, validation_msg = (
        lic_service.is_license_valid(curr_license) if curr_license else (True, "免费版本")
    )

    # Vault info
    default_vault = vault_mgr.get_default_vault()
    vaults = vault_mgr.list_vaults()

    # Recovery / drafts info
    crash_mgr = CrashRecoveryManager(root_dir / "accounts" / default_vault.vault_id if default_vault else root_dir)
    drafts = crash_mgr.list_drafts()

    # Project health check (if projects exist)
    health_status = "healthy"
    projects_dir = root_dir / "projects"
    first_proj = None
    if default_vault:
        v_proj_dir = vault_mgr.get_projects_dir(default_vault.vault_id)
        subdirs = [p for p in v_proj_dir.iterdir() if p.is_dir()] if v_proj_dir.is_dir() else []
        if subdirs:
            first_proj = subdirs[0]
    if not first_proj and projects_dir.is_dir():
        subdirs = [p for p in projects_dir.iterdir() if p.is_dir()]
        if subdirs:
            first_proj = subdirs[0]

    if first_proj and (first_proj / "project.db").is_file():
        checker = ProjectHealthChecker(first_proj)
        rep = checker.run_check()
        health_status = rep.overall_status.value

    return {
        "license": {
            "tier": tier.value,
            "holder_name": curr_license.payload.holder_name if curr_license else "本地创作者",
            "expires_at": curr_license.payload.expires_at if curr_license else None,
            "is_valid": is_valid,
            "validation_msg": validation_msg,
            "entitlements": ent_service.list_entitlements(),
        },
        "vault": {
            "active_vault_id": default_vault.vault_id if default_vault else "default",
            "active_vault_name": default_vault.name if default_vault else "默认空间",
            "pin_enabled": default_vault.pin_enabled if default_vault else False,
            "vault_count": len(vaults),
            "storage_path": str(root_dir / "accounts"),
        },
        "recovery": {
            "unsaved_drafts_count": len(drafts),
            "health_status": health_status,
        },
        "budget": {
            "today_spent_cny": _budget_guard.get_today_spent_cny(),
            "daily_budget_cny": _budget_guard.daily_budget_cny,
            "task_budget_cny": _budget_guard.task_budget_cny,
        },
    }


@router.post("/license/trial")
def start_pro_trial() -> Dict[str, Any]:
    """Provision an immediate 14-day Pro Trial license."""
    _, lic_service, _ = _get_managers()
    trial_license = lic_service.start_trial(holder_name="体验创作者", days=14)
    return {
        "success": True,
        "status": "activated",
        "message": "已成功开通 14 天 Pro 试用特权！",
        "expires_at": trial_license.payload.expires_at,
        "tier": "trial",
        "license": trial_license.to_dict(),
    }


@router.post("/license/activate")
def activate_license(req: ActivateLicenseRequest) -> Dict[str, Any]:
    """Activate an offline signed license."""
    _, lic_service, _ = _get_managers()
    ok, msg = lic_service.apply_license(req.license_json)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "status": "activated", "message": msg}


@router.post("/recovery/health-check")
def run_health_check() -> Dict[str, Any]:
    """Run health check on active projects."""
    vault_mgr, _, root_dir = _get_managers()
    default_vault = vault_mgr.get_default_vault()
    target_dir = root_dir / "projects"
    if default_vault:
        v_proj_dir = vault_mgr.get_projects_dir(default_vault.vault_id)
        if v_proj_dir.is_dir() and any(v_proj_dir.iterdir()):
            target_dir = v_proj_dir

    subdirs = [p for p in target_dir.iterdir() if p.is_dir()] if target_dir.is_dir() else []
    if not subdirs:
        return {"success": True, "status": "healthy", "issues": [], "message": "暂无需要体检的项目"}

    first_proj = subdirs[0]
    checker = ProjectHealthChecker(first_proj)
    report = checker.run_check()
    issues = [issue.message for chk in report.checks for issue in chk.issues]
    return {
        "success": True,
        "status": report.overall_status,
        "report": report.to_dict(),
        "issues": issues,
    }


@router.post("/recovery/auto-repair")
def run_auto_repair() -> Dict[str, Any]:
    """Run automated SQLite repair and optimize."""
    vault_mgr, _, root_dir = _get_managers()
    default_vault = vault_mgr.get_default_vault()
    target_dir = root_dir / "projects"
    if default_vault:
        v_proj_dir = vault_mgr.get_projects_dir(default_vault.vault_id)
        if v_proj_dir.is_dir() and any(v_proj_dir.iterdir()):
            target_dir = v_proj_dir

    subdirs = [p for p in target_dir.iterdir() if p.is_dir()] if target_dir.is_dir() else []
    if not subdirs:
        return {"success": True, "actions": ["没有需要修复的项目数据库"]}

    first_proj = subdirs[0]
    checker = ProjectHealthChecker(first_proj)
    res = checker.auto_repair()
    return res


@router.post("/recovery/backup")
def create_vault_backup() -> Dict[str, Any]:
    """Create a standardized .inkrest-vault backup package."""
    vault_mgr, _, root_dir = _get_managers()
    default_vault = vault_mgr.get_default_vault()
    vault_dir = root_dir / "accounts" / default_vault.vault_id if default_vault else root_dir
    backup_path = BackupManager.create_backup(vault_dir)
    return {
        "success": True,
        "backup_path": str(backup_path),
        "backup_name": backup_path.name,
        "size_bytes": backup_path.stat().st_size,
    }


@router.post("/recovery/diagnostics")
def create_diagnostics() -> Dict[str, Any]:
    """Create desensitized diagnostic zip package."""
    _, _, root_dir = _get_managers()
    mgr = DiagnosticManager(root_dir)
    pkg = mgr.generate_diagnostic_package(
        vault_metadata={"status": "active"},
        health_summary={"status": "checked"},
    )
    return {
        "success": True,
        "diagnostic_path": str(pkg),
        "diagnostic_name": pkg.name,
        "size_bytes": pkg.stat().st_size,
    }


@router.post("/budget/estimate")
def estimate_batch_cost(req: EstimateCostRequest) -> Dict[str, Any]:
    """Estimate token costs for batch generation."""
    res = _budget_guard.estimate_batch(
        num_chapters=req.num_chapters,
        avg_input_tokens=req.avg_input_tokens,
        avg_output_tokens=req.avg_output_tokens,
        model=req.model,
    )
    total_tokens = res["total_input_tokens"] + res["total_output_tokens"]
    res["total_tokens"] = total_tokens
    res["daily_budget_remaining_cny"] = max(
        0.0, _budget_guard.daily_budget_cny - (_budget_guard.get_today_spent_cny() + res["estimated_cost_cny"])
    )
    res["fits_daily_budget"] = res["is_within_daily_budget"]
    return res
