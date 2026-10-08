import asyncio
import threading
from time import monotonic
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import payments
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import UserLogin, UserRegister
from app.services import auth_service
from app.services.auth_service import AuthService


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["login", "register", "change", "set", "guest"])
async def test_concurrent_password_work_keeps_event_loop_responsive(
    monkeypatch, operation
):
    password = "password123"
    original_hash = get_password_hash(password)
    loop_thread = threading.get_ident()
    worker_threads = set()
    hashes_to_check = []

    def hash_in_worker(value):
        worker_threads.add(threading.get_ident())
        assert threading.get_ident() != loop_thread
        return get_password_hash(value)

    def verify_in_worker(value, hashed):
        worker_threads.add(threading.get_ident())
        assert threading.get_ident() != loop_thread
        return verify_password(value, hashed)

    monkeypatch.setattr(auth_service, "get_password_hash", hash_in_worker)
    monkeypatch.setattr(auth_service, "verify_password", verify_in_worker)
    monkeypatch.setattr(payments, "get_password_hash", hash_in_worker)

    async def run_operation(index):
        db = AsyncMock(spec=AsyncSession)
        user = User(
            id=uuid4(),
            email=f"worker{index}@example.com",
            password_hash=original_hash,
            token_version=0,
        )
        result = Mock()
        result.scalar_one_or_none.return_value = user if operation in {"login", "change"} else None
        result.scalars.return_value.first.return_value = None
        db.execute.return_value = result
        if operation == "login":
            assert (
                await AuthService.authenticate_user(
                    db, UserLogin(email=user.email, password=password)
                )
                is user
            )
        elif operation == "register":
            created = await AuthService.register_user(
                db,
                UserRegister(
                    email=user.email,
                    password=password,
                    password_confirm=password,
                    offer_accepted=True,
                    personal_data_consent=True,
                ),
            )
            hashes_to_check.append((password, created.password_hash))
        elif operation == "change":
            assert await AuthService.change_password(
                db, user, password, "new-password123"
            )
            assert user.token_version == 1
            hashes_to_check.append(("new-password123", user.password_hash))
        elif operation == "set":
            await AuthService.set_password(db, user, "new-password123")
            assert user.token_version == 1
            hashes_to_check.append(("new-password123", user.password_hash))
        else:
            created, is_new = await payments._get_or_create_user(db, user.email, None)
            assert is_new and created.password_hash.startswith("$2b$12$")

    ticks = []
    finished = asyncio.Event()

    async def heartbeat():
        while not finished.is_set():
            ticks.append(monotonic())
            await asyncio.sleep(0.01)
        ticks.append(monotonic())

    monitor = asyncio.create_task(heartbeat())
    try:
        await asyncio.gather(*(run_operation(index) for index in range(4)))
    finally:
        finished.set()
        await monitor
    assert worker_threads
    assert len(ticks) >= 3
    assert max(b - a for a, b in zip(ticks, ticks[1:])) < 0.25

    for plain, hashed in hashes_to_check:
        assert verify_password(plain, hashed)
