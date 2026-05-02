"""Tests for the email verification server."""

import pytest
from server.server import EmailVerificationService


class TestParseVerificationResult:
    """Tests for EmailVerificationService._parse_verification_result"""

    @pytest.fixture
    def service(self):
        return EmailVerificationService(api_key="test-key")

    def test_valid_email(self, service):
        data = {
            "format_valid": True,
            "mx_found": True,
            "smtp_check": True,
            "catch_all": False,
            "role": False,
            "disposable": False,
        }
        status, reason = service._parse_verification_result(data)
        assert status == "Valid"
        assert "valid and deliverable" in reason

    def test_invalid_format(self, service):
        data = {
            "format_valid": False,
            "mx_found": False,
            "smtp_check": False,
            "catch_all": False,
            "role": False,
            "disposable": False,
        }
        status, reason = service._parse_verification_result(data)
        assert status == "Invalid"
        assert "format is invalid" in reason

    def test_disposable_email(self, service):
        data = {
            "format_valid": True,
            "mx_found": True,
            "smtp_check": True,
            "catch_all": False,
            "role": False,
            "disposable": True,
        }
        status, reason = service._parse_verification_result(data)
        assert status == "Disposable"
        assert "disposable" in reason.lower()

    def test_no_mx_records(self, service):
        data = {
            "format_valid": True,
            "mx_found": False,
            "smtp_check": False,
            "catch_all": False,
            "role": False,
            "disposable": False,
        }
        status, reason = service._parse_verification_result(data)
        assert status == "Undeliverable"
        assert "No mail servers" in reason

    def test_catch_all_domain(self, service):
        data = {
            "format_valid": True,
            "mx_found": True,
            "smtp_check": True,
            "catch_all": True,
            "role": False,
            "disposable": False,
        }
        status, reason = service._parse_verification_result(data)
        assert status == "Catch-All"
        assert "accepts all" in reason

    def test_role_account_deliverable(self, service):
        data = {
            "format_valid": True,
            "mx_found": True,
            "smtp_check": True,
            "catch_all": False,
            "role": True,
            "disposable": False,
        }
        status, reason = service._parse_verification_result(data)
        assert status == "Role Account"
        assert "Role-based" in reason

    def test_role_account_not_deliverable(self, service):
        data = {
            "format_valid": True,
            "mx_found": True,
            "smtp_check": False,
            "catch_all": False,
            "role": True,
            "disposable": False,
        }
        status, reason = service._parse_verification_result(data)
        assert status == "Role Account"
        assert "delivery uncertain" in reason

    def test_undeliverable_smtp_failed(self, service):
        data = {
            "format_valid": True,
            "mx_found": True,
            "smtp_check": False,
            "catch_all": False,
            "role": False,
            "disposable": False,
        }
        status, reason = service._parse_verification_result(data)
        assert status == "Undeliverable"
        assert "verification failed" in reason

    def test_disposable_takes_priority_over_mx(self, service):
        """Disposable check should happen before mx_found check."""
        data = {
            "format_valid": True,
            "mx_found": False,
            "smtp_check": False,
            "catch_all": False,
            "role": False,
            "disposable": True,
        }
        status, reason = service._parse_verification_result(data)
        assert status == "Disposable"


class TestVerifyEmailNoApiKey:
    """Tests for verify_email when API key is missing."""

    def test_configuration_error(self):
        service = EmailVerificationService(api_key="")
        status, reason = service.verify_email("test@example.com")
        assert status == "Configuration Error"
        assert "not configured" in reason
