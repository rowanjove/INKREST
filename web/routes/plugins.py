from typing import Any, Dict, List

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from web.context import get_plugin_manager
from web.helpers import _validate_id

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


class ToggleRequest(BaseModel):
    enabled: bool


class TrustRequest(BaseModel):
    digest: str
    capabilities: List[str]


class ConfigUpdateRequest(BaseModel):
    config: Dict[str, Any]


def _reload_plugin_manager(pm):
    from novel_agent.plugins.base import PluginType

    pm.shutdown()
    pm.plugins.clear()
    pm._active_by_type = {t: [] for t in PluginType}
    pm.initialize()
    from web.app import mount_plugin_web_extensions

    mount_plugin_web_extensions(pm)


@router.get("")
def list_plugins():
    """List all discovered plugins and their states."""
    pm = get_plugin_manager()
    return pm.list_plugin_catalog()


@router.get("/untrusted")
def list_untrusted_plugins():
    """List local plugins that require an explicit trust action before import."""
    pm = get_plugin_manager()
    catalog = pm.list_plugin_catalog()
    return {
        "plugins": [
            p["name"]
            for p in catalog
            if p.get("source") == "local" and not p.get("trusted")
        ]
    }


@router.post("/install")
async def install_plugin(file: UploadFile = File(...)):
    """Install a plugin from a .zip package (inkrest.plugin.json at archive root)."""
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(400, "请上传 .zip 格式的插件包")
    data = await file.read()
    pm = get_plugin_manager()
    try:
        result = pm.install_from_zip(data, replace=True)
    except Exception as exc:
        from novel_agent.plugins.manifest import ManifestError

        if isinstance(exc, ManifestError):
            raise HTTPException(400, str(exc)) from exc
        raise HTTPException(400, f"安装失败: {exc}") from exc
    _reload_plugin_manager(pm)
    return {"status": "ok", **result}


@router.post("/reload")
def reload_plugins():
    """Rescan and reload all plugins."""
    pm = get_plugin_manager()
    _reload_plugin_manager(pm)
    return {"status": "ok", "plugins_loaded": len(pm.plugins)}


@router.post("/{name}/trust")
def trust_plugin(name: str, req: TrustRequest):
    """Persist the exact content digest and permission grant confirmed by the user."""
    name = _validate_id(name, "plugin_name")
    pm = get_plugin_manager()
    catalog = {item["name"]: item for item in pm.list_plugin_catalog()}
    row = catalog.get(name)
    if not row or row.get("source") != "local":
        raise HTTPException(404, f"Local plugin {name} not found")
    if not pm.trust_local_plugin(
        name,
        digest=req.digest,
        capabilities=req.capabilities,
    ):
        raise HTTPException(
            409,
            detail={
                "code": "plugin_grant_changed",
                "message": "插件内容或权限已变化，请刷新后重新确认。",
                "digest": row.get("digest"),
                "capabilities": row.get("effective_capabilities", []),
            },
        )
    return {
        "name": name,
        "enabled": False,
        "trusted": True,
        "digest": row.get("digest"),
        "effective_capabilities": row.get("effective_capabilities", []),
    }


@router.get("/{name}")
def get_plugin(name: str):
    """Get single plugin detailed information."""
    name = _validate_id(name, "plugin_name")
    pm = get_plugin_manager()
    for item in pm.list_plugin_catalog():
        if item.get("name") == name:
            return item
    raise HTTPException(404, f"Plugin {name} not found")


@router.delete("/{name}")
def delete_plugin(name: str):
    """Uninstall a local plugin (remove files and registry)."""
    name = _validate_id(name, "plugin_name")
    pm = get_plugin_manager()
    if not pm.uninstall_plugin_by_id(name):
        raise HTTPException(404, f"Plugin {name} not found")
    _reload_plugin_manager(pm)
    return {"status": "ok", "name": name, "removed": True}


@router.put("/{name}/toggle")
def toggle_plugin(name: str, req: ToggleRequest):
    """Enable or disable a plugin."""
    name = _validate_id(name, "plugin_name")
    pm = get_plugin_manager()
    catalog = {p["name"]: p for p in pm.list_plugin_catalog()}
    row = catalog.get(name)
    if not row:
        raise HTTPException(404, f"Plugin {name} not found")

    if req.enabled:
        if row.get("source") == "local" and not row.get("trusted"):
            raise HTTPException(
                409,
                detail={
                    "code": "plugin_trust_required",
                    "message": "启用前必须先确认插件来源、内容摘要与权限。",
                    "digest": row.get("digest"),
                    "capabilities": row.get("effective_capabilities", []),
                },
            )
        if row.get("source") == "local" and name not in pm.plugins:
            pm._set_desired_enabled(name, True)
            _reload_plugin_manager(pm)
        if name not in pm.plugins:
            raise HTTPException(400, f"插件 {name} 未能加载，请检查清单与代码")
        success = pm.plugins[name].enabled or pm.enable_plugin(name)
    else:
        if name not in pm.plugins:
            pm._set_desired_enabled(name, False)
            success = True
        else:
            success = pm.disable_plugin(name)

    if not success:
        raise HTTPException(400, f"Failed to toggle plugin {name} to {req.enabled}")

    enabled = pm.plugins[name].enabled if name in pm.plugins else False
    payload: Dict[str, Any] = {"name": name, "enabled": enabled}
    if enabled:
        payload["security_notice"] = (
            "已启用的插件会在本机执行 Python 代码，等同于安装第三方程序；仅启用来源可信的插件。"
        )
    return payload


@router.put("/{name}/config")
def update_plugin_config(name: str, req: ConfigUpdateRequest):
    """Update plugin configuration."""
    name = _validate_id(name, "plugin_name")
    pm = get_plugin_manager()
    if name not in pm.plugins:
        pm._load_state_config()
        reg = pm._state_config.setdefault("plugins", {}).setdefault("registry", {}).setdefault(name, {})
        reg["config"] = req.config
        pm._save_state_config()
        return {"name": name, "config": req.config}

    success = pm.update_plugin_config(name, req.config)
    if not success:
        raise HTTPException(400, f"Failed to update plugin config for {name}")

    return {"name": name, "config": pm.get_plugin_config(name)}


@router.get("/{name}/schema")
def get_plugin_schema(name: str):
    """Get the JSON schema for configuring a plugin."""
    name = _validate_id(name, "plugin_name")
    pm = get_plugin_manager()
    for item in pm.list_plugin_catalog():
        if item.get("name") == name:
            return item.get("config_schema") or {}
    raise HTTPException(404, f"Plugin {name} not found")
