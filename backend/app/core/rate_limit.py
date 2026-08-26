"""Shared request-rate limits with proxy-safe client identification."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import settings


def client_ip(request: Request) -> str:
    """Use only the peer address normalized by Uvicorn's trusted proxy list."""
    return get_remote_address(request)


limiter = Limiter(
    key_func=client_ip,
    default_limits=["200/minute"],
    storage_uri=settings.REDIS_URL or "memory://",
)
