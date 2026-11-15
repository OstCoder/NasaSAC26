"""LunaNav API entry point.

Run:  uvicorn app.main:app --reload --port 8000   (from backend/)
Docs: http://localhost:8000/docs
"""

from __future__ import annotations

import hashlib
import os
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response

from app.api.routes import router
from app.core.errors import LunaNavError
from app.core.settings import get_settings

settings = get_settings()

app = FastAPI(
    title="LunaNav API",
    version=settings.raw["app"]["version"],
    description="Lunar landing-site Sun/Earth visibility analysis. "
    "Every result carries a provenance block; Demo Mode data is synthetic.",
)


@app.get("/health", include_in_schema=True)
def health():
    """Top-level liveness probe (Render healthCheckPath). Mirrors /api/health."""
    return {"status": "ok"}

# Middleware (registration order: first = innermost, last = outermost).
# Pure ASGI (not BaseHTTPMiddleware) so we can buffer the response body for
# ETag hashing without confusing GZipMiddleware's size threshold.
_ETAG_PATHS = {"/api/config", "/api/sites", "/api/craters",
               "/api/psrs", "/api/science/psrs"}


class _ETagMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or scope.get("method") != "GET":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path not in _ETAG_PATHS:
            await self.app(scope, receive, send)
            return

        messages: list[dict] = []

        async def send_wrapper(message):
            messages.append(message)

        await self.app(scope, receive, send_wrapper)

        start_msg = next((m for m in messages if m["type"] == "http.response.start"), None)
        if start_msg is None:
            for m in messages:
                await send(m)
            return

        body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
        status = start_msg["status"]
        headers = [(k, v) for (k, v) in start_msg.get("headers", [])]

        if status >= 400 or not body:
            await send(start_msg)
            for m in messages:
                if m["type"] == "http.response.body":
                    await send(m)
            return

        etag = 'W/"' + hashlib.md5(body).hexdigest() + '"'
        inm = ""
        for k, v in scope.get("headers", []):
            if k.decode("latin-1").lower() == "if-none-match":
                inm = v.decode("latin-1").strip()
                break
        cache_control = "public, max-age=300"
        for k, v in headers:
            if k.decode("latin-1").lower() == "cache-control":
                cache_control = v.decode("latin-1")
                break

        if inm == etag:
            await send({"type": "http.response.start", "status": 304,
                        "headers": [(b"etag", etag.encode("latin-1")),
                                    (b"cache-control", cache_control.encode("latin-1"))]})
            await send({"type": "http.response.body", "body": b"", "more_body": False})
            return

        if not any(k.decode("latin-1").lower() == "etag" for k, _ in headers):
            headers.append((b"etag", etag.encode("latin-1")))
        if not any(k.decode("latin-1").lower() == "cache-control" for k, _ in headers):
            headers.append((b"cache-control", cache_control.encode("latin-1")))
        start_msg["headers"] = headers
        await send(start_msg)
        for m in messages:
            if m["type"] == "http.response.body":
                await send(m)


class _TimingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        start = time.perf_counter()

        async def send_wrapper(message):
            if message.get("type") == "http.response.start":
                headers = list(message.get("headers", []))
                if not any(k.decode("latin-1").lower() == "x-response-time" for k, _ in headers):
                    headers.append((b"x-response-time",
                                    f"{(time.perf_counter() - start) * 1000:.1f}ms".encode("latin-1")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


app.add_middleware(_ETagMiddleware)
app.add_middleware(_TimingMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("LUNANAV_CORS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
    max_age=86400,
    expose_headers=["X-Response-Time", "X-LunaNav-Imagery", "ETag"],
)


@app.exception_handler(LunaNavError)
async def lunanav_error(_: Request, exc: LunaNavError):
    return JSONResponse(
        status_code=exc.http_status,
        content={"code": exc.code, "message": exc.message, "details": exc.details},
    )


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(x) for x in first.get("loc", []) if x != "body")
    return JSONResponse(
        status_code=422,
        content={
            "code": "INVALID_INPUT",
            "message": f"{loc}: {first.get('msg', 'invalid request')}" if loc else first.get("msg", "invalid"),
            "details": {"errors": [{"loc": e.get("loc"), "msg": e.get("msg")} for e in exc.errors()]},
        },
    )


app.include_router(router)
