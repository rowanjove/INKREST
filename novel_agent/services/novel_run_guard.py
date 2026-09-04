"""Pre-flight checks for POST /api/novel/continue (aligned with UI 开书清单)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_logger = logging.getLogger(__name__)

from novel_agent.services.arc_queue import load_workspace_arcs
from novel_agent.services.novel_autopilot import (
    chapters_remaining_to_target,
    is_novel_batch_paused,
    novel_batch_pause_reason,
)
from novel_agent.services.outline_sync import check_arc_queue_stale

# Aligned with web/helpers.ASSET_FILES + CONFIG_ASSET_FILES and UI projectReadiness.
CORE_WRITING_ASSET_CANDIDATES = (
    ("world_bible", ("world_bible.md",)),
    ("style_guide", ("style_guide.md",)),
    ("rules", ("rules.yaml", "rules.md")),
    ("sensitive_words", ("sensitive_words.txt", "sensitive_words.md")),
)


def _outline_read_error(root: Path) -> Optional[str]:
    path = root / "workspace" / "outline.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return "outline.json 根节点必须是 JSON 对象"
        return None
    except (json.JSONDecodeError, OSError) as exc:
        return f"outline.json 无法解析：{exc}"


def _load_outline(root: Path) -> Dict[str, Any]:
    path = root / "workspace" / "outline.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def outline_planning_ready(outline: Dict[str, Any]) -> bool:
    """Reject quick-create placeholders while accepting existing real outlines."""
    macro = outline.get("macro_outline") or []
    if not isinstance(macro, list) or not macro:
        return False
    if str(outline.get("planning_status") or "").strip().lower() == "draft":
        return False
    if len(macro) != 1 or not isinstance(macro[0], dict):
        return True
    arc = macro[0]
    placeholder = (
        str(arc.get("name") or "") == "起始卷"
        and str(arc.get("goal") or "") == "确立主线与读者抓手"
        and str(arc.get("turning_point") or "") == "待定"
        and str(arc.get("payoff") or "") == "待定"
    )
    return not placeholder


def _model_provider_usable(root: Path, model_id: str) -> bool:
    from novel_agent.pipeline import _load_models_library

    entry = (_load_models_library(root) or {}).get(model_id) or {}
    return _model_config_usable(entry)


def _model_config_usable(entry: Any) -> bool:
    """Return whether a model can make a real request, not just be named.

    Local OpenAI-compatible servers intentionally do not require an API key.
    Every other endpoint defaults to a remote OpenAI-compatible service and
    must have a non-empty credential before a paid generation task is queued.
    """
    if not isinstance(entry, dict):
        return False
    provider = str(entry.get("provider") or "").strip().lower()
    if not provider or provider == "static":
        return False

    local_providers = {"ollama", "vllm", "lmstudio", "llama.cpp", "llamacpp", "local"}
    base_url = str(entry.get("base_url") or "").strip()
    if provider in local_providers and not base_url:
        return True

    from urllib.parse import urlparse

    from web.security import is_dev_model_host, is_loopback_host

    parsed = urlparse(base_url or "https://api.openai.com/v1")
    host = str(parsed.hostname or "").strip()
    if is_loopback_host(host) or is_dev_model_host(host):
        return True

    api_key = str(entry.get("api_key") or entry.get("api_token") or "").strip()
    if api_key in {"", "********", "***", "******"}:
        return False
    return True


def _engine_ready(root: Path) -> bool:
    return bool(build_model_readiness(root).get("ok"))


def build_model_readiness(root: Path) -> Dict[str, Any]:
    """Resolve every role/fallback that production can actually select."""
    try:
        from novel_agent.agents.base import _resolve_model_ref
        from novel_agent.pipeline import (
            _apply_global_fallback_ids,
            _daily_model_id,
            _load_models_library,
            _resolve_llm_config,
            _resolve_tiered_overrides,
            _should_use_library_default,
            _first_model_id,
            load_pipeline_settings,
        )

        llm = load_pipeline_settings(root).get("llm") or {}
        if not isinstance(llm, dict):
            return {"ok": False, "routes": [], "missing": ["llm"]}
        llm_copy = dict(llm)
        default_config, explicit_overrides = _resolve_llm_config(dict(llm_copy))
        library = _load_models_library(root)
        default_model_id = _daily_model_id(llm_copy)
        if not default_model_id and _should_use_library_default(llm_copy):
            default_model_id = _first_model_id(library)
        if default_model_id and default_model_id in library:
            default_config = {"model_ref": default_model_id}
        default_config = _apply_global_fallback_ids(default_config, llm_copy)
        routed = _resolve_tiered_overrides(llm_copy, explicit_overrides)

        routes: List[Dict[str, Any]] = []
        for role, override in sorted(routed.items()):
            config = {**default_config, **override}
            model_ref = str(config.get("model_ref") or "")
            resolved = _resolve_model_ref(config, library)
            ready = _model_config_usable(resolved)
            routes.append(
                {
                    "role": role,
                    "model_id": model_ref,
                    "model": str(resolved.get("model") or model_ref),
                    "provider": str(resolved.get("provider") or ""),
                    "ready": ready,
                    "reason": "" if ready else "模型不存在、仍为 Static 或缺少凭据",
                }
            )

        # A flat/default-only configuration still needs one explicit readiness row.
        if not routes:
            resolved = _resolve_model_ref(default_config, library)
            ready = _model_config_usable(resolved)
            routes.append(
                {
                    "role": "default",
                    "model_id": str(default_config.get("model_ref") or ""),
                    "model": str(resolved.get("model") or ""),
                    "provider": str(resolved.get("provider") or ""),
                    "ready": ready,
                    "reason": "" if ready else "模型不存在、仍为 Static 或缺少凭据",
                }
            )

        fallback_ids = [str(item) for item in llm_copy.get("fallback_model_ids") or [] if item]
        for model_id in fallback_ids:
            ready = _model_provider_usable(root, model_id)
            routes.append(
                {
                    "role": "fallback",
                    "model_id": model_id,
                    "model": str((library.get(model_id) or {}).get("model") or model_id),
                    "provider": str((library.get(model_id) or {}).get("provider") or ""),
                    "ready": ready,
                    "reason": "" if ready else "备用模型不存在、仍为 Static 或缺少凭据",
                }
            )
        missing = sorted({str(row["role"]) for row in routes if not row["ready"]})
        return {"ok": not missing, "routes": routes, "missing": missing}
    except Exception as exc:
        _logger.warning("Failed to resolve model readiness for %s: %s", root, exc)
        return {"ok": False, "routes": [], "missing": ["configuration"]}


def _asset_group_ready(assets_dir: Path, filenames: tuple) -> bool:
    for name in filenames:
        path = assets_dir / name
        try:
            if path.is_file() and path.stat().st_size > 0:
                return True
        except OSError:
            continue
    return False


def _core_assets_ready(root: Path) -> bool:
    assets_dir = root / "assets"
    if not assets_dir.is_dir():
        return False
    return all(
        _asset_group_ready(assets_dir, candidates)
        for _asset_id, candidates in CORE_WRITING_ASSET_CANDIDATES
    )


def _max_available_chapters(root: Path, outline: Dict[str, Any]) -> int:
    from novel_agent.services.progress_summary import build_progress_summary

    prof = outline.get("scale_profile") or {}
    scale = str(prof.get("scale") or "")
    hard_max = int(prof.get("max_chapters") or 0)
    limit = int(outline.get("target_chapters") or hard_max or 20)
    cap = limit if hard_max >= 999999 or scale == "infinite" else min(limit, hard_max or limit)
    done = int(build_progress_summary(root).get("authoritative_completed") or 0)
    return max(0, cap - done)


def build_readiness_report(root: Path, *, dry_run: bool = False) -> Dict[str, Any]:
    """Return { ok, pending: [{id, label}], warnings: [...] }."""
    outline_err = _outline_read_error(root)
    outline = _load_outline(root)
    macro = outline.get("macro_outline") or []
    pending: List[Dict[str, str]] = []

    if outline_err:
        pending.append({"id": "outline_corrupt", "label": "outline.json 可正常解析"})

    model_readiness = build_model_readiness(root)
    if not dry_run and not model_readiness.get("ok"):
        missing = "、".join(model_readiness.get("missing") or [])
        suffix = f"：{missing}" if missing else ""
        pending.append({"id": "engine", "label": f"生产模型路由全部可用{suffix}"})
    if not outline_planning_ready(outline):
        pending.append({"id": "outline", "label": "已生成并保存大纲（含卷纲）"})
    if not outline.get("chosen_title"):
        pending.append({"id": "title", "label": "已确定最终书名"})
    if not _core_assets_ready(root):
        pending.append({"id": "assets", "label": "核心写作资产齐全"})
    remaining = _max_available_chapters(root, outline)
    if remaining <= 0:
        pending.append({"id": "quota", "label": "未达大纲章节上限"})

    stale = check_arc_queue_stale(root)
    has_arcs = bool(load_workspace_arcs(root))

    warnings: List[str] = []
    vector_readiness_level = "auto"
    if macro and not has_arcs:
        warnings.append("卷级队列尚未建立，确认连写时会自动同步（首次可能需要 1～5 分钟）。")
    if stale.get("stale"):
        warnings.append(str(stale.get("message") or "卷队列与大纲不一致，确认连写时会自动同步。"))

    try:
        from novel_agent.control.runtime_policy import is_semantic_search_effective
        from novel_agent.control.vector_readiness import resolve_vector_readiness_level
        from novel_agent.pipeline import load_pipeline_settings

        emb = load_pipeline_settings(root).get("embedding", {}) or {}
        provider = str(emb.get("provider") or "").strip().lower()
        scale = str((outline.get("scale_profile") or {}).get("scale") or "")
        vector_stub = provider in ("", "stub", "none") or not is_semantic_search_effective(root)
        level = resolve_vector_readiness_level(root, scale, vector_stub=vector_stub)
        vector_readiness_level = level
        if level == "block":
            pending.append({"id": "vector", "label": "长篇模式需配置有效 Embedding（非 stub）"})
        elif level == "warn":
            warnings.append(
                "长篇/超长篇且 Embedding 未就绪：跨章去重与伏笔召回不可用，请在设置中配置真实向量。"
            )
    except Exception:
        pass

    try:
        from novel_agent.control.runtime_policy import resolve_runtime_policy

        policy = resolve_runtime_policy(root)
        if policy.scale in ("epic", "infinite"):
            warnings.append(
                f"当前体量 {policy.scale}：generation_policy 可能启用抽检门禁，连写更快但需勤查待处理章节。"
            )
    except Exception:
        pass

    factory_mode = ""
    yaml_mirror_warnings: List[str] = []
    embedding_backend = "sqlite"
    chromadb_available = False
    embedding_backend_hint = ""
    try:
        from novel_agent.control.factory_policy import load_project_factory_mode
        from novel_agent.state.yaml_mirror import check_yaml_mirror_drift

        factory_mode = load_project_factory_mode(root)
        yaml_mirror_warnings = check_yaml_mirror_drift(root)
        warnings.extend(yaml_mirror_warnings)
    except Exception:
        pass

    try:
        from novel_agent.pipeline import load_pipeline_settings
        from novel_agent.services.embedding_policy import resolve_embedding_config
        from novel_agent.state.vector_store import CHROMA_AVAILABLE

        resolved_emb = resolve_embedding_config(load_pipeline_settings(root), root)
        embedding_backend = str(resolved_emb.get("backend") or "sqlite")
        chromadb_available = bool(CHROMA_AVAILABLE)
        embedding_backend_hint = str(resolved_emb.get("_backend_hint") or "")
        if embedding_backend_hint:
            warnings.append(embedding_backend_hint)

        # Vector scale warning for NumPy / SQLite linear engine
        from novel_agent.state.sqlite_store import safe_connection
        db_path = root / "data" / "novel.sqlite"
        if db_path.is_file():
            with safe_connection(db_path) as conn:
                table_exists = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='vector_embeddings'"
                ).fetchone()
                if table_exists:
                    count = conn.execute("SELECT count(*) FROM vector_embeddings").fetchone()[0]
                    if count > 2000 and embedding_backend == "sqlite":
                        warnings.append(
                            f"当前已索引的向量块数量为 {count}。由于正在使用 NumPy 内存向量引擎，"
                            f"体量较大时可能会导致检索速度下降，建议在设置中启用并配置 ChromaDB 向量数据库。"
                        )
    except Exception:
        pass

    return {
        "ok": len(pending) == 0,
        "pending": pending,
        "warnings": warnings,
        "remaining_chapters": remaining,
        "arc_queue_stale": stale,
        "has_arcs": has_arcs,
        "factory_mode": factory_mode,
        "yaml_mirror_warnings": yaml_mirror_warnings,
        "vector_readiness_level": vector_readiness_level,
        "vector_blocks_continue": any(item.get("id") == "vector" for item in pending),
        "embedding_backend": embedding_backend,
        "chromadb_available": chromadb_available,
        "embedding_backend_hint": embedding_backend_hint,
        "model_readiness": model_readiness,
    }


def validate_novel_continue(
    root: Path,
    *,
    force_resume: bool = False,
    dry_run: bool = False,
) -> Tuple[bool, str]:
    """
    Validate before starting novel continue/autopilot.
    Returns (ok, detail_message).
    """
    outline_err = _outline_read_error(root)
    if outline_err:
        return False, outline_err

    report = build_readiness_report(root, dry_run=dry_run)

    pending = report.get("pending") or []
    if pending:
        labels = "、".join(p["label"] for p in pending)
        return False, f"开书清单未就绪：{labels}"

    if not report.get("has_arcs"):
        outline = _load_outline(root)
        if outline.get("macro_outline"):
            return False, "卷级队列尚未建立，请先调用「同步卷队列」或在工作台启动前自动 ensure-queue。"

    stale = report.get("arc_queue_stale") or {}
    if stale.get("stale"):
        return False, str(stale.get("message") or "卷队列与大纲不一致，请在大纲页同步卷队列后再续跑。")

    try:
        from novel_agent.services.external_review import (
            block_continue_until_external_pass,
            count_pending_external,
        )

        if block_continue_until_external_pass(root):
            pending_ext = count_pending_external(root)
            if pending_ext > 0:
                return (
                    False,
                    f"尚有 {pending_ext} 章标记为「待外审」，请在外站试发通过后勾选「外审已通过」再续跑。",
                )
    except Exception as exc:
        _logger.exception("external_review check failed for %s", root)
        return False, "外审状态检查失败，请检查 external_review 配置后重试。"

    if is_novel_batch_paused(root) and not force_resume:
        from novel_agent.services.arc_queue import load_arc_progress

        prog = load_arc_progress(root)
        ch = prog.get("last_chapter_id") or "—"
        arc = prog.get("last_arc_id") or "—"
        streak = prog.get("fail_streak") or 0
        extra = f"，连续失败 {streak} 次" if streak else ""
        reason = novel_batch_pause_reason(root) or "paused"
        reason_msgs = {
            "circuit_breaker": "全书批量因质量熔断已暂停",
            "quality_blocked": "全书批量因统一门禁阻断已暂停",
            "batch_skip_limit": "全书批量因连续跳章保护已暂停",
            "chapter_retry_exhausted": "全书批量因单章重试次数耗尽已暂停",
        }
        head = reason_msgs.get(reason, f"全书批量已暂停（{reason}）")
        return (
            False,
            f"{head}（卷 {arc} / 章 {ch}{extra}）。"
            "请先在生产中心或正文页处理阻断章，确认后使用 force_resume 续跑。",
        )

    if report.get("remaining_chapters", 0) <= 0 and chapters_remaining_to_target(root) <= 0:
        if not load_workspace_arcs(root):
            return False, "无可执行卷队列且已达章节上限。"

    return True, ""
