from __future__ import annotations

from pathlib import Path

from disposable_email_domains import blocklist as disposable_blocklist
from Levenshtein import distance as levenshtein_distance

from app.config import settings
from app.core.logging import get_logger
from app.models.responses import DatabaseCheckResult

logger = get_logger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

_free_providers: set[str] | None = None
_role_prefixes: set[str] | None = None
_popular_domains: list[str] | None = None


def _load_free_providers() -> set[str]:
    global _free_providers
    if _free_providers is not None:
        return _free_providers

    filepath = DATA_DIR / "free_providers.txt"
    if filepath.exists():
        _free_providers = {
            line.strip().lower() for line in filepath.read_text().splitlines() if line.strip()
        }
    else:
        _free_providers = set()
        logger.warning("free_providers_file_not_found")
    return _free_providers


def _load_role_prefixes() -> set[str]:
    global _role_prefixes
    if _role_prefixes is not None:
        return _role_prefixes

    filepath = DATA_DIR / "role_prefixes.txt"
    if filepath.exists():
        _role_prefixes = {
            line.strip().lower() for line in filepath.read_text().splitlines() if line.strip()
        }
    else:
        _role_prefixes = set()
        logger.warning("role_prefixes_file_not_found")
    return _role_prefixes


def _load_popular_domains() -> list[str]:
    global _popular_domains
    if _popular_domains is not None:
        return _popular_domains

    filepath = DATA_DIR / "popular_domains.txt"
    if filepath.exists():
        _popular_domains = [
            line.strip().lower() for line in filepath.read_text().splitlines() if line.strip()
        ]
    else:
        _popular_domains = []
        logger.warning("popular_domains_file_not_found")
    return _popular_domains


def check_disposable(domain: str) -> bool:
    return domain.lower() in disposable_blocklist


def check_free_provider(domain: str) -> bool:
    providers = _load_free_providers()
    return domain.lower() in providers


def check_role_account(local_part: str) -> bool:
    prefixes = _load_role_prefixes()
    clean_local = local_part.lower().split("+")[0]
    return clean_local in prefixes


def check_typo(domain: str, max_distance: int = 2) -> str | None:
    domain_lower = domain.lower()
    popular = _load_popular_domains()

    if domain_lower in popular:
        return None

    for popular_domain in popular:
        if abs(len(domain_lower) - len(popular_domain)) > max_distance:
            continue
        dist = levenshtein_distance(domain_lower, popular_domain)
        if 0 < dist <= max_distance:
            return popular_domain

    return None


def check_all_database(
    email: str,
    check_disposable_flag: bool = True,
    check_free_flag: bool = True,
    check_role_flag: bool = True,
    check_typo_flag: bool = True,
) -> DatabaseCheckResult:
    parts = email.lower().split("@")
    if len(parts) != 2:
        return DatabaseCheckResult()

    local_part, domain = parts

    is_disposable = check_disposable(domain) if check_disposable_flag else False
    is_free = check_free_provider(domain) if check_free_flag else False
    is_role = check_role_account(local_part) if check_role_flag else False
    typo_suggestion = check_typo(domain) if check_typo_flag else None

    detected_provider = None
    provider_map = {
        "gmail.com": "Google",
        "googlemail.com": "Google",
        "outlook.com": "Microsoft",
        "hotmail.com": "Microsoft",
        "live.com": "Microsoft",
        "msn.com": "Microsoft",
        "yahoo.com": "Yahoo",
        "yahoo.co.uk": "Yahoo",
        "icloud.com": "Apple",
        "me.com": "Apple",
        "mac.com": "Apple",
        "protonmail.com": "ProtonMail",
        "proton.me": "ProtonMail",
        "zoho.com": "Zoho",
        "yandex.com": "Yandex",
        "mail.ru": "Mail.ru",
        "fastmail.com": "Fastmail",
        "tutanota.com": "Tutanota",
        "aol.com": "AOL",
        "gmx.com": "GMX",
        "mail.com": "Mail.com",
    }
    if is_free:
        detected_provider = provider_map.get(domain)

    return DatabaseCheckResult(
        is_disposable=is_disposable,
        is_free=is_free,
        is_role=is_role,
        is_spam_trap=False,
        typo_suggestion=typo_suggestion,
        detected_provider=detected_provider,
    )
