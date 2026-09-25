"""Access to the small allow-list of mutable operational settings."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.runtime_setting import RuntimeSetting


class RuntimeSettingsService:
    CHECKOUT_KEY = "checkout_enabled"

    @staticmethod
    async def checkout_enabled(
        db: AsyncSession, *, default_enabled: bool | None = None
    ) -> bool:
        row = await db.get(RuntimeSetting, RuntimeSettingsService.CHECKOUT_KEY)
        if row is None:
            return settings.CHECKOUT_ENABLED if default_enabled is None else default_enabled
        return bool(row.value.get("enabled", False))

    @staticmethod
    async def set_checkout_enabled(
        db: AsyncSession, *, enabled: bool, updated_by_id
    ) -> RuntimeSetting:
        row = await db.get(RuntimeSetting, RuntimeSettingsService.CHECKOUT_KEY)
        if row is None:
            row = RuntimeSetting(
                key=RuntimeSettingsService.CHECKOUT_KEY,
                value={"enabled": enabled},
                updated_by_id=updated_by_id,
            )
            db.add(row)
        else:
            row.value = {"enabled": enabled}
            row.updated_by_id = updated_by_id
        return row
