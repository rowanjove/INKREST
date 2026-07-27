import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import FastAPI

import web.context as context
from web.lifespan import lifespan


class V2LifespanTests(unittest.IsolatedAsyncioTestCase):
    async def test_global_runtime_folders_are_not_auto_migrated_into_a_project(self):
        original_base = context.BASE_DIR
        original_active = context._active_project_id
        with tempfile.TemporaryDirectory(prefix="novel-agent-lifespan-v2-") as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "workspace").mkdir()
            context.BASE_DIR = root
            context._active_project_id = "stale-project"
            broadcast = MagicMock()
            try:
                with (
                    patch("web.security.enforce_remote_auth_at_startup"),
                    patch("novel_agent.logging_config.setup_logging"),
                    patch("web.lifespan._init_prompt_defaults"),
                    patch(
                        "web.task_ws_hub.start_task_broadcast_loop",
                        return_value=broadcast,
                    ),
                ):
                    async with lifespan(FastAPI()):
                        self.assertIsNone(context._active_project_id)
                        self.assertFalse((root / "projects" / "default").exists())
                        self.assertFalse((root / "projects.json").exists())
            finally:
                context.BASE_DIR = original_base
                context._active_project_id = original_active

        broadcast.cancel.assert_called_once()

