"""Hız sınırlama ve güvenlik başlıkları."""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
GIRIS_LIMITI = "5/minute"
TARAMA_TETIKLE_LIMITI = "10/minute"


class GuvenlikBasliklariMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response
