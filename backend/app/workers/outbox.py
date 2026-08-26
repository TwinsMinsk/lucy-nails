"""Standalone durable-notification worker."""

import asyncio
import logging

from app.core.config import settings
from app.core.database import async_session_maker
from app.services.lifecycle_service import LifecycleService
from app.services.outbox_service import process_outbox_batch


logger = logging.getLogger(__name__)


async def run_forever() -> None:
    last_lifecycle_scan = 0.0
    while True:
        try:
            async with async_session_maker() as db:
                monotonic_now = asyncio.get_running_loop().time()
                if monotonic_now - last_lifecycle_scan >= settings.LIFECYCLE_SCAN_SECONDS:
                    scheduled = await LifecycleService.schedule(db)
                    await db.commit()
                    if scheduled:
                        logger.info("Scheduled %s lifecycle notifications", scheduled)
                    last_lifecycle_scan = monotonic_now
                processed = await process_outbox_batch(db)
        except Exception:
            logger.exception("Outbox worker iteration failed")
            processed = 0
        if processed == 0:
            await asyncio.sleep(settings.OUTBOX_POLL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_forever())
