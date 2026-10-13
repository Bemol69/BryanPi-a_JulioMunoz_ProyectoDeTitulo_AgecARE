"""Fixtures: BD SQLite en memoria + cliente HTTP + datos demo del seed."""
import asyncio
import os

os.environ["GENERAL_DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["GENERAL_JWT_SECRET"] = "secreto-de-test-con-largo-suficiente-123456"
os.environ["GENERAL_ADMIN_SYNC_KEY"] = "clave-de-test"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.database as database
from app import storage
from app import sync as sync_module
from app.database import Base
from app.main import app as fastapi_app

INTERNAL = {"X-Internal-Key": "clave-de-test"}


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool,
                              connect_args={"check_same_thread": False})
    database._engine = eng
    database._session_factory = async_sessionmaker(eng, expire_on_commit=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture(autouse=True)
def no_network(monkeypatch, tmp_path):
    """Sin llamadas reales a la Consola y con archivos subidos en una carpeta temporal."""
    async def fake_post(path, payload):
        return True
    async def fake_fetch(email):
        return []
    monkeypatch.setattr(sync_module, "_post_to_admin", fake_post)
    monkeypatch.setattr(sync_module, "fetch_admin_documents", fake_fetch)
    import app.routers.caregiver as caregiver_router
    monkeypatch.setattr(caregiver_router, "fetch_admin_documents", fake_fetch)
    monkeypatch.setattr(storage, "LOCAL_ROOT", tmp_path)


@pytest_asyncio.fixture
async def client(engine):
    """Cada prueba parte de los datos demo recién sembrados."""
    from scripts.seed import seed
    await seed()
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def login(client, email, password):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest_asyncio.fixture
async def family(client):
    return await login(client, "familia@demo.cl", "Familia123!")


@pytest_asyncio.fixture
async def maria(client):
    return await login(client, "maria@cuidado.cl", "Cuidado123!")


@pytest_asyncio.fixture
async def javiera(client):
    return await login(client, "javiera@cuidado.cl", "Cuidado123!")
