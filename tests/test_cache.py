import pytest

from app.services.cache import VerificationCache


class TestVerificationCache:
    def test_dns_cache_set_get(self):
        c = VerificationCache()
        c.set_dns("example.com", {"mx_found": True})
        result = c.get_dns("example.com")
        assert result is not None
        assert result["mx_found"] is True

    def test_dns_cache_miss(self):
        c = VerificationCache()
        assert c.get_dns("nonexistent.com") is None

    def test_smtp_cache_set_get(self):
        c = VerificationCache()
        c.set_smtp("user@example.com", {"deliverable": True})
        result = c.get_smtp("user@example.com")
        assert result is not None
        assert result["deliverable"] is True

    def test_result_cache_set_get(self):
        c = VerificationCache()
        c.set_result("user@example.com", {"status": "Valid"})
        result = c.get_result("user@example.com")
        assert result is not None

    def test_cache_normalization(self):
        c = VerificationCache()
        c.set_dns("EXAMPLE.COM", {"mx_found": True})
        result = c.get_dns("example.com")
        assert result is not None

    def test_cache_clear(self):
        c = VerificationCache()
        c.set_dns("example.com", {"mx_found": True})
        c.clear()
        assert c.get_dns("example.com") is None

    def test_cache_stats(self):
        c = VerificationCache()
        c.set_dns("example.com", {"mx_found": True})
        stats = c.stats
        assert stats["dns_cache_size"] == 1
        assert stats["smtp_cache_size"] == 0
