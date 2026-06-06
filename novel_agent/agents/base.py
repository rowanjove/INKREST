import json
import time
import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

import httpx

from novel_agent.exceptions import AgentError, LLMResponseError, RetryExhaustedError
from novel_agent.logging_config import get_logger

logger = get_logger("agents.base")


# Re-export for backward compatibility
__all__ = [
    "AgentError",
    "LLMResponseError",
    "RetryExhaustedError",
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


@dataclass
class StaticLLM:
    """Deterministic LLM substitute for tests and dry runs."""

    responses: Dict[str, str] = field(default_factory=dict)

    def generate(self, role: str, prompt: str) -> str:
        if role in self.responses:
            return self.responses[role]

        # Smart mock logic for text editors to preserve content during dry runs
        if role == "stitch_editor":
            if "=== 场景A结尾 ===" in prompt:
                import re
                a_match = re.search(r"=== 场景A结尾 ===\s*(.*?)\s*=== 场景B开头 ===", prompt, re.DOTALL)
                b_match = re.search(r"=== 场景B开头 ===\s*(.*)", prompt, re.DOTALL)
                a_text = a_match.group(1).strip() if a_match else ""
                b_text = b_match.group(1).strip() if b_match else ""
                return f"{a_text}\n\n{b_text}"
            parts = prompt.split("输出完整章节正文。\n\n")
            if len(parts) > 1:
                return parts[-1].strip()
            return prompt.strip()

        if role == "style_editor":
            if "=== 待润色片段 ===" in prompt:
                import re
                match = re.search(r"=== 待润色片段 ===\s*(.*?)(?:\s*===|$)", prompt, re.DOTALL)
                if match:
                    return match.group(1).strip()
            parts = prompt.split("输出完整修订版。\n\n")
            if len(parts) > 1:
                return parts[-1].strip()
            return prompt.strip()

        if role in ("expander", "compressor", "length_fix"):
            parts = prompt.split("以下是待修正文本：\n")
            if len(parts) > 1:
                return parts[-1].strip()
            return prompt.strip()

        # JSON roles fallbacks
        if role == "state_extractor":
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

        if role == "chief_editor":
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

        if role == "managing_editor":
            return json.dumps({
                "arc_id": "A01",
                "arc_name": "起步",
                "arc_goal": "开始旅程",
                "chapters": [
                    {"chapter_id": "001", "chapter_title": "第一章", "chapter_goal": "踏出第一步", "input_state": "起始", "output_state": "发展", "reader_payoff": "爽点", "hook": "悬念", "must_include": [], "must_not_include": []}
                ]
            }, ensure_ascii=False)

        if role == "chapter_planner":
            return json.dumps({
                "chapter_id": "001",
                "chapter_title": "第一章",
                "detailed_synopsis": "这是静态模式下的章节规划内容。",
                "beats": [{"beat_id": "B01", "function": "起", "content": "起步", "state_change": "变化"}],
                "character_intents": [],
                "foreshadow_plan": [],
                "handoff_to_scene_planner": {"must_include": [], "must_not_include": []}
            }, ensure_ascii=False)

        if role == "planner":
            return json.dumps({
                "chapter_id": "001",
                "chapter_title": "第一章",
                "target_chars": [1500, 2500],
                "scenes": [
                    {"scene_id": "001-01", "target_chars": [800, 1200], "purpose": "引出故事", "entry": "开场", "exit": "收尾", "must_include": [], "must_not_include": []}
                ]
            }, ensure_ascii=False)

        if role == "auditor":
            return json.dumps({
                "risk_level": "低",
                "issues": [],
                "state_update": {}
            }, ensure_ascii=False)

        if role == "continuity_checker":
            return json.dumps({
                "pass": True,
                "issues": []
            }, ensure_ascii=False)

        if role == "asset_compressor":
            return json.dumps({
                "compressed": True,
                "archived_threads": [],
                "removed_events": []
            }, ensure_ascii=False)

        return self.responses.get(
            "default",
            "这是一个占位输出。请接入真实模型后重新生成本段内容。",
        )

    async def agenerate(self, role: str, prompt: str) -> str:
        return self.generate(role, prompt)


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
    timeout: float = 120.0
    max_retries: int = 3
    retry_delay: float = 1.0
    proxy: str = ""

    def __post_init__(self):
        client_kwargs: Dict[str, Any] = {"timeout": self.timeout}
        if self.proxy:
            client_kwargs["proxy"] = self.proxy
        self._client = httpx.Client(**client_kwargs)
        self._aclient = httpx.AsyncClient(**client_kwargs)
        self.call_log: List[Dict[str, Any]] = []

    def generate(self, role: str, prompt: str) -> str:
        from novel_agent.progress import check_aborted
        check_aborted()
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": f"你是{role}。"},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        # Non-retryable HTTP status codes
        non_retryable_status = {400, 401, 403, 404, 422}

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            check_aborted()
            t0 = time.time()
            try:
                resp = self._client.post(url, headers=headers, json=payload)

                # Check for non-retryable errors before raising
                if resp.status_code in non_retryable_status:
                    error_body = resp.text[:500]
                    raise LLMResponseError(
                        f"Non-retryable HTTP {resp.status_code}: {error_body}"
                    )

                resp.raise_for_status()
                data = resp.json()

                # Validate response structure
                if "choices" not in data or not data["choices"]:
                    raise LLMResponseError(f"Invalid response structure: missing 'choices'")

                result = data["choices"][0].get("message", {}).get("content", "").strip()
                if not result:
                    raise LLMResponseError("Empty response content")

                latency_ms = int((time.time() - t0) * 1000)
                usage = data.get("usage", {})
                self.call_log.append({
                    "role": role,
                    "model": data.get("model", self.model),
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                    "latency_ms": latency_ms,
                    "timestamp": time.time(),
                })
                logger.debug("LLM call succeeded for role=%s, length=%d, tokens=%d, latency=%dms",
                           role, len(result), usage.get("total_tokens", 0), latency_ms)
                return result
            except (httpx.HTTPStatusError, httpx.RequestError, KeyError, LLMResponseError) as exc:
                last_error = exc
                logger.warning("LLM call attempt %d/%d failed for role=%s: %s",
                             attempt + 1, self.max_retries, role, exc)

                # Don't retry non-retryable errors
                if isinstance(exc, LLMResponseError):
                    raise

                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
        logger.error("LLM call failed after %d attempts for role=%s", self.max_retries, role)
        raise RetryExhaustedError(
            f"OpenAI API call failed after {self.max_retries} attempts: {last_error}"
        )

    async def agenerate(self, role: str, prompt: str) -> str:
        from novel_agent.progress import check_aborted
        check_aborted()
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": f"你是{role}。"},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        non_retryable_status = {400, 401, 403, 404, 422}
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            check_aborted()
            t0 = time.time()
            try:
                resp = await self._aclient.post(url, headers=headers, json=payload)
                if resp.status_code in non_retryable_status:
                    error_body = resp.text[:500]
                    raise LLMResponseError(
                        f"Non-retryable HTTP {resp.status_code}: {error_body}"
                    )
                resp.raise_for_status()
                data = resp.json()
                if "choices" not in data or not data["choices"]:
                    raise LLMResponseError(f"Invalid response structure: missing 'choices'")
                result = data["choices"][0].get("message", {}).get("content", "").strip()
                if not result:
                    raise LLMResponseError("Empty response content")

                latency_ms = int((time.time() - t0) * 1000)
                usage = data.get("usage", {})
                self.call_log.append({
                    "role": role,
                    "model": data.get("model", self.model),
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                    "latency_ms": latency_ms,
                    "timestamp": time.time(),
                })
                logger.debug("LLM call succeeded for role=%s, length=%d, tokens=%d, latency=%dms",
                           role, len(result), usage.get("total_tokens", 0), latency_ms)
                return result
            except (httpx.HTTPStatusError, httpx.RequestError, KeyError, LLMResponseError) as exc:
                last_error = exc
                logger.warning("LLM call attempt %d/%d failed for role=%s: %s",
                             attempt + 1, self.max_retries, role, exc)
                if isinstance(exc, LLMResponseError):
                    raise
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
        logger.error("LLM call failed after %d attempts for role=%s", self.max_retries, role)
        raise RetryExhaustedError(
            f"OpenAI API call failed after {self.max_retries} attempts: {last_error}"
        )

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
            resp = self._client.post(url, headers=headers, json=payload)
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
        except Exception as exc:
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
            client_kwargs = {"timeout": timeout}
            if self.proxy:
                client_kwargs["proxy"] = self.proxy
            
            with httpx.Client(**client_kwargs) as test_client:
                resp = test_client.post(url, headers=headers, json=payload)
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
                        "message": f"上下文承载测试成功！成功提取测试暗号。总耗时 {latency_ms} ms。"
                    }
                else:
                    return {
                        "success": False,
                        "latency_ms": latency_ms,
                        "error": f"大模型回复未包含正确暗号。模型回复预览：'{reply[:100]}'"
                    }
        except Exception as exc:
            latency_ms = int((time.time() - t0) * 1000)
            return {
                "success": False,
                "latency_ms": latency_ms,
                "error": f"测试时发生网络或网关限制报错: {str(exc)}"
            }

    def close(self):
        self._client.close()

    async def aclose(self):
        self._client.close()
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
            timeout=config.get("timeout", 120.0),
            max_retries=config.get("max_retries", 3),
            proxy=config.get("proxy", ""),
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
