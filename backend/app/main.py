"""LunaNav API entry point.

Run:  uvicorn app.main:app --reload --port 8000   (from backend/)
Docs: http://localhost:8000/docs
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

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

# The PSR catalogue (~2 MB) and the crater gazetteer (~140 kB) are JSON that
# gzip to a fraction of their size. Threshold keeps small payloads uncompressed,
# where framing costs more than it saves.
app.add_middleware(GZipMiddleware, minimum_size=1024)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("LUNANAV_CORS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
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
