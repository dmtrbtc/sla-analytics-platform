"""Shared fixtures and helpers for all tests."""

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


# ---------------------------------------------------------------------------
# API client fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(base_url=BASE_URL) as ac:
        yield ac
