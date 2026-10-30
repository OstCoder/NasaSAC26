import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Tests must never touch the network or the real cache: point JPL services at a
# closed local port and the cache at a throwaway directory BEFORE importing the app.
os.environ["LUNANAV_HORIZONS_URL"] = "http://127.0.0.1:9/api/horizons.api"
os.environ["LUNANAV_TREK_URL"] = "http://127.0.0.1:9/tiles"
os.environ["LUNANAV_CACHE_DIR"] = tempfile.mkdtemp(prefix="lunanav-test-cache-")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.settings import get_settings  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture
def landing():
    return datetime(2027, 1, 15, 12, tzinfo=timezone.utc)


@pytest.fixture
def write_json():
    def _w(path: Path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj))
        return path
    return _w
