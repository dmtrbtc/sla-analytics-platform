"""Root test configuration.

Pure unit tests live in tests/unit/ — no external dependencies.
Integration/API tests (all others) require running services.
"""
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.helpers import (
    admin_token,
    cleanup_imports,
    cleanup_users,
    create_import_session,
    create_team,
    create_user,
)

BASE_URL = "http://localhost:8000"

_UNIT_DIR = Path(__file__).parent / "unit"

# Register SQLite compiles for PostgreSQL types — needed by some tests
import uuid as uuid_mod
import sqlite3
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.ext.compiler import compiles

compiles(UUID, "sqlite")(lambda t, c, **k: "TEXT")
compiles(JSONB, "sqlite")(lambda t, c, **k: "TEXT")
compiles(INET, "sqlite")(lambda t, c, **k: "TEXT")
sqlite3.register_adapter(uuid_mod.UUID, lambda u: str(u))


def pytest_collection_modifyitems(session, config, items):
    for item in items:
        item_path = Path(item.fspath) if hasattr(item, "fspath") else item.path
        if not str(item_path.resolve()).startswith(str(_UNIT_DIR.resolve())):
            item.add_marker(pytest.mark.integration)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(base_url=BASE_URL) as ac:
        yield ac
