"""Scene generation binding tests for CONTENT_LOCK persistence."""

import json
import tempfile
import unittest
from pathlib import Path

from novel_agent.agents.context_builder import ContextBuilderAgent


class TestSceneRenderBinding(unittest.TestCase):
    def test_context_builder_emits_and_persists_scene_content_lock(self):
        with tempfile.TemporaryDirectory(prefix="scene-render-binding-") as raw_root:
            root = Path(raw_root)
            builder = ContextBuilderAgent(root)
            scene = {
                "chapter_id": "004",
                "scene_id": "004-01",
                "pov": "林澈",
                "entry": "进入旧城区",
                "exit": "发现脚印",
                "must_include": ["发现脚印"],
                "must_not_include": ["不得揭露父亲身份"],
            }
            context = builder.build(
                "查明旧城区的异常",
                scene,
                plan={"immutable_facts": ["铜钥匙仍在林澈手中"]},
            )

            self.assertIn("[CONTENT_LOCK]", context)
            self.assertIn("发现脚印", context)
            contract_path = (
                root
                / "workspace"
                / "chapters"
                / "chapter_004"
                / "reports"
                / "scene_004-01_render_contract.json"
            )
            self.assertTrue(contract_path.is_file())
            payload = json.loads(contract_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["stage"], "scene_generation")
            self.assertEqual(payload["content_lock"]["scene_id"], "004-01")
            self.assertIn("铜钥匙仍在林澈手中", payload["content_lock"]["immutable_canon_facts"])


if __name__ == "__main__":
    unittest.main()
