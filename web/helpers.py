"""Utility helper functions for the Novel Agent web service."""

import copy
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
import logging
from fastapi import HTTPException

from web.context import BASE_DIR, get_root_dir
from novel_agent.state.sqlite_store import SQLiteStateStore
from novel_agent.scripts.count_chars import count_chinese_chars
from novel_agent.pipeline import load_pipeline_settings
from web.models import ChapterSummary

logger = logging.getLogger("web.helpers")

SECRET_MASK = "********"
SECRET_KEYS = {"api_key"}

PROMPT_ROLES = [
    "chief_editor", "managing_editor", "chapter_planner",
    "planner", "writer", "auditor", "continuity_checker",
    "chapter_summary", "stitch_editor", "style_editor",
    "expander", "compressor", "asset_compressor",
]

ASSET_FILES = {
    "character_cards": "assets/character_cards.yaml",
    "world_bible": "assets/world_bible.md",
    "terminology": "assets/terminology.md",
    "style_guide": "assets/style_guide.md",
    "rules": "assets/rules.yaml",
}

CONFIG_ASSET_FILES = {
    "sensitive_words": "assets/sensitive_words.txt",
}

_ALL_ASSET_FILES = {**ASSET_FILES, **CONFIG_ASSET_FILES}


def _validate_id(value: str, name: str = "id") -> str:
    """Validate that an ID contains only safe characters (no path traversal)."""
    if not value or not re.match(r'^[a-zA-Z0-9_-]+$', value):
        raise HTTPException(400, f"Invalid {name}: must contain only alphanumeric, underscore, hyphen")
    if '..' in value or '/' in value or '\\' in value:
        raise HTTPException(400, f"Invalid {name}: path traversal detected")
    return value


def _template_prompts_dir() -> Path:
    template_root = os.environ.get("NOVEL_AGENT_TEMPLATES")
    if template_root:
        return Path(template_root) / "prompts"
    return BASE_DIR / "prompts"


def _template_presets_dir() -> Path:
    template_root = os.environ.get("NOVEL_AGENT_TEMPLATES")
    if template_root:
        return Path(template_root) / "presets"
    return BASE_DIR / "presets"


def _template_assets_dir() -> Path:
    template_root = os.environ.get("NOVEL_AGENT_TEMPLATES")
    if template_root:
        return Path(template_root) / "assets"
    return BASE_DIR / "assets"


def _demo_projects_dir() -> Path:
    """Bundled demo novels (dev repo assets/ or Electron templates/assets/)."""
    return _template_assets_dir() / "demo_projects"


def _copy_default_assets(target_assets: Path) -> None:
    default_assets = _template_assets_dir()
    if not default_assets.exists():
        return
    target_assets.mkdir(parents=True, exist_ok=True)
    for name in (
        "character_cards.yaml",
        "world_bible.md",
        "terminology.md",
        "style_guide.md",
        "rules.yaml",
        "sensitive_words.txt",
    ):
        source = default_assets / name
        target = target_assets / name
        if not source.exists():
            continue
        if name == "sensitive_words.txt" and target.exists():
            active_words = [
                line.strip()
                for line in target.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            if active_words:
                continue
            shutil.copy2(source, target)
            continue
        if not target.exists():
            shutil.copy2(source, target)


def _rules_yaml_needs_seed(text: str) -> bool:
    """True when rules.yaml is empty or uses legacy non-RuleBook schema."""
    stripped = (text or "").strip()
    if not stripped:
        return True
    if "forbiddenWords:" in stripped or "commonWords:" in stripped:
        return False
    return stripped.startswith("rules:") or "chapter_structure:" in stripped


def _sensitive_words_needs_seed(text: str) -> bool:
    for line in (text or "").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            return False
    return True


def ensure_writing_standards_assets(root_dir: Path) -> None:
    """Ensure style_guide, rules.yaml, and sensitive_words exist with usable defaults."""
    assets_dir = Path(root_dir) / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    template_dir = _template_assets_dir()

    pairs = (
        ("style_guide.md", lambda t: len((t or "").strip()) < 40),
        ("rules.yaml", _rules_yaml_needs_seed),
        ("sensitive_words.txt", _sensitive_words_needs_seed),
    )
    for filename, needs_seed in pairs:
        target = assets_dir / filename
        source = template_dir / filename
        if target.exists():
            try:
                current = target.read_text(encoding="utf-8")
            except OSError:
                current = ""
            if not needs_seed(current):
                continue
        elif source.exists():
            shutil.copy2(source, target)
            continue
        if source.exists():
            shutil.copy2(source, target)


def _copy_default_prompts(target_prompts: Path) -> None:
    default_prompts = _template_prompts_dir()
    if not default_prompts.exists():
        return
    target_prompts.mkdir(parents=True, exist_ok=True)
    for f in default_prompts.glob("*.md"):
        target = target_prompts / f.name
        if not target.exists():
            shutil.copy2(f, target)
    defaults_src = default_prompts / "defaults"
    defaults_dst = target_prompts / "defaults"
    defaults_dst.mkdir(exist_ok=True)
    if defaults_src.exists():
        for f in defaults_src.glob("*.md"):
            target = defaults_dst / f.name
            if not target.exists():
                shutil.copy2(f, target)


def _init_prompt_defaults(root: Path) -> None:
    prompts_dir = root / "prompts"
    defaults_dir = prompts_dir / "defaults"
    if defaults_dir.exists():
        return
    defaults_dir.mkdir(parents=True, exist_ok=True)
    for f in prompts_dir.glob("*.md"):
        if f.parent == defaults_dir:
            continue
        target = defaults_dir / f.name
        target.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")


def _read_yaml(path: Path) -> Any:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _mask_config_secrets(data: Dict[str, Any]) -> Dict[str, Any]:
    masked = copy.deepcopy(data)

    def visit(value: Any) -> Any:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in SECRET_KEYS:
                    value[key] = SECRET_MASK if child else ""
                else:
                    value[key] = visit(child)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                value[index] = visit(child)
        return value

    return visit(masked)


def _merge_preserving_masked_secrets(existing: Any, incoming: Any) -> Any:
    if not isinstance(existing, dict) or not isinstance(incoming, dict):
        return incoming

    merged: Dict[str, Any] = {}
    for key, value in incoming.items():
        old_value = existing.get(key)
        if key in SECRET_KEYS and value in ("", SECRET_MASK, "******"):
            merged[key] = old_value if old_value is not None else ""
        elif isinstance(value, dict) and isinstance(old_value, dict):
            merged[key] = _merge_preserving_masked_secrets(old_value, value)
        elif isinstance(value, list) and isinstance(old_value, list):
            merged[key] = [
                _merge_preserving_masked_secrets(old_item, new_item)
                if isinstance(old_item, dict) and isinstance(new_item, dict)
                else new_item
                for old_item, new_item in zip(old_value, value)
            ] + value[len(old_value):]
        else:
            merged[key] = value
    return merged


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _custom_assets_dir() -> Path:
    return get_root_dir() / "assets" / "custom"


def _asset_label_path() -> Path:
    return get_root_dir() / "assets" / "_labels.json"


def _load_asset_labels() -> Dict[str, str]:
    path = _asset_label_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_asset_label(name: str, label: str) -> None:
    labels = _load_asset_labels()
    if label:
        labels[name] = label
    path = _asset_label_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")


def _custom_asset_rel_path(name: str, extension: str = "md") -> str:
    _validate_id(name, "asset_name")
    if extension not in {"md", "yaml", "yml", "json", "txt"}:
        raise HTTPException(400, "Unsupported asset extension")
    return f"assets/custom/{name}.{extension}"


def _resolve_asset_file(name: str) -> Optional[str]:
    if name in _ALL_ASSET_FILES:
        return _ALL_ASSET_FILES[name]
    _validate_id(name, "asset_name")
    custom_dir = _custom_assets_dir()
    for extension in ("md", "yaml", "yml", "json", "txt"):
        candidate = custom_dir / f"{name}.{extension}"
        if candidate.exists():
            return str(candidate.relative_to(get_root_dir())).replace("\\", "/")
    return None


def _delete_chapter_dir(root_dir: Path, chapter_id: str) -> Path:
    safe_id = _validate_id(chapter_id, "chapter_id")
    chapters_dir = Path(root_dir) / "workspace" / "chapters"
    chapter_dir = chapters_dir / f"chapter_{safe_id}"
    if not chapter_dir.exists() or not chapter_dir.is_dir():
        raise HTTPException(404, f"Chapter {safe_id} not found")
    shutil.rmtree(chapter_dir)
    store = SQLiteStateStore(root_dir)
    store.delete_chapter_index(safe_id)
    _purge_chapter_vectors_best_effort(root_dir, safe_id)
    return chapter_dir


def _purge_chapter_vectors_best_effort(root_dir: Path, chapter_id: str) -> None:
    """Chroma cleanup after SQLite purge (must not run inside db_write_lock)."""
    import logging

    logger = logging.getLogger("web.server")
    try:
        from novel_agent.services.embedding_policy import create_vector_store_for_project

        vector_store = create_vector_store_for_project(root_dir)
        collection = getattr(vector_store, "chroma_collection", None)
        if collection is None:
            return
        import json
        import sqlite3

        db_path = root_dir / "data" / "novel.sqlite"
        ids_to_delete: list = []
        if db_path.is_file():
            conn = sqlite3.connect(str(db_path))
            try:
                for row in conn.execute("select id, metadata from vector_embeddings"):
                    id_val, meta_str = row[0], row[1]
                    if str(id_val).startswith(f"chapter_{chapter_id}"):
                        ids_to_delete.append(id_val)
                        continue
                    if meta_str:
                        try:
                            meta = json.loads(meta_str)
                            ch = meta.get("chapter") or meta.get("chapter_id")
                            if str(ch) == str(chapter_id):
                                ids_to_delete.append(id_val)
                        except json.JSONDecodeError:
                            pass
            finally:
                conn.close()
        if ids_to_delete:
            collection.delete(ids=list(set(ids_to_delete)))
    except Exception as exc:
        logger.debug("Chroma vector purge skipped for chapter %s: %s", chapter_id, exc)


def _sync_outline_to_character_cards(root: Path, outline: Dict[str, Any]):
    import logging
    logger = logging.getLogger("web.server")
    char_cards_path = root / "assets" / "character_cards.yaml"
    protagonist = outline.get("protagonist", {})
    proto_name = protagonist.get("name", "林越")
    if proto_name == "主角":
        proto_name = "林越"
        
    lines = ["characters:"]
    lines.append("  - id: protagonist")
    lines.append(f"    name: {proto_name}")
    lines.append("    fixed_profile:")
    lines.append("      role: 主角")
    lines.append(f"      core_motivation: {protagonist.get('desire', '探索真相')}")
    lines.append("    current_state:")
    lines.append("      location: 未知")
    lines.append("      emotion: 平静")
    lines.append("      physical_state: 健康")
    lines.append("    personality_constraints:")
    lines.append(f"      - {protagonist.get('flaw', '有些执着')}")
    lines.append(f"      - {protagonist.get('edge', '独特能力')}")
    lines.append("    speech_style:")
    lines.append("      - 语气沉稳")
    lines.append("    must_not:")
    lines.append("      - 轻易放弃")
    
    main_cast = outline.get("main_cast", [])
    if isinstance(main_cast, list):
        for idx, cast in enumerate(main_cast):
            cast_name = ""
            cast_role = "重要配角"
            relationship = "待填写"
            cast_confidential = "待填写"
            if isinstance(cast, dict):
                cast_name = cast.get("name")
                cast_role = cast.get("role", "配角")
                relationship = cast.get("relationship_to_protagonist", "与主角的关系待定")
                cast_confidential = cast.get("secret_or_pressure", "无特殊秘密")
            elif isinstance(cast, str):
                cast_name = cast
            
            if cast_name and cast_name != "主角" and cast_name != proto_name:
                safe_id = f"cast_{idx + 1}"
                lines.append(f"  - id: {safe_id}")
                lines.append(f"    name: {cast_name}")
                lines.append("    fixed_profile:")
                lines.append(f"      role: {cast_role}")
                lines.append(f"      core_motivation: {relationship}")
                lines.append("    current_state:")
                lines.append("      location: 未知")
                lines.append("      emotion: 平静")
                lines.append("      physical_state: 健康")
                lines.append("    personality_constraints:")
                lines.append(f"      - {cast_confidential}")
                lines.append("    speech_style:")
                lines.append("      - 语气正常")
                lines.append("    must_not:")
                lines.append("      - OOC (脱离人设)")
                
    char_cards_path.parent.mkdir(parents=True, exist_ok=True)
    char_cards_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    
    # 同步更新 SQLite 数据库中的主角名
    db_path = root / "data" / "novel.sqlite"
    if db_path.exists():
        try:
            import sqlite3
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "UPDATE character_state SET name = ? WHERE id = 'protagonist'",
                    (proto_name,)
                )
                conn.commit()
                logger.info("Successfully updated protagonist name to '%s' in sqlite", proto_name)
        except Exception as e:
            logger.warning("Failed to sync protagonist name to sqlite character_state: %s", e)


def _sync_outline_to_world_bible(root: Path, outline: Dict[str, Any]):
    import logging
    logger = logging.getLogger("web.server")
    world_bible_path = root / "assets" / "world_bible.md"
    genre = outline.get("genre_positioning", "通用题材")
    theme = outline.get("core_theme", "")
    logline = outline.get("logline", "")
    rules = outline.get("world_rules", [])
    forbidden = outline.get("forbidden_moves", [])
    antagonists = outline.get("antagonistic_forces", [])
    promises = outline.get("reader_promise", [])
    
    lines = []
    lines.append(f"# 世界观设定 ({genre})")
    lines.append("")
    if theme:
        lines.append(f"本作品核心主题：{theme}")
        lines.append("")
    if logline:
        lines.append(f"一句话梗概：{logline}")
        lines.append("")
        
    lines.append("## 核心规则")
    if rules:
        for r in rules:
            lines.append(f"- {r}")
    else:
        lines.append("- 不要让子 Agent 临时发明能力来源。")
        lines.append("- 不要让官方组织过早介入。")
        lines.append("- 所有超自然或异常设定都必须先在伏笔中出现，再进入明示阶段。")
    lines.append("")

    if antagonists:
        lines.append("## 阻力系统/敌对势力")
        for a in antagonists:
            lines.append(f"- {a}")
        lines.append("")

    if promises:
        lines.append("## 读者承诺")
        for p in promises:
            lines.append(f"- {p}")
        lines.append("")
        
    lines.append("## 创作禁忌")
    if forbidden:
        for f in forbidden:
            lines.append(f"- {f}")
    else:
        lines.append("- 关键人物的身份、年龄、核心动机不能在正文 Agent 中更改。")
        lines.append("- 已关闭伏笔不能被重新打开，除非总控明确允许。")
    lines.append("")
    
    world_bible_path.parent.mkdir(parents=True, exist_ok=True)
    world_bible_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Successfully synced outline settings to world_bible.md")


def _preserve_outline_identity(generated: Dict[str, Any], existing: Dict[str, Any]) -> Dict[str, Any]:
    if not existing:
        return generated
    merged = dict(generated)
    for key in ("title_options", "chosen_title"):
        if existing.get(key):
            merged[key] = existing[key]
    if existing.get("protagonist"):
        protagonist = dict(generated.get("protagonist", {}))
        protagonist.update(existing.get("protagonist", {}))
        merged["protagonist"] = protagonist
    return merged


def get_outline(root_dir: Optional[Path] = None) -> Dict[str, Any]:
    outline_path = Path(root_dir or get_root_dir()) / "workspace" / "outline.json"
    if not outline_path.exists():
        return {}
    return _read_json(outline_path)


def list_chapters() -> List[ChapterSummary]:
    chapters_dir = get_root_dir() / "workspace" / "chapters"
    results: List[ChapterSummary] = []
    if not chapters_dir.exists():
        return results
    existing_ids: List[int] = []
    by_num: dict = {}
    for chapter_dir in sorted(chapters_dir.glob("chapter_*")):
        if not chapter_dir.is_dir():
            continue
        chapter_id = chapter_dir.name.replace("chapter_", "")
        plan = _read_json(chapter_dir / "plan.json")
        wordcount = _read_json(chapter_dir / "reports" / "wordcount.json")
        audit = _read_json(chapter_dir / "reports" / "audit.json")
        word_count = wordcount.get("count", 0)
        if not word_count:
            word_count = count_chinese_chars(_read_text(chapter_dir / "chapter_final.txt"))
        try:
            num = int(chapter_id)
            existing_ids.append(num)
        except ValueError:
            num = None
        summary = ChapterSummary(
            chapter_id=chapter_id,
            title=plan.get("chapter_title", ""),
            word_count=word_count,
            risk_level=audit.get("risk_level", ""),
            final_path=str(chapter_dir / "chapter_final.txt"),
        )
        if num is not None:
            by_num[num] = summary
        else:
            results.append(summary)
    # Fill gaps between min and max chapter numbers
    if existing_ids:
        for n in range(min(existing_ids), max(existing_ids) + 1):
            if n in by_num:
                results.append(by_num[n])
            else:
                results.append(ChapterSummary(
                    chapter_id=f"{n:03d}",
                    title="[缺失断档章]",
                    word_count=0,
                    risk_level="",
                    final_path="",
                    is_missing=True,
                ))
    return results


def _ensure_dirs(root: Path) -> None:
    """Create required directories and default config files if missing."""
    for d in ("config", "state", "assets", "prompts", "workspace", "dashboard"):
        (root / d).mkdir(parents=True, exist_ok=True)
    config_path = root / "config" / "pipeline.yaml"
    if not config_path.exists():
        global_config_path = BASE_DIR / "config" / "pipeline.yaml"
        if global_config_path.exists():
            try:
                shutil.copy2(global_config_path, config_path)
            except Exception as exc:
                logger.warning("Failed to copy default pipeline config: %s", exc)
        if not config_path.exists():
            _write_yaml(config_path, {
                "chapter": {"default_target_chars": [1200, 2200], "default_scene_target_chars": [400, 800]},
                "runtime": {"max_workers": 4, "retry_attempts": 1, "interactive": False},
                "llm": {"provider": "openai", "base_url": "${OPENAI_BASE_URL}", "api_key": "${OPENAI_API_KEY}"},
                "embedding": {"provider": "stub"},
            })
    _copy_default_assets(root / "assets")
    _copy_default_prompts(root / "prompts")


def _first_configured_model_id(root_dir: Path) -> str:
    from web.model_library import ModelLibrary
    models = ModelLibrary(root_dir).list_models()
    return models[0]["id"] if models else ""


def _effective_pipeline_settings(root_dir: Path) -> Dict[str, Any]:
    settings = load_pipeline_settings(root_dir)
    llm = settings.setdefault("llm", {})
    has_model_ref = bool(
        llm.get("daily_model_id")
        or llm.get("default_model_id")
        or llm.get("default", {}).get("model_ref")
    )
    provider = llm.get("provider")
    nested_provider = llm.get("default", {}).get("provider")
    is_static = provider in (None, "", "static") and nested_provider in (None, "", "static")
    if not has_model_ref and is_static:
        model_id = _first_configured_model_id(root_dir)
        if model_id:
            llm["daily_model_id"] = model_id
            llm["default_model_id"] = model_id
    if not llm.get("reasoning_model_id"):
        from web.model_library import ModelLibrary
        model_ids = {model["id"] for model in ModelLibrary(root_dir).list_models()}
        if "deepseek-v4-pro" in model_ids:
            llm["reasoning_model_id"] = "deepseek-v4-pro"
    return settings
