from __future__ import annotations

import asyncio

import dns.asyncresolver
import dns.exception
import dns.flags
import dns.name
import dns.rdatatype
import dns.resolver

from app.config import settings
from app.core.logging import get_logger
from app.models.responses import DNSCheckResult

logger = get_logger(__name__)

_resolver: dns.asyncresolver.Resolver | None = None

COMMON_DKIM_SELECTORS = [
    "default",
    "google",
    "selector1",
    "selector2",
    "k1",
    "s1",
    "s2",
    "mail",
    "dkim",
    "smtp",
    "sig1",
    "alpha",
    "beta",
    "gamma",
    "delta",
    "epsilon",
]


def _get_resolver() -> dns.asyncresolver.Resolver:
    global _resolver
    if _resolver is None:
        _resolver = dns.asyncresolver.Resolver()
        _resolver.nameservers = ["8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1"]
        _resolver.lifetime = settings.smtp_command_timeout
        _resolver.timeout = 5.0
    return _resolver


async def _query_dns(domain: str, rdtype: str) -> list[str | tuple[int, str]]:
    resolver = _get_resolver()
    try:
        answer = await resolver.resolve(domain, rdtype)
        results: list[str | tuple[int, str]] = []
        for rdata in answer:
            if rdtype == "MX":
                results.append((rdata.preference, str(rdata.exchange).rstrip(".")))
            elif rdtype in ("A", "AAAA"):
                results.append(str(rdata))
            elif rdtype in ("TXT", "SPF"):
                txt = b"".join(rdata.strings).decode("utf-8", errors="replace")
                results.append(txt)
            else:
                results.append(str(rdata))
        return results
    except dns.resolver.NXDOMAIN:
        return []
    except dns.resolver.NoAnswer:
        return []
    except dns.resolver.NoNameservers:
        return []
    except dns.exception.Timeout:
        logger.debug("dns_timeout", domain=domain, rdtype=rdtype)
        return []
    except Exception as e:
        logger.debug("dns_error", domain=domain, rdtype=rdtype, error=str(e))
        return []


async def resolve_mx(domain: str) -> list[tuple[int, str]]:
    raw = await _query_dns(domain, "MX")
    mx_records = []
    for item in raw:
        if isinstance(item, tuple):
            preference, exchange = item
            if exchange == ".":
                return [(-1, ".")]
            mx_records.append((preference, exchange))
    mx_records.sort(key=lambda x: x[0])
    return mx_records


async def resolve_a(domain: str) -> list[str]:
    results = await _query_dns(domain, "A")
    return [r for r in results if isinstance(r, str)]


async def resolve_aaaa(domain: str) -> list[str]:
    results = await _query_dns(domain, "AAAA")
    return [r for r in results if isinstance(r, str)]


async def resolve_mx_with_fallback(domain: str) -> list[tuple[int, str]]:
    mx_records = await resolve_mx(domain)

    if mx_records and mx_records[0] == (-1, "."):
        return [(-1, ".")]

    if mx_records:
        return mx_records

    a_records = await resolve_a(domain)
    aaaa_records = await resolve_aaaa(domain)

    if a_records or aaaa_records:
        return [(0, domain)]

    return []


async def check_spf(domain: str) -> tuple[bool | None, str | None]:
    txt_records = await _query_dns(domain, "TXT")
    for record in txt_records:
        if isinstance(record, str) and record.startswith("v=spf1"):
            has_fail = "~all" in record or "-all" in record
            return has_fail, record
    return None, None


async def _check_single_dkim_selector(domain: str, selector: str) -> bool:
    dkim_domain = f"{selector}._domainkey.{domain}"
    txt_records = await _query_dns(dkim_domain, "TXT")
    for record in txt_records:
        if isinstance(record, str) and ("v=DKIM1" in record or "p=" in record):
            return True
    return False


async def check_dkim(domain: str) -> bool | None:
    tasks = [
        _check_single_dkim_selector(domain, selector)
        for selector in COMMON_DKIM_SELECTORS
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, bool) and result:
            return True
    return None


async def check_dmarc(domain: str) -> tuple[bool | None, str | None]:
    dmarc_domain = f"_dmarc.{domain}"
    txt_records = await _query_dns(dmarc_domain, "TXT")
    for record in txt_records:
        if isinstance(record, str) and "v=DMARC1" in record:
            has_policy = "p=reject" in record or "p=quarantine" in record
            return has_policy, record
    return None, None


async def check_ptr(ip: str) -> bool | None:
    try:
        resolver = _get_resolver()
        answer = await resolver.resolve_address(ip)
        return len(answer) > 0
    except Exception:
        return None


async def check_dns_health(
    domain: str,
    mx_hosts: list[tuple[int, str]],
) -> DNSCheckResult:
    a_records, aaaa_records, spf_result, dkim_result, dmarc_result = await asyncio.gather(
        resolve_a(domain),
        resolve_aaaa(domain),
        check_spf(domain),
        check_dkim(domain),
        check_dmarc(domain),
    )

    spf_valid, spf_record = spf_result
    dmarc_valid, dmarc_record = dmarc_result

    ptr_valid = None
    if a_records:
        ptr_valid = await check_ptr(a_records[0])

    is_null_mx = len(mx_hosts) == 1 and mx_hosts[0] == (-1, ".")

    return DNSCheckResult(
        mx_found=len(mx_hosts) > 0 and not is_null_mx,
        mx_records=[mx for _, mx in mx_hosts if mx != "."],
        a_records=a_records,
        aaaa_records=aaaa_records,
        spf_valid=spf_valid,
        spf_record=spf_record,
        dkim_valid=dkim_result,
        dmarc_valid=dmarc_valid,
        dmarc_record=dmarc_record,
        ptr_valid=ptr_valid,
        null_mx=is_null_mx,
    )
