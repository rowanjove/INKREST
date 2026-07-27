import json
import tempfile
import unittest
from pathlib import Path

import yaml

from novel_agent.state.manager import StateManager
from novel_agent.state.yaml_mirror import (
    check_yaml_mirror_drift,
    export_yaml_mirror,
    is_yaml_mirror_enabled,
    resolve_yaml_mirror_mode,
)


class YamlMirrorTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="yaml-mirror-"))
        config = self.tmpdir / "config"
        config.mkdir(parents=True)
        (config / "pipeline.yaml").write_text(
            "llm:\n  default:\n    provider: static\n",
            encoding="utf-8",
        )

    def _write_runtime_flag(self, enabled: bool) -> None:
        path = self.tmpdir / "config" / "pipeline.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["runtime"] = {"yaml_mirror_enabled": enabled}
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def test_yaml_mirror_enabled_by_default(self):
        self.assertFalse(is_yaml_mirror_enabled(self.tmpdir))
        self.assertEqual(resolve_yaml_mirror_mode(self.tmpdir), "off")

    def test_yaml_mirror_can_be_disabled(self):
        self._write_runtime_flag(False)
        self.assertFalse(is_yaml_mirror_enabled(self.tmpdir))

    def test_yaml_mirror_read_only_mode(self):
        path = self.tmpdir / "config" / "pipeline.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["runtime"] = {"yaml_mirror_mode": "read_only"}
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        self.assertEqual(resolve_yaml_mirror_mode(self.tmpdir), "read_only")
        self.assertFalse(is_yaml_mirror_enabled(self.tmpdir))

    def test_export_yaml_mirror_writes_state_files(self):
        from novel_agent.state.sqlite_store import SQLiteStateStore

        store = SQLiteStateStore(self.tmpdir)
        store.sync_state_update(
            "001",
            {"events": [{"id": "e1", "summary": "exported", "confidence": 1.0}]},
        )
        counts = export_yaml_mirror(self.tmpdir)
        self.assertEqual(counts.get("events"), 1)
        self.assertTrue((self.tmpdir / "state" / "events.yaml").is_file())

    def test_state_manager_skips_yaml_when_mirror_disabled(self):
        self._write_runtime_flag(False)
        state_dir = self.tmpdir / "state"
        state_dir.mkdir(parents=True)
        manager = StateManager(self.tmpdir)
        manager.apply_update(
            "001",
            {"events": [{"id": "e1", "summary": "test", "confidence": 1.0}]},
        )
        self.assertFalse((state_dir / "events.yaml").exists())

    def test_drift_check_reports_count_mismatch(self):
        from novel_agent.state.sqlite_store import SQLiteStateStore

        # 1. Test write mode drift warning
        self._write_runtime_flag(True)  # Set yaml_mirror_enabled to true -> mode: write
        state_dir = self.tmpdir / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "events.yaml").write_text(
            yaml.safe_dump({"events": [{"id": "e1"}, {"id": "e2"}]}, allow_unicode=True),
            encoding="utf-8",
        )
        store = SQLiteStateStore(self.tmpdir)
        store.sync_state_update(
            "001",
            {"events": [{"id": "e1", "summary": "one"}]},
        )
        warnings = check_yaml_mirror_drift(self.tmpdir)
        self.assertTrue(any("events.yaml" in item for item in warnings))

        # 2. Test read_only mode import warning (SQLite empty, YAML has data)
        store.clear_narrative_state()

        # Set mode to read_only
        path = self.tmpdir / "config" / "pipeline.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["runtime"] = {"yaml_mirror_mode": "read_only"}
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

        warnings_ro = check_yaml_mirror_drift(self.tmpdir)
        self.assertTrue(any("SQLite" in item and "state/events.yaml" in item for item in warnings_ro))


if __name__ == "__main__":
    unittest.main()
