import json
import tempfile
import unittest
from pathlib import Path

from scripts.cleanup_v2_runtime import (
    CONFIRMATION,
    UnsafeCleanupTarget,
    cleanup_root,
    main,
)


class CleanupV2RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="novel-agent-cleanup-v2-")
        self.root = Path(self.tmp.name)
        (self.root / "projects" / "registered").mkdir(parents=True)
        (self.root / "projects" / "orphan").mkdir()
        (self.root / "projects.json").write_text(
            json.dumps({"projects": {"registered": {"name": "Keep"}}}),
            encoding="utf-8",
        )
        for name in ("data", "state", "workspace", "logs"):
            path = self.root / name
            path.mkdir()
            (path / "runtime.txt").write_text(name, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_dry_run_reports_without_deleting(self):
        report = cleanup_root(self.root, remove_runtime_roots=True)

        self.assertEqual(report.orphan_projects, ["orphan"])
        self.assertEqual(report.runtime_roots, ["data", "state", "workspace", "logs"])
        self.assertTrue((self.root / "projects" / "orphan").is_dir())
        self.assertTrue((self.root / "data").is_dir())

    def test_execute_preserves_registered_project_and_removes_exact_targets(self):
        report = cleanup_root(
            self.root,
            execute=True,
            remove_runtime_roots=True,
        )

        self.assertTrue(report.execute)
        self.assertTrue((self.root / "projects" / "registered").is_dir())
        self.assertFalse((self.root / "projects" / "orphan").exists())
        for name in ("data", "state", "workspace", "logs"):
            self.assertFalse((self.root / name).exists())

    def test_refuses_symlinked_orphan(self):
        link = self.root / "projects" / "linked"
        try:
            link.symlink_to(self.root / "projects" / "orphan", target_is_directory=True)
        except OSError:
            self.skipTest("Directory symlinks are unavailable")

        with self.assertRaises(UnsafeCleanupTarget):
            cleanup_root(self.root)

    def test_execute_requires_exact_confirmation(self):
        with self.assertRaises(SystemExit):
            main([str(self.root), "--execute", "--confirmation", "CLEAN"])

        result = main(
            [
                str(self.root),
                "--execute",
                "--confirmation",
                CONFIRMATION,
            ]
        )
        self.assertEqual(result, 0)

