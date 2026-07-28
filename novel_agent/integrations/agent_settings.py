"""Persisted workspace settings for external AI agent integration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_AGENT_BRIDGE: Dict[str, Any] = {
    "mcp_mode": "auto",
    "api_url_override": "",
    "show_integration_hints": True,
}

CONFIG_REL = "config/agent_bridge.json"


def agent_bridge_config_path(base_dir: Path) -> Path:
    return base_dir / CONFIG_REL


def load_agent_bridge_settings(base_dir: Path) -> Dict[str, Any]:
    path = agent_bridge_config_path(base_dir)
    if not path.is_file():
        return dict(DEFAULT_AGENT_BRIDGE)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_AGENT_BRIDGE)
    if not isinstance(data, dict):
        return dict(DEFAULT_AGENT_BRIDGE)
    merged = dict(DEFAULT_AGENT_BRIDGE)
    merged.update({k: v for k, v in data.items() if k in DEFAULT_AGENT_BRIDGE})
    return merged


def save_agent_bridge_settings(base_dir: Path, patch: Dict[str, Any]) -> Dict[str, Any]:
    current = load_agent_bridge_settings(base_dir)
    for key in DEFAULT_AGENT_BRIDGE:
        if key in patch:
            current[key] = patch[key]
    path = agent_bridge_config_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return current