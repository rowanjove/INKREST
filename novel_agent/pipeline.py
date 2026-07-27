import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from novel_agent.agents.base import LLMClient, StaticLLM, create_llm, create_llm_registry


DEFAULT_SETTINGS: Dict[str, Any] = {
    "runtime": {
        "max_workers": 4,
        "retry_attempts": 1,
        "interactive": False,
        "hook_fail_fast": False,
        "hook_timeout_seconds": 30,
        "batch_fail_streak_max": 5,
        "vector_search_window": 80,
        "hnsw_rebuild_every": 50,
        "merge_review_stages": True,
        "yaml_mirror_enabled": False,
    },
    "chapter": {
        "default_target_chars": [1200, 2200],
        "default_scene_target_chars": [400, 800],
        "quality_mode": "report_only",
        "quality_auto_rewrite": True,
        "persona_evaluations": "auto",
        "generation_style_mode": "full",
        "boundary_recheck_after_style": True,
        "boundary_recheck_only_after_style": True,
        "writer_anti_ai_hints": True,
    },
    "llm": {"provider": "static"},
    "embedding": {"provider": "stub"},
}

DEFAULT_LLM_ROLE_TIERS: Dict[str, str] = {
    "novel_chat": "daily",
    "writer": "daily",
    "stitch_editor": "daily",
    "style_editor": "daily",
    "length_fix": "daily",
    "chapter_summary": "daily",
    "asset_compressor": "daily",
    "compressor": "daily",
    "expander": "daily",
    "persona_reader": "daily",
    "asset_generator": "daily",
    "assistant": "daily",
    "chief_editor": "reasoning",
    "managing_editor": "reasoning",
    "chapter_planner": "reasoning",
    "planner": "reasoning",
    "auditor": "reasoning",
    "continuity_checker": "reasoning",
    "state_extractor": "reasoning",
}

_LLM_ROUTING_KEYS = {
    "assistant",
    "daily_model_id",
    "default_model_id",
    "reasoning_model_id",
    "role_tiers",
}

# Multi-project layout: models + embedding are global; chapter/runtime stay per book.
GLOBAL_SHARED_SECTIONS = frozenset({"llm", "embedding"})
PROJECT_SCOPED_SECTIONS = frozenset({"chapter", "runtime", "quality"})


_ENV_VAR_RE = re.compile(r"\$\{([^}]+)\}")

logger = logging.getLogger("novel_agent.pipeline")


def _substitute_env_vars(obj: Any) -> Any:
    """Recursively replace ${VAR_NAME} patterns with os.environ values."""
    if isinstance(obj, str):
        def _replace(m: re.Match) -> str:
            var_name = m.group(1)
            value = os.environ.get(var_name)
            if value is None:
                logger.warning("Environment variable %s is not set, using empty string", var_name)
            return value or ""
        return _ENV_VAR_RE.sub(_replace, obj)
    if isinstance(obj, dict):
        return {k: _substitute_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute_env_vars(item) for item in obj]
    return obj


def resolve_global_config_dir(root_dir: Path) -> Optional[Path]:
    """When root is projects/<id>, return repo-level config/ (shared models & embedding)."""
    root_dir = Path(root_dir).resolve()
    registry = root_dir.parent.parent / "projects.json"
    if registry.is_file():
        return root_dir.parent.parent / "config"
    return None


def _load_yaml_pipeline(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError):
        return {}
    return _substitute_env_vars(loaded) if isinstance(loaded, dict) else {}


def _merge_pipeline_section(settings: Dict[str, Any], section: str, values: Any) -> None:
    if isinstance(values, dict) and "default" not in values:
        settings.setdefault(section, {})
        if isinstance(settings.get(section), dict):
            settings[section].update(values)
        else:
            settings[section] = dict(values)
    else:
        settings[section] = values


def _bootstrap_settings() -> Dict[str, Any]:
    settings: Dict[str, Any] = {}
    for section, values in DEFAULT_SETTINGS.items():
        if isinstance(values, dict):
            settings[section] = dict(values)
        else:
            settings[section] = values
    return settings


def load_pipeline_settings(root_dir: Path) -> Dict[str, Any]:
    settings = _bootstrap_settings()
    root_dir = Path(root_dir)
    global_dir = resolve_global_config_dir(root_dir)
    project_path = root_dir / "config" / "pipeline.yaml"

    if global_dir:
        global_loaded = _load_yaml_pipeline(global_dir / "pipeline.yaml")
        for section, values in global_loaded.items():
            _merge_pipeline_section(settings, section, values)
        project_loaded = _load_yaml_pipeline(project_path)
        for section, values in project_loaded.items():
            if section in PROJECT_SCOPED_SECTIONS:
                _merge_pipeline_section(settings, section, values)
        return settings

    project_loaded = _load_yaml_pipeline(project_path)
    for section, values in project_loaded.items():
        _merge_pipeline_section(settings, section, values)
    return settings


def load_project_pipeline_file(root_dir: Path) -> Dict[str, Any]:
    """Raw on-disk project pipeline (no global merge)."""
    return _load_yaml_pipeline(Path(root_dir) / "config" / "pipeline.yaml")


def load_global_pipeline_file(global_dir: Path) -> Dict[str, Any]:
    """Raw on-disk global pipeline (no defaults merge)."""
    return _load_yaml_pipeline(Path(global_dir) / "pipeline.yaml")


def write_pipeline_file(path: Path, data: Dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _resolve_embedding_config(settings: Dict[str, Any], root_dir: Path) -> Dict[str, Any]:
    from novel_agent.services.embedding_policy import resolve_embedding_config

    return resolve_embedding_config(settings, Path(root_dir))


def _resolve_llm_config(llm_settings: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """Extract default config and overrides from llm settings.

    Supports two formats:
    1. Flat: {"provider": "openai", "model": "xxx"} — no overrides
    2. Nested: {"default": {...}, "overrides": {"writer": {...}}} — with routing
    """
    if "default" in llm_settings:
        default_config = llm_settings["default"]
        overrides = llm_settings.get("overrides", {})
        return default_config, overrides
    # Flat format — no overrides
    overrides = llm_settings.pop("overrides", {})
    for key in _LLM_ROUTING_KEYS:
        llm_settings.pop(key, None)
    return llm_settings, overrides


def _daily_model_id(llm_settings: Dict[str, Any]) -> str:
    return llm_settings.get("daily_model_id") or llm_settings.get("default_model_id") or ""


def _apply_global_fallback_ids(
    config: Dict[str, Any], llm_settings: Dict[str, Any]
) -> Dict[str, Any]:
    """Attach backup slot models as fallback_models for FallbackLLM."""
    fb_ids = llm_settings.get("fallback_model_ids") or []
    if not fb_ids:
        return config
    cfg = dict(config)
    primary_ref = cfg.get("model_ref")
    existing = list(cfg.get("fallback_models") or [])
    for fid in fb_ids:
        if not fid or fid == primary_ref or fid in existing:
            continue
        existing.append(fid)
    if existing:
        cfg["fallback_models"] = existing
    return cfg


def _resolve_tiered_overrides(
    llm_settings: Dict[str, Any],
    overrides: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    role_tiers = {**DEFAULT_LLM_ROLE_TIERS, **llm_settings.get("role_tiers", {})}
    daily_model_id = _daily_model_id(llm_settings)
    reasoning_model_id = llm_settings.get("reasoning_model_id") or daily_model_id
    routed: Dict[str, Dict[str, Any]] = {}
    for role, tier in role_tiers.items():
        model_id = reasoning_model_id if tier == "reasoning" else daily_model_id
        inherited = {"model_ref": model_id} if model_id else {}
        role_override = overrides.get(role, {})
        if inherited or role_override:
            routed[role] = {**inherited, **role_override}
    for role, role_override in overrides.items():
        routed.setdefault(role, role_override)
    return routed


def _load_models_library(root_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Load model library from config/models.json."""
    grandparent = Path(root_dir).parent.parent
    if (grandparent / "projects.json").exists():
        global_config = grandparent / "config"
    else:
        global_config = Path(root_dir) / "config"
    path = global_config / "models.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return _substitute_env_vars(data.get("models", {}))
    except (json.JSONDecodeError, OSError):
        return {}


def _first_model_id(models_library: Dict[str, Dict[str, Any]]) -> str:
    return next(iter(models_library), "")


def _should_use_library_default(llm_settings: Dict[str, Any]) -> bool:
    if _daily_model_id(llm_settings) or llm_settings.get("default", {}).get("model_ref"):
        return False
    provider = llm_settings.get("provider")
    nested_provider = llm_settings.get("default", {}).get("provider")
    return provider in (None, "", "static") and nested_provider in (None, "", "static")


def llm_config_error(root_dir: Path) -> Optional[str]:
    """Return a user-facing message when real LLM generation is not configured."""
    from novel_agent.services.novel_run_guard import _engine_ready

    if _engine_ready(root_dir):
        return None
    return "日常模型未配置或仍为 Static 占位，请在设置中选择可用模型后再生成。"


def assert_llm_ready(root_dir: Path) -> None:
    """Fail fast before starting a paid generation task."""
    err = llm_config_error(root_dir)
    if err:
        from novel_agent.exceptions import FatalPipelineError

        raise FatalPipelineError(err)


@dataclass
class PipelineConfig:
    root_dir: Path
    llm: LLMClient
    llm_registry: Dict[str, LLMClient] = field(default_factory=dict)
    max_workers: int = 4
    interactive: bool = False
    max_rewrites: int = 2
    skip_stitch: bool = False
    max_tokens_per_chapter: int = 0
    skip_style_edit: bool = False
    embedding_config: Dict[str, Any] = field(default_factory=lambda: {"provider": "stub"})
    plugin_manager: Optional[Any] = None

    def get_llm(self, role: str) -> LLMClient:
        """Get LLM client for a specific agent role, falling back to default."""
        return self.llm_registry.get(role, self.llm)

    def get_call_log(self) -> List[Dict[str, Any]]:
        """Aggregate call logs from all LLM clients in the registry."""
        logs: List[Dict[str, Any]] = []
        for client in self.llm_registry.values():
            if hasattr(client, "call_log"):
                logs.extend(client.call_log)
        return logs

    async def close_llm_clients(self) -> None:
        """Release HTTP clients held by LLM backends after a generation task."""
        from novel_agent.agents.base import FallbackLLM

        seen: set[int] = set()

        async def _close_client(client: LLMClient) -> None:
            key = id(client)
            if key in seen:
                return
            seen.add(key)
            if isinstance(client, FallbackLLM):
                await _close_client(client.primary)
                for fallback in client.fallbacks:
                    await _close_client(fallback)
                return
            if hasattr(client, "aclose"):
                await client.aclose()
            elif hasattr(client, "close"):
                client.close()

        await _close_client(self.llm)
        for client in self.llm_registry.values():
            await _close_client(client)

    @classmethod
    def from_config(cls, root_dir: Path) -> "PipelineConfig":
        settings = load_pipeline_settings(root_dir)
        llm_settings = settings.get("llm", {"provider": "static"})
        default_config, overrides = _resolve_llm_config(dict(llm_settings))

        if "provider" not in default_config:
            default_config["provider"] = "static"

        # Load model library
        models_library = _load_models_library(root_dir)
        if not llm_settings.get("reasoning_model_id") and "deepseek-v4-pro" in models_library:
            llm_settings = {**llm_settings, "reasoning_model_id": "deepseek-v4-pro"}
        default_model_id = _daily_model_id(llm_settings)
        if not default_model_id and _should_use_library_default(llm_settings):
            default_model_id = _first_model_id(models_library)
        if default_model_id and default_model_id in models_library:
            default_config = {"model_ref": default_model_id}

        from novel_agent.plugins import PluginManager
        pm = PluginManager(Path(root_dir))
        pm.initialize()

        overrides = _resolve_tiered_overrides(llm_settings, overrides)
        default_config = _apply_global_fallback_ids(default_config, llm_settings)
        if overrides:
            overrides = {
                role: _apply_global_fallback_ids(cfg, llm_settings)
                for role, cfg in overrides.items()
            }
        registry = create_llm_registry(default_config, overrides or None, models_library)
        default_llm = registry["default"]

        return cls(
            root_dir=Path(root_dir),
            llm=default_llm,
            llm_registry=registry,
            max_workers=int(settings["runtime"].get("max_workers", 4)),
            interactive=bool(settings["runtime"].get("interactive", False)),
            max_rewrites=int(settings["runtime"].get("max_rewrites", 2)),
            skip_stitch=bool(settings.get("runtime", {}).get("skip_stitch", False)),
            max_tokens_per_chapter=int(settings.get("runtime", {}).get("max_tokens_per_chapter", 0)),
            embedding_config=_resolve_embedding_config(settings, root_dir),
            plugin_manager=pm,
        )

    @classmethod
    def dry_run(cls, root_dir: Path):
        settings = load_pipeline_settings(root_dir)
        responses = {
            "default": "这是一个占位输出。请在接入真实模型后重新生成。",
            "chief_editor": json.dumps({
                "title_options": ["《示例小说》"],
                "logline": "一个关于冒险的故事",
                "core_theme": "冒险与成长",
                "genre_positioning": "玄幻",
                "target_reader": "网文读者",
                "reader_promise": ["精彩的冒险"],
                "world_rules": ["灵气世界"],
                "protagonist": {
                    "name": "主角",
                    "desire": "变强",
                    "flaw": "冲动",
                    "edge": "特殊体质",
                    "limit": "需要修炼"
                },
                "main_cast": [{"name": "师父", "role": "导师", "relationship_to_protagonist": "师徒", "secret_or_pressure": ""}],
                "antagonistic_forces": ["反派势力"],
                "macro_outline": [
                    {"arc_id": "A01", "name": "起始篇", "chapters": "1-5", "goal": "主角觉醒", "turning_point": "发现能力", "payoff": "初战告捷"}
                ],
                "forbidden_moves": []
            }, ensure_ascii=False),
            "managing_editor": json.dumps({
                "arc_id": "A01",
                "arc_name": "起始篇",
                "arc_goal": "主角觉醒",
                "chapters": [
                    {"chapter_id": "001", "chapter_title": "觉醒", "chapter_goal": "主角发现自己的特殊能力",
                     "input_state": "普通人", "output_state": "初步觉醒",
                     "reader_payoff": "能力展示", "hook": "更大的危机",
                     "must_include": ["觉醒场景"], "must_not_include": []}
                ]
            }, ensure_ascii=False),
            "chapter_planner": json.dumps({
                "chapter_id": "001",
                "chapter_title": "觉醒",
                "detailed_synopsis": "主角在一次危机中发现自己拥有特殊能力，从此踏上修炼之路。",
                "beats": [
                    {"beat_id": "B01", "function": "开场", "content": "日常场景", "state_change": "平静"},
                    {"beat_id": "B02", "function": "冲突", "content": "危机出现", "state_change": "危险"},
                    {"beat_id": "B03", "function": "转折", "content": "能力觉醒", "state_change": "觉醒"}
                ],
                "character_intents": [{"character": "主角", "wants": "生存", "hidden_pressure": "", "change": "觉醒"}],
                "foreshadow_plan": [],
                "handoff_to_scene_planner": {"must_include": ["觉醒"], "must_not_include": []}
            }, ensure_ascii=False),
            "state_extractor": json.dumps({
                "events": [{"id": "E001_001", "summary": "主角觉醒了特殊能力", "characters": ["主角"], "objects": [], "threads": []}],
                "characters": {"主角": {"location": "初始地", "emotion": "震惊", "physical_state": "正常"}},
                "objects": [],
                "threads": [{"id": "T001", "name": "觉醒之路", "status": "open"}],
                "foreshadows": [],
                "hooks": []
            }, ensure_ascii=False),
            "planner": (
                '{"chapter_id":"001","chapter_title":"示例章节",'
                '"target_chars":[1200,2200],"scenes":[{"scene_id":"001-01",'
                '"target_chars":[400,700],"purpose":"建立开场压力",'
                '"entry":"主角进入场景","exit":"异常出现",'
                '"must_include":["具体动作","环境细节"],'
                '"must_not_include":["解释世界观"]}]}'
            ),
            "auditor": '{"risk_level":"低","issues":[],"state_update":{"events":[]}}',
            "continuity_checker": '{"pass":true,"issues":[]}',
            "asset_compressor": '{"compressed":true,"archived_threads":[],"removed_events":[]}',
            "expander": "这是一个扩写占位输出。请在接入真实模型后重新生成。",
            "compressor": "这是一个压缩占位输出。请在接入真实模型后重新生成。",
            "chapter_summary": (
                "## 章节概述\n干跑模式生成的章节总结。\n\n"
                "## 人物发展\n- 暂无。\n\n"
                "## 看点/爽点\n- 暂无。\n\n"
                "## 故事伏笔\n- 暂无。\n\n"
                "## 收尾特征\n暂无。\n\n"
                "## 张力心电图\n暂无。\n\n"
                "## 总体评分\n暂无。"
            ),
        }
        default_llm = StaticLLM(responses)
        registry: Dict[str, LLMClient] = {"default": default_llm}

        from novel_agent.plugins import PluginManager
        pm = PluginManager(Path(root_dir))
        pm.initialize()

        return cls(
            root_dir=Path(root_dir),
            llm=default_llm,
            llm_registry=registry,
            max_workers=int(settings["runtime"].get("max_workers", 4)),
            embedding_config={"provider": "stub"},
            plugin_manager=pm,
        )
