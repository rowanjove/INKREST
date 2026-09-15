"""Network and outbound endpoint security utilities."""

from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse

ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV = "NOVEL_AGENT_ALLOW_PRIVATE_MODEL_ENDPOINTS"


def is_dev_model_host(host: str) -> bool:
    """Hosts used by unit tests and local mocks (skip live DNS guard)."""
    normalized = (host or "").strip().lower()
    if not normalized:
        return False
    if normalized in ("test", "testserver", "invalid", "localhost"):
        return True
    return normalized.endswith((".test", ".invalid", ".localhost", ".example"))


def is_loopback_host(host: str) -> bool:
    """True for loopback Host names or IP strings."""
    normalized = host.strip().lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _allows_private_model_endpoints() -> bool:
    return os.environ.get(ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV, "").lower() in ("1", "true", "yes")


def validate_outbound_model_base_url(raw_url: str) -> str:
    """Reject model endpoints that can target local or private networks."""
    url = str(raw_url or "").strip()
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        raise ValueError("Model endpoint host is required")
    try:
        addr_infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        if is_dev_model_host(host):
            return url.rstrip("/")
        raise ValueError(f"Model endpoint host cannot be resolved: {host}") from exc
    resolved_ips = [ipaddress.ip_address(info[4][0]) for info in addr_infos]
    is_loopback = bool(resolved_ips) and all(ip.is_loopback for ip in resolved_ips)
    for ip in resolved_ips:
        if ip.is_loopback:
            continue
        if ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            if not _allows_private_model_endpoints():
                raise ValueError("Model endpoint cannot target private or local networks")
    if parsed.scheme != "https" and not is_loopback:
        if not _allows_private_model_endpoints():
            raise ValueError("Model endpoint must use https")
    return url.rstrip("/")
