from __future__ import annotations

from app.models.responses import (
    DatabaseCheckResult,
    Deliverability,
    DNSCheckResult,
    SMTPCheckResult,
    SyntaxCheckResult,
    VerificationStatus,
)

SCORE_SYNTAX_VALID = 15
SCORE_MX_FOUND = 15
SCORE_SPF_VALID = 5
SCORE_DKIM_VALID = 5
SCORE_DMARC_VALID = 5
SCORE_PTR_VALID = 5
SCORE_SMTP_DELIVERABLE = 35
SCORE_CATCH_ALL = 20
SCORE_CATCH_ALL_FREE = 5
SCORE_CATCH_ALL_SPF = 5
SCORE_DNS_FALLBACK = 10

THRESHOLD_HIGH = 70
THRESHOLD_MEDIUM = 50


def compute_score(
    syntax: SyntaxCheckResult,
    dns: DNSCheckResult | None,
    database: DatabaseCheckResult,
    smtp: SMTPCheckResult | None,
) -> tuple[int, VerificationStatus, str | None, Deliverability]:
    if not syntax.valid:
        return 0, VerificationStatus.INVALID, "failed_syntax_check", Deliverability.UNDELIVERABLE

    score = SCORE_SYNTAX_VALID

    if database.is_disposable:
        return score, VerificationStatus.DISPOSABLE, None, Deliverability.RISKY

    if database.is_spam_trap:
        return score, VerificationStatus.SPAM_TRAP, None, Deliverability.UNDELIVERABLE

    if database.typo_suggestion:
        return score, VerificationStatus.TYPO_DETECTED, None, Deliverability.LOW

    if dns:
        if dns.null_mx:
            return score, VerificationStatus.INVALID, "null_mx", Deliverability.UNDELIVERABLE

        if not dns.mx_found and not dns.a_records and not dns.aaaa_records:
            return score, VerificationStatus.UNDELIVERABLE, "no_mx_record", Deliverability.UNDELIVERABLE

        if dns.mx_found:
            score += SCORE_MX_FOUND

        if dns.spf_valid is True:
            score += SCORE_SPF_VALID
        if dns.dkim_valid is True:
            score += SCORE_DKIM_VALID
        if dns.dmarc_valid is True:
            score += SCORE_DMARC_VALID
        if dns.ptr_valid is True:
            score += SCORE_PTR_VALID
    else:
        score += SCORE_DNS_FALLBACK

    if smtp:
        if smtp.verification_blocked:
            return score, VerificationStatus.VERIFICATION_BLOCKED, None, Deliverability.UNKNOWN

        if smtp.greylisted:
            return score, VerificationStatus.GREYLISTED, None, Deliverability.UNKNOWN

        if smtp.error_code in (450, 451):
            return score, VerificationStatus.GREYLISTED, None, Deliverability.UNKNOWN

        if smtp.deliverable is True:
            if smtp.catch_all:
                score += SCORE_CATCH_ALL
                if database.is_free:
                    score += SCORE_CATCH_ALL_FREE
                if dns and dns.spf_valid:
                    score += SCORE_CATCH_ALL_SPF
                return score, VerificationStatus.CATCH_ALL, None, Deliverability.MEDIUM

            score += SCORE_SMTP_DELIVERABLE

        elif smtp.deliverable is False:
            if smtp.error_code in (550, 551, 553):
                return score, VerificationStatus.INVALID, "mailbox_not_found", Deliverability.UNDELIVERABLE
            elif smtp.error_code == 554:
                return score, VerificationStatus.UNDELIVERABLE, "relay_denied", Deliverability.UNDELIVERABLE
            else:
                return score, VerificationStatus.UNDELIVERABLE, "verification_failed", Deliverability.UNDELIVERABLE

        else:
            return score, VerificationStatus.UNKNOWN, "temporary_failure", Deliverability.UNKNOWN

    if database.is_role:
        return score, VerificationStatus.ROLE_ACCOUNT, None, Deliverability.MEDIUM

    if database.is_free:
        return score, VerificationStatus.FREE_EMAIL, None, Deliverability.HIGH

    if score >= THRESHOLD_HIGH:
        return score, VerificationStatus.VALID, None, Deliverability.HIGH
    elif score >= THRESHOLD_MEDIUM:
        return score, VerificationStatus.VALID, None, Deliverability.MEDIUM
    else:
        return score, VerificationStatus.VALID, None, Deliverability.LOW
