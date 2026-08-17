"""Global request limits and API response hardening."""

import asyncio

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.utils.logger import logger

# Response hardening headers, injected on every response including the error
# responses this middleware generates directly (413/504), which never reach the
# app's normal response path.
SECURITY_HEADERS: list[tuple[bytes, bytes]] = [
    (b"cache-control", b"no-store"),
    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
    (b"referrer-policy", b"no-referrer"),
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
]


class RequestProtectionMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        max_body_bytes: int,
        timeout_seconds: float,
        enable_hsts: bool,
    ) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.timeout_seconds = timeout_seconds
        self.enable_hsts = enable_hsts

    def _error_headers(self) -> dict[str, str]:
        """Security headers for responses this middleware emits directly."""
        headers = {key.decode(): value.decode() for key, value in SECURITY_HEADERS}
        if self.enable_hsts:
            headers["strict-transport-security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return headers

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        body_parts: list[bytes] = []
        total = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body = message.get("body", b"")
            total += len(body)
            if total > self.max_body_bytes:
                await JSONResponse(
                    {"detail": "Request body too large"},
                    status_code=413,
                    headers=self._error_headers(),
                )(scope, receive, send)
                return
            body_parts.append(body)
            if not message.get("more_body", False):
                break

        replayed = False

        async def replay_receive() -> Message:
            nonlocal replayed
            if replayed:
                return await receive()
            replayed = True
            return {
                "type": "http.request",
                "body": b"".join(body_parts),
                "more_body": False,
            }

        started = False

        async def protected_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                headers = list(message.get("headers", []))
                existing = {key.lower() for key, _value in headers}
                headers.extend(
                    (key, value)
                    for key, value in SECURITY_HEADERS
                    if key not in existing
                )
                if self.enable_hsts:
                    headers.append(
                        (b"strict-transport-security", b"max-age=31536000; includeSubDomains")
                    )
                message["headers"] = headers
            await send(message)

        try:
            await asyncio.wait_for(
                self.app(scope, replay_receive, protected_send),
                timeout=self.timeout_seconds,
            )
        except TimeoutError:
            logger.warning("Request deadline exceeded: %s", scope.get("path", ""))
            if not started:
                await JSONResponse(
                    {"detail": "Request timed out"}, status_code=504
                )(scope, replay_receive, protected_send)
