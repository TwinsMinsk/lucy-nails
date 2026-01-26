"""
API эндпоинты для покупок.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.purchase import PurchaseCreate, PurchaseResponse, MyCourseResponse
from app.services.purchase_service import PurchaseService


router = APIRouter()


@router.post("/create", response_model=PurchaseResponse)
async def create_purchase(
    purchase_data: PurchaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создать заказ на покупку курса.
    """
    try:
        purchase = await PurchaseService.create_purchase(db, current_user.id, purchase_data)
        
        # Mock payment URL (в реальном интеграции здесь будет запрос к Prodamus)
        response = PurchaseResponse.from_orm(purchase)
        response.payment_url = f"https://mock-payment-gateway.com/pay/{purchase.id}"
        
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/my", response_model=list[MyCourseResponse])
async def get_my_purchases(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить мои курсы с прогрессом.
    """
    return await PurchaseService.get_my_courses_with_progress(db, current_user.id)
