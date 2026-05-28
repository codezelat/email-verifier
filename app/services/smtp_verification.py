from __future__ import annotations

import asyncio
import ipaddress
import secrets
import socket
import time
from collections import defaultdict

import aiosmtplib

from app.config import settings
from app.core.logging import get_logger
from app.models.responses import SMTPCheckResult

logger = get_logger(__name__)

RATE_WINDOW_SECONDS = 60.0
SMTP_PORT = 25
GREYLIST_RETRIES = 2
GREYLIST_INITIAL_DELAY = 300


class _RateLimiter:
    def __init__(self) -> None:
        self._timestamps: dict[str, list[float]] = defaultdict(list)

    def can_proceed(self, domain: str) -> bool:
        now = time.monotonic()
        rate = settings.get_smtp_rate_limit(domain)
        self._timestamps[domain] = [
            ts for ts in self._timestamps[domain] if now - ts < RATE_WINDOW_SECONDS
        ]
        return len(self._timestamps[domain]) < rate

    def record(self, domain: str) -> None:
        self._timestamps[domain].append(time.monotonic())

    def wait_seconds(self, domain: str) -> float:
        now = time.monotonic()
        rate = settings.get_smtp_rate_limit(domain)
        self._timestamps[domain] = [
            ts for ts in self._timestamps[domain] if now - ts < RATE_WINDOW_SECONDS
        ]
        if len(self._timestamps[domain]) < rate:
            return 0.0
        oldest = self._timestamps[domain][0]
        return max(0.0, RATE_WINDOW_SECONDS - (now - oldest) + 0.1)


_rate_limiter = _RateLimiter()
_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.smtp_max_concurrent)
    return _semaphore


def _generate_random_local() -> str:
    return f"verify-check-{secrets.token_hex(8)}"


def _is_safe_mx_host(mx_host: str) -> bool:
    """Check that MX host does not resolve to private/reserved IPs (SSRF prevention)."""
    try:
        addrinfos = socket.getaddrinfo(mx_host, SMTP_PORT, family=socket.AF_UNSPEC)
        for family, _, _, _, sockaddr in addrinfos:
            ip_str = sockaddr[0]
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                logger.warning("blocked_private_mx", mx=mx_host, ip=ip_str)
                return False
        return True
    except (socket.gaierror, OSError, ValueError):
        return True


async def _connect_to_mx(mx_host: str) -> aiosmtplib.SMTP:
    if not _is_safe_mx_host(mx_host):
        raise aiosmtplib.SMTPConnectError(
            f"MX host {mx_host} resolves to a private/reserved IP"
        )
    smtp = aiosmtplib.SMTP(
        hostname=mx_host,
        port=SMTP_PORT,
        timeout=settings.smtp_connect_timeout,
        start_tls=False,
        use_tls=False,
    )
    await smtp.connect()
    return smtp


async def _do_smtp_handshake(smtp: aiosmtplib.SMTP, email: str) -> None:
    await smtp.ehlo(hostname=settings.verify_ehlo_hostname)
    if smtp.supports_extension("STARTTLS"):
        try:
            await smtp.starttls(validate_certs=True)
            await smtp.ehlo(hostname=settings.verify_ehlo_hostname)
        except Exception as e:
            logger.debug("starttls_failed", error=str(e))


async def _check_single_address(
    smtp: aiosmtplib.SMTP,
    address: str,
    from_email: str,
) -> tuple[int, str]:
    try:
        await smtp.mail(f"<{from_email}>")
        code, message = await smtp.rcpt(f"<{address}>")
        return code, message.decode() if isinstance(message, bytes) else str(message)
    except aiosmtplib.SMTPRecipientsRefused as e:
        if e.recipients:
            addr, (code, msg) = next(iter(e.recipients.items()))
            return code, msg.decode() if isinstance(msg, bytes) else str(msg)
        return 550, "Recipient refused"
    except aiosmtplib.SMTPServerDisconnected:
        raise
    except Exception as e:
        return 550, str(e)


async def _verify_with_mx(
    email: str,
    mx_host: str,
    check_catch_all: bool,
) -> SMTPCheckResult:
    domain = email.split("@")[1].lower()
    from_email = settings.verify_from_email

    try:
        async with asyncio.timeout(settings.smtp_overall_timeout):
            smtp = await _connect_to_mx(mx_host)
            try:
                await _do_smtp_handshake(smtp, email)

                code, message = await _check_single_address(smtp, email, from_email)

                try:
                    await smtp.rset()
                except Exception:
                    pass

                if code in (250, 251):
                    if check_catch_all:
                        random_email = f"{_generate_random_local()}@{domain}"
                        try:
                            await smtp.mail(f"<{from_email}>")
                            catch_code, _ = await _check_single_address(
                                smtp, random_email, from_email
                            )
                            try:
                                await smtp.rset()
                            except Exception:
                                pass

                            if catch_code == 250:
                                return SMTPCheckResult(
                                    deliverable=True,
                                    catch_all=True,
                                    mx_used=mx_host,
                                )
                        except Exception as e:
                            logger.debug("catch_all_check_failed", error=str(e))

                    return SMTPCheckResult(
                        deliverable=True,
                        catch_all=False,
                        mx_used=mx_host,
                    )

                elif code == 550:
                    return SMTPCheckResult(
                        deliverable=False,
                        error_code=550,
                        error_message="Mailbox not found",
                        mx_used=mx_host,
                    )

                elif code == 551:
                    return SMTPCheckResult(
                        deliverable=False,
                        error_code=551,
                        error_message="User not local",
                        mx_used=mx_host,
                    )

                elif code == 552:
                    return SMTPCheckResult(
                        deliverable=True,
                        error_code=552,
                        error_message="Mailbox full",
                        mx_used=mx_host,
                    )

                elif code in (450, 451):
                    return SMTPCheckResult(
                        deliverable=None,
                        greylisted=True,
                        error_code=code,
                        error_message="Temporarily rejected (greylisted)",
                        mx_used=mx_host,
                    )

                elif code == 553:
                    return SMTPCheckResult(
                        deliverable=False,
                        error_code=553,
                        error_message="Mailbox name invalid",
                        mx_used=mx_host,
                    )

                elif code == 554:
                    return SMTPCheckResult(
                        deliverable=False,
                        verification_blocked=True,
                        error_code=554,
                        error_message="Transaction failed",
                        mx_used=mx_host,
                    )

                else:
                    return SMTPCheckResult(
                        deliverable=None,
                        error_code=code,
                        error_message="Unknown response",
                        mx_used=mx_host,
                    )

            finally:
                try:
                    await smtp.quit()
                except Exception:
                    pass

    except asyncio.TimeoutError:
        return SMTPCheckResult(
            deliverable=None,
            error_message="Connection timeout",
            mx_used=mx_host,
        )
    except aiosmtplib.SMTPConnectError as e:
        return SMTPCheckResult(
            deliverable=None,
            error_message="Connection failed",
            mx_used=mx_host,
        )
    except OSError as e:
        return SMTPCheckResult(
            deliverable=None,
            error_message="Network error",
            mx_used=mx_host,
        )
    except Exception as e:
        logger.warning("smtp_unexpected_error", mx=mx_host, error=str(e))
        return SMTPCheckResult(
            deliverable=None,
            error_message="Unexpected error",
            mx_used=mx_host,
        )


async def verify_smtp(
    email: str,
    mx_hosts: list[tuple[int, str]],
    check_catch_all: bool = True,
) -> SMTPCheckResult:
    if not mx_hosts:
        return SMTPCheckResult(
            deliverable=None,
            error_message="No MX records found",
        )

    domain = email.split("@")[1].lower()

    wait_time = _rate_limiter.wait_seconds(domain)
    if wait_time > 0:
        logger.debug("rate_limit_wait", domain=domain, wait=wait_time)
        await asyncio.sleep(wait_time)

    semaphore = _get_semaphore()

    sorted_hosts = sorted(mx_hosts, key=lambda x: x[0])
    last_result: SMTPCheckResult | None = None

    for priority, mx_host in sorted_hosts:
        async with semaphore:
            _rate_limiter.record(domain)
            result = await _verify_with_mx(email, mx_host, check_catch_all)

            if result.deliverable is not None or result.greylisted or result.verification_blocked:
                return result

            last_result = result

    if last_result:
        return last_result

    return SMTPCheckResult(
        deliverable=None,
        error_message="All MX hosts failed",
    )
