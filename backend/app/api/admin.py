"""
API эндпоинты для админ-панели.
"""

from datetime import datetime, timedelta
from uuid import UUID, uuid4
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.purchase import Purchase
from app.schemas.auth import UserResponse


router = APIRouter()


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Проверяет, что пользователь имеет роль admin."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# === Pydantic Schemas ===

class GrantAccessRequest(BaseModel):
    """Схема запроса на выдачу доступа."""
    user_id: UUID
    course_id: UUID
    tariff: str = "self"


class GrantAccessResponse(BaseModel):
    """Схема ответа на выдачу доступа."""
    message: str
    purchase_id: UUID
    expires_at: datetime


# --- Course Schemas ---
class CourseCreateRequest(BaseModel):
    """Схема создания курса."""
    title: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    cover_image_url: Optional[str] = None
    price_self: int = Field(default=5000, ge=0)
    price_support: int = Field(default=20000, ge=0)
    is_published: bool = False


class CourseUpdateRequest(BaseModel):
    """Схема обновления курса."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    price_self: Optional[int] = Field(None, ge=0)
    price_support: Optional[int] = Field(None, ge=0)
    is_published: Optional[bool] = None


class CourseResponse(BaseModel):
    """Схема ответа с данными курса."""
    id: UUID
    title: str
    description: str
    cover_image_url: Optional[str] = None
    price_self: int
    price_support: int
    is_published: bool
    created_at: datetime
    modules_count: int = 0
    lessons_count: int = 0
    
    class Config:
        from_attributes = True


# --- Module Schemas ---
class ModuleCreateRequest(BaseModel):
    """Схема создания модуля."""
    course_id: UUID
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    order_index: int = Field(default=0, ge=0)
    is_published: bool = False


class ModuleUpdateRequest(BaseModel):
    """Схема обновления модуля."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    order_index: Optional[int] = Field(None, ge=0)
    is_published: Optional[bool] = None


class LessonBriefResponse(BaseModel):
    """Краткая информация об уроке."""
    id: UUID
    title: str
    order_index: int
    duration_seconds: int
    kinescope_video_id: Optional[str] = None
    is_preview: bool
    
    class Config:
        from_attributes = True


class ModuleResponse(BaseModel):
    """Схема ответа с данными модуля."""
    id: UUID
    course_id: UUID
    title: str
    description: Optional[str]
    order_index: int
    is_published: bool
    created_at: datetime
    lessons_count: int = 0
    lessons: list[LessonBriefResponse] = []
    
    class Config:
        from_attributes = True


# --- Lesson Schemas ---
class LessonCreateRequest(BaseModel):
    """Схема создания урока."""
    module_id: UUID
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    content: Optional[str] = None
    kinescope_video_id: Optional[str] = None
    duration_seconds: int = Field(default=0, ge=0)
    order_index: int = Field(default=0, ge=0)
    is_preview: bool = False


class LessonUpdateRequest(BaseModel):
    """Схема обновления урока."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    content: Optional[str] = None
    kinescope_video_id: Optional[str] = None
    duration_seconds: Optional[int] = Field(None, ge=0)
    order_index: Optional[int] = Field(None, ge=0)
    is_preview: Optional[bool] = None


class LessonResponse(BaseModel):
    """Схема ответа с данными урока."""
    id: UUID
    module_id: UUID
    title: str
    description: Optional[str]
    content: Optional[str]
    kinescope_video_id: Optional[str]
    duration_seconds: int
    order_index: int
    is_preview: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# --- Analytics Schemas ---
class AnalyticsResponse(BaseModel):
    """Схема ответа с аналитикой."""
    total_users: int
    total_courses: int
    total_purchases: int
    total_revenue: int  # В рублях
    recent_purchases: int  # За последние 30 дней
    recent_registrations: int  # За последние 30 дней


# === User Endpoints ===

@router.get("/users", response_model=list[UserResponse])
async def get_all_users(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Получить список всех пользователей."""
    query = select(User).order_by(User.created_at.desc())
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [UserResponse.from_orm(user) for user in users]


# === Course CRUD ===

@router.get("/courses", response_model=list[CourseResponse])
async def get_all_courses(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Получить список всех курсов с количеством модулей и уроков."""
    query = select(Course).options(
        selectinload(Course.modules).selectinload(Module.lessons)
    ).order_by(Course.created_at.desc())
    
    result = await db.execute(query)
    courses = result.scalars().all()
    
    response = []
    for course in courses:
        modules_count = len(course.modules) if course.modules else 0
        lessons_count = sum(len(m.lessons) for m in course.modules) if course.modules else 0
        
        response.append(CourseResponse(
            id=course.id,
            title=course.title,
            description=course.description or "",
            cover_image_url=course.cover_image_url,
            price_self=course.price_self,
            price_support=course.price_support,
            is_published=course.is_published,
            created_at=course.created_at,
            modules_count=modules_count,
            lessons_count=lessons_count
        ))
    
    return response


@router.post("/courses", response_model=CourseResponse)
async def create_course(
    data: CourseCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Создать новый курс."""
    new_course = Course(
        id=uuid4(),
        title=data.title,
        description=data.description,
        cover_image_url=data.cover_image_url,
        price_self=data.price_self,
        price_support=data.price_support,
        is_published=data.is_published,
        created_at=datetime.utcnow()
    )
    
    db.add(new_course)
    await db.commit()
    await db.refresh(new_course)
    
    return CourseResponse(
        id=new_course.id,
        title=new_course.title,
        description=new_course.description or "",
        cover_image_url=new_course.cover_image_url,
        price_self=new_course.price_self,
        price_support=new_course.price_support,
        is_published=new_course.is_published,
        created_at=new_course.created_at,
        modules_count=0,
        lessons_count=0
    )


@router.get("/courses/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Получить курс по ID."""
    query = select(Course).where(Course.id == course_id).options(
        selectinload(Course.modules).selectinload(Module.lessons)
    )
    result = await db.execute(query)
    course = result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    modules_count = len(course.modules) if course.modules else 0
    lessons_count = sum(len(m.lessons) for m in course.modules) if course.modules else 0
    
    return CourseResponse(
        id=course.id,
        title=course.title,
        description=course.description or "",
        cover_image_url=course.cover_image_url,
        price_self=course.price_self,
        price_support=course.price_support,
        is_published=course.is_published,
        created_at=course.created_at,
        modules_count=modules_count,
        lessons_count=lessons_count
    )


@router.put("/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: UUID,
    data: CourseUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Обновить курс."""
    query = select(Course).where(Course.id == course_id).options(
        selectinload(Course.modules).selectinload(Module.lessons)
    )
    result = await db.execute(query)
    course = result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Обновляем только переданные поля
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(course, key, value)
    
    await db.commit()
    await db.refresh(course)
    
    modules_count = len(course.modules) if course.modules else 0
    lessons_count = sum(len(m.lessons) for m in course.modules) if course.modules else 0
    
    return CourseResponse(
        id=course.id,
        title=course.title,
        description=course.description or "",
        cover_image_url=course.cover_image_url,
        price_self=course.price_self,
        price_support=course.price_support,
        is_published=course.is_published,
        created_at=course.created_at,
        modules_count=modules_count,
        lessons_count=lessons_count
    )


@router.delete("/courses/{course_id}")
async def delete_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Удалить курс."""
    query = select(Course).where(Course.id == course_id)
    result = await db.execute(query)
    course = result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    await db.delete(course)
    await db.commit()
    
    return {"message": "Course deleted successfully"}


# === Module CRUD ===

@router.get("/courses/{course_id}/modules", response_model=list[ModuleResponse])
async def get_course_modules(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Получить все модули курса."""
    query = select(Module).where(Module.course_id == course_id).options(
        selectinload(Module.lessons)
    ).order_by(Module.order_index)
    
    result = await db.execute(query)
    modules = result.scalars().all()
    
    response = []
    for module in modules:
        lessons = [LessonBriefResponse.model_validate(l) for l in module.lessons] if module.lessons else []
        response.append(ModuleResponse(
            id=module.id,
            course_id=module.course_id,
            title=module.title,
            description=module.description,
            order_index=module.order_index,
            is_published=module.is_published,
            created_at=module.created_at,
            lessons_count=len(lessons),
            lessons=lessons
        ))
    
    return response


@router.post("/modules", response_model=ModuleResponse)
async def create_module(
    data: ModuleCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Создать новый модуль."""
    # Проверяем существование курса
    course_query = select(Course).where(Course.id == data.course_id)
    course_result = await db.execute(course_query)
    course = course_result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    new_module = Module(
        id=uuid4(),
        course_id=data.course_id,
        title=data.title,
        description=data.description,
        order_index=data.order_index,
        is_published=data.is_published,
        created_at=datetime.utcnow()
    )
    
    db.add(new_module)
    await db.commit()
    await db.refresh(new_module)
    
    return ModuleResponse(
        id=new_module.id,
        course_id=new_module.course_id,
        title=new_module.title,
        description=new_module.description,
        order_index=new_module.order_index,
        is_published=new_module.is_published,
        created_at=new_module.created_at,
        lessons_count=0,
        lessons=[]
    )


@router.put("/modules/{module_id}", response_model=ModuleResponse)
async def update_module(
    module_id: UUID,
    data: ModuleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Обновить модуль."""
    query = select(Module).where(Module.id == module_id).options(selectinload(Module.lessons))
    result = await db.execute(query)
    module = result.scalar_one_or_none()
    
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(module, key, value)
    
    await db.commit()
    await db.refresh(module)
    
    lessons = [LessonBriefResponse.model_validate(l) for l in module.lessons] if module.lessons else []
    
    return ModuleResponse(
        id=module.id,
        course_id=module.course_id,
        title=module.title,
        description=module.description,
        order_index=module.order_index,
        is_published=module.is_published,
        created_at=module.created_at,
        lessons_count=len(lessons),
        lessons=lessons
    )


@router.delete("/modules/{module_id}")
async def delete_module(
    module_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Удалить модуль."""
    query = select(Module).where(Module.id == module_id)
    result = await db.execute(query)
    module = result.scalar_one_or_none()
    
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    await db.delete(module)
    await db.commit()
    
    return {"message": "Module deleted successfully"}


# === Lesson CRUD ===

@router.post("/lessons", response_model=LessonResponse)
async def create_lesson(
    data: LessonCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Создать новый урок."""
    # Проверяем существование модуля
    module_query = select(Module).where(Module.id == data.module_id)
    module_result = await db.execute(module_query)
    module = module_result.scalar_one_or_none()
    
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    new_lesson = Lesson(
        id=uuid4(),
        module_id=data.module_id,
        title=data.title,
        description=data.description,
        content=data.content,
        kinescope_video_id=data.kinescope_video_id,
        duration_seconds=data.duration_seconds,
        order_index=data.order_index,
        is_preview=data.is_preview,
        created_at=datetime.utcnow()
    )
    
    db.add(new_lesson)
    await db.commit()
    await db.refresh(new_lesson)
    
    return LessonResponse.model_validate(new_lesson)


@router.get("/lessons/{lesson_id}", response_model=LessonResponse)
async def get_lesson_admin(
    lesson_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Получить детали урока."""
    query = select(Lesson).where(Lesson.id == lesson_id)
    result = await db.execute(query)
    lesson = result.scalar_one_or_none()
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    return LessonResponse.model_validate(lesson)


@router.put("/lessons/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: UUID,
    data: LessonUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Обновить урок."""
    query = select(Lesson).where(Lesson.id == lesson_id)
    result = await db.execute(query)
    lesson = result.scalar_one_or_none()
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lesson, key, value)
    
    await db.commit()
    await db.refresh(lesson)
    
    return LessonResponse.model_validate(lesson)


@router.delete("/lessons/{lesson_id}")
async def delete_lesson(
    lesson_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Удалить урок."""
    query = select(Lesson).where(Lesson.id == lesson_id)
    result = await db.execute(query)
    lesson = result.scalar_one_or_none()
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    await db.delete(lesson)
    await db.commit()
    
    return {"message": "Lesson deleted successfully"}


# === Analytics ===

@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Получить общую аналитику."""
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Total users
    users_result = await db.execute(select(func.count(User.id)))
    total_users = users_result.scalar() or 0
    
    # Total courses
    courses_result = await db.execute(select(func.count(Course.id)))
    total_courses = courses_result.scalar() or 0
    
    # Total purchases (successful)
    purchases_result = await db.execute(
        select(func.count(Purchase.id)).where(Purchase.payment_status == "success")
    )
    total_purchases = purchases_result.scalar() or 0
    
    # Total revenue (in rubles)
    revenue_result = await db.execute(
        select(func.sum(Purchase.amount_kopecks)).where(Purchase.payment_status == "success")
    )
    total_revenue_kopecks = revenue_result.scalar() or 0
    total_revenue = total_revenue_kopecks // 100
    
    # Recent purchases (last 30 days)
    recent_purchases_result = await db.execute(
        select(func.count(Purchase.id)).where(
            and_(
                Purchase.payment_status == "success",
                Purchase.created_at >= thirty_days_ago
            )
        )
    )
    recent_purchases = recent_purchases_result.scalar() or 0
    
    # Recent registrations (last 30 days)
    recent_registrations_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= thirty_days_ago)
    )
    recent_registrations = recent_registrations_result.scalar() or 0
    
    return AnalyticsResponse(
        total_users=total_users,
        total_courses=total_courses,
        total_purchases=total_purchases,
        total_revenue=total_revenue,
        recent_purchases=recent_purchases,
        recent_registrations=recent_registrations
    )


# === Access Management ===

@router.post("/grant-access", response_model=GrantAccessResponse)
async def grant_course_access(
    data: GrantAccessRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Выдать доступ к курсу пользователю."""
    # Проверяем существование пользователя
    user_query = select(User).where(User.id == data.user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Проверяем существование курса
    course_query = select(Course).where(Course.id == data.course_id)
    course_result = await db.execute(course_query)
    course = course_result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Проверяем существующую покупку
    purchase_query = select(Purchase).where(
        and_(
            Purchase.user_id == data.user_id,
            Purchase.course_id == data.course_id
        )
    )
    purchase_result = await db.execute(purchase_query)
    existing_purchase = purchase_result.scalar_one_or_none()
    
    expires_at = datetime.utcnow() + timedelta(days=365)
    
    if existing_purchase:
        existing_purchase.expires_at = expires_at
        existing_purchase.payment_status = "success"
        existing_purchase.tariff = data.tariff
        
        await db.commit()
        await db.refresh(existing_purchase)
        
        return GrantAccessResponse(
            message="Access extended successfully",
            purchase_id=existing_purchase.id,
            expires_at=existing_purchase.expires_at
        )
    else:
        price = course.price_support if data.tariff == "support" else course.price_self
        
        new_purchase = Purchase(
            id=uuid4(),
            user_id=data.user_id,
            course_id=data.course_id,
            tariff=data.tariff,
            amount_kopecks=price * 100,
            payment_id=f"admin_grant_{uuid4().hex[:12]}",
            payment_status="success",
            expires_at=expires_at,
            created_at=datetime.utcnow()
        )
        
        db.add(new_purchase)
        await db.commit()
        await db.refresh(new_purchase)
        
        return GrantAccessResponse(
            message="Access granted successfully",
            purchase_id=new_purchase.id,
            expires_at=new_purchase.expires_at
        )
