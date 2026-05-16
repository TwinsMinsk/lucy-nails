"""
Точка входа FastAPI приложения.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.rate_limit import limiter
from app.core.security import get_password_hash
from app.models.user import User


def _is_production() -> bool:
    return settings.ENVIRONMENT.lower() == "production"


def _cors_allow_origins() -> list[str]:
    raw = (settings.CORS_ORIGINS or "").strip()
    if raw:
        return [x.strip() for x in raw.split(",") if x.strip()]
    return [settings.FRONTEND_URL.rstrip("/")]


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


class CsrfProtectionMiddleware(BaseHTTPMiddleware):
    """Double-submit CSRF protection for cookie-authenticated unsafe requests."""

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
    # Auth endpoints establish/rotate the cookie+CSRF pair themselves, so they must
    # work even when stale auth cookies remain from a previous session.
    EXEMPT_PATHS = {
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/refresh",
        "/api/auth/logout",
    }

    async def dispatch(self, request: Request, call_next):
        if request.method.upper() in self.SAFE_METHODS:
            return await call_next(request)

        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        uses_auth_cookie = bool(request.cookies.get("access_token") or request.cookies.get("refresh_token"))
        if not uses_auth_cookie:
            return await call_next(request)

        csrf_cookie = request.cookies.get("csrf_token")
        csrf_header = request.headers.get("x-csrf-token")
        if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
            return JSONResponse({"detail": "CSRF token missing or invalid"}, status_code=403)

        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not _is_production():
        async with async_session_maker() as session:
            try:
                for email, password, role in [
                    ("admin@nails-course.ru", "admin123", "admin"),
                    ("student@test.ru", "student123", "student"),
                ]:
                    result = await session.execute(select(User).where(User.email == email))
                    user = result.scalars().first()

                    h = get_password_hash(password)
                    if not user:
                        print(f"[STARTUP] Creating {role}: {email}")
                        user = User(email=email, password_hash=h, role=role)
                        session.add(user)
                    else:
                        print(f"[STARTUP] Updating password for {role}: {email}")
                        user.password_hash = h

                await session.commit()
                print("[STARTUP] Initial users synced!")
            except Exception as e:
                print(f"[WARN] Initial seeding/update failed: {e}")

    yield


_docs_url = "/docs" if not _is_production() else None
_redoc_url = "/redoc" if not _is_production() else None
_openapi_url = "/openapi.json" if not _is_production() else None

app = FastAPI(
    title="Nails Course API",
    description="API для платформы видео-курсов по дизайну ногтей",
    version="0.1.0",
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

if _is_production():
    hosts = [h.strip() for h in (settings.TRUSTED_HOSTS or "").split(",") if h.strip()]
    if hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CsrfProtectionMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Nails Course API is running"}


@app.get("/health")
async def health_check():
    """Проверка работоспособности API."""
    return {"status": "ok"}


# Serve uploaded admin files (course banners, lesson posters, etc.) when
# persistent storage is configured. UPLOAD_STORAGE_DIR must point to a
# directory backed by a Railway Volume (or local disk in dev).
if settings.UPLOAD_STORAGE_DIR:
    import os

    from fastapi.staticfiles import StaticFiles

    os.makedirs(settings.UPLOAD_STORAGE_DIR, exist_ok=True)
    app.mount(
        "/uploads",
        StaticFiles(directory=settings.UPLOAD_STORAGE_DIR),
        name="uploads",
    )


# Подключение роутеров
from app.api import auth, courses, modules, lessons, purchases, admin, upload, payments, landing, admin_landing  # noqa: E402
from app.api.integrations import kinescope as kinescope_integration  # noqa: E402

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(courses.router, prefix="/api/courses", tags=["Courses"])
app.include_router(modules.router, prefix="/api/modules", tags=["Modules"])
app.include_router(lessons.router, prefix="/api/lessons", tags=["Lessons"])
app.include_router(purchases.router, prefix="/api/purchases", tags=["Purchases"])
app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(upload.router, prefix="/api/admin", tags=["Upload"])
app.include_router(landing.router, prefix="/api/landing", tags=["Landing"])
app.include_router(admin_landing.router, prefix="/api/admin", tags=["Admin: Landing"])
app.include_router(
    kinescope_integration.router,
    prefix="/api/integrations/kinescope",
    tags=["Integrations: Kinescope"],
)
