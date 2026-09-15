import pytest
from pathlib import Path
from pydantic import BaseModel, Field

from plugins.script_murder.package.services.model_service import ModelService


class SampleModel(BaseModel):
    name: str
    count: int = Field(..., ge=1)


def test_prompt_loading():
    root = Path(__file__).resolve().parent.parent.parent.parent
    svc = ModelService(root)
    base_text = svc.load_prompt("base_contract")
    assert "唯一事实源原则" in base_text
    assert "严格认知四象限" in base_text

    truth_prompt = svc.build_system_prompt("truth_architect")
    assert "案件真相架构师" in truth_prompt
    assert "唯一事实源原则" in truth_prompt


def test_json_extraction():
    root = Path(__file__).resolve().parent.parent.parent.parent
    svc = ModelService(root)

    # Markdown fence
    fence_input = "这是模型回复：\n```json\n{\"name\": \"test_case\", \"count\": 5}\n```\n谢谢！"
    data = svc.extract_json(fence_input)
    assert data["name"] == "test_case"
    assert data["count"] == 5

    # Plain JSON
    plain_input = "  {\"name\": \"direct\", \"count\": 2}  "
    data2 = svc.extract_json(plain_input)
    assert data2["name"] == "direct"


def test_self_healing_model_fallback():
    root = Path(__file__).resolve().parent.parent.parent.parent
    svc = ModelService(root)
    # Test generation with offline fallback
    from plugins.script_murder.package.schemas import TruthCanon
    canon = svc.generate_structured(
        role="truth_architect",
        system_prompt="system",
        user_prompt="prompt",
        response_model=TruthCanon,
    )
    assert canon.victim != ""
    assert canon.killer == "CHAR_02"
    assert len(canon.facts) >= 1
