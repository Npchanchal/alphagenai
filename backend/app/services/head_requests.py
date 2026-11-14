"""Answer HEAD on public read paths as GET without a body.

Crawlers, feed readers and link checkers send HEAD for the OG card, the changelog
feed and the public API. FastAPI registers GET only, so those requests got 405.
Only the public read prefixes below are served; a HEAD elsewhere still gets 405,
so it never meters a seat or counts against a guest limit.
"""

from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

PUBLIC_READ_PREFIXES = (
    "/health",
    "/openapi.json",
    "/api/meta",
    "/api/og/",
    "/api/public/",
    "/api/v1/",
)


def serves_head(path: str) -> bool:
    return any(path == p.rstrip("/") or path.startswith(p) for p in PUBLIC_READ_PREFIXES)


class HeadAsGetMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "HEAD" or not serves_head(scope["path"]):
            await self.app(scope, receive, send)
            return

        async def send_headers_only(message: Message) -> None:
            if message["type"] == "http.response.body":
                message = {**message, "body": b""}
            await send(message)

        await self.app({**scope, "method": "GET"}, receive, send_headers_only)
