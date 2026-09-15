"""Pin outbound HTTP(S) requests to already-validated IPs to block DNS rebinding."""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import httpx

from web.security import (
    _allows_private_model_endpoints,
    is_dev_model_host,
    is_loopback_host,
    validate_outbound_model_base_url,
)


@dataclass(frozen=True)
class PinnedEndpoint:
    original_url: str
    hostname: str
    pinned_ip: str
    port: int
    scheme: str


def _first_usable_ip(host: str, port: Optional[int]) -> ipaddress._BaseAddress:
    addr_infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addr_infos:
        raise ValueError(f"Host cannot be resolved: {host}")
    return ipaddress.ip_address(addr_infos[0][4][0])


def _reject_ip(ip: ipaddress._BaseAddress, *, require_public: bool, allow_loopback: bool) -> None:
    if ip.is_loopback:
        if not allow_loopback:
            raise ValueError("Endpoint cannot target private or local networks")
        return
    if ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_multicast:
        if require_public or not _allows_private_model_endpoints():
            raise ValueError("Endpoint cannot target private or local networks")


def pin_url(
    raw_url: str,
    *,
    require_public: bool,
    allow_loopback: bool,
    require_https: bool,
) -> Optional[PinnedEndpoint]:
    """Return a pinned endpoint, or None when the host is a local/dev skip."""
    url = str(raw_url or "").strip()
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        raise ValueError("Endpoint host is required")
    if is_dev_model_host(host) and not require_public:
        return None
    if is_loopback_host(host) and allow_loopback and not require_public:
        return None
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    ip = _first_usable_ip(host, port)
    _reject_ip(ip, require_public=require_public, allow_loopback=allow_loopback)
    if require_https and parsed.scheme != "https" and not ip.is_loopback:
        if not _allows_private_model_endpoints():
            raise ValueError("Endpoint must use https")
    return PinnedEndpoint(
        original_url=url,
        hostname=host,
        pinned_ip=str(ip),
        port=int(port),
        scheme=parsed.scheme or "https",
    )


def pin_model_base_url(raw_url: str) -> Optional[PinnedEndpoint]:
    validate_outbound_model_base_url(raw_url)
    return pin_url(
        raw_url,
        require_public=False,
        allow_loopback=True,
        require_https=True,
    )


def pin_public_image_url(raw_url: str) -> PinnedEndpoint:
    parsed = urlparse(str(raw_url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Image URL must use http or https")
    pinned = pin_url(
        raw_url,
        require_public=True,
        allow_loopback=False,
        require_https=False,
    )
    if pinned is None:
        raise ValueError("Image URL host cannot be used")
    return pinned


def _rewrite_url(url: httpx.URL, ip: str) -> httpx.URL:
    host = ip
    if ":" in ip and not ip.startswith("["):
        host = f"[{ip}]"
    return url.copy_with(host=host)


class PinnedIPTransport(httpx.HTTPTransport):
    def __init__(self, endpoint: PinnedEndpoint, **kwargs):
        super().__init__(**kwargs)
        self._endpoint = endpoint

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        headers = request.headers.copy()
        headers["host"] = (
            self._endpoint.hostname
            if (request.url.port in (None, 80, 443))
            else f"{self._endpoint.hostname}:{request.url.port}"
        )
        extensions = dict(request.extensions)
        extensions["sni_hostname"] = self._endpoint.hostname
        pinned = httpx.Request(
            request.method,
            _rewrite_url(request.url, self._endpoint.pinned_ip),
            headers=headers,
            content=request.content,
            extensions=extensions,
        )
        return super().handle_request(pinned)


class PinnedAsyncIPTransport(httpx.AsyncHTTPTransport):
    def __init__(self, endpoint: PinnedEndpoint, **kwargs):
        super().__init__(**kwargs)
        self._endpoint = endpoint

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        headers = request.headers.copy()
        headers["host"] = (
            self._endpoint.hostname
            if (request.url.port in (None, 80, 443))
            else f"{self._endpoint.hostname}:{request.url.port}"
        )
        extensions = dict(request.extensions)
        extensions["sni_hostname"] = self._endpoint.hostname
        pinned = httpx.Request(
            request.method,
            _rewrite_url(request.url, self._endpoint.pinned_ip),
            headers=headers,
            content=request.content,
            extensions=extensions,
        )
        return await super().handle_async_request(pinned)


def model_httpx_transport(base_url: str, *, async_mode: bool = False):
    endpoint = pin_model_base_url(base_url)
    if endpoint is None:
        return None
    if async_mode:
        return PinnedAsyncIPTransport(endpoint)
    return PinnedIPTransport(endpoint)


def public_image_httpx_transport(url: str) -> PinnedIPTransport:
    return PinnedIPTransport(pin_public_image_url(url))
