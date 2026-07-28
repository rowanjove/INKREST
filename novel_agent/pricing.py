"""Model token pricing helpers (USD per 1k tokens, blended CNY estimates)."""

from __future__ import annotations

from typing import Dict, Tuple

# (input_usd_per_1k, output_usd_per_1k) — aligned with orchestrator._persist_llm_cost
_MODEL_PRICES_USD: Dict[str, Tuple[float, float]] = {
    "gpt-4o-mini": (0.001, 0.004),
    "gpt-4o": (0.036, 0.108),
    "gpt-5": (0.036, 0.108),
    "claude-3-5-sonnet": (0.021, 0.108),
    "claude-sonnet": (0.021, 0.108),
    "claude-opus": (0.036, 0.108),
    "deepseek-chat": (0.001, 0.002),
    "deepseek-coder": (0.001, 0.002),
    "deepseek-v4": (0.001, 0.002),
    "gemini": (0.001, 0.003),
}

_DEFAULT_USD: Tuple[float, float] = (0.001, 0.003)
_USD_TO_CNY = 7.2
# Chapter pipeline skew: more prompt than completion
_BLEND_INPUT_WEIGHT = 0.7
_BLEND_OUTPUT_WEIGHT = 0.3


def resolve_model_prices_usd(model_name: str) -> Tuple[float, float]:
    """Return (input, output) USD per 1k tokens for a model id or API model string."""
    key = (model_name or "").lower()
    if not key:
        return _DEFAULT_USD
    for pattern, prices in _MODEL_PRICES_USD.items():
        if pattern in key:
            return prices
    return _DEFAULT_USD


def usd_to_cny(amount_usd: float, *, usd_cny: float = _USD_TO_CNY) -> float:
    """Convert a USD cost estimate to CNY for persisted cost fields."""
    return amount_usd * usd_cny


def blended_cny_per_1k_tokens(model_name: str, *, usd_cny: float = _USD_TO_CNY) -> float:
    """Single blended ¥/1k tokens for UI rough estimates."""
    in_usd, out_usd = resolve_model_prices_usd(model_name)
    blended_usd = in_usd * _BLEND_INPUT_WEIGHT + out_usd * _BLEND_OUTPUT_WEIGHT
    return blended_usd * usd_cny


def pricing_hint_for_model(model_id: str, model_entry: Dict) -> Dict[str, float]:
    """Attachable pricing hints for API model list responses."""
    name = str(model_entry.get("model") or model_entry.get("name") or model_id)
    in_usd, out_usd = resolve_model_prices_usd(name)
    blended_cny = blended_cny_per_1k_tokens(name)
    return {
        "input_price_per_1k_usd": in_usd,
        "output_price_per_1k_usd": out_usd,
        "blended_price_per_1k_cny": round(blended_cny, 4),
    }
