import tempfile
import unittest
from pathlib import Path

import yaml

from novel_agent.services.long_form_preset import apply_long_form_preset, sync_pipeline_for_scale


class LongFormPresetTests(unittest.TestCase):
    def test_sync_when_scale_long(self):
        tmp = Path(tempfile.mkdtemp(prefix="novel-preset-"))
        (tmp / "config").mkdir(parents=True)
        (tmp / "config" / "pipeline.yaml").write_text("chapter: {}\nruntime: {}\n", encoding="utf-8")
        applied, scale = sync_pipeline_for_scale(tmp, scale="long")
        self.assertTrue(applied)
        self.assertEqual(scale, "long")
        loaded = yaml.safe_load((tmp / "config" / "pipeline.yaml").read_text(encoding="utf-8"))
        self.assertEqual(loaded["chapter"]["persona_evaluations"], "auto")
        self.assertEqual(loaded["runtime"]["merge_review_stages"], True)

    def test_sync_skips_short_scale(self):
        tmp = Path(tempfile.mkdtemp(prefix="novel-preset2-"))
        (tmp / "config").mkdir(parents=True)
        (tmp / "config" / "pipeline.yaml").write_text("chapter: {}\nruntime: {}\n", encoding="utf-8")
        applied, scale = sync_pipeline_for_scale(tmp, scale="short")
        self.assertFalse(applied)
        self.assertEqual(scale, "short")

    def test_apply_alias_does_not_force_long_when_scale_empty(self):
        tmp = Path(tempfile.mkdtemp(prefix="novel-preset3-"))
        (tmp / "config").mkdir(parents=True)
        (tmp / "workspace").mkdir(parents=True)
        (tmp / "workspace" / "outline.json").write_text(
            '{"scale_profile":{"scale":"short"}}',
            encoding="utf-8",
        )
        (tmp / "config" / "pipeline.yaml").write_text("chapter: {}\nruntime: {}\n", encoding="utf-8")
        _, resolved = apply_long_form_preset(tmp, scale="")
        self.assertEqual(resolved, "short")
        loaded = yaml.safe_load((tmp / "config" / "pipeline.yaml").read_text(encoding="utf-8"))
        self.assertNotIn("merge_review_stages", loaded.get("runtime") or {})