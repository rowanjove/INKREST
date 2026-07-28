"""Model library tier slots: daily/reasoning exclusive, backup multi."""

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from web.model_library import ModelLibrary, SLOT_BACKUP, SLOT_DAILY, SLOT_REASONING


class ModelSlotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="novel-slots-"))
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        (self.repo / "projects.json").write_text("{}", encoding="utf-8")
        (self.repo / "config").mkdir()
        (self.repo / "config" / "pipeline.yaml").write_text(
            "llm:\n  daily_model_id: m-a\n  reasoning_model_id: m-b\n",
            encoding="utf-8",
        )
        (self.repo / "config" / "models.json").write_text(
            json.dumps(
                {
                    "models": {
                        "m-a": {"name": "A", "provider": "openai", "model": "a"},
                        "m-b": {"name": "B", "provider": "openai", "model": "b"},
                        "m-c": {"name": "C", "provider": "openai", "model": "c"},
                    }
                }
            ),
            encoding="utf-8",
        )
        self.project = self.repo / "projects" / "p1"
        self.project.mkdir(parents=True)
        self.lib = ModelLibrary(self.project)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_migrate_pipeline_into_slots(self):
        listed = {m["id"]: m["slot"] for m in self.lib.list_models()}
        self.assertEqual(listed.get("m-a"), SLOT_DAILY)
        self.assertEqual(listed.get("m-b"), SLOT_REASONING)

    def test_daily_exclusive(self):
        self.lib.set_model_slot("m-b", SLOT_DAILY)
        listed = {m["id"]: m["slot"] for m in self.lib.list_models()}
        self.assertEqual(listed["m-b"], SLOT_DAILY)
        self.assertEqual(listed["m-a"], "")
        slots = self.lib.get_slots()
        self.assertEqual(slots["daily"], "m-b")
        global_llm = yaml.safe_load(
            (self.repo / "config" / "pipeline.yaml").read_text(encoding="utf-8")
        )["llm"]
        self.assertEqual(global_llm["daily_model_id"], "m-b")

    def test_backup_multiple_and_fallback_ids(self):
        self.lib.set_model_slot("m-a", SLOT_BACKUP)
        self.lib.set_model_slot("m-c", SLOT_BACKUP)
        slots = self.lib.get_slots()
        self.assertEqual(set(slots["backup"]), {"m-a", "m-c"})
        global_llm = yaml.safe_load(
            (self.repo / "config" / "pipeline.yaml").read_text(encoding="utf-8")
        )["llm"]
        self.assertIn("m-a", global_llm["fallback_model_ids"])
        self.assertIn("m-c", global_llm["fallback_model_ids"])

    def test_reasoning_exclusive(self):
        self.lib.set_model_slot("m-c", SLOT_REASONING)
        self.lib.set_model_slot("m-b", SLOT_REASONING)
        slots = self.lib.get_slots()
        self.assertEqual(slots["reasoning"], "m-b")
        listed = {m["id"]: m["slot"] for m in self.lib.list_models()}
        self.assertEqual(listed["m-c"], "")
        self.assertEqual(listed["m-b"], SLOT_REASONING)


if __name__ == "__main__":
    unittest.main()