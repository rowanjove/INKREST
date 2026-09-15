"""Main plugin entry point for Script Murder Workshop."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Dict, Optional

from novel_agent.plugins.base import PluginMeta, PluginType, WebExtensionPlugin
try:  # source-tree imports
    from .package import (
        CanonService,
        DatabaseManager,
        ModelService,
        PlaytestService,
        ProjectService,
        ScriptMurderOrchestrator,
        ScriptMurderExporter,
        DeterministicValidator,
        CharacterProfile,
        ClueItem,
        DeductiveConclusion,
        create_router,
    )
    from .package.services.task_service import ScriptMurderTaskService
except ImportError:  # installed plugin loader imports plugin.py as a top-level module
    from package import (
        CanonService,
        DatabaseManager,
        ModelService,
        PlaytestService,
        ProjectService,
        ScriptMurderOrchestrator,
        ScriptMurderExporter,
        DeterministicValidator,
        CharacterProfile,
        ClueItem,
        DeductiveConclusion,
        create_router,
    )
    from package.services.task_service import ScriptMurderTaskService


class ScriptMurderPlugin(WebExtensionPlugin):
    """Web Extension plugin providing Script Murder creation workspace."""

    def __init__(self) -> None:
        super().__init__()
        self.db_manager: Optional[DatabaseManager] = None
        self.project_svc: Optional[ProjectService] = None
        self.canon_svc: Optional[CanonService] = None
        self.model_svc: Optional[ModelService] = None
        self.orchestrator: Optional[ScriptMurderOrchestrator] = None
        self.playtest_svc: Optional[PlaytestService] = None
        self.task_svc: Optional[ScriptMurderTaskService] = None
        self.router: Optional[Any] = None

    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="script_murder",
            display_name="墨局 · 剧本杀工坊",
            version="0.1.0",
            plugin_type=PluginType.WEB_EXTENSION,
            description="面向严肃本格与变格创作的独立剧本杀工坊，支持 Truth Canon 事实库、人物四象限视界、物证链网与确定性逻辑审计。",
            author="Inkrest Community",
        )

    def on_activate(self, context: Any) -> None:
        self.context = context
        root_dir = getattr(context, "root_dir", None)
        if not root_dir:
            from web.context import BASE_DIR
            root_dir = BASE_DIR

        self.db_manager = DatabaseManager(Path(root_dir))
        self.project_svc = ProjectService(self.db_manager)
        self.canon_svc = CanonService(self.project_svc)
        llm, registry = self._load_host_models(Path(root_dir))
        self.model_svc = ModelService(Path(root_dir), llm, registry)
        self.orchestrator = ScriptMurderOrchestrator(self.model_svc)
        self.playtest_svc = PlaytestService(self.model_svc)
        self.task_svc = ScriptMurderTaskService(
            self.project_svc,
            self.canon_svc,
            self.orchestrator,
            self.playtest_svc,
        )

        self.router = create_router(
            self.project_svc,
            self.canon_svc,
            self.orchestrator,
            self.playtest_svc,
            self.task_svc,
        )

    @staticmethod
    def _load_host_models(root_dir: Path) -> tuple[Any, Dict[str, Any]]:
        """Reuse the host's configured model routing without initializing another plugin manager."""
        try:
            from novel_agent.agents.base import create_llm_registry
            from novel_agent.config.io import resolve_environment_values
            from novel_agent.pipeline import (
                _apply_global_fallback_ids,
                _daily_model_id,
                _load_models_library,
                _resolve_llm_config,
                _resolve_tiered_overrides,
                _should_use_library_default,
                load_pipeline_settings,
            )

            settings = load_pipeline_settings(root_dir)
            llm_settings = resolve_environment_values(settings.get("llm", {"provider": "static"}))
            default_config, overrides = _resolve_llm_config(dict(llm_settings))
            models = _load_models_library(root_dir)
            default_id = _daily_model_id(llm_settings)
            if not default_id and _should_use_library_default(llm_settings) and models:
                default_id = next(iter(models))
            if default_id and default_id in models:
                default_config = {"model_ref": default_id}
            overrides = _resolve_tiered_overrides(llm_settings, overrides)
            default_config = _apply_global_fallback_ids(default_config, llm_settings)
            overrides = {
                role: _apply_global_fallback_ids(cfg, llm_settings)
                for role, cfg in (overrides or {}).items()
            }
            registry = create_llm_registry(default_config, overrides or None, models)
            return registry["default"], registry
        except Exception:
            # A broken optional model config must not prevent hand editing/offline validation.
            return None, {}

    def handle_view_rpc(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        session: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Dispatch the allowlisted business surface used by the sandboxed UI."""
        params = dict(params or {})
        if not self.project_svc or not self.canon_svc or not self.task_svc:
            raise RuntimeError("插件尚未激活")
        project_id = str(params.get("project_id") or "")
        if method == "project.list":
            return {"projects": self.project_svc.list_projects()}
        if method == "project.create":
            return {"workspace": self.project_svc.create_project(params).model_dump()}
        if method == "project.get":
            ws = self.project_svc.get_workspace(project_id)
            if not ws:
                raise ValueError(f"Project '{project_id}' not found")
            return {"workspace": ws.model_dump()}
        if method == "project.delete":
            if not self.project_svc.delete_project(project_id):
                raise ValueError(f"Project '{project_id}' not found")
            return {"deleted": project_id}
        if method == "project.trash.list":
            return {"projects": self.db_manager.list_deleted_projects()}
        if method == "project.trash.restore":
            restored = self.db_manager.restore_deleted_project(str(params.get("trash_id") or ""))
            if not restored:
                raise ValueError("Trash project not found")
            return {"restored": restored}
        if method == "canon.update":
            return {"canon": self.canon_svc.update_canon(project_id, params.get("canon") or {}).model_dump()}
        if method == "character.save":
            return {"character": self.canon_svc.upsert_character(project_id, CharacterProfile.model_validate(params.get("character") or {})).model_dump()}
        if method == "characters.replace":
            chars = [CharacterProfile.model_validate(item) for item in (params.get("characters") or [])]
            return {"characters": [c.model_dump() for c in self.canon_svc.replace_characters(project_id, chars)]}
        if method == "clue.save":
            return {"clue": self.canon_svc.upsert_clue(project_id, ClueItem.model_validate(params.get("clue") or {})).model_dump()}
        if method == "clues.replace":
            clues = [ClueItem.model_validate(item) for item in (params.get("clues") or [])]
            conclusions = [DeductiveConclusion.model_validate(item) for item in (params.get("conclusions") or [])]
            return {"clues": [c.model_dump() for c in self.canon_svc.replace_clues(project_id, clues, conclusions)]}
        if method == "flow.update":
            return {"flow": self.canon_svc.update_flow(project_id, params.get("flow") or {}).model_dump()}
        if method == "snapshot.create":
            return {"snapshot_id": self.project_svc.create_snapshot(project_id, str(params.get("label") or "手动快照"))}
        if method == "task.submit":
            task = self.task_svc.submit(project_id, str(params.get("node") or ""), params.get("params") or {})
            return {"task": task.model_dump()}
        if method == "task.get":
            task = self.task_svc.get(str(params.get("task_id") or ""))
            if not task:
                raise ValueError("Task not found")
            return {"task": task.model_dump()}
        if method == "task.list":
            return {"tasks": [t.model_dump() for t in self.task_svc.list(project_id)]}
        if method == "task.cancel":
            task = self.task_svc.cancel(str(params.get("task_id") or ""))
            if not task:
                raise ValueError("Task not found")
            return {"task": task.model_dump()}
        if method == "task.accept":
            task = self.task_svc.accept(str(params.get("task_id") or ""))
            if not task:
                raise ValueError("Task not found")
            return {"task": task.model_dump()}
        if method == "task.reject":
            task = self.task_svc.reject(str(params.get("task_id") or ""))
            if not task:
                raise ValueError("Task not found")
            return {"task": task.model_dump()}
        if method == "validation.run":
            ws = self.project_svc.get_workspace(project_id)
            if not ws:
                raise ValueError(f"Project '{project_id}' not found")
            return {"report": DeterministicValidator(ws).validate_all().model_dump()}
        if method == "export.preflight":
            ws = self.project_svc.get_workspace(project_id)
            if not ws:
                raise ValueError(f"Project '{project_id}' not found")
            return {"preflight": ScriptMurderExporter(ws).preflight_check().model_dump()}
        if method == "export.zip":
            ws = self.project_svc.get_workspace(project_id)
            if not ws:
                raise ValueError(f"Project '{project_id}' not found")
            raw = ScriptMurderExporter(ws).build_zip_bytes()
            safe_title = str(ws.meta.title or "script_murder").replace("/", "_").replace("\\", "_").replace("..", "_")
            return {"filename": f"{safe_title}_剧本杀完整开本包.zip", "base64": base64.b64encode(raw).decode("ascii")}
        raise ValueError(f"Unsupported script_murder RPC method: {method}")

    def get_router(self) -> Optional[Any]:
        return self.router

    def on_deactivate(self) -> None:
        if self.task_svc:
            self.task_svc.shutdown()
        self.task_svc = None
        self.router = None
        self.project_svc = None
        self.canon_svc = None
        self.db_manager = None

    def get_frontend_manifest(self) -> Dict[str, Any]:
        return {
            "plugin_id": "script_murder",
            "name": "墨局 · 剧本杀工坊",
            "scope": "global",
            "icon": "collection",
            "pages": [
                {
                    "id": "studio",
                    "title": "剧本工坊",
                    "path": "/extensions/library/script_murder/studio",
                    "entry": "/api/ext/script-murder/ui/",
                }
            ],
        }


PLUGIN_CLASS = ScriptMurderPlugin
