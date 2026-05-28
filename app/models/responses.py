from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    VALID = "Valid"
    INVALID = "Invalid"
    UNDELIVERABLE = "Undeliverable"
    CATCH_ALL = "Catch-All"
    DISPOSABLE = "Disposable"
    ROLE_ACCOUNT = "Role Account"
    FREE_EMAIL = "Free Email"
    SPAM_TRAP = "Spam Trap"
    GREYLISTED = "Greylisted"
    VERIFICATION_BLOCKED = "Verification Blocked"
    TYPO_DETECTED = "Typo Detected"
    UNKNOWN = "Unknown"
    ERROR = "Error"


class SubStatus(str, Enum):
    MAILBOX_NOT_FOUND = "mailbox_not_found"
    FAILED_SYNTAX = "failed_syntax_check"
    DOMAIN_NOT_FOUND = "domain_not_found"
    NULL_MX = "null_mx"
    NO_MX_RECORD = "no_mx_record"
    CONNECTION_FAILED = "connection_failed"
    MAILBOX_FULL = "mailbox_quota_exceeded"
    DOES_NOT_ACCEPT_MAIL = "does_not_accept_mail"
    RELAY_DENIED = "relay_denied"
    TIMEOUT = "timeout"
    TEMPORARY_FAILURE = "temporary_failure"
    DNS_ERROR = "dns_error"
    NETWORK_ERROR = "network_error"
    CONFIG_ERROR = "config_error"
    INTERNAL_ERROR = "internal_error"


class Deliverability(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    RISKY = "risky"
    UNDELIVERABLE = "undeliverable"
    UNKNOWN = "unknown"


class SyntaxCheckResult(BaseModel):
    valid: bool
    normalized_email: str
    warnings: list[str] = []
    errors: list[str] = []


class DNSCheckResult(BaseModel):
    mx_found: bool = False
    mx_records: list[str] = []
    a_records: list[str] = []
    aaaa_records: list[str] = []
    spf_valid: bool | None = None
    spf_record: str | None = None
    dkim_valid: bool | None = None
    dmarc_valid: bool | None = None
    dmarc_record: str | None = None
    ptr_valid: bool | None = None
    null_mx: bool = False
    errors: list[str] = []


class DatabaseCheckResult(BaseModel):
    is_disposable: bool = False
    is_free: bool = False
    is_role: bool = False
    is_spam_trap: bool = False
    typo_suggestion: str | None = None
    detected_provider: str | None = None


class SMTPCheckResult(BaseModel):
    deliverable: bool | None = None
    catch_all: bool = False
    greylisted: bool = False
    error_code: int | None = None
    error_message: str | None = None
    mx_used: str | None = None
    verification_blocked: bool = False


class VerificationChecks(BaseModel):
    syntax: SyntaxCheckResult | None = None
    dns: DNSCheckResult | None = None
    database: DatabaseCheckResult | None = None
    smtp: SMTPCheckResult | None = None


class SingleVerifyResponse(BaseModel):
    email: str
    status: VerificationStatus
    sub_status: SubStatus | str | None = None
    confidence_score: int = Field(..., ge=0, le=100)
    deliverability: Deliverability
    is_deliverable: bool = False
    is_disposable: bool = False
    is_role_account: bool = False
    is_free_email: bool = False
    is_catch_all: bool = False
    typo_suggestion: str | None = None
    smtp_provider: str | None = None
    checks: VerificationChecks = Field(default_factory=VerificationChecks)
    processing_time_ms: int
    verified_at: datetime
    from_cache: bool = False
    request_id: str


class BulkVerifyResponse(BaseModel):
    results: list[SingleVerifyResponse]
    total_requested: int
    total_processed: int
    processing_time_ms: int
    request_id: str


class ErrorResponse(BaseModel):
    error: str
    detail: Any | None = None
    request_id: str | None = None


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    checks: dict[str, bool] = {}
    database_enabled: bool = False
