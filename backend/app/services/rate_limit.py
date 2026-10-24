"""In-process soft rate limits (Desk pricing + auth abuse controls)."""

from __future__ import annotations

import ipaddress
import os
import time
from collections import defaultdict, deque
from typing import Callable, Deque, Dict, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


def rate_limit_rpm() -> int:
    try:
        return max(30, int(os.environ.get("RATE_LIMIT_RPM", "300")))
    except ValueError:
        return 300


def auth_rate_limit_rpm() -> int:
    """Stricter limit for register / guest / reset (B2C abuse control)."""
    try:
        return max(5, int(os.environ.get("AUTH_RATE_LIMIT_RPM", "20")))
    except ValueError:
        return 20


def public_api_rpm() -> int:
    """Per-key limit on the public API (/api/v1) and MCP server."""
    try:
        return max(5, int(os.environ.get("PUBLIC_API_RPM", "60")))
    except ValueError:
        return 60


def public_api_keys() -> frozenset[str]:
    """Keys shipped in the browser bundle — shared by every visitor, so they are bucketed per IP."""
    extra = os.environ.get("PUBLIC_API_KEYS", "")
    return frozenset({"intellens-demo", *(k.strip() for k in extra.split(",") if k.strip())})


def _is_internal(host: str) -> bool:
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    return addr.is_loopback or addr.is_private


def client_ip(request: Request) -> str:
    """Visitor IP. X-Real-IP is honoured only from our own reverse proxy (loopback / private peer)."""
    peer = request.client.host if request.client else "unknown"
    if _is_internal(peer):
        real = (request.headers.get("x-real-ip") or "").strip()
        if real:
            return real
    return peer


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window RPM by API key or client IP. Skips /health."""

    def __init__(self, app, rpm: Optional[int] = None, auth_rpm: Optional[int] = None):
        super().__init__(app)
        self.rpm = rpm or rate_limit_rpm()
        self.auth_rpm = auth_rpm or auth_rate_limit_rpm()
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def _key(self, request: Request) -> str:
        api_key = request.headers.get("x-api-key")
        bearer = (request.headers.get("authorization") or "").removeprefix("Bearer ").strip()
        if not api_key and bearer.startswith("ca_live_"):
            api_key = bearer
        if api_key and api_key not in public_api_keys():
            return f"key:{api_key}"
        return f"ip:{client_ip(request)}"

    def _limit_for(self, path: str, method: str = "GET") -> Tuple[int, str]:
        if path.startswith("/api/v1/analyst/") or path == "/api/mcp":
            return public_api_rpm(), "public_api"
        if path == "/api/pilot-request":
            return self.auth_rpm, "auth"
        # Only credential / account-creation writes are abuse-prone; session reads such as
        # /api/auth/me run on every page load and must not share the strict bucket.
        if path.startswith("/api/auth/") and method == "POST" and path != "/api/auth/logout":
            return self.auth_rpm, "auth"
        return self.rpm, "api"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if path in ("/health", "/api/meta") or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)

        limit, bucket = self._limit_for(path, request.method)
        key = f"{bucket}:{self._key(request)}"
        now = time.monotonic()
        window = self._hits[key]
        while window and now - window[0] > 60.0:
            window.popleft()
        if len(window) >= limit:
            retry_after = max(1, int(60.0 - (now - window[0])) + 1)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "limit_rpm": limit,
                    "bucket": bucket,
                    "retry_after_sec": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )
        window.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - len(window)))
        response.headers["X-RateLimit-Bucket"] = bucket
        return response
