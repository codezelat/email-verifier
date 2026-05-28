from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class VerificationOptions(BaseModel):
    check_smtp: bool = True
    check_dns_health: bool = True
    check_catch_all: bool = True
    check_disposable: bool = True
    check_role: bool = True
    check_free: bool = True
    check_typo: bool = True


class SingleVerifyRequest(BaseModel):
    email: str = Field(
        ...,
        min_length=3,
        max_length=254,
        description="Email address to verify",
        json_schema_extra={"example": "user@example.com"},
    )
    options: VerificationOptions = Field(default_factory=VerificationOptions)

    @field_validator("email")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class BulkVerifyRequest(BaseModel):
    emails: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of email addresses to verify (max 50)",
        json_schema_extra={"example": ["user@example.com", "test@mail.com"]},
    )
    options: VerificationOptions = Field(default_factory=VerificationOptions)

    @field_validator("emails")
    @classmethod
    def strip_and_deduplicate(cls, v: list[str]) -> list[str]:
        cleaned = [e.strip() for e in v if isinstance(e, str) and e.strip()]
        return list(dict.fromkeys(cleaned))
