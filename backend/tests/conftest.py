import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.settings import get_settings
from app.main import app


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
