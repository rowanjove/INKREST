from novel_agent.pipeline import (
    DEFAULT_LLM_ROLE_TIERS,
    _resolve_tiered_overrides,
)


def test_default_role_tiers_contain_three_tiers():
    # 验证三大层级正确划分
    assert DEFAULT_LLM_ROLE_TIERS["chief_editor"] == "reasoning"
    assert DEFAULT_LLM_ROLE_TIERS["auditor"] == "reasoning"
    assert DEFAULT_LLM_ROLE_TIERS["writer"] == "daily"
    assert DEFAULT_LLM_ROLE_TIERS["style_editor"] == "daily"
    assert DEFAULT_LLM_ROLE_TIERS["length_fix"] == "fast"
    assert DEFAULT_LLM_ROLE_TIERS["chapter_summary"] == "fast"
    assert DEFAULT_LLM_ROLE_TIERS["compressor"] == "fast"


def test_resolve_tiered_overrides_with_fast_model():
    llm_settings = {
        "daily_model_id": "claude-3-5-sonnet",
        "reasoning_model_id": "claude-3-7-reasoning",
        "fast_model_id": "gemini-2-5-flash",
    }
    routed = _resolve_tiered_overrides(llm_settings, {})
    
    # 验证 Tier 1 路由至 reasoning
    assert routed["chief_editor"]["model_ref"] == "claude-3-7-reasoning"
    assert routed["auditor"]["model_ref"] == "claude-3-7-reasoning"

    # 验证 Tier 2 路由至 daily
    assert routed["writer"]["model_ref"] == "claude-3-5-sonnet"
    assert routed["style_editor"]["model_ref"] == "claude-3-5-sonnet"

    # 验证 Tier 3 路由至 fast
    assert routed["length_fix"]["model_ref"] == "gemini-2-5-flash"
    assert routed["chapter_summary"]["model_ref"] == "gemini-2-5-flash"


def test_resolve_tiered_overrides_backward_compatibility():
    # 没有配置 fast_model_id 时，自动 fallback 到 daily_model_id
    llm_settings = {
        "daily_model_id": "deepseek-v3",
        "reasoning_model_id": "deepseek-r1",
    }
    routed = _resolve_tiered_overrides(llm_settings, {})
    assert routed["length_fix"]["model_ref"] == "deepseek-v3"
    assert routed["chapter_summary"]["model_ref"] == "deepseek-v3"
