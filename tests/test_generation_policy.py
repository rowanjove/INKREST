"""Tests for generation / de-AI pipeline policy helpers."""

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from novel_agent.quality.audit_rewrite import audit_requires_rewrite
from novel_agent.quality.generation_policy import (
    build_writer_anti_ai_block,
    should_length_fix_after_audit_rewrite,
    should_run_boundary_recheck,
    should_run_generation_style_edit,
)
from novel_agent.quality.style_precheck import (
    compute_style_rule_checks,
    load_style_precheck_cache,
    write_style_precheck_cache,
)
from novel_agent.quality.report import build_quality_report
from novel_agent.phases.base import ChapterContext
from novel_agent.phases.generation import GenerationPhase
from novel_agent.pipeline import PipelineConfig
from novel_agent.orchestrator import NovelOrchestrator


class TestGenerationPolicy(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def _write_pipeline(self, chapter: dict):
        cfg_dir = self.tmpdir / "config"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "pipeline.yaml").write_text(
            yaml.safe_dump({"chapter": chapter, "runtime": {"pipeline_tier": "standard"}}),
            encoding="utf-8",
        )

    def test_audit_requires_rewrite_on_ai_flavor_high(self):
        audit = {
            "risk_level": "低",
            "issues": [
                {
                    "type": "ai_flavor",
                    "severity": "high",
                    "target_text": "不禁",
                }
            ],
        }
        self.assertTrue(audit_requires_rewrite(audit))

    def test_audit_requires_rewrite_on_ai_flavor_medium_when_block_on_fail(self):
        self._write_pipeline({"quality_mode": "block_on_fail"})
        audit = {
            "risk_level": "低",
            "issues": [{"type": "ai_flavor", "severity": "medium", "target_text": "竟然"}],
        }
        self.assertTrue(audit_requires_rewrite(audit, root_dir=self.tmpdir))

    def test_generation_style_mode_gate_only_skips_style(self):
        self._write_pipeline({"generation_style_mode": "gate_only"})
        self.assertFalse(should_run_generation_style_edit(self.tmpdir))

    def test_generation_style_mode_auto_economy_uses_gate_only(self):
        cfg_dir = self.tmpdir / "config"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "pipeline.yaml").write_text(
            yaml.safe_dump(
                {"chapter": {"generation_style_mode": "auto"}, "runtime": {"pipeline_tier": "economy"}}
            ),
            encoding="utf-8",
        )
        self.assertFalse(should_run_generation_style_edit(self.tmpdir))

    def test_length_fix_after_rewrite_only_for_wordcount(self):
        self.assertFalse(should_length_fix_after_audit_rewrite([], {"status": "ok"}))
        self.assertTrue(
            should_length_fix_after_audit_rewrite(
                [{"type": "word_count_out_of_bounds"}], {"status": "ok"}
            )
        )
        self.assertTrue(should_length_fix_after_audit_rewrite([], {"status": "under"}))

    def test_style_precheck_cache_reused_in_quality_report(self):
        text = "这是一段测试正文，没有 AI 腔。"
        reports = self.tmpdir / "reports"
        write_style_precheck_cache(reports, text, self.tmpdir)
        cached = load_style_precheck_cache(reports, text)
        self.assertIsNotNone(cached)

        checks = compute_style_rule_checks(text, self.tmpdir)
        report = build_quality_report(text, style_precheck=cached, mode="report_only")
        self.assertEqual(report["checks"]["style"]["score"], cached["style"]["score"])
        self.assertEqual(
            report["checks"]["anti_ai_flavor"]["score"],
            checks["anti_ai_flavor"]["score"],
        )

        doc = json.loads((reports / "style_precheck.json").read_text(encoding="utf-8"))
        self.assertIn("fingerprint", doc)

    def test_writer_anti_ai_block_nonempty(self):
        block = build_writer_anti_ai_block(self.tmpdir)
        self.assertIn("不禁", block)

    def test_boundary_recheck_truncation_keeps_original_text(self):
        config = PipelineConfig.dry_run(self.tmpdir)
        phase = GenerationPhase(NovelOrchestrator(config))
        ctx = ChapterContext(
            chapter_id="001",
            chapter_goal="测试",
            chapter_dir=self.tmpdir / "ch001",
            scenes_dir=self.tmpdir / "ch001" / "scenes",
            reports_dir=self.tmpdir / "ch001" / "reports",
        )
        ctx.chapter_dir.mkdir(parents=True, exist_ok=True)
        original = "。".join(["这是第{}段场景衔接测试内容" for _ in range(40)])
        truncated = "短输出。"
        final, new_ctx = phase._finalize_boundary_recheck(ctx, original, truncated)
        self.assertEqual(final, original)
        self.assertTrue(
            any("truncated" in w.lower() or "截断" in w for w in new_ctx.warnings)
        )

    def test_write_style_precheck_cache_reuses_auditor_checks(self):
        from novel_agent.quality.audit_persist import split_audit_for_persist

        text = "林澈推开门，雨水滴在地上。"
        checks = compute_style_rule_checks(text, self.tmpdir)
        audit = {"risk_level": "低", "issues": [], "style_rule_checks": checks}
        reports = self.tmpdir / "reports"
        write_style_precheck_cache(
            reports, text, self.tmpdir, checks=split_audit_for_persist(audit)[1]
        )
        cached = load_style_precheck_cache(reports, text)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["style"]["score"], checks["style"]["score"])

    def test_audit_json_excludes_internal_style_rule_checks(self):
        from novel_agent.quality.audit_persist import split_audit_for_persist

        audit = {
            "risk_level": "低",
            "style_rule_checks": {"fingerprint": "abc", "style": {}, "anti_ai_flavor": {}},
        }
        public, checks = split_audit_for_persist(audit)
        self.assertNotIn("style_rule_checks", public)
        self.assertIsNotNone(checks)

    def test_boundary_recheck_skipped_without_style_when_configured(self):
        self._write_pipeline(
            {
                "boundary_recheck_after_style": True,
                "boundary_recheck_only_after_style": True,
            }
        )
        self.assertFalse(
            should_run_boundary_recheck(self.tmpdir, style_ran=False, scene_count=3)
        )
        self.assertTrue(
            should_run_boundary_recheck(self.tmpdir, style_ran=True, scene_count=3)
        )


if __name__ == "__main__":
    unittest.main()