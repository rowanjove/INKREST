"""FastAPI lifespan event handler for the Novel Agent service."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

import web.context as context
from web.project_manager import ProjectManager
from web.helpers import _ensure_dirs, _init_prompt_defaults
from web.project_task_registry import ProjectTaskRegistry

logger = logging.getLogger("web.lifespan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for FastAPI app startup and shutdown."""
    from web.security import enforce_remote_auth_at_startup
    from novel_agent.logging_config import setup_logging

    enforce_remote_auth_at_startup()
    setup_logging(context.BASE_DIR / "logs")

    project_manager = ProjectManager(context.BASE_DIR)

    # V2 never guesses that global runtime folders are a book. Projects must be
    # explicitly created/imported and registered in projects.json.
    context._active_project_id = project_manager.get_active_id()

    if context._active_project_id:
        root = context.get_root_dir()
        _ensure_dirs(root)
        _init_prompt_defaults(root)
        ProjectTaskRegistry.shared().get(root)
        from novel_agent.pipeline import llm_config_error

        llm_err = llm_config_error(root)
        if llm_err:
            logger.warning("LLM not ready for active project: %s", llm_err)
        try:
            from novel_agent.state.yaml_mirror import check_yaml_mirror_drift

            drift = check_yaml_mirror_drift(root)
            for warning in drift:
                logger.warning("YAML mirror drift: %s", warning)
        except Exception as exc:
            logger.debug("YAML mirror startup check skipped: %s", exc)

    _init_prompt_defaults(context.BASE_DIR)

    from web.task_ws_hub import start_task_broadcast_loop

    broadcast_task = start_task_broadcast_loop()

    yield

    broadcast_task.cancel()
    logger.info("FastAPI web service shutdown complete")
