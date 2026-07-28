import json
import base64
import httpx
import ipaddress
import socket
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

import web.context as ws_server
from web.llm_errors import model_provider_http_error
from web.models import GenerateCoverRequest, SaveCoverRequest

router = APIRouter()

MAX_COVER_BYTES = 10 * 1024 * 1024


def _is_supported_image(data: bytes) -> bool:
    return (
        data.startswith(b"\xff\xd8\xff")
        or data.startswith(b"\x89PNG\r\n\x1a\n")
        or (len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP")
    )


def _image_type(data: bytes) -> Tuple[str, str]:
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp", "image/webp"
    raise HTTPException(400, "Cover image must be JPEG, PNG, or WebP")


def _cover_file(project_dir: Path) -> Tuple[Path, str]:
    for suffix, mime in ((".jpg", "image/jpeg"), (".png", "image/png"), (".webp", "image/webp")):
        candidate = project_dir / f"cover{suffix}"
        if candidate.exists():
            return candidate, mime
    raise HTTPException(404, "Cover image not found")


def _decode_cover_base64(cover_data: str) -> Tuple[bytes, str]:
    if "," in cover_data:
        cover_data = cover_data.split(",", 1)[1]
    if len(cover_data) > ((MAX_COVER_BYTES + 2) // 3) * 4:
        raise HTTPException(413, "Cover image exceeds the size limit")
    try:
        img_bytes = base64.b64decode(cover_data, validate=True)
    except Exception as exc:
        raise HTTPException(400, f"Base64 decode failed: {exc}")
    if len(img_bytes) > MAX_COVER_BYTES:
        raise HTTPException(413, "Cover image exceeds the size limit")
    _, mime = _image_type(img_bytes)
    return img_bytes, mime


def _validate_remote_image_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(400, "Image URL must use http or https")
    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(
                parsed.hostname,
                parsed.port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        }
    except socket.gaierror as exc:
        raise HTTPException(400, f"Image URL host could not be resolved: {exc}")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise HTTPException(400, "Image URL resolves to a private or non-public address")
    return url


def _download_remote_image(client: httpx.Client, url: str) -> Tuple[bytes, str]:
    safe_url = _validate_remote_image_url(url)
    with client.stream("GET", safe_url) as response:
        if response.status_code != 200:
            raise HTTPException(400, f"下载图片失败 (HTTP {response.status_code})")
        content = bytearray()
        for chunk in response.iter_bytes():
            content.extend(chunk)
            if len(content) > MAX_COVER_BYTES:
                raise HTTPException(413, "Cover image exceeds the size limit")
    _, mime = _image_type(bytes(content))
    return bytes(content), mime


@router.get("/api/projects/{pid}/cover")
def get_project_cover(pid: str) -> FileResponse:
    ws_server._validate_id(pid, "project_id")
    cover_path, mime = _cover_file(ws_server.BASE_DIR / "projects" / pid)
    return FileResponse(str(cover_path), media_type=mime)


@router.post("/api/projects/{pid}/suggest-cover-prompt")
def suggest_cover_prompt(pid: str) -> Dict[str, str]:
    ws_server._validate_id(pid, "project_id")
    project_dir = ws_server.BASE_DIR / "projects" / pid
    
    # 读取大纲/题材
    outline_path = project_dir / "workspace" / "outline.json"
    meta_path = project_dir / "config" / "project_meta.json"
    
    title = pid
    genre = "网络小说"
    description = "暂无简介"
    
    if outline_path.exists():
        try:
            outline = json.loads(outline_path.read_text(encoding="utf-8"))
            title = outline.get("chosen_title") or title
            genre = outline.get("genre") or genre
        except Exception:
            pass
            
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            genre = meta.get("genre") or genre
        except Exception:
            pass
    
    # 读项目简介
    registry = ws_server.project_manager._read_registry()
    if pid in registry.get("projects", {}):
        description = registry["projects"][pid].get("description") or description
        
    from novel_agent.pipeline import PipelineConfig
    config = PipelineConfig.from_config(project_dir)
    llm = config.get_llm("chief_editor")
    
    prompt_gen = f"""你是一名专业的网文封面画师。请根据以下小说的书名、题材和简介，设计一段用于 AI 图像生成模型（如 Midjourney、FLUX、DALL-E 3）的画图提示词（Prompt）。
画图提示词应当能够传达小说的题材氛围（例如仙侠修真、科幻星际、都市异能等）、主要视觉元素和情绪基调。
提示词可以使用英文，也可以是中文（更适合中文画图模型）。请直接给出最终的 Prompt 文本，不需要任何解释。

【小说书名】
{title}

【题材】
{genre}

【小说简介】
{description}

【输出提示词要求】
- 聚焦于画面背景、色彩、光影、题材标志性元素（例如修仙飞剑、科幻机甲、都市霓虹）。
- 画面应当有强烈的网文封面质感，气势恢宏或意境深远。
- 请直接输出生成的 Prompt 文本本身，不要带引号或任何解释性语言。
"""
    try:
        result = llm.generate("chief_editor", prompt_gen).strip()
        if result.startswith("`") or result.startswith('"'):
            result = result.strip("`\"'")
        return {"prompt": result}
    except Exception as e:
        raise model_provider_http_error("生成画图提示词", e)


@router.post("/api/projects/{pid}/generate-cover")
def generate_cover(pid: str, req: GenerateCoverRequest) -> Dict[str, str]:
    ws_server._validate_id(pid, "project_id")
    project_dir = ws_server.BASE_DIR / "projects" / pid
    
    # 从模型库读取配置
    lib = ws_server.ModelLibrary(project_dir)
    try:
        cfg = lib.get_model(req.model_id)
    except Exception:
        raise HTTPException(400, f"未找到指定的图像模型: {req.model_id}")
        
    url = f"{cfg.get('base_url', 'https://api.openai.com/v1').rstrip('/')}/images/generations"
    headers = {
        "Authorization": f"Bearer {cfg.get('api_key', '')}",
        "Content-Type": "application/json"
    }
    body = {
        "model": cfg.get("model", "dall-e-3"),
        "prompt": req.prompt,
        "n": 1
    }
    
    try:
        with httpx.Client(proxy=cfg.get("proxy") or None, timeout=float(cfg.get("timeout", 120))) as client:
            resp = client.post(url, headers=headers, json=body)
            if resp.status_code != 200:
                try:
                    err_msg = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    err_msg = resp.text
                raise HTTPException(400, f"绘图模型接口返回错误: {err_msg}")
            
            res_data = resp.json()
            img_url = None
            if "data" in res_data and len(res_data["data"]) > 0:
                img_url = res_data["data"][0].get("url")
                b64_json = res_data["data"][0].get("b64_json")
                if b64_json:
                    img_bytes, mime = _decode_cover_base64(b64_json)
                    encoded = base64.b64encode(img_bytes).decode("utf-8")
                    return {"image": f"data:{mime};base64,{encoded}"}
            
            if not img_url:
                raise HTTPException(400, f"接口未返回图片 URL 或数据: {res_data}")
            
            img_bytes, mime = _download_remote_image(client, img_url)
            encoded = base64.b64encode(img_bytes).decode("utf-8")
            return {"image": f"data:{mime};base64,{encoded}"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise model_provider_http_error("图像生成请求", e)


@router.post("/api/projects/{pid}/save-cover")
def save_cover(pid: str, req: SaveCoverRequest) -> Dict[str, str]:
    ws_server._validate_id(pid, "project_id")
    project_dir = ws_server.BASE_DIR / "projects" / pid
    if not project_dir.exists():
        raise HTTPException(404, "Project not found")
        
    cover_data = req.cover
    if "," in cover_data:
        cover_data = cover_data.split(",", 1)[1]
    if len(cover_data) > ((MAX_COVER_BYTES + 2) // 3) * 4:
        raise HTTPException(413, "Cover image exceeds the size limit")
        
    try:
        img_bytes = base64.b64decode(cover_data, validate=True)
    except Exception as e:
        raise HTTPException(400, f"Base64 解析失败: {e}")
        
    if len(img_bytes) > MAX_COVER_BYTES:
        raise HTTPException(413, "Cover image exceeds the size limit")
    suffix, _ = _image_type(img_bytes)

    for stale_suffix in (".jpg", ".png", ".webp"):
        stale_path = project_dir / f"cover{stale_suffix}"
        if stale_path.exists():
            stale_path.unlink()
    cover_path = project_dir / f"cover{suffix}"
    cover_path.write_bytes(img_bytes)
    
    ws_server.project_manager.touch_activity(pid)
        
    return {"status": "saved"}
