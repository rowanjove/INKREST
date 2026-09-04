"""Permission vocabulary and content identity for first-party plugins.

Python plugins still execute in the local application process. These permissions
describe the product surfaces a plugin is expected to use and form an explicit,
content-bound trust contract; they are not an operating-system sandbox.
"""

from __future__ import annotations

import hashlib
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List


class PluginCapability(str, Enum):
    LOCAL_CODE = "local_code"
    PROJECT_CATALOG_READ = "project_catalog_read"
    PROJECT_READ = "project_read"
    PROJECT_WRITE = "project_write"
    ALL_PROJECTS_READ = "all_projects_read"
    ALL_PROJECTS_WRITE = "all_projects_write"
    MODEL_ACCESS = "model_access"
    NETWORK_ACCESS = "network_access"
    FILE_EXPORT = "file_export"
    WEB_ROUTES = "web_routes"
    UI_EMBED = "ui_embed"
    COMMAND_EXECUTION = "command_execution"
    LEGACY_FULL_ACCESS = "legacy_full_access"


CAPABILITY_INFO: Dict[str, Dict[str, str]] = {
    PluginCapability.LOCAL_CODE.value: {
        "label": "运行本机 Python 代码",
        "description": "最高风险：代码在栖墨后端进程中运行，可继承当前用户权限，必须单独确认。",
        "risk": "high",
    },
    PluginCapability.PROJECT_CATALOG_READ.value: {
        "label": "读取项目目录元数据",
        "description": "读取作品列表、书名、ID、更新时间和章节数等目录元数据，不读取正文。",
        "risk": "low",
    },
    PluginCapability.PROJECT_READ.value: {
        "label": "读取项目内容",
        "description": "读取正文、设定、状态和项目配置。",
        "risk": "low",
    },
    PluginCapability.PROJECT_WRITE.value: {
        "label": "修改项目内容",
        "description": "写入正文、状态、规则或项目配置。",
        "risk": "medium",
    },
    PluginCapability.ALL_PROJECTS_READ.value: {
        "label": "跨项目读取正文与设定",
        "description": "读取所有已存在作品的正文、设定与状态；跨作品检索或统计所需。",
        "risk": "high",
    },
    PluginCapability.ALL_PROJECTS_WRITE.value: {
        "label": "跨项目修改作品内容",
        "description": "跨项目批量修改或删除内容；极高风险。",
        "risk": "high",
    },
    PluginCapability.MODEL_ACCESS.value: {
        "label": "调用模型能力",
        "description": "参与模型路由、提示词处理或生成流水线。",
        "risk": "medium",
    },
    PluginCapability.NETWORK_ACCESS.value: {
        "label": "访问网络",
        "description": "连接第三方服务；可能传输插件处理的数据。",
        "risk": "high",
    },
    PluginCapability.FILE_EXPORT.value: {
        "label": "创建导出文件",
        "description": "在用户选择的位置生成或转换文件。",
        "risk": "medium",
    },
    PluginCapability.WEB_ROUTES.value: {
        "label": "注册本地 Web 路由",
        "description": "向本地应用增加 API 或页面入口。",
        "risk": "high",
    },
    PluginCapability.UI_EMBED.value: {
        "label": "嵌入前端界面",
        "description": "在栖墨宿主内嵌入独立页面或沙箱视图。",
        "risk": "medium",
    },
    PluginCapability.COMMAND_EXECUTION.value: {
        "label": "注册命令",
        "description": "向应用命令系统增加可执行操作。",
        "risk": "high",
    },
    PluginCapability.LEGACY_FULL_ACCESS.value: {
        "label": "旧式插件完全访问",
        "description": "插件没有清单，无法预先判定边界；按最高权限处理。",
        "risk": "high",
    },
}


DEFAULT_CAPABILITIES: Dict[str, tuple[str, ...]] = {
    "pipeline_hook": ("project_read", "project_write", "model_access"),
    "quality_guard": ("project_read",),
    "exporter": ("project_read", "file_export"),
    "llm_provider": ("model_access", "network_access"),
    "agent_override": ("project_read", "model_access"),
    "pipeline_phase": ("project_read", "project_write", "model_access"),
    "vector_store": ("project_read", "project_write"),
    "embedding_provider": ("model_access", "network_access"),
    "approval_strategy": ("project_read",),
    "rules_extension": ("project_read",),
    "prompt_enhancer": ("project_read", "model_access"),
    "event_listener": ("project_read",),
    "web_extension": ("project_read", "project_write", "web_routes"),
    "command": ("project_read", "project_write", "command_execution"),
    "sensitive_scanner": ("project_read",),
}

RISK_ORDER = {"low": 0, "medium": 1, "high": 2}
IGNORED_DIGEST_PARTS = {"__pycache__", ".git", ".DS_Store"}


def validate_declared_capabilities(raw: Any) -> List[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("capabilities 必须是字符串数组")
    values: List[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("capabilities 只能包含非空字符串")
        value = item.strip()
        if value not in CAPABILITY_INFO:
            raise ValueError(f"未知插件权限: {value}")
        if value in values:
            raise ValueError(f"重复插件权限: {value}")
        values.append(value)
    return values


def effective_capabilities(
    plugin_type: str,
    declared: Iterable[str] = (),
    *,
    local: bool = True,
    legacy: bool = False,
) -> List[str]:
    values = set(DEFAULT_CAPABILITIES.get(plugin_type, ()))
    values.update(str(item) for item in declared)
    if local:
        values.add(PluginCapability.LOCAL_CODE.value)
    if legacy:
        values.add(PluginCapability.LEGACY_FULL_ACCESS.value)
    return sorted(values)


def capability_details(capabilities: Iterable[str]) -> List[Dict[str, str]]:
    return [
        {"id": capability, **CAPABILITY_INFO[capability]}
        for capability in capabilities
        if capability in CAPABILITY_INFO
    ]


def risk_level(capabilities: Iterable[str]) -> str:
    level = "low"
    for capability in capabilities:
        risk = CAPABILITY_INFO.get(capability, {}).get("risk", "high")
        if RISK_ORDER[risk] > RISK_ORDER[level]:
            level = risk
    return level


def risk_summary(capabilities: Iterable[str], *, legacy: bool = False) -> str:
    values = set(capabilities)
    if legacy:
        return "旧式单文件插件没有权限清单，将以本机 Python 代码的最高风险边界运行。"
    if (
        PluginCapability.ALL_PROJECTS_READ.value in values
        or PluginCapability.ALL_PROJECTS_WRITE.value in values
    ):
        return "插件请求了跨项目读取或修改全部作品内容的权限；请确认插件来源绝对可信。"
    if PluginCapability.NETWORK_ACCESS.value in values:
        return "插件会在本机运行代码并可访问网络；请只信任来源明确且内容经过核对的插件。"
    return "插件会在本机后端进程中运行 Python 代码；权限确认不等同于操作系统沙箱。"


def digest_plugin_path(path: Path) -> str:
    root = Path(path)
    digest = hashlib.sha256()
    if root.is_file():
        _update_digest(digest, root.name, root)
        return digest.hexdigest()

    files = sorted(
        candidate
        for candidate in root.rglob("*")
        if candidate.is_file()
        and not any(part in IGNORED_DIGEST_PARTS for part in candidate.relative_to(root).parts)
        and candidate.suffix.lower() not in {".pyc", ".pyo"}
    )
    for candidate in files:
        _update_digest(digest, candidate.relative_to(root).as_posix(), candidate)
    return digest.hexdigest()


def _update_digest(digest: Any, relative_name: str, path: Path) -> None:
    digest.update(relative_name.encode("utf-8"))
    digest.update(b"\0")
    digest.update(path.read_bytes())
    digest.update(b"\0")
