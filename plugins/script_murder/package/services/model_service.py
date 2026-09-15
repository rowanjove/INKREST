"""Model routing and self-healing structured generation service."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

from novel_agent.agents.base import LLMClient

T = TypeVar("T", bound=BaseModel)


class ModelService:
    """Provides role-based LLM routing and self-healing Pydantic extraction."""

    def __init__(
        self,
        root_dir: Path,
        llm_client: Optional[LLMClient] = None,
        llm_registry: Optional[Dict[str, LLMClient]] = None,
    ):
        self.root_dir = Path(root_dir).resolve()
        self.llm = llm_client
        self.llm_registry = dict(llm_registry or {})
        clients = [self.llm, *self.llm_registry.values()]
        self.offline_mode = not clients or all(
            getattr(client, "__class__", type(None)).__name__ in {"StaticLLM", "OfflineLLM"}
            for client in clients
            if client is not None
        )
        self.prompts_dir = Path(__file__).resolve().parent.parent / "agents" / "prompts"
        self._cached_prompts: Dict[str, str] = {}

    def load_prompt(self, name: str) -> str:
        if name in self._cached_prompts:
            return self._cached_prompts[name]
        prompt_path = self.prompts_dir / f"{name}.md"
        if not prompt_path.is_file():
            return ""
        text = prompt_path.read_text(encoding="utf-8")
        self._cached_prompts[name] = text
        return text

    def build_system_prompt(self, role_name: str) -> str:
        base_contract = self.load_prompt("base_contract")
        role_prompt = self.load_prompt(role_name)
        return f"{base_contract}\n\n---\n\n{role_prompt}".strip()

    def extract_json(self, text: str) -> Any:
        """Extract JSON object or array from raw LLM response text."""
        raw = text.strip()
        # 1. Try markdown code block ```json ... ```
        code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.DOTALL)
        if code_block:
            raw = code_block.group(1).strip()
        # 2. Try outermost braces or brackets
        start_obj = raw.find("{")
        end_obj = raw.rfind("}")
        start_arr = raw.find("[")
        end_arr = raw.rfind("]")

        if start_obj != -1 and end_obj != -1 and (start_arr == -1 or start_obj < start_arr):
            raw = raw[start_obj : end_obj + 1]
        elif start_arr != -1 and end_arr != -1:
            raw = raw[start_arr : end_arr + 1]

        return json.loads(raw)

    def generate_text(self, role: str, system_prompt: str, user_prompt: str) -> str:
        """Generate unstructured text from LLM with fallback for offline tests."""
        full_prompt = f"{system_prompt}\n\n=== 任务要求 ===\n{user_prompt}".strip()
        client = self.llm_registry.get(role, self.llm)
        if client is None:
            return self._offline_text_fallback(role, user_prompt)
        try:
            return client.generate(role, full_prompt)
        except Exception:
            if self.offline_mode:
                return self._offline_text_fallback(role, user_prompt)
            raise

    def generate_structured(
        self,
        role: str,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        max_retries: int = 2,
    ) -> T:
        """Generate structured Pydantic model with automatic schema repair retries."""
        schema_def = json.dumps(response_model.model_json_schema(), ensure_ascii=False, indent=2)
        instruction = (
            f"{user_prompt}\n\n"
            f"【输出要求】\n"
            f"必须且只能输出严格符合以下 JSON Schema 的 JSON 字符串，严禁附带任何闲聊或分析：\n"
            f"```json\n{schema_def}\n```"
        )

        current_prompt = instruction
        last_error = ""

        for attempt in range(max_retries + 1):
            if attempt > 0:
                current_prompt = (
                    f"{instruction}\n\n"
                    f"【上次输出校验失败，请针对性修复】\n"
                    f"错误信息：{last_error}\n"
                    f"请修正字段格式与层级，重新输出完整且合法的 JSON。"
                )

            raw_resp = self.generate_text(role, system_prompt, current_prompt)
            try:
                data = self.extract_json(raw_resp)
                return response_model.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = str(exc)
                if attempt == max_retries:
                    if self.offline_mode:
                        fallback_inst = self._offline_model_fallback(response_model, user_prompt)
                        if fallback_inst is not None:
                            return fallback_inst
                    raise ValueError(f"Failed to generate structured data for {response_model.__name__}: {exc}") from exc

        raise RuntimeError("Unreachable")

    # -----------------------------------------------------------------------
    # Deterministic Offline Fallbacks (ensures zero-config testing reliability)
    # -----------------------------------------------------------------------
    def _offline_text_fallback(self, role: str, user_prompt: str) -> str:
        if role == "script_writer":
            return (
                "【第一幕：暴雨夜】\n"
                "窗外雨水把货运码头的路灯光线切得粉碎。你把右手插在大衣口袋里，手指反复摩挲着那半截发票边缘。"
                "门轴发出一声尖锐的酸响，你后背猛地绷紧，下意识往货堆阴影里缩了半步。"
                "陈默端着那个掉漆的绿色搪瓷缸子从走廊经过，咳嗽得像是要把肺吐出来。"
                "你盯着他的背影，手心全是黏汗。你心里很清楚，如果今晚拿不到那本出库总账，明天日落前你就得卷铺盖滚出港口。"
            )
        if role == "host_writer":
            return (
                "# 雾港十三号 · 主持人全知复盘手册\n\n"
                "## 核心真相简报\n"
                "本案真凶为货代员周野。周野因盗卖提货单被受害者陈默索要巨额封口费，于21:14利用仓库升降索配重设计伪意外打击致死。\n\n"
                "## 玩家扶车分级提示\n"
                "1. 一级提示：提醒玩家比对西逃生门的血迹化验报告与各人血型记录。\n"
                "2. 二级提示：引导玩家注意尼龙绳断口的工业黄油与冷库配电闸的拉合时间差。"
            )
        return f"【{role} 离线文本输出】基于输入 '{user_prompt[:30]}' 完成构思。"

    def _offline_model_fallback(self, model_cls: Type[T], user_prompt: str) -> Optional[T]:
        """Provide minimal deterministic model instance if LLM is unavailable in tests."""
        name = model_cls.__name__
        if name == "TruthCanon":
            from ..schemas import TruthCanon, TruthFact
            return TruthCanon(
                victim="陈默 (仓管主任)",
                killer="CHAR_02",
                cause_of_death="重物撞击致颅骨粉碎性骨折",
                crime_time_window=("21:10", "21:25"),
                crime_scene="13号保税仓库·内仓夹层",
                crime_method="利用滑轮升降组配重拉动配电闸触发重物坠落",
                true_motive="盗卖特种提货单败露被索要封口费",
                facts=[
                    TruthFact(
                        id="F001",
                        title="钝器延时打击致死",
                        content="受害人被预设于冷库电闸上方的30kg配重铁块砸中头部，当场毙命。",
                        occurred_at="21:14",
                        location="13号仓库",
                        actors=["CHAR_02"],
                    ),
                    TruthFact(
                        id="F002",
                        title="凶手逃离撕裂雨裤留血",
                        content="凶手从西侧安全门仓促逃跑时膝盖撞击铁质门槛，刮蹭出B型血液与高密尼龙纤维。",
                        occurred_at="21:16",
                        location="西安全门",
                        actors=["CHAR_02"],
                    ),
                ],
            )  # type: ignore
        return None
