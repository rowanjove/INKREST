from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException

import web.context as ws_server
import web.helpers as ws_helpers
from web.deps import ProjectSession, RequireProjectDep, coerce_project_session

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