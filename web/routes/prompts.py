from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException

import web.context as ws_server
import web.helpers as ws_helpers
from web.deps import ProjectSession, RequireProjectDep, coerce_project_session
from novel_agent.prompt_registry import prompt_manifest
from novel_agent.quality.prose_identity import (
    list_prose_identity_profile_versions,
    load_prose_identity_profile,
    restore_prose_identity_profile,
)
from novel_agent.quality.voice_lab import is_voice_lab_frozen

ws_server._copy_default_prompts = ws_helpers._copy_default_prompts
ws_server.PROMPT_ROLES = ws_helpers.PROMPT_ROLES
ws_server._read_text = ws_helpers._read_text

router = APIRouter()


@router.get("/api/prompts")
def list_prompts(session: ProjectSession = RequireProjectDep) -> List[Dict[str, Any]]:
    session = coerce_project_session(session)
    root = session.root_dir
    ws_server._copy_default_prompts(root / "prompts")
    prompts_dir = root / "prompts"
    defaults_dir = prompts_dir / "defaults"
    result = []
    for role in ws_server.PROMPT_ROLES:
        path = prompts_dir / f"{role}.md"
        default_path = defaults_dir / f"{role}.md"
        if (not path.exists() or not path.read_text(encoding="utf-8").strip()) and default_path.exists():
            path.write_text(default_path.read_text(encoding="utf-8"), encoding="utf-8")
        content = path.read_text(encoding="utf-8").strip() if path.exists() else ""
        result.append({
            "role": role,
            "content": content,
            "has_default": default_path.exists(),
        })
    return result


@router.get("/api/prompts/manifest")
def get_prompt_manifest(session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    """Return prompt source/digest metadata without changing prompt content."""

    session = coerce_project_session(session)
    root = session.root_dir
    ws_server._copy_default_prompts(root / "prompts")
    return prompt_manifest(root, roles=ws_server.PROMPT_ROLES)


@router.get("/api/prose-profile")
def get_prose_profile(session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    """Return the active prose profile and revision summaries."""

    session = coerce_project_session(session)
    root = session.root_dir
    return {
        "profile": load_prose_identity_profile(root),
        "versions": list_prose_identity_profile_versions(root),
    }


@router.get("/api/prose-profile/versions")
def get_prose_profile_versions(session: ProjectSession = RequireProjectDep) -> List[Dict[str, Any]]:
    session = coerce_project_session(session)
    return list_prose_identity_profile_versions(session.root_dir)


@router.post("/api/prose-profile/restore")
def restore_prose_profile(
    body: Dict[str, Any],
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    session = coerce_project_session(session)
    if is_voice_lab_frozen(session.root_dir) and not bool(body.get("force")):
        raise HTTPException(
            409,
            {
                "code": "VOICE_PROFILE_FROZEN",
                "message": "声线档案已冻结，请先在质量中心解除冻结。",
            },
        )
    raw_revision = body.get("revision")
    try:
        revision = int(raw_revision)
    except (TypeError, ValueError):
        raise HTTPException(400, "revision must be an integer")
    try:
        target = restore_prose_identity_profile(session.root_dir, revision=revision)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return {
        "status": "restored",
        "path": str(target),
        "revision": revision,
        "profile": load_prose_identity_profile(session.root_dir),
    }


@router.get("/api/prompts/{role}")
def get_prompt(role: str, session: ProjectSession = RequireProjectDep) -> Dict[str, str]:
    session = coerce_project_session(session)
    if role not in ws_server.PROMPT_ROLES:
        raise HTTPException(404, f"Unknown prompt role: {role}")
    root = session.root_dir
    ws_server._copy_default_prompts(root / "prompts")
    path = root / "prompts" / f"{role}.md"
    default_path = root / "prompts" / "defaults" / f"{role}.md"
    if (not path.exists() or not path.read_text(encoding="utf-8").strip()) and default_path.exists():
        path.write_text(default_path.read_text(encoding="utf-8"), encoding="utf-8")
    return {"role": role, "content": ws_server._read_text(path)}


@router.put("/api/prompts/{role}")
def update_prompt(
    role: str,
    body: Dict[str, str],
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, str]:
    session = coerce_project_session(session)
    if role not in ws_server.PROMPT_ROLES:
        raise HTTPException(404, f"Unknown prompt role: {role}")
    content = body.get("content", "")
    path = session.root_dir / "prompts" / f"{role}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"role": role, "status": "updated"}


@router.post("/api/prompts/{role}/reset")
def reset_prompt(role: str, session: ProjectSession = RequireProjectDep) -> Dict[str, str]:
    session = coerce_project_session(session)
    if role not in ws_server.PROMPT_ROLES:
        raise HTTPException(404, f"Unknown prompt role: {role}")
    root = session.root_dir
    ws_server._copy_default_prompts(root / "prompts")
    default_path = root / "prompts" / "defaults" / f"{role}.md"
    if not default_path.exists():
        raise HTTPException(404, f"No default prompt for role: {role}")
    target = root / "prompts" / f"{role}.md"
    target.write_text(default_path.read_text(encoding="utf-8"), encoding="utf-8")
    return {"role": role, "status": "reset"}
