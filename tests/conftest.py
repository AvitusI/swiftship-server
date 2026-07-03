from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.enums import UserRole
from app.models.user import User

# A single shared in-memory SQLite connection for the whole test session.
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, expire_on_commit=False, autoflush=False
)


@pytest_asyncio.fixture(autouse=True)
async def _setup_db() -> AsyncGenerator[None, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _make_user(email: str, password: str, role: UserRole) -> User:
    async with TestSessionLocal() as session:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=f"{role.value.title()} User",
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _login(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient) -> str:
    await _make_user("admin@test.io", "admin12345", UserRole.ADMIN)
    return await _login(client, "admin@test.io", "admin12345")


@pytest_asyncio.fixture
async def dispatcher_token(client: AsyncClient) -> str:
    await _make_user("dispatch@test.io", "dispatch12345", UserRole.DISPATCHER)
    return await _login(client, "dispatch@test.io", "dispatch12345")


@pytest_asyncio.fixture
async def driver(client: AsyncClient) -> dict:
    user = await _make_user("driver@test.io", "driver12345", UserRole.DRIVER)
    token = await _login(client, "driver@test.io", "driver12345")
    return {"id": user.id, "token": token}


@pytest_asyncio.fixture
async def customer(client: AsyncClient) -> dict:
    user = await _make_user("cust@test.io", "cust12345", UserRole.CUSTOMER)
    token = await _login(client, "cust@test.io", "cust12345")
    return {"id": user.id, "token": token}


# Re-export helper for tests.
auth = _auth
