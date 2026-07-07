"""
Точка входа FastAPI приложения.
"""

import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import select, text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.rate_limit import limiter
from app.core.security import get_password_hash
from app.models.user import User

logger = logging.getLogger(__name__)


def _is_production() -> bool:
    return settings.ENVIRONMENT.lower() == "production"


def _cors_allow_origins() -> list[str]:
    raw = (settings.CORS_ORIGINS or "").strip()
    if raw:
        return [x.strip() for x in raw.split(",") if x.strip()]
    return [settings.FRONTEND_URL.rstrip("/")]


def _resolve_seed_password(configured: str, env_var: str) -> str:
    """Return the configured seed password, or generate one and log it once (WARNING)."""
    if configured:
        return configured
    generated = secrets.token_urlsafe(16)
    logger.warning(
        "%s не задан — сгенерирован dev-seed пароль: %s (зафиксируй через env %s)",
        env_var,
        generated,
        env_var,
    )
    return generated


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Production-only: force HTTPS (HSTS) and lock the API down with a strict
        # CSP. Swagger/openapi are disabled in production, so a hard CSP is safe
        # here; in dev it's skipped so /docs keeps working.
        if _is_production():
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'none'; frame-ancestors 'none'; "
                "img-src 'self' data: https:; style-src 'self' 'unsafe-inline'",
            )
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
        "/api/auth/forgot-password",
        "/api/auth/reset-password",
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
    if settings.ENVIRONMENT.lower() == "development":
        async with async_session_maker() as session:
            try:
                seed_accounts = [
                    (
                        "admin@nails-course.ru",
                        _resolve_seed_password(settings.SEED_ADMIN_PASSWORD, "SEED_ADMIN_PASSWORD"),
                        "admin",
                    ),
                    (
                        "student@test.ru",
                        _resolve_seed_password(settings.SEED_STUDENT_PASSWORD, "SEED_STUDENT_PASSWORD"),
                        "student",
                    ),
                ]
                for email, password, role in seed_accounts:
                    result = await session.execute(select(User).where(User.email == email))
                    user = result.scalars().first()

                    h = get_password_hash(password)
                    if not user:
                        logger.info("[STARTUP] Creating %s: %s", role, email)
                        user = User(email=email, password_hash=h, role=role)
                        session.add(user)
                    else:
                        logger.info("[STARTUP] Updating password for %s: %s", role, email)
                        user.password_hash = h

                await session.commit()
                logger.info("[STARTUP] Initial users synced!")
            except Exception as e:
                logger.warning("[STARTUP] Initial seeding/update failed: %s", e)

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
    """Readiness probe: verifies the app can reach the database."""
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check: database unreachable")
        return JSONResponse(status_code=503, content={"status": "db_unreachable"})
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
