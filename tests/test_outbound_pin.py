import socket
from unittest.mock import patch

import pytest

from web.outbound import pin_model_base_url, pin_public_image_url, pin_url


def _addr(ip: str):
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    return (family, socket.SOCK_STREAM, 6, "", (ip, 443))


def test_pin_model_url_uses_resolved_public_ip():
    with patch("web.outbound.socket.getaddrinfo", return_value=[_addr("8.8.8.8")]):
        pinned = pin_model_base_url("https://api.example.com/v1")
    assert pinned is not None
    assert pinned.pinned_ip == "8.8.8.8"
    assert pinned.hostname == "api.example.com"


def test_pin_model_url_skips_loopback_hosts():
    assert pin_model_base_url("http://127.0.0.1:11434/v1") is None
    assert pin_model_base_url("http://localhost:1234/v1") is None


def test_pin_public_image_rejects_loopback():
    with pytest.raises(ValueError):
        pin_public_image_url("http://127.0.0.1/cover.png")


def test_pin_url_rejects_private_lan_for_public_images():
    with patch("web.outbound.socket.getaddrinfo", return_value=[_addr("192.168.1.20")]):
        with pytest.raises(ValueError, match="private or local"):
            pin_url(
                "https://cdn.example.com/a.png",
                require_public=True,
                allow_loopback=False,
                require_https=False,
            )


def test_rewrite_url_ipv6_brackets():
    import httpx
    from web.outbound import _rewrite_url

    url = httpx.URL("https://api.example.com:8443/v1/chat")
    rewritten_ipv6 = _rewrite_url(url, "2606:4700:4700::1111")
    assert str(rewritten_ipv6) == "https://[2606:4700:4700::1111]:8443/v1/chat"

    rewritten_ipv4 = _rewrite_url(url, "1.1.1.1")
    assert str(rewritten_ipv4) == "https://1.1.1.1:8443/v1/chat"

