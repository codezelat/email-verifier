from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.database import database_enabled
from app.models.responses import HealthResponse
from app.services.cache import cache

router = APIRouter(tags=["monitoring"])

VERSION = "2.0.0"


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns server health status. Use for uptime monitoring.",
)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version=VERSION,
        database_enabled=database_enabled,
    )


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="Readiness probe",
    description="Returns server readiness status including dependency checks.",
)
async def readiness_check() -> HealthResponse:
    checks: dict[str, bool] = {}
    checks["database"] = database_enabled

    all_ok = all(checks.values())

    return HealthResponse(
        status="ready" if all_ok else "degraded",
        timestamp=datetime.now(timezone.utc),
        version=VERSION,
        checks=checks,
        database_enabled=database_enabled,
    )


@router.get(
    "/cache-stats",
    summary="Cache statistics",
    description="Returns current in-memory cache sizes.",
)
async def cache_stats() -> dict:
    return {
        "status": "ok",
        "cache": cache.stats,
    }
