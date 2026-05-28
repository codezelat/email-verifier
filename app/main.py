from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import INSECURE_PLACEHOLDER, settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.database import close_database, init_database
from app.middleware.request_id import RequestIDMiddleware, TimingMiddleware
from app.routers import health, verify

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(settings.log_level)

    if settings.secret_api_key == INSECURE_PLACEHOLDER:
        logger.critical(
            "SECURITY: SECRET_API_KEY is set to the default placeholder. "
            "Set a strong random key before deploying."
        )

    logger.info("server_starting", host=settings.host, port=settings.port)
    await init_database()
    logger.info("server_ready")
    yield
    await close_database()
    logger.info("server_stopped")


app = FastAPI(
    title="Email Verification API",
    description=(
        "Production-grade email verification service with multi-layer verification: "
        "syntax validation, DNS health checks (MX/SPF/DKIM/DMARC), disposable/role/free "
        "email detection, typo suggestion, and direct SMTP verification with catch-all "
        "detection and greylisting handling."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    openapi_tags=[
        {"name": "verification", "description": "Email verification operations"},
        {"name": "monitoring", "description": "Health checks and cache stats"},
    ],
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(TimingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Process-Time", "X-Request-ID"],
    max_age=600,
)

register_exception_handlers(app)

app.include_router(verify.router)
app.include_router(health.router)


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "service": "Email Verification API",
        "version": "2.0.0",
        "docs": "/docs" if settings.debug else None,
        "health": "/health",
    }
