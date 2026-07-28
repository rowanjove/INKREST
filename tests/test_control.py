import json
import unittest
from pathlib import Path

from novel_agent.control.scale_profile import (
    build_upgrade_pressure,
    is_vector_enabled_for_project,
    load_outline_scale_profile,
    resolve_scale_profile,
)
from novel_agent.control.calibration import build_calibration_report


class TestScaleProfile(unittest.TestCase):
    def test_resolve_scale_profile_target_chapters(self):
        # 1. 极短篇 (target = 2) -> micro
        p_micro = resolve_scale_profile(target_chapters=2)
        self.assertEqual(p_micro["scale"], "micro")
        self.assertFalse(p_micro["vector_enabled"])
        self.assertEqual(p_micro["target_chapters"], 2)

        # 2. 短篇 (target = 10) -> short
        p_short = resolve_scale_profile(target_chapters=10)
        self.assertEqual(p_short["scale"], "short")
        self.assertFalse(p_short["vector_enabled"])

        # 3. 中篇 (target = 50) -> medium
        p_medium = resolve_scale_profile(target_chapters=50)
        self.assertEqual(p_medium["scale"], "medium")
        self.assertTrue(p_medium["vector_enabled"])
        self.assertEqual(p_medium["calibration_interval"], 20)

        # 4. 长篇 (target = 350) -> long
        p_long = resolve_scale_profile(target_chapters=350)
        self.assertEqual(p_long["scale"], "long")
        self.assertTrue(p_long["vector_enabled"])

        # 5. 巨著 (target = 1000) -> epic
        p_epic = resolve_scale_profile(target_chapters=1000)
        self.assertEqual(p_epic["scale"], "epic")
        self.assertTrue(p_epic["vector_enabled"])

    def test_resolve_scale_profile_by_label_and_scale(self):
        p_label = resolve_scale_profile(scale_label="长篇小说")
        self.assertEqual(p_label["scale"], "long")

        p_scale = resolve_scale_profile(scale="infinite")
        self.assertEqual(p_scale["scale"], "infinite")
        self.assertTrue(p_scale["vector_enabled"])

    def test_resolve_scale_profile_fallback(self):
        # 兜底测试
        p_fallback = resolve_scale_profile()
        self.assertEqual(p_fallback["scale"], "short")  # 默认 short

    def test_load_outline_scale_profile_from_workspace(self):
        root = Path(self._testMethodName + "_outline")
        root.mkdir(exist_ok=True)
        try:
            ws = root / "workspace"
            ws.mkdir(exist_ok=True)
            (ws / "outline.json").write_text(
                json.dumps({"scale_profile": {"scale": "short", "vector_enabled": False}}),
                encoding="utf-8",
            )
            profile = load_outline_scale_profile(root)
            self.assertEqual(profile["scale"], "short")
            self.assertFalse(is_vector_enabled_for_project(root))
        finally:
            import shutil
            shutil.rmtree(root, ignore_errors=True)

    def test_is_vector_enabled_without_outline_defaults_true(self):
        root = Path(self._testMethodName + "_legacy")
        root.mkdir(exist_ok=True)
        try:
            self.assertTrue(is_vector_enabled_for_project(root))
        finally:
            import shutil
            shutil.rmtree(root, ignore_errors=True)

    def test_build_upgrade_pressure(self):
        profile = {
            "scale": "short",
            "max_chapters": 20,
        }
        # 1. 章节数为 10 / 20 (50%) -> should_prompt 应为 False
        pres_low = build_upgrade_pressure(profile, 10)
        self.assertFalse(pres_low["should_prompt"])
        self.assertEqual(pres_low["ratio"], 0.5)

        # 2. 章节数为 17 / 20 (85%) -> should_prompt 应为 True，且推荐的 scale 为 medium
        pres_high = build_upgrade_pressure(profile, 17)
        self.assertTrue(pres_high["should_prompt"])
        self.assertEqual(pres_high["recommended_scale"], "medium")

        # 3. 无限连载 (max_chapters >= 999999) -> 永远不提示升级
        profile_inf = {
            "scale": "infinite",
            "max_chapters": 999999,
        }
        pres_inf = build_upgrade_pressure(profile_inf, 50000)
        self.assertFalse(pres_inf["should_prompt"])


class TestCalibration(unittest.TestCase):
    def test_build_calibration_report_overdue_debt(self):
        outline = {
            "genre_genes": {"pleasure_mechanism": "战斗爽"},
            "scale_profile": {"scale": "short"},
        }
        # 构造最近章节列表 (为了满足 build_pacing_report 至少会读取 chapters 且不抛错)
        # build_pacing_report 接收 chapters 并提取 word_count，计算步伐
        chapters = [
            {"id": "001", "word_count": 2000},
            {"id": "002", "word_count": 1800},
        ]
        # 构造包含逾期债务的 debt 映射
        debt = {
            "foreshadows": [
                {"id": "F001", "title": "神秘宝藏", "debt_status": "overdue"}
            ]
        }
        
        report = build_calibration_report(outline, chapters, debt)
        
        self.assertFalse(report["pass"])
        self.assertIn("存在过期叙事债务", report["issues"])
        self.assertEqual(report["overdue_debt_count"], 1)
        self.assertEqual(report["genre_genes"]["pleasure_mechanism"], "战斗爽")

    def test_build_calibration_report_clean(self):
        outline = {
            "genre_genes": {"pleasure_mechanism": "日常爽"},
            "scale_profile": {"scale": "micro"},
        }
        chapters = [
            {"id": "001", "word_count": 1500},
            {"id": "002", "word_count": 1600},
        ]
        # 无过期债务
        debt = {
            "foreshadows": [
                {"id": "F001", "title": "神秘人", "debt_status": "open"}
            ],
            "secrets": []
        }
        
        report = build_calibration_report(outline, chapters, debt)
        
        # 因为字数波动在合理范围内且没有 overdue 的债务，应该顺利通过
        self.assertTrue(report["pass"])
        self.assertEqual(report["issues"], [])
        self.assertEqual(report["overdue_debt_count"], 0)


if __name__ == "__main__":
    unittest.main()
