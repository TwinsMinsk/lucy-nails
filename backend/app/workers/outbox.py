"""Standalone durable-notification worker."""

import asyncio
import logging

from app.core.config import settings
from app.core.database import async_session_maker
from app.services.outbox_service import process_outbox_batch


logger = logging.getLogger(__name__)


async def run_forever() -> None:
    while True:
        try:
            async with async_session_maker() as db:
                processed = await process_outbox_batch(db)
        except Exception:
            logger.exception("Outbox worker iteration failed")
            processed = 0
        if processed == 0:
            await asyncio.sleep(settings.OUTBOX_POLL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_forever())
