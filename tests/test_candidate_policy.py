from novel_agent.quality.candidate_policy import (
    CandidatePolicyConfig,
    evaluate_candidate_policy,
)


def test_default_policy_is_manual_and_report_only():
    result = evaluate_candidate_policy("005", explicit_mark=True)
    assert result["mode"] == "manual_only"
    assert result["generate"] is False
    assert result["report_only"] is True
    assert "explicit_mark" in result["reason_codes"]


def test_high_value_and_l1_risk_are_explainable_triggers():
    result = evaluate_candidate_policy(
        "010",
        volume_position=1,
        scene_kind="高潮",
        quality_report={
            "l0_pass": True,
            "quality_layers": {"L1": {"status": "review", "risk_score": 0.8}},
        },
        recent_metrics={"recent_rework_rate": 0.5},
    )
    assert result["recommend"] is True
    assert {"volume_start", "high_value_scene", "l0_pass_l1_risk", "rewrite_rise"}.issubset(result["reason_codes"])
    assert result["budget"]["chapter_cost_units"] == 3


def test_auto_requires_explicit_mark_and_budgets_are_bounded():
    config = CandidatePolicyConfig.from_mapping(
        {"mode": "auto", "chapter_cost_budget": 999, "volume_cost_budget": 1, "max_concurrency": 99}
    )
    assert config.chapter_cost_budget == 100
    assert config.volume_cost_budget == 100
    assert config.max_concurrency == 8
    assert evaluate_candidate_policy("1", scene_kind="reveal", config=config)["generate"] is False
    assert evaluate_candidate_policy("1", scene_kind="reveal", explicit_mark=True, config=config)["generate"] is True
