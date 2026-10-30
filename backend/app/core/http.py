"""Minimal outbound HTTP for NASA/JPL services (stdlib only).

All network access goes through ``get_bytes`` so tests can replace it and so
there is one place to add proxies, retries or user-agent changes.
"""

from __future__ import annotations

import os
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass

USER_AGENT = "LunaNav/0.2 (NASA Space Apps 2026 prototype)"


@dataclass
class HttpResult:
    status: int
    body: bytes
    content_type: str = ""


class HttpError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def _context() -> ssl.SSLContext:
    # Respect a custom CA bundle (corporate proxies), otherwise system defaults.
    bundle = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    return ssl.create_default_context(cafile=bundle) if bundle else ssl.create_default_context()


def get_bytes(url: str, timeout: float) -> HttpResult:
    """GET a URL. Raises HttpError on network failure; returns non-2xx statuses as results."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_context()) as r:
            return HttpResult(r.status, r.read(), r.headers.get("Content-Type", ""))
    except urllib.error.HTTPError as e:
        return HttpResult(e.code, e.read() if e.fp else b"", e.headers.get("Content-Type", "") if e.headers else "")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        reason = getattr(e, "reason", e)
        raise HttpError(f"{type(e).__name__}: {reason}") from e
