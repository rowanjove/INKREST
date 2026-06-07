"""Security helpers for local and explicitly-enabled remote serving."""

from __future__ import annotations

import asyncio
import hmac
import ipaddress
import json
import os
import secrets
from pathlib import Path
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.websockets import WebSocket, WebSocketDisconnect

ACCESS_TOKEN_ENV = "NOVEL_AGENT_ACCESS_TOKEN"
ACCESS_TOKEN_HEADER = "X-Novel-Agent-Token"
BIND_HOST_ENV = "NOVEL_AGENT_HOST"
ALLOW_REMOTE_ENV = "NOVEL_AGENT_ALLOW_REMOTE"
DISABLE_LOCAL_TOKEN_ENV = "NOVEL_AGENT_DISABLE_LOCAL_TOKEN"
LOCAL_TOKEN_FILENAME = ".local_access_token"
PUBLIC_API_PATHS = frozenset({"/api/health", "/api/auth/local-setup"})


def _tokens_match(supplied: str, expected: str) -> bool:
    """Constant-time compare; avoids compare_digest length mismatch TypeError."""
    if not expected:
        return True
    if len(supplied) != len(expected):
        return False
    return hmac.compare_digest(supplied, expected)


def is_loopback_client(request: Request) -> bool:
    """True for loopback TCP clients and in-process ASGI test transports."""
    if request.client and request.client.host:
        host = request.client.host.strip().lower()
        if host in ("testclient", "testserver"):
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            pass
    return False


def _token_storage_dir(root_dir: Optional[Path] = None) -> Path:
    if root_dir is not None:
        return Path(root_dir)
    env_root = os.environ.get("NOVEL_AGENT_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    return Path.cwd()


def bootstrap_loopback_access_token(root_dir: Optional[Path] = None) -> Optional[str]:
    """
    Ensure a persistent access token exists for loopback-only serving.

    Skipped when DISABLE_LOCAL_TOKEN is set, a token is already configured,
    or the bind host is not loopback.
    """
    if os.environ.get(DISABLE_LOCAL_TOKEN_ENV, "").lower() in ("1", "true", "yes"):
        return None
    existing = os.environ.get(ACCESS_TOKEN_ENV, "").strip()
    if existing:
        return existing
    host = os.environ.get(BIND_HOST_ENV, "127.0.0.1").strip()
    if not is_loopback_host(host):
        return None

    base = _token_storage_dir(root_dir)
    token_path = base / "data" / LOCAL_TOKEN_FILENAME
    token_path.parent.mkdir(parents=True, exist_ok=True)
    if token_path.is_file():
        token = token_path.read_text(encoding="utf-8").strip()
    else:
        token = secrets.token_urlsafe(32)
        token_path.write_text(token, encoding="utf-8")
        try:
            os.chmod(token_path, 0o600)
        except OSError:
            pass
    os.environ[ACCESS_TOKEN_ENV] = token
    return token


def is_loopback_host(host: str) -> bool:
    normalized = host.strip().lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def require_remote_token(host: str, allow_remote: bool, token: str) -> None:
    if is_loopback_host(host):
        return
    if not allow_remote:
        raise ValueError("Non-loopback binding requires --allow-remote")
    if not token:
        raise ValueError("Remote serving requires NOVEL_AGENT_ACCESS_TOKEN")


def enforce_remote_auth_at_startup() -> None:
    """Fail fast when remote bind is configured without an access token."""
    host = os.environ.get(BIND_HOST_ENV, "127.0.0.1").strip()
    allow_remote = os.environ.get(ALLOW_REMOTE_ENV, "").lower() in ("1", "true", "yes")
    if is_loopback_host(host) or not allow_remote:
        return
    if not os.environ.get(ACCESS_TOKEN_ENV, "").strip():
        raise RuntimeError(
            "Non-loopback remote serving requires NOVEL_AGENT_ACCESS_TOKEN "
            "(set via `python main.py serve --allow-remote` or export the token)"
        )


class AccessTokenMiddleware(BaseHTTPMiddleware):
    """Require a token for API requests whenever remote access is configured."""

    async def dispatch(self, request: Request, call_next):
        expected = os.environ.get(ACCESS_TOKEN_ENV, "")
        if (
            expected
            and request.url.path.startswith("/api/")
            and request.url.path not in PUBLIC_API_PATHS
        ):
            supplied = request.headers.get(ACCESS_TOKEN_HEADER, "")
            if not _tokens_match(supplied, expected):
                return JSONResponse({"detail": "Invalid or missing access token"}, status_code=401)
        return await call_next(request)


def websocket_has_access_token(ws: WebSocket) -> bool:
    """Token via header only (never query string — avoids log/history leakage)."""
    expected = os.environ.get(ACCESS_TOKEN_ENV, "")
    if not expected:
        return True
    supplied = ws.headers.get(ACCESS_TOKEN_HEADER, "")
    return _tokens_match(supplied, expected)


async def authorize_websocket(ws: WebSocket) -> bool:
    """
    Accept WebSocket after auth.

    Browsers cannot set custom headers on WebSocket; clients may send
    ``{"type":"auth","token":"..."}`` as the first text frame after connect.
    """
    expected = os.environ.get(ACCESS_TOKEN_ENV, "").strip()
    if not expected:
        await ws.accept()
        return True
    if websocket_has_access_token(ws):
        await ws.accept()
        return True
    await ws.accept()
    try:
        raw = await asyncio.wait_for(ws.receive_text(), timeout=15.0)
        data = json.loads(raw)
        if data.get("type") == "auth" and _tokens_match(str(data.get("token") or ""), expected):
            return True
    except WebSocketDisconnect:
        return False
    except (asyncio.TimeoutError, json.JSONDecodeError, TypeError):
        pass
    await ws.close(code=1008, reason="Invalid or missing access token")
    return False
