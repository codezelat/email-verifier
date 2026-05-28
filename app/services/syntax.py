from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from app.config import settings
from app.core.logging import get_logger
from app.models.responses import SyntaxCheckResult

logger = get_logger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

_TLD_SET: set[str] | None = None

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)

QUOTED_LOCAL_REGEX = re.compile(
    r'^"([a-zA-Z0-9.!#$%&\'*+/=?^_`{|} ~\-]+)"@([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*)$'
)

IP_LITERAL_REGEX = re.compile(r"^\[([^\]]+)\]$")
IPV4_REGEX = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")

GMAIL_DOMAINS = {"gmail.com", "googlemail.com"}


def _load_tlds() -> set[str]:
    global _TLD_SET
    if _TLD_SET is not None:
        return _TLD_SET

    tld_file = DATA_DIR / "tlds.txt"
    if tld_file.exists():
        _TLD_SET = {
            line.strip().lower() for line in tld_file.read_text().splitlines() if line.strip()
        }
    else:
        _TLD_SET = set()
        logger.warning("tld_file_not_found", path=str(tld_file))
    return _TLD_SET


def _count_bytes(s: str) -> int:
    return len(s.encode("utf-8"))


def _normalize_unicode(email: str) -> str:
    normalized = unicodedata.normalize("NFC", email)
    zero_width = "\u200b\u200c\u200d\u200e\u200f\ufeff\u00ad\u2060\u2061\u2062\u2063\u2064"
    for char in zero_width:
        normalized = normalized.replace(char, "")
    return normalized.strip()


def _strip_gmail_dots(local: str, domain: str) -> str:
    if domain.lower() in GMAIL_DOMAINS:
        return local.replace(".", "")
    return local


def _is_gibberish(local: str) -> bool:
    if len(local) < 3:
        return False
    vowels = set("aeiouAEIOU")
    vowel_count = sum(1 for c in local if c in vowels)
    consonant_count = sum(1 for c in local if c.isalpha() and c not in vowels)
    if consonant_count > 0 and vowel_count == 0 and len(local) > 8:
        return True
    if len(local) > 6:
        unique_chars = len(set(local.lower()))
        if unique_chars / len(local) < 0.3:
            return True
    return False


def _validate_ipv4(ip: str) -> bool:
    match = IPV4_REGEX.match(ip)
    if not match:
        return False
    return all(0 <= int(match.group(i)) <= 255 for i in range(1, 5))


def validate_syntax(email: str) -> SyntaxCheckResult:
    warnings: list[str] = []
    errors: list[str] = []

    email = _normalize_unicode(email)

    if not email:
        errors.append("Email address is empty")
        return SyntaxCheckResult(valid=False, normalized_email=email, warnings=warnings, errors=errors)

    if len(email) > 254:
        errors.append(f"Email exceeds maximum length of 254 characters ({len(email)})")

    at_count = email.count("@")
    if at_count == 0:
        errors.append("Missing @ symbol")
        return SyntaxCheckResult(valid=False, normalized_email=email, warnings=warnings, errors=errors)
    if at_count > 1:
        quoted_match = QUOTED_LOCAL_REGEX.match(email)
        if not quoted_match:
            errors.append("Multiple @ symbols found (not in quoted string)")
            return SyntaxCheckResult(valid=False, normalized_email=email, warnings=warnings, errors=errors)

    quoted_match = QUOTED_LOCAL_REGEX.match(email)
    if quoted_match:
        local_part = quoted_match.group(1)
        domain = quoted_match.group(2)
        warnings.append("Quoted local part detected (extremely rare)")
    else:
        parts = email.rsplit("@", 1)
        local_part = parts[0]
        domain = parts[1]

    if not local_part:
        errors.append("Local part is empty")

    if _count_bytes(local_part) > 64:
        errors.append(f"Local part exceeds 64 octets ({_count_bytes(local_part)})")

    if not quoted_match:
        if local_part.startswith(".") or local_part.endswith("."):
            errors.append("Local part has leading or trailing dot")
        if ".." in local_part:
            errors.append("Local part contains consecutive dots")

    if not domain:
        errors.append("Domain is empty")

    if len(domain) > 253:
        errors.append(f"Domain exceeds 253 characters ({len(domain)})")

    ip_match = IP_LITERAL_REGEX.match(domain)
    if ip_match:
        ip_addr = ip_match.group(1)
        if ip_addr.startswith("IPv6:"):
            pass
        elif not _validate_ipv4(ip_addr):
            errors.append(f"Invalid IP address literal: {ip_addr}")
        else:
            warnings.append("IP address domain detected (extremely rare)")
            octets = ip_addr.split(".")
            first = int(octets[0])
            second = int(octets[1])
            if first == 10 or (first == 172 and 16 <= second <= 31) or (first == 192 and second == 168):
                warnings.append("Private/reserved IP address")
    else:
        domain_labels = domain.split(".")
        for label in domain_labels:
            if not label:
                errors.append("Domain contains empty label (consecutive dots)")
                break
            if len(label) > 63:
                errors.append(f"Domain label exceeds 63 characters: {label}")
                break

        if len(domain_labels) >= 2:
            tld = domain_labels[-1].lower()
            tlds = _load_tlds()
            if tlds and tld not in tlds:
                errors.append(f"Unknown TLD: .{tld}")

    if not quoted_match:
        if " " in local_part:
            errors.append("Unquoted space in local part")

    if not quoted_match and not ip_match and not EMAIL_REGEX.match(email):
        if not errors:
            errors.append("Email format is invalid")

    if not errors:
        is_catch_all_provider = domain.lower() in GMAIL_DOMAINS
        normalized_local = _strip_gmail_dots(local_part, domain) if is_catch_all_provider else local_part
        if _is_gibberish(normalized_local):
            warnings.append("Local part appears to be gibberish")

    normalized_email = f"{local_part}@{domain}".lower()
    if domain.lower() in GMAIL_DOMAINS:
        normalized_local = local_part.replace(".", "").split("+")[0]
        normalized_email = f"{normalized_local}@{domain.lower()}"

    return SyntaxCheckResult(
        valid=len(errors) == 0,
        normalized_email=normalized_email,
        warnings=warnings,
        errors=errors,
    )
