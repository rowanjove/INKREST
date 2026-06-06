"""Planner skip, persona evaluation policy, embedding honesty."""

import json
import tempfile
import unittest
from pathlib import Path

from novel_agent.control.runtime_policy import should_skip_chapter_planner
from novel_agent.quality.settings import (
    default_persona_mode_for_scale,
    quality_report_warrants_persona_eval,
    resolve_persona_evaluations,
    should_run_persona_evaluations,
)


class PipelineEfficiencyTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-efficiency-"))
        (self.tmpdir / "config").mkdir(parents=True, exist_ok=True)
        (self.tmpdir / "workspace").mkdir(parents=True, exist_ok=True)

    def _write_pipeline(self, yaml_text: str) -> None:
        (self.tmpdir / "config" / "pipeline.yaml").write_text(yaml_text, encoding="utf-8")

    def _write_outline_scale(self, scale: str) -> None:
        outline = {
            "title": "Test",
            "scale_profile": {"scale": scale, "planning_mode": "rolling_window"},
        }
        (self.tmpdir / "workspace" / "outline.json").write_text(
            json.dumps(outline, ensure_ascii=False), encoding="utf-8"
        )

    def test_persona_auto_defaults_long_to_off(self):
        self._write_pipeline("chapter:\n  persona_evaluations: auto\n")
        self._write_outline_scale("epic")
        self.assertEqual(resolve_persona_evaluations(self.tmpdir), "off")

    def test_persona_auto_medium_to_on_fail_only(self):
        self._write_pipeline("chapter:\n  persona_evaluations: auto\n")
        self._write_outline_scale("medium")
        self.assertEqual(resolve_persona_evaluations(self.tmpdir), "on_fail_only")

    def test_should_run_persona_only_on_fail(self):
        self._write_pipeline('chapter:\n  persona_evaluations: "on_fail_only"\n')
        passing = {"overall_pass": True, "guard_summary": {"overall_status": "PASS"}, "checks": {}}
        failing = {
            "overall_pass": False,
            "guard_summary": {"overall_status": "FAIL"},
            "checks": {},
        }
        self.assertFalse(should_run_persona_evaluations(self.tmpdir, passing))
        self.assertTrue(should_run_persona_evaluations(self.tmpdir, failing))
        self.assertTrue(quality_report_warrants_persona_eval(failing))

    def test_skip_planner_when_generation_complete_and_plan_hash_matches(self):
        plan = {"chapter_title": "T", "scenes": [{"scene_id": "s1", "purpose": "p"}]}
        from novel_agent.control.runtime_policy import goal_fingerprint, plan_fingerprint

        goal = "goal"
        cp = {
            "goal_hash": goal_fingerprint(goal),
            "plan_hash": plan_fingerprint(plan),
            "completed_stages": ["planner", "generation"],
            "last_stage": "generation",
        }
        skip, reason = should_skip_chapter_planner(cp, cp["completed_stages"], goal_fingerprint(goal), plan)
        self.assertTrue(skip)
        self.assertEqual(reason, "resume_from_checkpoint")

    def test_skip_planner_on_quality_blocked_with_matching_plan_hash(self):
        plan = {"chapter_title": "T", "scenes": []}
        from novel_agent.control.runtime_policy import goal_fingerprint, plan_fingerprint

        goal = "goal"
        cp = {
            "goal_hash": goal_fingerprint(goal),
            "plan_hash": plan_fingerprint(plan),
            "completed_stages": ["planner", "generation"],
            "last_stage": "quality_blocked",
            "resumable_from": "audit",
        }
        skip, reason = should_skip_chapter_planner(cp, cp["completed_stages"], goal_fingerprint(goal), plan)
        self.assertTrue(skip)
        self.assertEqual(reason, "resume_from_checkpoint")

    def test_replan_when_plan_hash_mismatch(self):
        plan = {"chapter_title": "T", "scenes": [{"scene_id": "new"}]}
        from novel_agent.control.runtime_policy import goal_fingerprint, plan_fingerprint

        goal = "goal"
        old_hash = plan_fingerprint({"chapter_title": "T", "scenes": [{"scene_id": "old"}]})
        cp = {
            "goal_hash": goal_fingerprint(goal),
            "plan_hash": old_hash,
            "completed_stages": ["planner", "generation"],
        }
        skip, reason = should_skip_chapter_planner(cp, cp["completed_stages"], goal_fingerprint(goal), plan)
        self.assertFalse(skip)
        self.assertEqual(reason, "plan_hash_mismatch")

    def test_default_persona_scale_map(self):
        self.assertEqual(default_persona_mode_for_scale("epic"), "off")
        self.assertEqual(default_persona_mode_for_scale("short"), "on_fail_only")