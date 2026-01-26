"""
Точка входа FastAPI приложения.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.user import User
from app.core.security import get_password_hash

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Check and create initial users
    async with async_session_maker() as session:
        try:
            result = await session.execute(select(User).limit(1))
            user = result.scalars().first()
            if not user:
                print("🚀 No users found. Seeding initial data...")
                admin = User(
                    email="admin@nails-course.ru",
                    password_hash=get_password_hash("admin123"),
                    role="admin"
                )
                student = User(
                    email="student@test.ru",
                    password_hash=get_password_hash("student123"),
                    role="student"
                )
                session.add_all([admin, student])
                await session.commit()
                print("✅ Initial users created!")
            else:
                print("✅ Users already exist.")
        except Exception as e:
            print(f"⚠️ Initial seeding failed (database might not be ready): {e}")
            
    yield
    # Shutdown logic (if any)

app = FastAPI(
    title="Nails Course API",
    description="API для платформы видео-курсов по дизайну ногтей",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Проверка работоспособности API."""
    return {"status": "ok"}


# Подключение роутеров
from app.api import auth, courses, modules, lessons, purchases, admin, upload

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(courses.router, prefix="/api/courses", tags=["Courses"])
app.include_router(modules.router, prefix="/api/modules", tags=["Modules"])
app.include_router(lessons.router, prefix="/api/lessons", tags=["Lessons"])
app.include_router(purchases.router, prefix="/api/purchases", tags=["Purchases"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(upload.router, prefix="/api/admin", tags=["Upload"])
