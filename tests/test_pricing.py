from novel_agent.pricing import blended_cny_per_1k_tokens, resolve_model_prices_usd


def test_resolve_deepseek_prices() -> None:
    in_usd, out_usd = resolve_model_prices_usd("deepseek-v4-flash")
    assert in_usd == 0.001
    assert out_usd == 0.002


def test_blended_cny_positive() -> None:
    cny = blended_cny_per_1k_tokens("gpt-4o-mini")
    assert cny > 0