import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

import web.context as ws_server
import web.helpers as ws_helpers

ws_server._validate_id = ws_helpers._validate_id
ws_server._resolve_asset_file = ws_helpers._resolve_asset_file
ws_server._load_asset_labels = ws_helpers._load_asset_labels
ws_server._read_text = ws_helpers._read_text
ws_server._ALL_ASSET_FILES = ws_helpers._ALL_ASSET_FILES
ws_server._custom_asset_rel_path = ws_helpers._custom_asset_rel_path
ws_server._save_asset_label = ws_helpers._save_asset_label
from web.models import (
    AssetCreate,
    AssetGenerateRequest,
    AssetUpdate,
    ComposeRequest,
)

router = APIRouter()


# ---- Assets ----

@router.get("/api/assets")
def list_assets() -> List[Dict[str, Any]]:
    return ws_server.preset_manager.list_assets()


@router.get("/api/assets/{name}")
def get_asset(name: str) -> Dict[str, str]:
    ws_server._validate_id(name, "asset_name")
    if name in ("style_guide", "rules", "sensitive_words"):
        ws_helpers.ensure_writing_standards_assets(ws_server.get_root_dir())
    rel_path = ws_server._resolve_asset_file(name)
    if not rel_path:
        raise HTTPException(404, f"Asset '{name}' not found")
    path = ws_server.get_root_dir() / rel_path
    return {
        "name": name,
        "label": ws_server._load_asset_labels().get(name, ""),
        "path": rel_path,
        "content": ws_server._read_text(path),
    }


@router.post("/api/assets")
def create_asset(body: AssetCreate) -> Dict[str, str]:
    name = ws_server._validate_id(body.name, "asset_name")
    rel_path = ws_server._ALL_ASSET_FILES.get(name)
    if rel_path:
        path = ws_server.get_root_dir() / rel_path
        if path.exists():
            raise HTTPException(409, f"Asset '{name}' already exists")
    else:
        resolved = ws_server._resolve_asset_file(name)
        if resolved:
            raise HTTPException(409, f"Asset '{name}' already exists")
        rel_path = ws_server._custom_asset_rel_path(name, body.extension)
        
    path = ws_server.get_root_dir() / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body.content, encoding="utf-8")
    ws_server._save_asset_label(name, body.label)
    return {"name": name, "path": rel_path, "status": "created"}


@router.put("/api/assets/{name}")
def update_asset(name: str, body: AssetUpdate) -> Dict[str, str]:
    ws_server._validate_id(name, "asset_name")
    rel_path = ws_server._resolve_asset_file(name)
    if not rel_path:
        raise HTTPException(404, f"Asset '{name}' not found")
    path = ws_server.get_root_dir() / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body.content, encoding="utf-8")
    return {"name": name, "status": "updated"}


@router.post("/api/assets/generate")
def generate_asset(body: AssetGenerateRequest) -> Dict[str, str]:
    from novel_agent.pipeline import PipelineConfig

    prompt = f"""你是小说项目素材编辑。请生成一份可直接保存的项目素材。

素材类型：{body.asset_type}
素材数量：{body.count}
必含属性：{", ".join(body.attributes) if body.attributes else "按素材类型自行设计"}
参数：{json.dumps(body.parameters, ensure_ascii=False)}
额外要求：{body.instructions or "无"}

输出要求：
1. 只输出素材正文，不要解释。
2. 如果是角色卡、规则、条目列表，优先使用 YAML。
3. 内容要便于后续小说生成 Agent 读取和复用。
"""
    config = PipelineConfig.from_config(ws_server.get_root_dir())
    content = config.get_llm("asset_generator").generate("asset_generator", prompt).strip()
    name = ws_server._validate_id(body.name, "asset_name")
    rel_path = ws_server._resolve_asset_file(name)
    if not rel_path:
        rel_path = ws_server._custom_asset_rel_path(name, "yaml" if body.asset_type in {"角色卡", "写作规则"} else "md")
    path = ws_server.get_root_dir() / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    ws_server._save_asset_label(name, body.label or body.asset_type)
    return {"name": name, "path": rel_path, "content": content, "status": "generated"}


class ExtractSyncRequest(BaseModel):
    chapter_text: str = Field(..., min_length=1)


@router.post("/api/assets/extract-sync")
def extract_and_sync_assets(body: ExtractSyncRequest) -> Dict[str, Any]:
    """Extract character and setting entities from the chapter text and sync them to assets."""
    from novel_agent.pipeline import PipelineConfig
    import re
    import yaml
    from pydantic import BaseModel
    
    prompt = f"""你是小说项目素材提取专家。请从以下的小说章节文本中，提取出所有出现的人物角色、特殊道具/宝物、核心世界观设定/地名等实体信息。
    
【小说章节文本】
{body.chapter_text}

【输出格式要求】
必须只输出一个 JSON 数组，包含提取到的所有实体，格式如下：
[
  {{"name": "实体英文ID", "label": "实体中文名称", "type": "角色/道具/设定", "description": "特征、外貌、性格或本章中新发生的状态变化"}}
]
注意：
1. "name" 字段必须符合标识符规范：仅包含英文字母、数字和下划线，禁止空格和特殊字符。例如“李四”可以为 "li_si" 或 "lisi"，“乾坤袋”可以为 "qian_kun_dai"。
2. 必须且只能输出 JSON 数组，严禁包含任何 Markdown 格式包裹（如 ```json 等）、旁白、前言或后续解释。"""

    try:
        config = PipelineConfig.from_config(ws_server.get_root_dir())
        llm = config.get_llm("asset_generator")
        raw_response = llm.generate("asset_generator", prompt).strip()
        
        # Clean response from markdown json wrapper if present
        if raw_response and raw_response.startswith("```"):
            lines = (raw_response or "").splitlines()
            if len(lines) > 2:
                raw_response = "\n".join(lines[1:-1]).strip()
        # Find json array block
        json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_response, re.DOTALL)
        if json_match:
            raw_response = json_match.group(0)
            
        entities = json.loads(raw_response)
        
        synced_assets = []
        for ent in entities:
            name = ent.get("name")
            label = ent.get("label", name)
            asset_type = ent.get("type", "设定")
            description = ent.get("description", "")
            
            if not name or not description:
                continue
                
            # Sanitize name to match path regex ^[a-zA-Z0-9_-]+$
            name = re.sub(r'[^a-zA-Z0-9_-]', '', name)
            if not name:
                continue
                
            # Check asset classification and sync accordingly
            if asset_type in {"角色", "角色卡"}:
                card_path = ws_server.get_root_dir() / "assets" / "character_cards.yaml"
                card_path.parent.mkdir(parents=True, exist_ok=True)
                card_data = {}
                if card_path.exists():
                    try:
                        card_data = yaml.safe_load(card_path.read_text(encoding="utf-8")) or {}
                    except Exception:
                        pass
                if not isinstance(card_data, dict):
                    card_data = {}
                characters_list = card_data.setdefault("characters", [])
                if not isinstance(characters_list, list):
                    characters_list = []
                    card_data["characters"] = characters_list
                
                existing_char = None
                for char in characters_list:
                    if char.get("id") == name or char.get("name") == label:
                        existing_char = char
                        break
                
                if existing_char:
                    curr_desc = existing_char.get("description", "")
                    if curr_desc:
                        existing_char["description"] = curr_desc + f"\n[本章提取更新]: {description}"
                    else:
                        existing_char["description"] = description
                    status = "updated"
                else:
                    new_char = {
                        "id": name,
                        "name": label,
                        "description": description,
                        "fixed_profile": {
                            "role": "配角",
                            "core_motivation": ""
                        }
                    }
                    characters_list.append(new_char)
                    status = "created"
                
                card_path.write_text(yaml.safe_dump(card_data, allow_unicode=True, sort_keys=False), encoding="utf-8")
                synced_assets.append({"name": name, "status": status, "label": label, "type": asset_type})
                
            elif asset_type in {"设定", "世界观设定", "世界观"}:
                bible_path = ws_server.get_root_dir() / "assets" / "world_bible.md"
                bible_path.parent.mkdir(parents=True, exist_ok=True)
                
                content = ""
                if bible_path.exists():
                    content = bible_path.read_text(encoding="utf-8")
                
                heading_pattern = f"## {label}"
                if heading_pattern in content:
                    content += f"\n\n### 本章提取更新 ({label})\n{description}\n"
                    status = "updated"
                else:
                    content += f"\n\n## {label} ({name})\n- 类型: {asset_type}\n- 描述: {description}\n"
                    status = "created"
                
                bible_path.write_text(content.strip() + "\n", encoding="utf-8")
                synced_assets.append({"name": name, "status": status, "label": label, "type": asset_type})
                
            else:
                ext = "md"
                rel_path = ws_server._custom_asset_rel_path(name, ext)
                path = ws_server.get_root_dir() / rel_path
                
                if path.exists():
                    try:
                        content = path.read_text(encoding="utf-8")
                        path.write_text(content.strip() + f"\n\n### 本章提取更新\n{description}\n", encoding="utf-8")
                        status = "updated"
                    except Exception:
                        status = "failed"
                else:
                    md_data = f"# {label}\n\n* 类型：{asset_type}\n* 标识：{name}\n\n## 设定描述\n{description}\n"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(md_data, encoding="utf-8")
                    ws_server._save_asset_label(name, label or asset_type)
                    status = "created"
                
                synced_assets.append({"name": name, "status": status, "label": label, "type": asset_type})
                
        return {"success": True, "synced": synced_assets}
    except Exception as e:
        return {"success": False, "error": str(e), "synced": []}


# ---- Presets ----

@router.get("/api/presets")
def list_presets(channel: Optional[str] = None) -> List[Dict[str, Any]]:
    return ws_server.preset_manager.list_presets(channel=channel)


@router.get("/api/presets/components")
def list_components(
    type: str = "themes", channel: Optional[str] = None
) -> List[Dict[str, Any]]:
    return ws_server.preset_manager.list_components(type, channel=channel)


@router.get("/api/presets/components/{component_type}/{component_id}")
def get_component(component_type: str, component_id: str) -> Dict[str, Any]:
    ws_server._validate_id(component_id, "component_id")
    return ws_server.preset_manager.get_component(component_type, component_id)


@router.get("/api/presets/{preset_id}")
def get_preset(preset_id: str) -> Dict[str, Any]:
    ws_server._validate_id(preset_id, "preset_id")
    return ws_server.preset_manager.get_preset(preset_id)


@router.post("/api/presets")
def create_preset(body: Dict[str, Any]) -> Dict[str, Any]:
    if body.get("id"):
        ws_server._validate_id(body["id"], "preset_id")
    return ws_server.preset_manager.create_preset(body)


@router.delete("/api/presets/{preset_id}")
def delete_preset(preset_id: str) -> Dict[str, str]:
    ws_server._validate_id(preset_id, "preset_id")
    ws_server.preset_manager.delete_preset(preset_id)
    return {"status": "deleted"}


@router.post("/api/presets/compose")
def compose_preset(req: ComposeRequest) -> Dict[str, Any]:
    project_dir = None
    if req.project_id:
        safe_project_id = ws_server._validate_id(req.project_id, "project_id")
        projects_root = (ws_server.BASE_DIR / "projects").resolve()
        project_dir = (projects_root / safe_project_id).resolve()
        if projects_root not in project_dir.parents:
            raise HTTPException(400, "Invalid project_id: path traversal detected")
        if not project_dir.exists():
            raise HTTPException(404, f"Project {safe_project_id} not found")
    return ws_server.preset_manager.apply_composition(
        channel=req.channel,
        theme=req.theme,
        mechanisms=req.mechanisms,
        cool_points=req.cool_points,
        project_dir=project_dir,
    )


# ---- Terminology Import & Asset Delete ----

class ImportToTerminologyRequest(BaseModel):
    names: List[str]


def update_markdown_section(doc_content: str, title: str, section_content: str) -> str:
    """Idempotently replace or append a markdown section headed by `title` (e.g. ## Label)."""
    lines = (doc_content or "").splitlines()
    start_idx = -1
    end_idx = -1
    
    for idx, line in enumerate(lines):
        if line.strip() == title.strip():
            start_idx = idx
            break
            
    if start_idx != -1:
        # Find ending index of this section (the next ## heading or EOF)
        for idx in range(start_idx + 1, len(lines)):
            if lines[idx].startswith("## "):
                end_idx = idx
                break
        if end_idx == -1:
            end_idx = len(lines)
            
        new_lines = lines[:start_idx] + [section_content.strip()] + lines[end_idx:]
        return "\n".join(new_lines)
    else:
        # Append to the end
        doc_content = doc_content.rstrip()
        if doc_content:
            return doc_content + "\n\n" + section_content.strip() + "\n"
        else:
            return section_content.strip() + "\n"


@router.post("/api/assets/import-to-terminology")
def import_to_terminology(body: ImportToTerminologyRequest) -> Dict[str, Any]:
    import shutil
    names = body.names
    if not names:
        raise HTTPException(400, "No asset names specified")
        
    root_dir = ws_server.get_root_dir()
    rel_path = ws_server._resolve_asset_file("terminology")
    if not rel_path:
        rel_path = "assets/terminology.md"
        
    terminology_path = root_dir / rel_path
    terminology_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not terminology_path.exists():
        default_tpl = ws_server.BASE_DIR / "assets" / "terminology.md"
        if default_tpl.exists():
            shutil.copy2(default_tpl, terminology_path)
        else:
            terminology_path.write_text("# 名词解释\n\n## 专有名词/术语列表\n", encoding="utf-8")
            
    doc_content = terminology_path.read_text(encoding="utf-8")
    labels = ws_server._load_asset_labels()
    imported = []
    
    for name in names:
        ws_server._validate_id(name, "asset_name")
        asset_rel = ws_server._resolve_asset_file(name)
        if not asset_rel:
            continue
            
        asset_path = root_dir / asset_rel
        if not asset_path.exists():
            continue
            
        asset_content = asset_path.read_text(encoding="utf-8").strip()
        label = labels.get(name, name)
        
        entry_title = f"## {label}"
        formatted_entry = f"## {label}\n- 标识：{name}\n\n{asset_content}\n"
        
        doc_content = update_markdown_section(doc_content, entry_title, formatted_entry)
        imported.append({"name": name, "label": label})
        
    terminology_path.write_text(doc_content, encoding="utf-8")
    return {"status": "success", "imported": imported}


@router.delete("/api/assets/{name}")
def delete_asset(name: str) -> Dict[str, str]:
    ws_server._validate_id(name, "asset_name")
    rel_path = ws_server._resolve_asset_file(name)
    if not rel_path:
        raise HTTPException(404, f"Asset '{name}' not found")
        
    if name in ws_server._ALL_ASSET_FILES:
        raise HTTPException(400, f"Cannot delete built-in asset '{name}'")
        
    path = ws_server.get_root_dir() / rel_path
    if path.exists():
        path.unlink()
        
    try:
        labels = ws_server._load_asset_labels()
        if name in labels:
            labels.pop(name)
            path_labels = ws_server._asset_label_path()
            path_labels.write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
        
    return {"name": name, "status": "deleted"}
