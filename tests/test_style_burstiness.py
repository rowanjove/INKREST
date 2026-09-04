from novel_agent.quality.style_rules import check_anti_ai_flavor, check_text_burstiness


def test_triadic_pattern_detection():
    # 包含三元排比
    text_with_triadic = (
        "主角心中满是痛苦、绝望与不甘。周围不仅风声呼啸而且雷电轰鸣更是大雨倾盆。"
    )
    result = check_anti_ai_flavor(text_with_triadic)
    assert result["triadic_hits"] >= 1
    assert any("三元并列" in d or "三重递进" in d for d in result["details"])


def test_burstiness_metric_uniform_vs_varied():
    # 模拟高度等长（典型的低呼吸感 AI 输出：每句都在 20 字左右）
    monotonous_text = (
        "他握紧手中的青色长剑快步穿过了漫长幽暗的走廊。\n"
        "空气中弥漫着一股刺鼻的血腥味令他感到无比的压抑。\n"
        "远处隐隐约约传来了巡逻守卫沉重而又机械的脚步声。\n"
        "他小心翼翼地屏住呼吸迅速隐入旁边冰冷的阴影之中。\n"
        "四周的一切在这一刻仿佛完全彻底地陷入了死寂之中。\n"
        "他不知道接下来的路究竟还会有怎样的危险在等待着。"
    )
    mono_res = check_text_burstiness(monotonous_text)
    assert mono_res["coefficient_of_variation"] < 0.35

    # 模拟长短句错落、有单句成段的真人风格
    varied_text = (
        "剑光炸开。\n"
        "他侧身，翻滚，反手一刺！\n"
        "锋利的剑尖毫无阻碍地切开了对方的护体罡气，在昏暗的夜色中带起一串滚烫耀眼的血花。\n"
        "死了。\n"
        "他大口大口喘着粗气，后背早已被冰冷的夜汗浸透，整条右臂剧烈痉挛着几乎握不住剑柄。\n"
        "走！"
    )
    varied_res = check_text_burstiness(varied_text)
    assert varied_res["coefficient_of_variation"] >= 0.35
    assert varied_res["single_sentence_para_ratio"] > 0
    assert varied_res["pass"] is True
