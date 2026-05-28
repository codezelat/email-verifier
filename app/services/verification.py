from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone

from app.config import settings
from app.core.logging import get_logger
from app.database import log_verification
from app.models.requests import VerificationOptions
from app.models.responses import (
    DatabaseCheckResult,
    Deliverability,
    DNSCheckResult,
    SingleVerifyResponse,
    SMTPCheckResult,
    SyntaxCheckResult,
    VerificationChecks,
    VerificationStatus,
)
from app.services.cache import cache
from app.services.database_checks import check_all_database
from app.services.dns_checks import check_dns_health, resolve_mx_with_fallback
from app.services.scoring import compute_score
from app.services.smtp_verification import verify_smtp
from app.services.syntax import validate_syntax

logger = get_logger(__name__)


def _build_response(
    *,
    email: str,
    syntax: SyntaxCheckResult,
    dns: DNSCheckResult | None = None,
    database: DatabaseCheckResult | None = None,
    smtp: SMTPCheckResult | None = None,
    score: int,
    status: VerificationStatus,
    sub_status: str | None = None,
    deliverability: Deliverability,
    start_time: float,
    request_id: str,
    from_cache: bool = False,
) -> SingleVerifyResponse:
    processing_ms = int((time.monotonic() - start_time) * 1000)

    if database is None:
        database = DatabaseCheckResult()

    is_deliverable = smtp.deliverable is True if smtp else False
    is_catch_all = smtp.catch_all if smtp else False

    return SingleVerifyResponse(
        email=email,
        status=status,
        sub_status=sub_status,
        confidence_score=score,
        deliverability=deliverability,
        is_deliverable=is_deliverable,
        is_disposable=database.is_disposable,
        is_role_account=database.is_role,
        is_free_email=database.is_free,
        is_catch_all=is_catch_all,
        typo_suggestion=database.typo_suggestion,
        smtp_provider=database.detected_provider,
        checks=VerificationChecks(
            syntax=syntax,
            dns=dns,
            database=database,
            smtp=smtp,
        ),
        processing_time_ms=processing_ms,
        verified_at=datetime.now(timezone.utc),
        from_cache=from_cache,
        request_id=request_id,
    )


async def _log_result(
    request_id: str,
    email: str,
    response: SingleVerifyResponse,
) -> None:
    try:
        checks_json = json.dumps(response.checks.model_dump(), default=str)
        await log_verification(
            request_id=request_id,
            email=email,
            status=response.status.value,
            sub_status=response.sub_status,
            confidence_score=response.confidence_score,
            processing_time_ms=response.processing_time_ms,
            from_cache=response.from_cache,
            checks_json=checks_json,
        )
    except Exception as e:
        logger.debug("db_log_failed", error=str(e))


async def verify_email(
    email: str,
    options: VerificationOptions | None = None,
    request_id: str = "",
) -> SingleVerifyResponse:
    start_time = time.monotonic()

    if options is None:
        options = VerificationOptions()

    cached = cache.get_result(email)
    if cached:
        cached["from_cache"] = True
        cached["request_id"] = request_id
        return SingleVerifyResponse(**cached)

    syntax_result = validate_syntax(email)

    if not syntax_result.valid:
        return _build_response(
            email=email,
            syntax=syntax_result,
            score=0,
            status=VerificationStatus.INVALID,
            sub_status="failed_syntax_check",
            deliverability=Deliverability.UNDELIVERABLE,
            start_time=start_time,
            request_id=request_id,
        )

    normalized_email = syntax_result.normalized_email
    parts = normalized_email.split("@")
    if len(parts) != 2:
        return _build_response(
            email=email,
            syntax=syntax_result,
            score=0,
            status=VerificationStatus.INVALID,
            sub_status="failed_syntax_check",
            deliverability=Deliverability.UNDELIVERABLE,
            start_time=start_time,
            request_id=request_id,
        )

    domain = parts[1]

    database_result = check_all_database(
        normalized_email,
        check_disposable_flag=options.check_disposable,
        check_free_flag=options.check_free,
        check_role_flag=options.check_role,
        check_typo_flag=options.check_typo,
    )

    if database_result.is_disposable or database_result.is_spam_trap or database_result.typo_suggestion:
        score, status, sub_status, deliverability = compute_score(
            syntax_result, None, database_result, None
        )
        response = _build_response(
            email=email,
            syntax=syntax_result,
            database=database_result,
            score=score,
            status=status,
            sub_status=sub_status,
            deliverability=deliverability,
            start_time=start_time,
            request_id=request_id,
        )
        return response

    mx_hosts: list[tuple[int, str]] = []
    dns_result: DNSCheckResult | None = None

    if options.check_dns_health or options.check_smtp:
        cached_dns = cache.get_dns(domain)
        if cached_dns:
            mx_hosts = [tuple(m) for m in cached_dns.get("mx_hosts", [])]
            dns_result = DNSCheckResult(**cached_dns.get("dns_result", {}))
        else:
            mx_hosts = await resolve_mx_with_fallback(domain)

            if options.check_dns_health:
                dns_result = await check_dns_health(domain, mx_hosts)
            else:
                is_null_mx = len(mx_hosts) == 1 and mx_hosts[0] == (-1, ".")
                dns_result = DNSCheckResult(
                    mx_found=len(mx_hosts) > 0 and not is_null_mx,
                    mx_records=[mx for _, mx in mx_hosts if mx != "."],
                    null_mx=is_null_mx,
                )

            cache.set_dns(domain, {
                "mx_hosts": mx_hosts,
                "dns_result": dns_result.model_dump(),
            })

    if dns_result and dns_result.null_mx:
        score, status, sub_status, deliverability = compute_score(
            syntax_result, dns_result, database_result, None
        )
        return _build_response(
            email=email,
            syntax=syntax_result,
            dns=dns_result,
            database=database_result,
            score=score,
            status=status,
            sub_status=sub_status,
            deliverability=deliverability,
            start_time=start_time,
            request_id=request_id,
        )

    if dns_result and not dns_result.mx_found and not dns_result.a_records and not dns_result.aaaa_records:
        score, status, sub_status, deliverability = compute_score(
            syntax_result, dns_result, database_result, None
        )
        return _build_response(
            email=email,
            syntax=syntax_result,
            dns=dns_result,
            database=database_result,
            score=score,
            status=status,
            sub_status=sub_status,
            deliverability=deliverability,
            start_time=start_time,
            request_id=request_id,
        )

    smtp_result: SMTPCheckResult | None = None

    if options.check_smtp and mx_hosts:
        cached_smtp = cache.get_smtp(normalized_email)
        if cached_smtp:
            smtp_result = SMTPCheckResult(**cached_smtp)
        else:
            smtp_result = await verify_smtp(
                normalized_email,
                mx_hosts,
                check_catch_all=options.check_catch_all,
            )
            cache.set_smtp(normalized_email, smtp_result.model_dump())

    score, status, sub_status, deliverability = compute_score(
        syntax_result, dns_result, database_result, smtp_result
    )

    response = _build_response(
        email=email,
        syntax=syntax_result,
        dns=dns_result,
        database=database_result,
        smtp=smtp_result,
        score=score,
        status=status,
        sub_status=sub_status,
        deliverability=deliverability,
        start_time=start_time,
        request_id=request_id,
    )

    cache.set_result(normalized_email, response.model_dump())

    await _log_result(request_id, email, response)

    return response
