import json
import tempfile
import unittest
from pathlib import Path

from novel_agent.control.factory_policy import (
    DEFAULT_FACTORY_MODE,
    load_project_factory_mode,
    resolve_factory_runtime_effects,
)
from novel_agent.control.runtime_policy import get_audit_profile_flags, resolve_runtime_policy
from novel_agent.quality.settings import resolve_quality_auto_rewrite, resolve_quality_mode
from novel_agent.services.novel_run_guard import build_readiness_report


class FactoryModePolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="factory-policy-"))

    def _write_meta(self, mode: str) -> None:
        config = self.tmpdir / "config"
        config.mkdir(parents=True, exist_ok=True)
        (config / "project_meta.json").write_text(
            json.dumps({"factory_mode": mode}, ensure_ascii=False),
            encoding="utf-8",
        )

    def _write_outline(self, scale: str = "medium") -> None:
        workspace = self.tmpdir / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "outline.json").write_text(
            json.dumps(
                {
                    "chosen_title": "测试书",
                    "macro_outline": [{"arc_id": "a1", "title": "卷一"}],
                    "scale_profile": {"scale": scale, "target_chapters": 120},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def _write_pipeline(self, **sections) -> None:
        config = self.tmpdir / "config"
        config.mkdir(parents=True, exist_ok=True)
        (config / "pipeline.yaml").write_text(
            "llm:\n  default:\n    provider: openai\n    model: test\n"
            "embedding:\n  provider: stub\n",
            encoding="utf-8",
        )
        if sections:
            import yaml

            data = yaml.safe_load((config / "pipeline.yaml").read_text(encoding="utf-8"))
            for key, value in sections.items():
                data[key] = value
            (config / "pipeline.yaml").write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

    def test_default_mode_without_meta(self):
        self.assertEqual(load_project_factory_mode(self.tmpdir), DEFAULT_FACTORY_MODE)
        effects = resolve_factory_runtime_effects(self.tmpdir)
        self.assertNotIn("quality_mode", effects)

    def test_newbie_auto_explicit_sets_block_on_fail(self):
        self._write_meta("newbie_auto")
        self._write_pipeline(chapter={"quality_mode": "report_only"})
        self.assertEqual(resolve_quality_mode(self.tmpdir), "block_on_fail")

    def test_platform_review_uses_premium_audit_profile(self):
        self._write_meta("platform_review")
        self._write_outline("medium")
        policy = resolve_runtime_policy(self.tmpdir)
        self.assertEqual(policy.factory_mode, "platform_review")
        self.assertEqual(policy.audit_profile, "premium")
        self.assertEqual(policy.pipeline_tier, "premium")
        flags = get_audit_profile_flags(self.tmpdir)
        self.assertFalse(flags.get("skip_continuity"))
        self.assertEqual(flags.get("max_rewrites_override"), 2)

    def test_author_copilot_uses_report_only_quality_mode(self):
        self._write_meta("author_copilot")
        self._write_pipeline(chapter={"quality_mode": "block_on_fail"})
        self.assertEqual(resolve_quality_mode(self.tmpdir), "report_only")
        self.assertFalse(resolve_quality_auto_rewrite(self.tmpdir))

    def test_newbie_auto_enables_quality_auto_rewrite(self):
        self._write_meta("newbie_auto")
        self._write_pipeline(chapter={"quality_auto_rewrite": False})
        self.assertTrue(resolve_quality_auto_rewrite(self.tmpdir))

    def test_longform_stable_blocks_continue_when_vector_stub_on_long_scale(self):
        self._write_meta("longform_stable")
        self._write_outline("long")
        self._write_pipeline()
        assets = self.tmpdir / "assets"
        assets.mkdir(parents=True)
        for name in ("world_bible.md", "style_guide.md", "rules.yaml", "sensitive_words.txt"):
            (assets / name).write_text("x", encoding="utf-8")
        (self.tmpdir / "workspace" / "arc_001.json").write_text("{}", encoding="utf-8")

        report = build_readiness_report(self.tmpdir)
        pending_ids = [item["id"] for item in report.get("pending") or []]
        self.assertIn("vector", pending_ids)
        self.assertFalse(report.get("ok"))

    def test_longform_stable_with_real_embedding_not_pending_vector(self):
        self._write_meta("longform_stable")
        self._write_outline("long")
        self._write_pipeline(embedding={"provider": "openai", "model": "text-embedding-3-small"})
        assets = self.tmpdir / "assets"
        assets.mkdir(parents=True)
        for name in ("world_bible.md", "style_guide.md", "rules.yaml", "sensitive_words.txt"):
            (assets / name).write_text("x", encoding="utf-8")
        (self.tmpdir / "workspace" / "arc_001.json").write_text("{}", encoding="utf-8")

        report = build_readiness_report(self.tmpdir)
        pending_ids = [item["id"] for item in report.get("pending") or []]
        self.assertNotIn("vector", pending_ids)

    def test_resolve_factory_runtime_effects_includes_mode_key(self):
        self._write_meta("studio")
        effects = resolve_factory_runtime_effects(self.tmpdir)
        self.assertEqual(effects["factory_mode"], "studio")
        self.assertEqual(effects.get("batch_fail_streak_max"), 3)

    def test_vector_readiness_override_ignore(self):
        self._write_meta("longform_stable")
        self._write_outline("long")
        import yaml

        config = self.tmpdir / "config"
        config.mkdir(parents=True, exist_ok=True)
        (config / "pipeline.yaml").write_text(
            yaml.safe_dump(
                {
                    "llm": {"default": {"provider": "openai", "model": "test"}},
                    "embedding": {"provider": "stub"},
                    "runtime": {"vector_readiness": "ignore"},
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        assets = self.tmpdir / "assets"
        assets.mkdir(parents=True)
        for name in ("world_bible.md", "style_guide.md", "rules.yaml", "sensitive_words.txt"):
            (assets / name).write_text("x", encoding="utf-8")
        (self.tmpdir / "workspace" / "arc_001.json").write_text("{}", encoding="utf-8")

        report = build_readiness_report(self.tmpdir)
        pending_ids = [item["id"] for item in report.get("pending") or []]
        self.assertNotIn("vector", pending_ids)


if __name__ == "__main__":
    unittest.main()