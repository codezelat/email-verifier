from __future__ import annotations

import hashlib
import time
from typing import Any

from cachetools import TTLCache

from app.config import settings


class VerificationCache:
    def __init__(self) -> None:
        self._dns_cache: TTLCache[str, Any] = TTLCache(
            maxsize=10000, ttl=settings.dns_cache_ttl
        )
        self._smtp_cache: TTLCache[str, Any] = TTLCache(
            maxsize=10000, ttl=settings.smtp_cache_ttl
        )
        self._result_cache: TTLCache[str, Any] = TTLCache(
            maxsize=10000, ttl=settings.smtp_cache_ttl
        )

    @staticmethod
    def _key(prefix: str, value: str) -> str:
        normalized = value.lower().strip()
        digest = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return f"{prefix}:{digest}"

    def get_dns(self, domain: str) -> dict | None:
        return self._dns_cache.get(self._key("dns", domain))

    def set_dns(self, domain: str, data: dict) -> None:
        self._dns_cache[self._key("dns", domain)] = data

    def get_smtp(self, email: str) -> dict | None:
        return self._smtp_cache.get(self._key("smtp", email))

    def set_smtp(self, email: str, data: dict) -> None:
        self._smtp_cache[self._key("smtp", email)] = data

    def get_result(self, email: str) -> dict | None:
        return self._result_cache.get(self._key("result", email))

    def set_result(self, email: str, data: dict) -> None:
        self._result_cache[self._key("result", email)] = data

    def clear(self) -> None:
        self._dns_cache.clear()
        self._smtp_cache.clear()
        self._result_cache.clear()

    @property
    def stats(self) -> dict[str, int]:
        return {
            "dns_cache_size": len(self._dns_cache),
            "smtp_cache_size": len(self._smtp_cache),
            "result_cache_size": len(self._result_cache),
        }


cache = VerificationCache()
