import json
import time
import asyncio
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional, Protocol, Set, Tuple

import httpx

from novel_agent.exceptions import (
    AgentError,
    LLMResponseError,
    LLMThinkingTruncatedError,
    RetryExhaustedError,
)
from novel_agent.logging_config import get_logger

logger = get_logger("agents.base")

def _assert_safe_model_base_url(base_url: str) -> None:
    from urllib.parse import urlparse

    from novel_agent.utils.network_security import (
        is_dev_model_host,
        is_loopback_host,
        validate_outbound_model_base_url,
    )

    host = urlparse(str(base_url or "")).hostname or ""
    if is_loopback_host(host) or is_dev_model_host(host):
        return
    validate_outbound_model_base_url(base_url)


# Re-export for backward compatibility
__all__ = [
    "AgentError",
    "LLMResponseError",
    "LLMThinkingTruncatedError",
    "RetryExhaustedError",
    "ReasoningPolicy",
    "LLMClient",
    "StaticLLM",
    "OpenAILLM",
    "PromptAgent",
    "FallbackLLM",
    "create_llm",
    "create_llm_registry",
    "register_llm_provider",
    "unregister_llm_provider",
]


class LLMClient(Protocol):
    def generate(self, role: str, prompt: str) -> str:
        """Return text generated for an agent role and prompt."""

    async def agenerate(self, role: str, prompt: str) -> str:
        """Return text generated asynchronously for an agent role and prompt."""


# ---------------------------------------------------------------------------
# StaticLLM mock response handlers (extracted from monolithic generate())
# ---------------------------------------------------------------------------

import re as _re


def _mock_stitch_editor(prompt: str) -> str:
    if "=== 场景A结尾 ===" in prompt:
        a_match = _re.search(r"=== 场景A结尾 ===\s*(.*?)\s*=== 场景B开头 ===", prompt, _re.DOTALL)
        b_match = _re.search(r"=== 场景B开头 ===\s*(.*)", prompt, _re.DOTALL)
        a_text = a_match.group(1).strip() if a_match else ""
        b_text = b_match.group(1).strip() if b_match else ""
        return f"{a_text}\n\n{b_text}"
    parts = prompt.split("输出完整章节正文。\n\n")
    if len(parts) > 1:
        return parts[-1].strip()
    return prompt.strip()


def _mock_style_editor(prompt: str) -> str:
    if "=== 待润色片段 ===" in prompt:
        match = _re.search(r"=== 待润色片段 ===\s*(.*?)(?:\s*===|$)", prompt, _re.DOTALL)
        if match:
            return match.group(1).strip()
    parts = prompt.split("输出完整修订版。\n\n")
    if len(parts) > 1:
        return parts[-1].strip()
    return prompt.strip()


def _mock_text_passthrough(prompt: str) -> str:
    parts = prompt.split("以下是待修正文本：\n")
    if len(parts) > 1:
        return parts[-1].strip()
    return prompt.strip()


def _mock_state_extractor(_prompt: str) -> str:
    return json.dumps({
        "events": [{"id": "E01_001", "summary": "故事开始，主角登场。", "characters": ["主角"], "objects": [], "threads": []}],
        "characters": {"主角": {"location": "小镇", "emotion": "平静", "physical_state": "正常"}},
        "objects": [],
        "threads": [],
        "foreshadows": [],
        "hooks": [],
        "character_behaviors": [],
        "character_memories": [],
        "character_relations": []
    }, ensure_ascii=False)


def _mock_chief_editor(_prompt: str) -> str:
    return json.dumps({
        "title_options": ["《干跑小说》"],
        "logline": "一个在静态测试模式下自动生成的故事描述",
        "core_theme": "成长",
        "genre_positioning": "都市",
        "target_reader": "测试读者",
        "reader_promise": ["精彩的故事"],
        "world_rules": ["现实世界"],
        "protagonist": {"name": "主角", "desire": "梦想", "flaw": "平凡", "edge": "努力", "limit": "时间"},
        "main_cast": [],
        "antagonistic_forces": [],
        "macro_outline": [{"arc_id": "A01", "name": "起步", "chapters": "1-3", "goal": "开始旅程", "turning_point": "抉择", "payoff": "出发"}],
        "forbidden_moves": []
    }, ensure_ascii=False)


def _mock_managing_editor(_prompt: str) -> str:
    return json.dumps({
        "arc_id": "A01",
        "arc_name": "起步",
        "arc_goal": "开始旅程",
        "chapters": [
            {"chapter_id": "001", "chapter_title": "第一章", "chapter_goal": "踏出第一步", "input_state": "起始", "output_state": "发展", "reader_payoff": "爽点", "hook": "悬念", "must_include": [], "must_not_include": []}
        ]
    }, ensure_ascii=False)


def _mock_chapter_planner(_prompt: str) -> str:
    return json.dumps({
        "chapter_id": "001",
        "chapter_title": "第一章",
        "detailed_synopsis": "这是静态模式下的章节规划内容。",
        "beats": [{"beat_id": "B01", "function": "起", "content": "起步", "state_change": "变化"}],
        "character_intents": [],
        "foreshadow_plan": [],
        "handoff_to_scene_planner": {"must_include": [], "must_not_include": []}
    }, ensure_ascii=False)


def _mock_planner(_prompt: str) -> str:
    return json.dumps({
        "chapter_id": "001",
        "chapter_title": "第一章",
        "target_chars": [1500, 2500],
        "scenes": [
            {"scene_id": "001-01", "target_chars": [800, 1200], "purpose": "引出故事", "entry": "开场", "exit": "收尾", "must_include": [], "must_not_include": []}
        ]
    }, ensure_ascii=False)


def _mock_auditor(_prompt: str) -> str:
    return json.dumps({"risk_level": "低", "issues": [], "state_update": {}}, ensure_ascii=False)


def _mock_continuity_checker(_prompt: str) -> str:
    return json.dumps({"pass": True, "issues": []}, ensure_ascii=False)


def _mock_asset_compressor(_prompt: str) -> str:
    return json.dumps({"compressed": True, "archived_threads": [], "removed_events": []}, ensure_ascii=False)


_STATIC_MOCK_HANDLERS: Dict[str, Any] = {
    "stitch_editor": _mock_stitch_editor,
    "style_editor": _mock_style_editor,
    "expander": _mock_text_passthrough,
    "compressor": _mock_text_passthrough,
    "length_fix": _mock_text_passthrough,
    "state_extractor": _mock_state_extractor,
    "chief_editor": _mock_chief_editor,
    "managing_editor": _mock_managing_editor,
    "chapter_planner": _mock_chapter_planner,
    "planner": _mock_planner,
    "auditor": _mock_auditor,
    "continuity_checker": _mock_continuity_checker,
    "asset_compressor": _mock_asset_compressor,
}

_DEFAULT_STATIC_RESPONSE = "这是一个占位输出。请接入真实模型后重新生成本段内容。"


@dataclass
class StaticLLM:
    """Deterministic LLM substitute for tests and dry runs."""

    responses: Dict[str, str] = field(default_factory=dict)

    def generate(self, role: str, prompt: str) -> str:
        if role in self.responses:
            return self.responses[role]

        handler = _STATIC_MOCK_HANDLERS.get(role)
        if handler is not None:
            return handler(prompt)

        return self.responses.get("default", _DEFAULT_STATIC_RESPONSE)

    async def agenerate(self, role: str, prompt: str) -> str:
        return self.generate(role, prompt)


@dataclass(frozen=True)
class ReasoningPolicy:
    """Standard policy resolving thinking / reasoning_effort across providers and roles."""

    thinking_enabled: bool
    reasoning_effort: Optional[str] = None
    strip_temperature: bool = False

    @classmethod
    def resolve(
        cls,
        role: str,
        model: str,
        *,
        user_thinking: Optional[bool] = None,
        user_reasoning_effort: Optional[str] = None,
        thinking_override: Optional[bool] = None,
    ) -> "ReasoningPolicy":
        model_str = str(model).lower()
        is_deepseek = any(tag in model_str for tag in ("deepseek-v4", "deepseek-r1", "deepseek-reasoner"))
        # Planning / reasoning roles default to thinking enabled on reasoning models;
        # creative writing / polishing roles (writer, expander, style_editor, stitch_editor) default to disabled.
        REASONING_ROLES = {
            "chief_editor",
            "chapter_planner",
            "planner",
            "auditor",
            "continuity_checker",
        }
        if thinking_override is not None:
            effective_thinking = thinking_override
        elif user_thinking is not None:
            effective_thinking = user_thinking
        elif is_deepseek:
            effective_thinking = role in REASONING_ROLES
        else:
            effective_thinking = False

        effort = user_reasoning_effort or ("high" if effective_thinking and is_deepseek else None)
        strip_temp = bool(is_deepseek and effective_thinking)
        return cls(
            thinking_enabled=effective_thinking,
            reasoning_effort=effort,
            strip_temperature=strip_temp,
        )

    def apply_to_payload(self, payload: Dict[str, Any], model: str) -> None:
        model_str = str(model).lower()
        is_deepseek = any(tag in model_str for tag in ("deepseek-v4", "deepseek-r1", "deepseek-reasoner"))
        if is_deepseek:
            payload["thinking"] = {"type": "enabled" if self.thinking_enabled else "disabled"}
            if self.thinking_enabled:
                if self.reasoning_effort:
                    payload["reasoning_effort"] = self.reasoning_effort
                if self.strip_temperature:
                    payload.pop("temperature", None)
        elif self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort


@dataclass
class OpenAILLM:
    """OpenAI-compatible chat completion client.

    Works with OpenAI, Ollama, vLLM, LiteLLM, and any provider
    that exposes the ``/v1/chat/completions`` endpoint.
    """

    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    max_tokens: int = 4096
    temperature: float = 0.7
    seed: Optional[int] = None
    timeout: float = 120.0
    max_retries: int = 3
    retry_delay: float = 1.0
    proxy: str = ""
    thinking: Optional[bool] = None
    reasoning_effort: Optional[str] = None

    def __post_init__(self):
        self._client: Optional[httpx.Client] = None
        self._aclient: Optional[httpx.AsyncClient] = None
        self.call_log: List[Dict[str, Any]] = []

    def _client_kwargs(self) -> Dict[str, Any]:
        client_kwargs: Dict[str, Any] = {"timeout": self.timeout}
        if self.proxy:
            client_kwargs["proxy"] = self.proxy
        return client_kwargs

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            kwargs = self._client_kwargs()
            from web.outbound import model_httpx_transport

            # Endpoint validation and DNS pinning are security boundaries.  If
            # they cannot be established, do not silently fall back to an
            # ordinary client which would re-resolve the host at connect time.
            transport = model_httpx_transport(self.base_url, async_mode=False)
            if transport is not None:
                if self.proxy:
                    raise ValueError(
                        "Model proxy cannot be combined with DNS pinning; "
                        "remove proxy or use a trusted local endpoint"
                    )
                kwargs["transport"] = transport
            self._client = httpx.Client(**kwargs)
        return self._client

    def _get_async_client(self) -> httpx.AsyncClient:
        if self._aclient is None or self._aclient.is_closed:
            kwargs = self._client_kwargs()
            from web.outbound import model_httpx_transport

            transport = model_httpx_transport(self.base_url, async_mode=True)
            if transport is not None:
                if self.proxy:
                    raise ValueError(
                        "Model proxy cannot be combined with DNS pinning; "
                        "remove proxy or use a trusted local endpoint"
                    )
                kwargs["transport"] = transport
            self._aclient = httpx.AsyncClient(**kwargs)
        return self._aclient

    # ---- shared helpers (eliminates ~100 lines of duplication) ----

    def _build_payload(
        self,
        role: str,
        prompt: str,
        max_tokens: Optional[int] = None,
        system_hint: Optional[str] = None,
        thinking_override: Optional[bool] = None,
    ) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
        """Build (url, headers, payload) for the chat/completions endpoint."""
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        system_content = f"你是{role}。"
        user_content = prompt
        if system_hint:
            system_content = f"{system_content}\n\n{system_hint}"
            user_content = f"{prompt}\n\n{system_hint}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "temperature": self.temperature,
        }
        if self.seed is not None:
            payload["seed"] = int(self.seed)

        policy = ReasoningPolicy.resolve(
            role,
            self.model,
            user_thinking=self.thinking,
            user_reasoning_effort=self.reasoning_effort,
            thinking_override=thinking_override,
        )
        policy.apply_to_payload(payload, self.model)
        return url, headers, payload

    _NON_RETRYABLE_STATUS: ClassVar[Set[int]] = {400, 401, 403, 404, 422}

    def _record_usage(
        self,
        data: Dict[str, Any],
        role: str,
        t0: float,
        *,
        outcome: str = "succeeded",
        finish_reason: Optional[str] = None,
    ) -> None:
        usage = data.get("usage") or {}
        if not isinstance(usage, dict) or not usage:
            return
        import uuid
        response_id = str(data.get("id") or "").strip()
        log = {
            "call_id": response_id or f"call_{uuid.uuid4().hex}",
            "provider_request_id": response_id,
            "role": role,
            "model": data.get("model", self.model),
            "prompt_tokens": int(usage.get("prompt_tokens") or 0),
            "completion_tokens": int(usage.get("completion_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
            "reasoning_tokens": int(
                ((usage.get("completion_tokens_details") or {}).get("reasoning_tokens"))
                or usage.get("reasoning_tokens")
                or 0
            ),
            "latency_ms": int((time.time() - t0) * 1000),
            "timestamp": time.time(),
            "outcome": outcome,
            "finish_reason": finish_reason or "",
        }
        from novel_agent.progress import record_llm_usage

        log["persisted"] = record_llm_usage(log)
        self.call_log.append(log)
        if len(self.call_log) > 1000:
            self.call_log = self.call_log[-1000:]

    def _process_response(self, resp: httpx.Response, role: str, t0: float) -> str:
        """Validate HTTP response, parse JSON, record metrics, return content.

        Raises LLMResponseError on non-retryable status or malformed payload.
        """
        if resp.status_code in self._NON_RETRYABLE_STATUS:
            error_body = resp.text[:500]
            raise LLMResponseError(f"Non-retryable HTTP {resp.status_code}: {error_body}")

        resp.raise_for_status()
        data = resp.json()

        if "choices" not in data or not data["choices"]:
            self._record_usage(data, role, t0, outcome="invalid_response")
            raise LLMResponseError("Invalid response structure: missing 'choices'")

        choice = data["choices"][0]
        msg = choice.get("message", {})
        result = (msg.get("content") or "").strip()
        finish_reason = choice.get("finish_reason")
        reasoning = (msg.get("reasoning_content") or "").strip()

        if not result:
            if finish_reason == "length" or (reasoning and len(reasoning) > 500):
                self._record_usage(
                    data,
                    role,
                    t0,
                    outcome="thinking_truncated",
                    finish_reason=finish_reason,
                )
                raise LLMThinkingTruncatedError(
                    f"模型思考过程超限截断 (finish_reason={finish_reason}, 思考长度={len(reasoning)} 字符)，未能输出有效正文内容。",
                    role=role,
                    model=str(data.get("model", self.model)),
                    finish_reason=str(finish_reason or ""),
                    usage=data.get("usage") or {},
                    recovery_action="escalate_tokens_and_concise_hint",
                )
            self._record_usage(
                data,
                role,
                t0,
                outcome="empty_content",
                finish_reason=finish_reason,
            )
            raise LLMResponseError("Empty response content")

        latency_ms = int((time.time() - t0) * 1000)
        usage = data.get("usage", {})
        self._record_usage(
            data,
            role,
            t0,
            outcome="succeeded",
            finish_reason=finish_reason,
        )
        logger.debug(
            "LLM call succeeded for role=%s, length=%d, tokens=%d, latency=%dms",
            role, len(result), usage.get("total_tokens", 0), latency_ms,
        )
        return result

    def clear_call_log(self) -> None:
        """Clear recorded call logs to free memory."""
        self.call_log.clear()

    # ---- public API ----

    def generate(self, role: str, prompt: str) -> str:
        from novel_agent.progress import check_aborted
        from novel_agent.control.model_rate_limit import enforce_model_call_rate_limit
        check_aborted()
        enforce_model_call_rate_limit()
        _assert_safe_model_base_url(self.base_url)
        current_max_tokens = self.max_tokens
        system_hint: str | None = None
        thinking_override: bool | None = None
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            check_aborted()
            t0 = time.time()
            url, headers, payload = self._build_payload(
                role,
                prompt,
                max_tokens=current_max_tokens,
                system_hint=system_hint,
                thinking_override=thinking_override,
            )
            try:
                resp = self._get_client().post(url, headers=headers, json=payload)
                return self._process_response(resp, role, t0)
            except (httpx.HTTPStatusError, httpx.RequestError, KeyError, LLMResponseError) as exc:
                last_error = exc
                logger.warning(
                    "LLM call attempt %d/%d failed for role=%s: %s",
                    attempt + 1, self.max_retries, role, exc,
                )
                if isinstance(exc, LLMResponseError) and "Non-retryable HTTP" in str(exc):
                    raise
                if isinstance(exc, LLMThinkingTruncatedError) or "模型思考过程超限截断" in str(exc):
                    old_tokens = current_max_tokens
                    current_max_tokens = min(max(current_max_tokens * 2, 8192), 16384)
                    system_hint = (
                        "【紧急生成指引】：上一轮生成由于思考链（Reasoning）过长消耗过多 Token 导致正文截断。"
                        "本轮请务必：极简思考（控制在 300 字以内），直接专注于输出高质量完整正文，严禁长篇展开内心推演。"
                    )
                    thinking_override = False
                    logger.warning(
                        "Thinking truncation detected: escalating max_tokens from %d to %d and adding concise-thinking directive (role=%s, attempt %d/%d)",
                        old_tokens, current_max_tokens, role, attempt + 1, self.max_retries,
                    )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
        logger.error("LLM call failed after %d attempts for role=%s", self.max_retries, role)
        raise RetryExhaustedError(
            f"OpenAI API call failed after {self.max_retries} attempts: {last_error}"
        )

    async def agenerate(self, role: str, prompt: str) -> str:
        from novel_agent.progress import check_aborted
        from novel_agent.control.model_rate_limit import enforce_model_call_rate_limit
        check_aborted()
        enforce_model_call_rate_limit()
        _assert_safe_model_base_url(self.base_url)
        current_max_tokens = self.max_tokens
        system_hint: str | None = None
        thinking_override: bool | None = None
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            check_aborted()
            t0 = time.time()
            url, headers, payload = self._build_payload(
                role,
                prompt,
                max_tokens=current_max_tokens,
                system_hint=system_hint,
                thinking_override=thinking_override,
            )
            try:
                resp = await self._get_async_client().post(url, headers=headers, json=payload)
                return self._process_response(resp, role, t0)
            except (httpx.HTTPStatusError, httpx.RequestError, KeyError, LLMResponseError) as exc:
                last_error = exc
                logger.warning(
                    "LLM call attempt %d/%d failed for role=%s: %s",
                    attempt + 1, self.max_retries, role, exc,
                )
                if isinstance(exc, LLMResponseError) and "Non-retryable HTTP" in str(exc):
                    raise
                if isinstance(exc, LLMThinkingTruncatedError) or "模型思考过程超限截断" in str(exc):
                    old_tokens = current_max_tokens
                    current_max_tokens = min(max(current_max_tokens * 2, 8192), 16384)
                    system_hint = (
                        "【紧急生成指引】：上一轮生成由于思考链（Reasoning）过长消耗过多 Token 导致正文截断。"
                        "本轮请务必：极简思考（控制在 300 字以内），直接专注于输出高质量完整正文，严禁长篇展开内心推演。"
                    )
                    thinking_override = False
                    logger.warning(
                        "Thinking truncation detected: escalating max_tokens from %d to %d and adding concise-thinking directive (role=%s, attempt %d/%d)",
                        old_tokens, current_max_tokens, role, attempt + 1, self.max_retries,
                    )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
        logger.error("LLM call failed after %d attempts for role=%s", self.max_retries, role)
        raise RetryExhaustedError(
            f"OpenAI API call failed after {self.max_retries} attempts: {last_error}"
        )

    async def astream(self, role: str, prompt: str):
        """Stream chunks from OpenAI-compatible SSE completion."""
        from novel_agent.progress import check_aborted
        from novel_agent.control.model_rate_limit import enforce_model_call_rate_limit
        check_aborted()
        enforce_model_call_rate_limit()
        _assert_safe_model_base_url(self.base_url)
        url, headers, payload = self._build_payload(role, prompt)
        stream_payload = dict(payload)
        stream_payload["stream"] = True
        if str(self.model).lower().startswith("deepseek-v4"):
            stream_payload["stream_options"] = {"include_usage": True}

        client = self._get_async_client()
        emitted_content = False
        malformed = 0
        reasoning_chars = 0
        final_usage: Dict[str, Any] = {}
        final_model = self.model
        response_id = ""
        finish_reason = ""
        t0 = time.time()
        try:
            async with client.stream("POST", url, headers=headers, json=stream_payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk_obj = json.loads(data_str)
                        except json.JSONDecodeError:
                            malformed += 1
                            logger.warning("Skipping malformed SSE chunk: %s", data_str[:120])
                            continue
                        choices = chunk_obj.get("choices") or []
                        response_id = str(chunk_obj.get("id") or response_id)
                        final_model = str(chunk_obj.get("model") or final_model)
                        if isinstance(chunk_obj.get("usage"), dict) and chunk_obj["usage"]:
                            final_usage = chunk_obj["usage"]
                        if choices:
                            delta = choices[0].get("delta") or {}
                            finish_reason = str(choices[0].get("finish_reason") or finish_reason)
                            reasoning_chars += len(delta.get("reasoning_content") or "")
                            content = delta.get("content") or ""
                            if content:
                                emitted_content = True
                                yield content
            usage_data = {
                "id": response_id,
                "model": final_model,
                "usage": final_usage,
            }
            outcome = "succeeded" if emitted_content else (
                "thinking_truncated" if reasoning_chars or finish_reason == "length" else "empty_content"
            )
            self._record_usage(
                usage_data,
                role,
                t0,
                outcome=outcome,
                finish_reason=finish_reason,
            )
            if not emitted_content:
                if reasoning_chars or finish_reason == "length":
                    raise LLMThinkingTruncatedError(
                        f"模型思考过程超限截断 (finish_reason={finish_reason or 'unknown'}, 思考长度={reasoning_chars} 字符)，未能输出有效正文内容。",
                        role=role,
                        model=str(final_model),
                        finish_reason=str(finish_reason or ""),
                        usage=final_usage,
                        recovery_action="stream_fallback_agenerate",
                    )
                raise LLMResponseError(
                    f"Streaming produced no content ({malformed} malformed SSE chunks)"
                )
        except LLMResponseError:
            raise
        except Exception as exc:
            if emitted_content:
                raise
            logger.warning("Streaming failed (%s), falling back to agenerate", exc)
            fallback_text = await self.agenerate(role, prompt)
            yield fallback_text

    def test(self) -> Dict[str, Any]:
        """Send a minimal request to verify connectivity. Returns result dict."""
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 10,
        }
        t0 = time.time()
        try:
            resp = self._get_client().post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            latency_ms = int((time.time() - t0) * 1000)
            preview = data["choices"][0]["message"]["content"].strip()[:100]
            return {
                "success": True,
                "latency_ms": latency_ms,
                "model": data.get("model", self.model),
                "response_preview": preview,
            }
        except (httpx.HTTPStatusError, httpx.RequestError, KeyError, json.JSONDecodeError) as exc:
            latency_ms = int((time.time() - t0) * 1000)
            return {"success": False, "latency_ms": latency_ms, "error": str(exc)}

    def test_context_budget(self, target_tokens: int) -> Dict[str, Any]:
        """Test model's ability to handle large context payloads by sending dummy text.

        Calculates payload size based on target_tokens and appends a verification prompt.
        """
        # Estimate repeater based on target_tokens. One repetition is ~38 tokens.
        sample_phrase = "这是一个用于测试大语言模型大上下文承载能力的填充测试句子。"
        repeat_count = int(target_tokens / 38)
        padding_text = "\n".join([sample_phrase] * max(1, repeat_count))

        ver_secret = "TEST_SECRET_BUDGET_OK_9981"
        prompt = (
            f"{padding_text}\n\n"
            f"=== 填充文本结束 ===\n"
            f"重要指令：请仔细阅读上面的填充内容，并严格按照本句的要求进行回复。 "
            f"请在您的回复中仅输出上面本指令给出的暗号，暗号是：{ver_secret}。 "
            f"不要输出任何其他解释、说明或 Markdown 标记，只输出这个暗号即可。"
        )

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 50,
            "temperature": 0.0,
        }

        t0 = time.time()
        try:
            timeout = max(self.timeout, 180.0)
            resp = self._get_client().post(
                url,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            latency_ms = int((time.time() - t0) * 1000)
            reply = data["choices"][0]["message"]["content"].strip()

            success = ver_secret in reply
            if success:
                return {
                    "success": True,
                    "latency_ms": latency_ms,
                    "model": data.get("model", self.model),
                    "message": f"上下文承载测试成功！成功提取测试暗号。总耗时 {latency_ms} ms。",
                }
            return {
                "success": False,
                "latency_ms": latency_ms,
                "error": f"大模型回复未包含正确暗号。模型回复预览：'{reply[:100]}'",
            }
        except (httpx.HTTPStatusError, httpx.RequestError, KeyError, json.JSONDecodeError) as exc:
            latency_ms = int((time.time() - t0) * 1000)
            return {
                "success": False,
                "latency_ms": latency_ms,
                "error": f"测试时发生网络或网关限制报错: {str(exc)}",
            }

    def close(self):
        if self._client is not None:
            self._client.close()

    async def aclose(self):
        self.close()
        if self._aclient is not None:
            await self._aclient.aclose()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class PromptAgent:
    """Base class for all prompt-driven agents."""

    def __init__(self, role: str, llm: LLMClient):
        self.role = role
        self.llm = llm
        self.logger = get_logger(f"agent.{role}")

    def run(self, prompt: str) -> str:
        self.logger.debug("Running agent %s with prompt length=%d", self.role, len(prompt))
        return self.llm.generate(self.role, prompt)

    async def arun(self, prompt: str) -> str:
        self.logger.debug("Running agent %s asynchronously with prompt length=%d", self.role, len(prompt))
        if hasattr(self.llm, "agenerate"):
            return await self.llm.agenerate(self.role, prompt)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.llm.generate, self.role, prompt)


@dataclass
class FallbackLLM:
    """Wraps a primary LLM with fallback alternatives.

    If the primary fails, tries each fallback in order.
    """

    primary: LLMClient
    fallbacks: List[LLMClient] = field(default_factory=list)

    @property
    def call_log(self) -> List[Dict[str, Any]]:
        """Aggregate call logs from all wrapped clients."""
        logs: List[Dict[str, Any]] = []
        for client in [self.primary] + self.fallbacks:
            if hasattr(client, "call_log"):
                logs.extend(client.call_log)
        return logs

    def generate(self, role: str, prompt: str) -> str:
        clients = [self.primary] + self.fallbacks
        last_error: Exception | None = None
        for i, client in enumerate(clients):
            try:
                result = client.generate(role, prompt)
                if i > 0:
                    logger.info("Fallback model succeeded for role=%s after %d failures", role, i)
                return result
            except Exception as exc:
                from novel_agent.exceptions import TaskAbortedError
                if isinstance(exc, TaskAbortedError):
                    raise
                last_error = exc
                logger.warning("Model %d/%d failed for role=%s: %s",
                             i + 1, len(clients), role, exc)
        raise RetryExhaustedError(
            f"All {len(clients)} models failed for role={role}: {last_error}"
        )

    async def agenerate(self, role: str, prompt: str) -> str:
        clients = [self.primary] + self.fallbacks
        last_error: Exception | None = None
        for i, client in enumerate(clients):
            try:
                if hasattr(client, "agenerate"):
                    result = await client.agenerate(role, prompt)
                else:
                    result = client.generate(role, prompt)
                if i > 0:
                    logger.info("Fallback model succeeded for role=%s after %d failures", role, i)
                return result
            except Exception as exc:
                from novel_agent.exceptions import TaskAbortedError
                if isinstance(exc, TaskAbortedError):
                    raise
                last_error = exc
                logger.warning("Model %d/%d failed for role=%s: %s",
                             i + 1, len(clients), role, exc)
        raise RetryExhaustedError(
            f"All {len(clients)} models failed for role={role}: {last_error}"
        )


_PLUGIN_PROVIDERS: Dict[str, Any] = {}


def register_llm_provider(name: str, provider: Any) -> None:
    _PLUGIN_PROVIDERS[name] = provider


def unregister_llm_provider(name: str) -> None:
    _PLUGIN_PROVIDERS.pop(name, None)


def create_llm(config: Dict[str, Any]) -> LLMClient:
    """Create an LLM client from pipeline config dict."""
    provider = config.get("provider", "static")
    if provider == "static":
        return StaticLLM(config.get("responses", {}))
    if provider == "openai":
        return OpenAILLM(
            base_url=config.get("base_url", "https://api.openai.com/v1"),
            api_key=config.get("api_key", ""),
            model=config.get("model", "gpt-4o-mini"),
            max_tokens=config.get("max_tokens", 4096),
            temperature=config.get("temperature", 0.7),
            seed=config.get("seed"),
            timeout=config.get("timeout", 120.0),
            max_retries=config.get("max_retries", 3),
            proxy=config.get("proxy", ""),
            thinking=config.get("thinking"),
            reasoning_effort=config.get("reasoning_effort"),
        )
    if provider in _PLUGIN_PROVIDERS:
        return _PLUGIN_PROVIDERS[provider].create_client(config)
    raise ValueError(f"Unknown LLM provider: {provider}")


def _resolve_model_ref(
    config: Dict[str, Any],
    models_library: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Resolve model_ref by merging library config under the inline config."""
    ref_id = config.get("model_ref")
    if not ref_id or ref_id not in models_library:
        return config
    # Library config is the base, inline config overrides
    lib = {k: v for k, v in models_library[ref_id].items() if k not in ("id", "name")}
    merged = {**lib, **{k: v for k, v in config.items() if k != "model_ref"}}
    return merged


def _build_llm_with_fallback(
    config: Dict[str, Any],
    models_library: Dict[str, Dict[str, Any]],
) -> LLMClient:
    """Create an LLM client, wrapping with FallbackLLM if fallback_models specified."""
    resolved = _resolve_model_ref(config, models_library)
    primary = create_llm(resolved)

    fallback_ids = config.get("fallback_models", [])
    if not fallback_ids:
        return primary

    fallbacks: List[LLMClient] = []
    for fid in fallback_ids:
        if fid in models_library:
            fallbacks.append(create_llm(models_library[fid]))
    if not fallbacks:
        return primary
    return FallbackLLM(primary=primary, fallbacks=fallbacks)


def create_llm_registry(
    default_config: Dict[str, Any],
    overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    models_library: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, LLMClient]:
    """Create a registry mapping agent roles to LLM clients.

    ``default_config`` is the base config for all agents.
    ``overrides`` maps role names to partial configs that are merged
    on top of the default (e.g. only override ``model``).
    ``models_library`` is the model library dict for resolving model_ref.

    Returns a dict like ``{"default": llm_a, "writer": llm_b, ...}``.
    """
    library = models_library or {}
    default_llm = _build_llm_with_fallback(default_config, library)
    registry: Dict[str, LLMClient] = {"default": default_llm}
    if overrides:
        for role, override in overrides.items():
            merged = {**default_config, **override}
            registry[role] = _build_llm_with_fallback(merged, library)
    return registry
