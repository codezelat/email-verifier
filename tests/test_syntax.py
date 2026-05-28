import pytest

from app.services.syntax import validate_syntax


class TestValidateSyntax:
    def test_valid_simple_email(self):
        result = validate_syntax("user@example.com")
        assert result.valid is True
        assert result.normalized_email == "user@example.com"
        assert result.errors == []

    def test_valid_with_plus(self):
        result = validate_syntax("user+tag@gmail.com")
        assert result.valid is True

    def test_valid_with_dots(self):
        result = validate_syntax("user.name@domain.com")
        assert result.valid is True

    def test_empty_email(self):
        result = validate_syntax("")
        assert result.valid is False
        assert any("empty" in e.lower() for e in result.errors)

    def test_missing_at(self):
        result = validate_syntax("userexample.com")
        assert result.valid is False
        assert any("@" in e for e in result.errors)

    def test_multiple_at(self):
        result = validate_syntax("user@@example.com")
        assert result.valid is False

    def test_empty_local_part(self):
        result = validate_syntax("@example.com")
        assert result.valid is False

    def test_empty_domain(self):
        result = validate_syntax("user@")
        assert result.valid is False

    def test_leading_dot_in_local(self):
        result = validate_syntax(".user@example.com")
        assert result.valid is False
        assert any("leading" in e.lower() or "dot" in e.lower() for e in result.errors)

    def test_trailing_dot_in_local(self):
        result = validate_syntax("user.@example.com")
        assert result.valid is False

    def test_consecutive_dots_in_local(self):
        result = validate_syntax("user..name@example.com")
        assert result.valid is False

    def test_space_in_local(self):
        result = validate_syntax("user name@example.com")
        assert result.valid is False

    def test_unknown_tld(self):
        result = validate_syntax("user@example.invalidtld")
        assert result.valid is False
        assert any("TLD" in e for e in result.errors)

    def test_valid_com_tld(self):
        result = validate_syntax("user@example.com")
        assert result.valid is True

    def test_valid_org_tld(self):
        result = validate_syntax("user@example.org")
        assert result.valid is True

    def test_gmail_dot_normalization(self):
        result = validate_syntax("u.s.e.r@gmail.com")
        assert result.valid is True
        assert result.normalized_email == "user@gmail.com"

    def test_gmail_plus_normalization(self):
        result = validate_syntax("user+tag@gmail.com")
        assert result.valid is True
        assert "+" not in result.normalized_email

    def test_local_part_too_long(self):
        long_local = "a" * 65
        result = validate_syntax(f"{long_local}@example.com")
        assert result.valid is False
        assert any("64" in e for e in result.errors)

    def test_domain_too_long(self):
        long_domain = "a" * 64 + "." + "b" * 64 + "." + "c" * 64 + "." + "d" * 64
        result = validate_syntax(f"user@{long_domain}")
        assert result.valid is False

    def test_ip_literal_domain(self):
        result = validate_syntax("user@[192.168.1.1]")
        assert result.valid is True
        assert any("IP" in w for w in result.warnings)

    def test_private_ip_warning(self):
        result = validate_syntax("user@[10.0.0.1]")
        assert result.valid is True
        assert any("private" in w.lower() for w in result.warnings)

    def test_quoted_local_part(self):
        result = validate_syntax('"john doe"@example.com')
        assert result.valid is True
        assert any("quoted" in w.lower() for w in result.warnings)

    def test_whitespace_stripping(self):
        result = validate_syntax("  user@example.com  ")
        assert result.valid is True

    def test_long_email(self):
        long_email = "a" * 255 + "@example.com"
        result = validate_syntax(long_email)
        assert result.valid is False

    def test_special_chars_in_local(self):
        result = validate_syntax("user!#$%&'*+/=?^`{|}~-@example.com")
        assert result.valid is True

    def test_numeric_local(self):
        result = validate_syntax("12345@example.com")
        assert result.valid is True

    def test_single_char_local(self):
        result = validate_syntax("a@example.com")
        assert result.valid is True

    def test_subdomain_domain(self):
        result = validate_syntax("user@mail.sub.example.com")
        assert result.valid is True

    def test_hyphen_in_domain(self):
        result = validate_syntax("user@my-domain.com")
        assert result.valid is True

    def test_domain_label_too_long(self):
        long_label = "a" * 64
        result = validate_syntax(f"user@{long_label}.com")
        assert result.valid is False
