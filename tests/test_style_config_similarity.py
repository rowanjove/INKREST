import unittest
import tempfile
import shutil
import yaml
from pathlib import Path
from novel_agent.quality.style_rules import (
    check_ai_style,
    check_anti_ai_flavor,
    check_reference_similarity,
    load_style_rules_config,
)
from novel_agent.quality.report import build_quality_report

class TestStyleConfigSimilarity(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-style-test-"))
        self.assets_dir = self.tmpdir / "assets"
        self.assets_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        import gc
        gc.collect()
        try:
            shutil.rmtree(self.tmpdir)
        except Exception:
            pass

    def test_custom_rule_weight_and_disable(self):
        # 1. 默认情况下，"不禁" 会触发 AI 味扣分
        text_with_bujin = "他不禁深吸一口气，心中暗道这不简单。"
        
        # 默认不传 config
        res_default = check_ai_style(text_with_bujin)
        score_default = res_default["score"]
        
        # 创建自定义配置：禁用 bujin 规则，并大幅提高 xi (深吸一口气) 规则的扣分权重
        config = {
            "rules": {
                "style_word_bujin": {"enabled": False, "weight": 1.0},
                "style_action_xi": {"enabled": True, "weight": 5.0}
            }
        }
        
        res_custom = check_ai_style(text_with_bujin, config)
        # 因为 bujin 规则被禁用，xi 规则的权重是 5.0，所以扣分主要来自 xi 规则（加权后占比高）
        self.assertNotIn("高频AI词：不禁", [d.split(" ")[0] for d in res_custom["details"]])
        self.assertTrue(any("深吸一口气" in d for d in res_custom["details"]))

    def test_reference_similarity_calculation(self):
        # 2. 测试文风相似度计算
        sample_text = "他，走了。她，哭了。为什么？这，就是命运。"
        ref_text = "我，笑了。你，怒了。凭什么？那，才是未来。"
        
        ref_path = self.assets_dir / "sample_prose.txt"
        ref_path.write_text(ref_text, encoding="utf-8")
        
        res = check_reference_similarity(sample_text, self.tmpdir)
        self.assertTrue(res["enabled"])
        self.assertGreater(res["score"], 50)
        self.assertTrue(any("标点特征重合度" in d for d in res["details"]))

    def test_build_quality_report_integration(self):
        # 3. 验证 build_quality_report 可以整合 similarity 检测
        ref_text = "我，笑了。你，怒了。"
        ref_path = self.assets_dir / "sample_prose.txt"
        ref_path.write_text(ref_text, encoding="utf-8")
        
        report = build_quality_report(
            final_text="他，走了。她，哭了。",
            previous_text=None,
            plugin_guards=None,
            root_dir=self.tmpdir
        )
        
        self.assertIn("reference_similarity", report["checks"])
        self.assertTrue(report["checks"]["reference_similarity"]["pass"])

if __name__ == "__main__":
    unittest.main()
