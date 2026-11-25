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
import app.services.payment_event_service as _payment_event_module  # noqa: E402
import app.bot.services.auth as _bot_auth_module  # noqa: E402

_payments_module.async_session_maker = TestingSessionLocal
_payment_event_module.async_session_maker = TestingSessionLocal
_bot_auth_module.async_session_maker = TestingSessionLocal


async def mfa_login(
    client: AsyncClient,
    db: AsyncSession,
    email: str,
    password: str,
):
    """Log in an account that needs MFA (owner/admin, legacy admin).

    Enrols an enabled TOTP credential when the account has none and signs in
    with a fresh single-use backup code, so repeated logins in one test never
    hit TOTP replay protection.
    """
    import secrets
    from datetime import datetime

    from sqlalchemy import func, select

    from app.models.user import User
    from app.services.mfa_service import MfaService, _backup_hash

    user = await db.scalar(select(User).where(func.lower(User.email) == email.lower()))
    assert user is not None, email
    credential = await MfaService.get_credential(db, user.id)
    if credential is None or credential.enabled_at is None:
        credential, _, _ = await MfaService.get_or_create_setup(db, user)
        credential.enabled_at = datetime.utcnow()
    code = secrets.token_hex(5).upper()
    credential.backup_code_hashes = [*(credential.backup_code_hashes or []), _backup_hash(code)]
    await db.commit()
    return await client.post(
        "/api/auth/login",
        json={"email": email, "password": password, "mfa_code": code},
    )


async def mfa_headers(client: AsyncClient, db: AsyncSession, user, password: str | None = None) -> dict[str, str]:
    """Bearer headers of a session obtained through the real login with MFA.

    Privileged accounts are served only from such a session. Without a known
    password the helper sets one, so fixtures may keep placeholder hashes.
    """
    from app.core.security import get_password_hash

    if password is None:
        password = "test-mfa-login-password"
        user.password_hash = get_password_hash(password)
        await db.commit()
    response = await mfa_login(client, db, user.email, password)
    assert response.status_code == 200, response.text
    client.cookies.clear()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


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
                "TRUNCATE TABLE ad_comments, ad_calendar_entries, ad_tasks, ad_files, ad_materials, ad_campaigns, "
                "helpdesk_messages, helpdesk_threads, telegram_updates, "
                "runtime_settings, telegram_link_tokens, student_tag_assignments, student_tags, student_notes, "
                "auth_sessions, mfa_credentials, audit_logs, "
                "user_role_assignments, role_permissions, permissions, roles, "
                "analytics_events, delivery_attempts, outbox_messages, refund_requests, payment_events, entitlements, orders, "
                "progress, purchases, certificates, lessons, modules, "
                "courses, users RESTART IDENTITY CASCADE"
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
