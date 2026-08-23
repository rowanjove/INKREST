"""Prompt source discovery and drift diagnostics.

The project historically keeps two prompt trees:

* ``prompts/*.md`` is the runtime/project override and the package fallback.
* ``prompts/defaults/*.md`` is copied into a new project and is also exposed by
  the prompt editor as the reset target.

This module does not change that precedence.  It makes the precedence explicit,
gives every resolved prompt a content digest, and reports when the duplicated
default snapshot has drifted from the canonical package prompt.  Callers can use
the report for review or migration without silently rewriting user prompts.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


_ROLE_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _normalise_prompt(text: str) -> str:
    return (text or "").replace("\r\n", "\n").strip()


def prompt_sha256(text: str) -> str:
    """Return a stable digest for a prompt, independent of line endings."""

    return hashlib.sha256(_normalise_prompt(text).encode("utf-8")).hexdigest()


def _read_prompt(path: Path) -> Optional[str]:
    try:
        if not path.is_file():
            return None
        text = _normalise_prompt(path.read_text(encoding="utf-8"))
        return text or None
    except (OSError, UnicodeError):
        return None


def _candidate(path: Path, kind: str) -> Dict[str, Any]:
    text = _read_prompt(path)
    return {
        "kind": kind,
        "path": str(path),
        "exists": path.is_file(),
        "usable": text is not None,
        "sha256": prompt_sha256(text) if text is not None else None,
    }


def _validate_role(role: str) -> str:
    if not isinstance(role, str) or not _ROLE_RE.fullmatch(role):
        raise ValueError("prompt role must contain only letters, digits, '_' or '-'")
    return role


def inspect_prompt_sources(
    root_dir: Path,
    role: str,
    *,
    env_templates: Optional[Path] = None,
    package_prompts_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Describe prompt candidates and the selected source for ``role``.

    Resolution intentionally mirrors :class:`novel_agent.prompts.PromptRepository`:
    project override, ``NOVEL_AGENT_TEMPLATES`` override, then package prompt.
    The ``defaults`` files are diagnostics/reset snapshots, not an extra runtime
    fallback, so a missing project override is never unexpectedly replaced by a
    local defaults copy.
    """

    role = _validate_role(role)
    root_dir = Path(root_dir)
    project_prompts = root_dir / "prompts"
    if env_templates is None:
        raw_env = os.environ.get("NOVEL_AGENT_TEMPLATES")
        env_templates = Path(raw_env) if raw_env else None
    if package_prompts_dir is None:
        package_prompts_dir = Path(__file__).resolve().parent.parent / "prompts"

    project = _candidate(project_prompts / f"{role}.md", "project")
    project_default = _candidate(project_prompts / "defaults" / f"{role}.md", "project_default")
    env = _candidate(
        (env_templates / "prompts" / f"{role}.md") if env_templates else Path("__missing__"),
        "environment",
    )
    package = _candidate(package_prompts_dir / f"{role}.md", "package")
    package_default = _candidate(package_prompts_dir / "defaults" / f"{role}.md", "package_default")

    selected = next((item for item in (project, env, package) if item["usable"]), None)
    drift: List[Dict[str, Any]] = []
    if package["usable"] and package_default["usable"] and package["sha256"] != package_default["sha256"]:
        drift.append(
            {
                "type": "canonical_default_mismatch",
                "severity": "warning",
                "canonical": package["sha256"],
                "default": package_default["sha256"],
            }
        )
    if project["usable"] and project_default["usable"] and project["sha256"] != project_default["sha256"]:
        drift.append(
            {
                "type": "project_override_differs_from_default",
                "severity": "info",
                "override": project["sha256"],
                "default": project_default["sha256"],
            }
        )

    return {
        "role": role,
        "selected": selected,
        "selected_source": selected["kind"] if selected else None,
        "selected_sha256": selected["sha256"] if selected else None,
        "canonical_path": package["path"],
        "canonical_sha256": package["sha256"],
        "candidates": {
            "project": project,
            "project_default": project_default,
            "environment": env,
            "package": package,
            "package_default": package_default,
        },
        "drift": drift,
        "has_drift": bool(drift),
    }


def prompt_manifest(
    root_dir: Path,
    roles: Optional[Iterable[str]] = None,
    *,
    env_templates: Optional[Path] = None,
    package_prompts_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Build a JSON-serialisable prompt manifest for diagnostics/export."""

    if roles is None:
        package_dir = package_prompts_dir or (Path(__file__).resolve().parent.parent / "prompts")
        role_names = sorted(path.stem for path in package_dir.glob("*.md"))
        project_dir = Path(root_dir) / "prompts"
        role_names = sorted(set(role_names) | {path.stem for path in project_dir.glob("*.md")})
    else:
        role_names = sorted({_validate_role(role) for role in roles})

    entries = [
        inspect_prompt_sources(
            root_dir,
            role,
            env_templates=env_templates,
            package_prompts_dir=package_prompts_dir,
        )
        for role in role_names
    ]
    return {
        "schema_version": 1,
        "canonical_source": "package/prompts/<role>.md",
        "resolution_order": ["project", "environment", "package"],
        "roles": entries,
        "drift_count": sum(1 for entry in entries if entry["has_drift"]),
    }


__all__ = ["inspect_prompt_sources", "prompt_manifest", "prompt_sha256"]
