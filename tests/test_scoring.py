import pytest

from app.services.scoring import compute_score
from app.models.responses import (
    DatabaseCheckResult,
    Deliverability,
    DNSCheckResult,
    SMTPCheckResult,
    SyntaxCheckResult,
    VerificationStatus,
)


@pytest.fixture
def valid_syntax():
    return SyntaxCheckResult(valid=True, normalized_email="user@example.com")


@pytest.fixture
def invalid_syntax():
    return SyntaxCheckResult(valid=False, normalized_email="invalid", errors=["bad format"])


@pytest.fixture
def good_dns():
    return DNSCheckResult(
        mx_found=True,
        mx_records=["mx1.example.com"],
        spf_valid=True,
        dkim_valid=True,
        dmarc_valid=True,
        ptr_valid=True,
    )


@pytest.fixture
def no_mx_dns():
    return DNSCheckResult(mx_found=False, a_records=[], aaaa_records=[])


@pytest.fixture
def null_mx_dns():
    return DNSCheckResult(mx_found=False, null_mx=True)


@pytest.fixture
def basic_db():
    return DatabaseCheckResult()


@pytest.fixture
def disposable_db():
    return DatabaseCheckResult(is_disposable=True)


@pytest.fixture
def role_db():
    return DatabaseCheckResult(is_role=True)


@pytest.fixture
def free_db():
    return DatabaseCheckResult(is_free=True)


@pytest.fixture
def typo_db():
    return DatabaseCheckResult(typo_suggestion="gmail.com")


@pytest.fixture
def valid_smtp():
    return SMTPCheckResult(deliverable=True, catch_all=False, mx_used="mx1.example.com")


@pytest.fixture
def invalid_smtp():
    return SMTPCheckResult(deliverable=False, error_code=550, error_message="User not found")


@pytest.fixture
def catch_all_smtp():
    return SMTPCheckResult(deliverable=True, catch_all=True, mx_used="mx1.example.com")


@pytest.fixture
def greylisted_smtp():
    return SMTPCheckResult(deliverable=None, greylisted=True, error_code=450)


class TestScoring:
    def test_invalid_syntax_returns_zero(self, invalid_syntax, basic_db):
        score, status, sub, deliv = compute_score(invalid_syntax, None, basic_db, None)
        assert score == 0
        assert status == VerificationStatus.INVALID
        assert sub == "failed_syntax_check"
        assert deliv == Deliverability.UNDELIVERABLE

    def test_disposable_returns_early(self, valid_syntax, disposable_db):
        score, status, sub, deliv = compute_score(valid_syntax, None, disposable_db, None)
        assert status == VerificationStatus.DISPOSABLE
        assert deliv == Deliverability.RISKY

    def test_typo_returns_early(self, valid_syntax, typo_db):
        score, status, sub, deliv = compute_score(valid_syntax, None, typo_db, None)
        assert status == VerificationStatus.TYPO_DETECTED

    def test_null_mx_returns_invalid(self, valid_syntax, null_mx_dns, basic_db):
        score, status, sub, deliv = compute_score(valid_syntax, null_mx_dns, basic_db, None)
        assert status == VerificationStatus.INVALID
        assert sub == "null_mx"

    def test_no_mx_undeliverable(self, valid_syntax, no_mx_dns, basic_db):
        score, status, sub, deliv = compute_score(valid_syntax, no_mx_dns, basic_db, None)
        assert status == VerificationStatus.UNDELIVERABLE
        assert sub == "no_mx_record"

    def test_valid_smtp_high_score(self, valid_syntax, good_dns, basic_db, valid_smtp):
        score, status, sub, deliv = compute_score(valid_syntax, good_dns, basic_db, valid_smtp)
        assert status == VerificationStatus.VALID
        assert score >= 70
        assert deliv == Deliverability.HIGH

    def test_catch_all_detected(self, valid_syntax, good_dns, basic_db, catch_all_smtp):
        score, status, sub, deliv = compute_score(valid_syntax, good_dns, basic_db, catch_all_smtp)
        assert status == VerificationStatus.CATCH_ALL

    def test_greylisted(self, valid_syntax, good_dns, basic_db, greylisted_smtp):
        score, status, sub, deliv = compute_score(valid_syntax, good_dns, basic_db, greylisted_smtp)
        assert status == VerificationStatus.GREYLISTED

    def test_invalid_smtp(self, valid_syntax, good_dns, basic_db, invalid_smtp):
        score, status, sub, deliv = compute_score(valid_syntax, good_dns, basic_db, invalid_smtp)
        assert status == VerificationStatus.INVALID
        assert sub == "mailbox_not_found"

    def test_role_account(self, valid_syntax, good_dns, role_db):
        score, status, sub, deliv = compute_score(valid_syntax, good_dns, role_db, None)
        assert status == VerificationStatus.ROLE_ACCOUNT

    def test_free_email(self, valid_syntax, good_dns, free_db):
        score, status, sub, deliv = compute_score(valid_syntax, good_dns, free_db, None)
        assert status == VerificationStatus.FREE_EMAIL

    def test_syntax_only_no_smtp(self, valid_syntax, basic_db):
        score, status, sub, deliv = compute_score(valid_syntax, None, basic_db, None)
        assert status == VerificationStatus.VALID
        assert score >= 15
