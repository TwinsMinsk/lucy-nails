"""
Точка входа FastAPI приложения.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title="Nails Course API",
    description="API для платформы видео-курсов по дизайну ногтей",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
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
