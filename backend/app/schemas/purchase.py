"""
Pydantic схемы для покупок.
"""

from datetime import datetime
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field


class TariffType(str, Enum):
    SELF = "self"
    SUPPORT = "support"


class PurchaseCreate(BaseModel):
    """Схема создания заказа."""

    course_id: UUID = Field(..., description="UUID курса")
    tariff: TariffType = Field(..., description="Тариф (self/support)")


class PaymentStartResponse(BaseModel):
    """Ответ при старте оплаты (редирект на Prodamus)."""

    payment_url: str = Field(..., description="URL платёжной формы Prodamus")
    course_id: UUID = Field(..., description="UUID курса")
    tariff: str = Field(..., description="Тариф")


class PurchaseResponse(BaseModel):
    """Схема ответа с данными покупки."""
    
    id: UUID = Field(..., description="UUID покупки")
    course_id: UUID = Field(..., description="UUID курса")
    tariff: str = Field(..., description="Тариф")
    amount_kopecks: int = Field(..., description="Сумма в копейках")
    payment_status: str = Field(..., description="Статус оплаты (pending/success/failed)")
    expires_at: datetime = Field(..., description="Дата истечения доступа")
    created_at: datetime = Field(..., description="Дата создания заказа")
    
    # Опционально можно добавить URL оплаты в будущем
    payment_url: str | None = Field(None, description="Ссылка на оплату")

    class Config:
        from_attributes = True
        use_enum_values = True


class MyCourseResponse(BaseModel):
    """Схема курса в личном кабинете с прогрессом."""

    id: UUID
    title: str
    description: str | None = None
    progress: int
    total_lessons: int
    completed_lessons: int
    last_lesson_id: UUID | None = None
    last_lesson_title: str | None = None
    cover_image_url: str | None = None
    tariff: str | None = None
    expires_at: datetime | None = None
    support_chat_url: str | None = Field(
        None,
        description="Ссылка на Telegram-чат (только тариф support)",
    )
    
    class Config:
        from_attributes = True

