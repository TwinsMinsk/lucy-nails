import os

# До импорта приложения — чтобы Settings и Prodamus линки в тестах были валидны
os.environ.setdefault("PRODAMUS_URL", "https://test.payform.example/")
os.environ.setdefault("PRODAMUS_SECRET_KEY", "test-prodamus-hmac-secret-key-for-ci")

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app

# Импортируем все модели, чтобы они зарегистрировались в Base
from app.models import *  # noqa

# Формируем URL для тестовой БД
# Заменяем имя БД на test_nails_course
DB_URL_STR = settings.DATABASE_URL
if "/nails_course" in DB_URL_STR:
    TEST_DATABASE_URL = DB_URL_STR.replace("/nails_course", "/test_nails_course")
else:
    TEST_DATABASE_URL = f"{DB_URL_STR}_test"

engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

# Prodamus webhook and guest/authenticated checkout open a session via
# async_session_maker() directly (they bypass the get_db dependency), so the
# dependency override in the `client` fixture cannot redirect them. Point their
# session factory at the test database as well.
import app.api.payments as _payments_module  # noqa: E402

_payments_module.async_session_maker = TestingSessionLocal


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    """
    Создаем таблицы перед тестами и удаляем после.
    ВАЖНО: База данных TEST_DATABASE_URL должна существовать!
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function", autouse=True)
def _reset_rate_limiter():
    """Clear slowapi's in-memory counters before each test.

    The limiter is a session-lived module object, so without a reset the
    per-test request volume accumulates and later tests get rate-limited
    (429 on /login → missing access_token).
    """
    from app.core.rate_limit import limiter

    limiter.reset()
    yield


@pytest_asyncio.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    Фикстура для сессии БД.
    Очищает таблицы перед каждым тестом.
    """
    async with TestingSessionLocal() as session:
        # Порядок удаления важен из-за FK
        await session.execute(
            text(
                "TRUNCATE TABLE progress, purchases, certificates, "
                "lessons, modules, courses, users RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()

        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Фикстура для HTTP клиента.
    Переопределяет зависимость get_db.
    """
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
