"""Standalone durable-notification worker."""

import asyncio
import logging

from app.core.config import settings
from app.core.database import async_session_maker
from app.services.lifecycle_service import LifecycleService
from app.services.outbox_service import process_outbox_batch


logger = logging.getLogger(__name__)


async def run_iteration(last_lifecycle_scan: float) -> tuple[int, float]:
    """Run scheduling and delivery independently so one cannot starve the other."""
    monotonic_now = asyncio.get_running_loop().time()
    next_lifecycle_scan = last_lifecycle_scan
    if monotonic_now - last_lifecycle_scan >= settings.LIFECYCLE_SCAN_SECONDS:
        # Advance the clock before the attempt so a broken integration cannot
        # hammer the database on every outbox poll.
        next_lifecycle_scan = monotonic_now
        try:
            async with async_session_maker() as db:
                scheduled = await LifecycleService.schedule(db)
                await db.commit()
                if scheduled:
                    logger.info("Scheduled %s lifecycle notifications", scheduled)
        except Exception:
            logger.exception("Lifecycle scheduling failed")

    try:
        # Use a fresh transaction even after a failed lifecycle scan. Existing
        # payment/access messages must remain deliverable during that outage.
        async with async_session_maker() as db:
            processed = await process_outbox_batch(db)
    except Exception:
        logger.exception("Outbox delivery iteration failed")
        processed = 0
    return processed, next_lifecycle_scan


async def run_forever() -> None:
    last_lifecycle_scan = 0.0
    while True:
        processed, last_lifecycle_scan = await run_iteration(last_lifecycle_scan)
        if processed == 0:
            await asyncio.sleep(settings.OUTBOX_POLL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_forever())
