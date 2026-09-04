import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

import web.context as ctx


class RequireProjectRootTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="require-project-root-"))
        self.original_base = ctx.BASE_DIR
        self.original_active = ctx._active_project_id
        ctx.BASE_DIR = self.tmpdir
        ctx._active_project_id = None

    def tearDown(self):
        ctx.BASE_DIR = self.original_base
        ctx._active_project_id = self.original_active

    def test_app_workspace_without_open_book_is_rejected(self):
        (self.tmpdir / "projects").mkdir()
        (self.tmpdir / "projects.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(HTTPException) as raised:
            ctx.require_project_root()
        self.assertEqual(raised.exception.status_code, 400)

    def test_legacy_single_book_root_is_still_allowed(self):
        (self.tmpdir / "workspace").mkdir()
        self.assertEqual(ctx.require_project_root(), self.tmpdir)
