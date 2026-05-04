import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.config import settings
from app.core.database import Base, get_db
# Импортируем все модели, чтобы они зарегистрировались в Base
from app.models import *  # noqa

# Формируем URL для тестовой БД
# Заменяем имя БД на test_nails_course
DB_URL_STR = settings.DATABASE_URL
if "/nails_course" in DB_URL_STR:
    TEST_DATABASE_URL = DB_URL_STR.replace("/nails_course", "/test_nails_course")
else:
    TEST_DATABASE_URL = f"{DB_URL_STR}_test"

# Синхронный движок для создания БД (psycopg2) нужен, но 
# мы можем попробовать создать таблицы в существующей БД, 
# либо использовать setup/teardown на уровне сессии.
# Для простоты и скорости локальной разработки:
# Будем использовать отдельную БД, но создавать её нужно вручную или скриптом.
# Однако, чтобы автоматизировать, добавим фикстуру scope='session'.

# WARN: Для этого теста предполагается, что БД test_nails_course уже создана или пользователь имеет права.
# Попробуем создать таблицы. Если БД нет - упадет.
# В идеале нужно подключаться к 'postgres' и делать CREATE DATABASE.

engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

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

@pytest_asyncio.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    Фикстура для сессии БД.
    Очищает таблицы перед каждым тестом.
    """
    async with TestingSessionLocal() as session:
        # Очистка данных
        from sqlalchemy import text
        # Порядок удаления важен из-за FK
        await session.execute(text("TRUNCATE TABLE progress, purchases, certificates, lessons, modules, courses, users RESTART IDENTITY CASCADE"))
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
