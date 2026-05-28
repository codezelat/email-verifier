from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status

from app.config import settings
from app.core.logging import get_logger
from app.dependencies import ApiKeyDep
from app.models.requests import BulkVerifyRequest, SingleVerifyRequest
from app.models.responses import (
    BulkVerifyResponse,
    Deliverability,
    ErrorResponse,
    SingleVerifyResponse,
    VerificationChecks,
    VerificationStatus,
)
from app.services.verification import verify_email

logger = get_logger(__name__)

router = APIRouter(tags=["verification"])


@router.post(
    "/verify",
    response_model=SingleVerifyResponse,
    responses={
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
    summary="Verify a single email address",
    description="Performs comprehensive email verification including syntax, DNS, disposable/role detection, and SMTP checks.",
)
async def verify_single(
    body: SingleVerifyRequest,
    request: Request,
    api_key: ApiKeyDep,
) -> SingleVerifyResponse:
    request_id = getattr(request.state, "request_id", "unknown")

    logger.info("verify_request", email_hash=hash(body.email) % 10**8, request_id=request_id)

    result = await verify_email(
        email=body.email,
        options=body.options,
        request_id=request_id,
    )

    logger.info(
        "verify_complete",
        status=result.status.value,
        score=result.confidence_score,
        duration_ms=result.processing_time_ms,
        from_cache=result.from_cache,
    )

    return result


@router.post(
    "/bulk-verify",
    response_model=BulkVerifyResponse,
    responses={
        401: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
    summary="Verify multiple email addresses",
    description="Verifies up to 50 email addresses in a single request.",
)
async def verify_bulk(
    body: BulkVerifyRequest,
    request: Request,
    api_key: ApiKeyDep,
) -> BulkVerifyResponse:
    start_time = time.monotonic()
    request_id = getattr(request.state, "request_id", "unknown")

    if len(body.emails) > settings.bulk_max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": "Bulk limit exceeded",
                "detail": f"Received {len(body.emails)} emails. Maximum is {settings.bulk_max_size} per request.",
                "suggestion": f"Split your list into chunks of {settings.bulk_max_size} and send multiple requests.",
            },
        )

    logger.info("bulk_verify_request", count=len(body.emails), request_id=request_id)

    tasks = [
        verify_email(
            email=email,
            options=body.options,
            request_id=request_id,
        )
        for email in body.emails
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    verified_results: list[SingleVerifyResponse] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error("bulk_item_failed", error=str(result))
            verified_results.append(
                SingleVerifyResponse(
                    email=body.emails[i],
                    status=VerificationStatus.ERROR,
                    sub_status="internal_error",
                    confidence_score=0,
                    deliverability=Deliverability.UNDELIVERABLE,
                    checks=VerificationChecks(),
                    processing_time_ms=0,
                    verified_at=datetime.now(timezone.utc),
                    request_id=request_id,
                )
            )
        else:
            verified_results.append(result)

    processing_ms = int((time.monotonic() - start_time) * 1000)

    logger.info("bulk_verify_complete", count=len(verified_results), duration_ms=processing_ms)

    return BulkVerifyResponse(
        results=verified_results,
        total_requested=len(body.emails),
        total_processed=len(verified_results),
        processing_time_ms=processing_ms,
        request_id=request_id,
    )
