"""Лимиты запросов (slowapi) для production."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def client_ip(request: Request) -> str:
    """Настоящий IP клиента за Cloudflare/Railway.

    Предпочитает CF-Connecting-IP (истинный клиентский IP от Cloudflare), затем
    левый адрес из X-Forwarded-For, затем peer-адрес. Без этого за общим прокси
    все клиенты попадают в одно ведро лимитов. Домен закрыт TrustedHostMiddleware,
    поэтому напрямую (в обход Cloudflare) подделать заголовок нельзя.
    """
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=client_ip, default_limits=["200/minute"])
