"""
API эндпоинты для покупок.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.api.payments import (
    _checkout_link_for_course,
    _create_checkout_order,
    _ensure_checkout_enabled,
    _resolve_course_for_checkout,
)
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.purchase import MyCourseResponse, PaymentStartResponse, PurchaseCreate
from app.services.purchase_service import PurchaseService


router = APIRouter()


@router.post("/create", response_model=PaymentStartResponse)
@limiter.limit("30/minute")
async def create_purchase(
    request: Request,
    purchase_data: PurchaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить ссылку на оплату Prodamus (авторизованный пользователь).
    Подставляется email/телефон профиля, если есть.
    """
    _ensure_checkout_enabled()
    course = await _resolve_course_for_checkout(db, str(purchase_data.course_id))
    order, status_token = await _create_checkout_order(
        db,
        course,
        purchase_data.tariff.value,
        current_user.email,
        current_user.phone,
        user_id=current_user.id,
    )
    url = _checkout_link_for_course(
        course,
        purchase_data.tariff.value,
        customer_email=current_user.email,
        customer_phone=current_user.phone,
        order_id=f"order|{order.id}",
        status_token=status_token,
    )
    return PaymentStartResponse(
        payment_url=url,
        course_id=course.id,
        tariff=purchase_data.tariff.value,
        order_id=f"order|{order.id}",
        status_token=status_token,
    )


@router.get("/my", response_model=list[MyCourseResponse])
async def get_my_purchases(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить мои курсы с прогрессом (только активный оплаченный доступ).
    """
    return await PurchaseService.get_my_courses_with_progress(db, current_user.id)
