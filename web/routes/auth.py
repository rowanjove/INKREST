"""Loopback-only access token bootstrap for local clients."""

from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from web.security import (
    ACCESS_TOKEN_ENV,
    ACCESS_TOKEN_HEADER,
    bootstrap_loopback_access_token,
    is_loopback_client,
    is_loopback_host,
    BIND_HOST_ENV,
)

router = APIRouter(tags=["auth"])


@router.get("/api/auth/local-setup")
def local_access_setup(request: Request) -> Dict[str, Any]:
    """
    Return the loopback access token for same-machine clients (browser/Electron).

    Only available when the bind host is loopback and the client connects from loopback.
    """
    host = os.environ.get(BIND_HOST_ENV, "127.0.0.1").strip()
    if not is_loopback_host(host):
        raise HTTPException(403, "Local setup is only available on loopback bind hosts")
    if not is_loopback_client(request):
        raise HTTPException(403, "Local setup is only available to loopback clients")
    token = bootstrap_loopback_access_token()
    if not token:
        raise HTTPException(503, "Access token is not configured")
    return {
        "token": token,
        "header": ACCESS_TOKEN_HEADER,
        "env": ACCESS_TOKEN_ENV,
    }