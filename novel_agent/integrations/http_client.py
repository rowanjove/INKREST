"""HTTP client for a running Novel Agent backend (optional for agents)."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def api_base_url() -> str:
    return os.environ.get("NOVEL_AGENT_API_URL", DEFAULT_BASE_URL).rstrip("/")


def api_headers() -> Dict[str, str]:
    token = os.environ.get("NOVEL_AGENT_ACCESS_TOKEN", "").strip()
    if token:
        return {"X-Novel-Agent-Token": token}
    return {}


def api_get(
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    url = urljoin(api_base_url() + "/", path.lstrip("/"))
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(url, params=params or {}, headers=api_headers())
        resp.raise_for_status()
        return resp.json()


def api_post(
    path: str,
    body: Optional[Dict[str, Any]] = None,
    *,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    url = urljoin(api_base_url() + "/", path.lstrip("/"))
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=body or {}, headers=api_headers())
        resp.raise_for_status()
        return resp.json()


def fetch_health() -> Dict[str, Any]:
    return api_get("/api/health")


def fetch_runtime_logs(since_id: int = 0, limit: int = 100) -> Dict[str, Any]:
    return api_get("/api/runtime-logs", params={"since_id": since_id, "limit": limit})


def fetch_agent_snapshot_http() -> Dict[str, Any]:
    return api_get("/api/agent/snapshot")


def fetch_tasks() -> Any:
    return api_get("/api/chapters/tasks")