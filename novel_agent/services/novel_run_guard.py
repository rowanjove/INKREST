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


def _model_provider_usable(root: Path, model_id: str) -> bool:
    from novel_agent.pipeline import _load_models_library

    entry = (_load_models_library(root) or {}).get(model_id) or {}
    if not isinstance(entry, dict):
        return False
    provider = str(entry.get("provider") or "").strip().lower()
    return bool(provider and provider != "static")


def _engine_ready(root: Path) -> bool:
    try:
        from novel_agent.pipeline import load_pipeline_settings

        llm = load_pipeline_settings(root).get("llm") or {}
        if not isinstance(llm, dict):
            return False
        daily = str(llm.get("daily_model_id") or llm.get("default_model_id") or "").strip()
        if daily:
            return _model_provider_usable(root, daily)
        nested_ref = str((llm.get("default") or {}).get("model_ref") or "").strip()
        if nested_ref:
            return _model_provider_usable(root, nested_ref)
        default = llm.get("default") if isinstance(llm.get("default"), dict) else {}
        provider = str(llm.get("provider") or default.get("provider") or "").strip()
        return bool(provider and provider != "static")
    except Exception:
        return False


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


def build_readiness_report(root: Path) -> Dict[str, Any]:
    """Return { ok, pending: [{id, label}], warnings: [...] }."""
    outline_err = _outline_read_error(root)
    outline = _load_outline(root)
    macro = outline.get("macro_outline") or []
    pending: List[Dict[str, str]] = []

    if outline_err:
        pending.append({"id": "outline_corrupt", "label": "outline.json 可正常解析"})

    if not _engine_ready(root):
        pending.append({"id": "engine", "label": "日常模型可用（非 Static 占位）"})
    if not macro:
        pending.append({"id": "outline", "label": "已生成并保存大纲（含卷纲）"})
    if not outline.get("chosen_title"):
        pending.append({"id": "title", "label": "已确定最终书名"})
    if not _core_assets_ready(root):
        pending.append({"id": "assets", "label": "核心写作资产齐全"})
    remaining = _max_available_chapters(root, outline)
    if remaining <= 0:
        pending.append({"id": "quota", "label": "未达大纲章节上限"})

    stale = check_arc_queue_stale(root)
    queue_ok = bool(load_workspace_arcs(root)) or not macro

    warnings: List[str] = []
    vector_readiness_level = "auto"
    if stale.get("stale"):
        warnings.append(str(stale.get("message") or "卷队列与大纲不一致"))

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
    try:
        from novel_agent.control.factory_policy import load_project_factory_mode
        from novel_agent.state.yaml_mirror import check_yaml_mirror_drift

        factory_mode = load_project_factory_mode(root)
        yaml_mirror_warnings = check_yaml_mirror_drift(root)
        warnings.extend(yaml_mirror_warnings)
    except Exception:
        pass

    return {
        "ok": len(pending) == 0 and queue_ok and not stale.get("stale"),
        "pending": pending,
        "warnings": warnings,
        "remaining_chapters": remaining,
        "arc_queue_stale": stale,
        "has_arcs": bool(load_workspace_arcs(root)),
        "factory_mode": factory_mode,
        "yaml_mirror_warnings": yaml_mirror_warnings,
        "vector_readiness_level": vector_readiness_level,
        "vector_blocks_continue": any(item.get("id") == "vector" for item in pending),
    }


def validate_novel_continue(root: Path, *, force_resume: bool = False) -> Tuple[bool, str]:
    """
    Validate before starting novel continue/autopilot.
    Returns (ok, detail_message).
    """
    outline_err = _outline_read_error(root)
    if outline_err:
        return False, outline_err

    report = build_readiness_report(root)

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
            "请先在章节维护或写作页处理阻断章，确认后使用 force_resume 续跑。",
        )

    if report.get("remaining_chapters", 0) <= 0 and chapters_remaining_to_target(root) <= 0:
        if not load_workspace_arcs(root):
            return False, "无可执行卷队列且已达章节上限。"

    return True, ""