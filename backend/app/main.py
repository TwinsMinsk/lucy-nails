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
    # Startup: Check and create/update initial users
    async with async_session_maker() as session:
        try:
            for email, password, role in [
                ("admin@nails-course.ru", "admin123", "admin"),
                ("student@test.ru", "student123", "student")
            ]:
                result = await session.execute(select(User).where(User.email == email))
                user = result.scalars().first()
                
                h = get_password_hash(password)
                if not user:
                    print(f"🚀 Creating {role}: {email}")
                    user = User(email=email, password_hash=h, role=role)
                    session.add(user)
                else:
                    print(f"🔄 Updating password for {role}: {email}")
                    user.password_hash = h
            
            await session.commit()
            print("✅ Initial users synced!")
        except Exception as e:
            print(f"⚠️ Initial seeding/update failed: {e}")
            
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
