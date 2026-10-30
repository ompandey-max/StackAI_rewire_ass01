import logging
import time
from uuid import uuid4

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started_at = time.perf_counter()
        status_code = 500

        async def send_with_context(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                message = dict(message)
                message["headers"] = [
                    *message.get("headers", []),
                    (b"x-request-id", request_id.encode("ascii")),
                ]
            await send(message)

        try:
            await self.app(scope, receive, send_with_context)
        finally:
            latency_ms = (time.perf_counter() - started_at) * 1000
            logger.info(
                "request_complete request_id=%s method=%s path=%s "
                "status_code=%d latency_ms=%.2f",
                request_id,
                scope.get("method", ""),
                scope.get("path", ""),
                status_code,
                latency_ms,
            )


class RequestSizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = next(
            (
                value
                for name, value in scope.get("headers", [])
                if name.lower() == b"content-length"
            ),
            None,
        )
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                await JSONResponse(
                    status_code=400,
                    content={
                        "error": "invalid_content_length",
                        "field": None,
                        "detail": "Content-Length must be a valid integer.",
                    },
                )(scope, receive, send)
                return
            if declared_size > self.max_body_bytes:
                await self._payload_too_large(scope, receive, send)
                return

        body_messages: list[Message] = []
        total_size = 0
        while True:
            message = await receive()
            body_messages.append(message)
            if message["type"] == "http.request":
                total_size += len(message.get("body", b""))
                if total_size > self.max_body_bytes:
                    await self._payload_too_large(scope, receive, send)
                    return
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                break

        next_message = 0

        async def replay_receive() -> Message:
            nonlocal next_message
            if next_message < len(body_messages):
                message = body_messages[next_message]
                next_message += 1
                return message
            return await receive()

        await self.app(scope, replay_receive, send)

    async def _payload_too_large(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        await JSONResponse(
            status_code=413,
            content={
                "error": "payload_too_large",
                "field": None,
                "detail": "Request body exceeds the configured size limit.",
            },
        )(scope, receive, send)
