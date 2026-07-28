"""Mirror checks for frontend tokenCostEstimate helpers (via contract file)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ESTIMATE = ROOT / "web" / "frontend" / "src" / "utils" / "tokenCostEstimate.ts"


def test_unknown_daily_model_does_not_fallback_to_first_model() -> None:
    source = ESTIMATE.read_text(encoding="utf-8")
    assert "models[0]" not in source
    assert "未知模型" in source