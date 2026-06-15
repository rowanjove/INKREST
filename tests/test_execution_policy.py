"""Execution policy: per-project chapter concurrency."""

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from novel_agent.services.execution_policy import (
    build_execution_snapshot,
    resolve_max_concurrent_chapters,
    resolve_scene_max_workers,
)


def _seed(root: Path, *, scale: str = "medium", target: int = 50, runtime=None) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "config").mkdir(parents=True, exist_ok=True)
    pipeline = {"llm": {"default": {"provider": "static"}}, "runtime": runtime or {}}
    (root / "config" / "pipeline.yaml").write_text(
        yaml.safe_dump(pipeline, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    (root / "workspace").mkdir(parents=True, exist_ok=True)
    outline = {
        "chosen_title": "并发测试",
        "target_chapters": target,
        "scale_profile": {"scale": scale, "target_chapters": target},
    }
    (root / "workspace" / "outline.json").write_text(
        json.dumps(outline, ensure_ascii=False),
        encoding="utf-8",
    )


class ExecutionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="execution-policy-"))

    def test_medium_defaults_to_two_concurrent_chapters(self):
        _seed(self.tmpdir, scale="medium", target=50)
        self.assertEqual(resolve_max_concurrent_chapters(self.tmpdir), 2)

    def test_long_defaults_to_one_concurrent_chapter(self):
        _seed(self.tmpdir, scale="long", target=200)
        self.assertEqual(resolve_max_concurrent_chapters(self.tmpdir), 1)

    def test_runtime_override_max_concurrent_chapters(self):
        _seed(
            self.tmpdir,
            scale="long",
            target=200,
            runtime={"max_concurrent_chapters": 3},
        )
        self.assertEqual(resolve_max_concurrent_chapters(self.tmpdir), 3)

    def test_scene_workers_from_max_workers(self):
        _seed(self.tmpdir, runtime={"max_workers": 6})
        self.assertEqual(resolve_scene_max_workers(self.tmpdir), 6)

    def test_execution_snapshot_includes_limits(self):
        _seed(self.tmpdir, scale="epic", target=800, runtime={"max_workers": 5})
        snap = build_execution_snapshot(self.tmpdir)
        self.assertEqual(snap["scale"], "epic")
        self.assertEqual(snap["max_concurrent_chapters"], 1)
        self.assertEqual(snap["max_scene_workers"], 5)


if __name__ == "__main__":
    unittest.main()