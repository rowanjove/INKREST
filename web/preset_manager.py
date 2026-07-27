"""Preset manager for managing novel genre templates and component guidelines."""

import json
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from novel_agent.pipeline import load_project_pipeline_file, write_pipeline_file

from web.helpers import (
    ASSET_FILES,
    _ALL_ASSET_FILES,
    PROMPT_ROLES,
    _copy_default_assets,
    _copy_default_prompts,
    _custom_asset_rel_path,
    _custom_assets_dir,
    _load_asset_labels,
    _read_yaml,
    _resolve_asset_file,
    _template_presets_dir,
    _template_prompts_dir,
    _validate_id,
)


class PresetManager:
    """Manages novel writing presets (genre templates)."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.user_presets_dir = base_dir / "presets"

    def _builtin_presets_dir(self) -> Path:
        return _template_presets_dir()

    def _find_preset_dir(self, preset_id: str) -> Optional[Path]:
        for root in (self.user_presets_dir, self._builtin_presets_dir()):
            preset_dir = root / preset_id
            if preset_dir.exists() and preset_dir.is_dir():
                return preset_dir
        return None

    def _read_preset_meta(self, preset_dir: Path, built_in: bool) -> Optional[Dict[str, Any]]:
        meta_path = preset_dir / "meta.json"
        if not meta_path.exists():
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        meta.setdefault("id", preset_dir.name)
        meta["built_in"] = bool(meta.get("built_in", built_in))
        return meta

    def list_presets(self, channel: Optional[str] = None) -> List[Dict[str, Any]]:
        result = []
        seen = set()
        for root, built_in in ((self.user_presets_dir, False), (self._builtin_presets_dir(), True)):
            if not root.exists():
                continue
            for preset_dir in sorted(root.iterdir()):
                if not preset_dir.is_dir() or preset_dir.name.startswith("_") or preset_dir.name in seen:
                    continue
                meta = self._read_preset_meta(preset_dir, built_in)
                if not meta:
                    continue
                if channel and meta.get("channel") != channel:
                    continue
                seen.add(preset_dir.name)
                result.append(meta)
        return result

    def get_preset(self, preset_id: str) -> Dict[str, Any]:
        preset_dir = self._find_preset_dir(preset_id)
        if not preset_dir:
            raise HTTPException(404, f"Preset {preset_id} not found")
        meta_path = preset_dir / "meta.json"
        guide_path = preset_dir / "guide.md"
        if not meta_path.exists():
            raise HTTPException(404, f"Preset {preset_id} has no meta.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        guide = guide_path.read_text(encoding="utf-8") if guide_path.exists() else ""
        overrides_dir = preset_dir / "prompt_overrides"
        overrides = {}
        if overrides_dir.exists():
            for f in overrides_dir.glob("*.md"):
                overrides[f.stem] = f.read_text(encoding="utf-8")
        return {**meta, "guide": guide, "prompt_overrides": overrides}

    def create_preset(self, data: Dict[str, Any]) -> Dict[str, Any]:
        preset_id = data.get("id") or uuid.uuid4().hex[:8]
        preset_dir = self.user_presets_dir / preset_id
        preset_dir.mkdir(parents=True, exist_ok=True)
        (preset_dir / "prompt_overrides").mkdir(exist_ok=True)

        meta = {
            "id": preset_id,
            "name": data.get("name", "未命名预设"),
            "channel": data.get("channel", "male"),
            "category": data.get("category", ""),
            "subcategory": data.get("subcategory", ""),
            "tags": data.get("tags", []),
            "description": data.get("description", ""),
            "built_in": False,
        }
        (preset_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        guide = data.get("guide", "")
        (preset_dir / "guide.md").write_text(guide, encoding="utf-8")

        overrides = data.get("prompt_overrides", {})
        for role, content in overrides.items():
            if role in PROMPT_ROLES and content.strip():
                (preset_dir / "prompt_overrides" / f"{role}.md").write_text(content, encoding="utf-8")

        return meta

    def delete_preset(self, preset_id: str) -> None:
        built_in_dir = self._builtin_presets_dir() / preset_id
        if built_in_dir.exists():
            raise HTTPException(403, "Cannot delete built-in preset")
        preset_dir = self.user_presets_dir / preset_id
        if not preset_dir.exists():
            raise HTTPException(404, f"Preset {preset_id} not found")
        meta_path = preset_dir / "meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("built_in"):
                raise HTTPException(403, "Cannot delete built-in preset")
        shutil.rmtree(preset_dir)

    def apply_preset(self, preset_id: str, project_dir: Path) -> None:
        preset_data = self.get_preset(preset_id)
        guide = preset_data.get("guide", "")
        if guide:
            assets_dir = project_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            (assets_dir / "writing_guide.md").write_text(guide, encoding="utf-8")
        overrides = preset_data.get("prompt_overrides", {})
        if overrides:
            prompts_dir = project_dir / "prompts"
            prompts_dir.mkdir(parents=True, exist_ok=True)
            for role, content in overrides.items():
                (prompts_dir / f"{role}.md").write_text(content, encoding="utf-8")
        config_path = project_dir / "config" / "pipeline.yaml"
        config = load_project_pipeline_file(project_dir)
        config["preset_id"] = preset_id
        write_pipeline_file(config_path, config)

    def _components_base_dir(self) -> Path:
        template = _template_presets_dir()
        if template.exists() and (template / "themes").exists():
            return template
        return self.base_dir / "presets"

    def list_components(
        self, component_type: str, channel: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        valid_types = ("channels", "themes", "mechanisms", "cool_points")
        if component_type not in valid_types:
            raise HTTPException(400, f"Invalid component type: {component_type}")
        comp_dir = self._components_base_dir() / component_type
        if not comp_dir.exists():
            return []
        result = []
        for json_file in sorted(comp_dir.glob("*.json")):
            try:
                meta = json.loads(json_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if channel and component_type != "channels":
                channels = meta.get("channels", [])
                if channels and channel not in channels:
                    continue
            result.append(meta)
        return result

    def get_component(self, component_type: str, component_id: str) -> Dict[str, Any]:
        valid_types = ("channels", "themes", "mechanisms", "cool_points")
        if component_type not in valid_types:
            raise HTTPException(400, f"Invalid component type: {component_type}")
        comp_dir = self._components_base_dir() / component_type
        json_path = comp_dir / f"{component_id}.json"
        md_path = comp_dir / f"{component_id}.md"
        if not json_path.exists():
            raise HTTPException(404, f"Component {component_id} not found in {component_type}")
        meta = json.loads(json_path.read_text(encoding="utf-8"))
        guide = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
        return {**meta, "guide": guide}

    def compose_guide(
        self,
        channel: str,
        theme: str,
        mechanisms: Optional[List[str]] = None,
        cool_points: Optional[List[str]] = None,
    ) -> str:
        parts = []
        ch = self.get_component("channels", channel)
        parts.append(ch.get("guide", ""))
        th = self.get_component("themes", theme)
        parts.append(th.get("guide", ""))
        for mech_id in (mechanisms or []):
            mech = self.get_component("mechanisms", mech_id)
            parts.append(mech.get("guide", ""))
        for cp_id in (cool_points or []):
            cp = self.get_component("cool_points", cp_id)
            parts.append(cp.get("guide", ""))
        return "\n\n---\n\n".join(p for p in parts if p.strip())

    def apply_composition(
        self,
        channel: str,
        theme: str,
        mechanisms: Optional[List[str]] = None,
        cool_points: Optional[List[str]] = None,
        project_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        guide = self.compose_guide(channel, theme, mechanisms, cool_points)
        if project_dir:
            assets_dir = project_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            (assets_dir / "writing_guide.md").write_text(guide, encoding="utf-8")
            config_path = project_dir / "config" / "pipeline.yaml"
            config = load_project_pipeline_file(project_dir)
            config["preset_composition"] = {
                "channel": channel,
                "theme": theme,
                "mechanisms": mechanisms or [],
                "cool_points": cool_points or [],
            }
            write_pipeline_file(config_path, config)
        return {
            "channel": channel,
            "theme": theme,
            "mechanisms": mechanisms or [],
            "cool_points": cool_points or [],
            "guide": guide,
        }

    def list_assets(self) -> List[Dict[str, Any]]:
        from web.context import get_root_dir
        result = []
        labels = _load_asset_labels()
        for name, rel_path in _ALL_ASSET_FILES.items():
            path = get_root_dir() / rel_path
            result.append({
                "name": name,
                "label": labels.get(name, ""),
                "path": rel_path,
                "exists": path.exists(),
                "size": path.stat().st_size if path.exists() else 0,
                "custom": False,
            })
        custom_dir = _custom_assets_dir()
        if custom_dir.exists():
            for path in sorted(custom_dir.iterdir()):
                if not path.is_file() or path.suffix.lower().lstrip(".") not in {"md", "yaml", "yml", "json", "txt"}:
                    continue
                name = path.stem
                rel_path = str(path.relative_to(get_root_dir())).replace("\\", "/")
                result.append({
                    "name": name,
                    "label": labels.get(name, name),
                    "path": rel_path,
                    "exists": True,
                    "size": path.stat().st_size,
                    "custom": True,
                })
        return result
