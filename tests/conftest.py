import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import close_database, init_database
from app.main import app
from app.services.cache import cache


@pytest.fixture(autouse=True)
def _test_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_API_KEY", "test-secret-key-for-testing-only-32chars!")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("VERIFY_FROM_EMAIL", "verify@test.com")
    monkeypatch.setenv("VERIFY_EHLO_HOSTNAME", "verify.test.com")
    from app import config as config_module
    config_module.settings = config_module.Settings()
    cache.clear()
    yield


@pytest_asyncio.fixture
async def client():
    await init_database()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await close_database()


@pytest.fixture
def auth_headers():
    return {"X-API-Key": "test-secret-key-for-testing-only-32chars!"}


@pytest.fixture
def invalid_auth_headers():
    return {"X-API-Key": "wrong-key"}
