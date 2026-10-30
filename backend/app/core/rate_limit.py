"""Лимиты запросов (slowapi) для production."""

import ipaddress

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

# Cloudflare edge ranges (https://www.cloudflare.com/ips/, checked 2026-10-30).
_CLOUDFLARE_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in (
        "173.245.48.0/20",
        "103.21.244.0/22",
        "103.22.200.0/22",
        "103.31.4.0/22",
        "141.101.64.0/18",
        "108.162.192.0/18",
        "190.93.240.0/20",
        "188.114.96.0/20",
        "197.234.240.0/22",
        "198.41.128.0/17",
        "162.158.0.0/15",
        "104.16.0.0/13",
        "104.24.0.0/14",
        "172.64.0.0/13",
        "131.0.72.0/22",
        "2400:cb00::/32",
        "2606:4700::/32",
        "2803:f800::/32",
        "2405:b500::/32",
        "2405:8100::/32",
        "2a06:98c0::/29",
        "2c0f:f248::/32",
    )
)


def _is_cloudflare(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in _CLOUDFLARE_NETWORKS)


def client_ip(request: Request) -> str:
    """Настоящий IP клиента за Railway (и опционально Cloudflare).

    X-Real-IP выставляет edge-прокси Railway — это адрес, который к нему
    подключился. CF-Connecting-IP учитывается, только если этот адрес — edge
    Cloudflare; иначе заголовок прислал сам клиент (прямой запрос на origin
    Railway) и ему верить нельзя. X-Forwarded-For не используется: его левую
    часть клиент задаёт сам. Без прокси (локально) — peer-адрес.
    """
    peer = (request.headers.get("X-Real-IP") or "").strip()
    if not peer:
        return get_remote_address(request)
    cf_ip = (request.headers.get("CF-Connecting-IP") or "").strip()
    if cf_ip and _is_cloudflare(peer):
        return cf_ip
    return peer


limiter = Limiter(key_func=client_ip, default_limits=["200/minute"])
