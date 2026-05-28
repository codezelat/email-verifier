# Email Verification API v2.0

Production-grade email verification service with multi-layer verification: syntax validation, DNS health checks, disposable/role/free email detection, typo suggestion, and direct SMTP verification.

## Architecture

```
Client → FastAPI → Verification Engine
  → Layer 1: Syntax (RFC 5321/5322, TLD, gibberish, normalization)
  → Layer 2: DNS (MX, A/AAAA fallback, SPF, DKIM, DMARC, PTR)
  → Layer 3: Database (disposable, free, role, typo detection)
  → Layer 4: SMTP (RCPT TO, catch-all, greylisting, rate limiting)
  → Response (status, confidence score, detailed checks)
```

## Quick Start

```bash
git clone https://github.com/codezelat/email-verifier.git
cd email-verifier
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set SECRET_API_KEY to a strong random value
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Interactive API docs at `http://localhost:8000/docs` (when `DEBUG=true`).

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/verify` | POST | Yes | Single email verification |
| `/bulk-verify` | POST | Yes | Bulk verification (max 50) |
| `/health` | GET | No | Liveness probe |
| `/ready` | GET | No | Readiness probe |
| `/cache-stats` | GET | No | Cache statistics |
| `/` | GET | No | Service info |

## Authentication

All verification endpoints require an `X-API-Key` header:

```bash
curl -X POST "http://localhost:8000/verify" \
  -H "X-API-Key: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

## Single Verification

### Request

```json
{
  "email": "user@example.com",
  "options": {
    "check_smtp": true,
    "check_dns_health": true,
    "check_catch_all": true,
    "check_disposable": true,
    "check_role": true,
    "check_free": true,
    "check_typo": true
  }
}
```

All options default to `true`. Disable checks you don't need for faster results.

### Response

```json
{
  "email": "user@example.com",
  "status": "Valid",
  "sub_status": null,
  "confidence_score": 95,
  "deliverability": "high",
  "is_deliverable": true,
  "is_disposable": false,
  "is_role_account": false,
  "is_free_email": false,
  "is_catch_all": false,
  "typo_suggestion": null,
  "smtp_provider": "Google",
  "checks": {
    "syntax": {
      "valid": true,
      "normalized_email": "user@example.com",
      "warnings": [],
      "errors": []
    },
    "dns": {
      "mx_found": true,
      "mx_records": ["mx1.example.com"],
      "a_records": ["93.184.216.34"],
      "aaaa_records": [],
      "spf_valid": true,
      "spf_record": "v=spf1 include:_spf.example.com ~all",
      "dkim_valid": true,
      "dmarc_valid": true,
      "dmarc_record": "v=DMARC1; p=reject;",
      "ptr_valid": true,
      "null_mx": false,
      "errors": []
    },
    "database": {
      "is_disposable": false,
      "is_free": false,
      "is_role": false,
      "is_spam_trap": false,
      "typo_suggestion": null,
      "detected_provider": null
    },
    "smtp": {
      "deliverable": true,
      "catch_all": false,
      "greylisted": false,
      "error_code": null,
      "error_message": null,
      "mx_used": "mx1.example.com",
      "verification_blocked": false
    }
  },
  "processing_time_ms": 1247,
  "verified_at": "2026-05-29T10:30:00Z",
  "from_cache": false,
  "request_id": "a1b2c3d4e5f6a7b8"
}
```

## Bulk Verification

### Request

```json
{
  "emails": ["user1@example.com", "user2@test.com"],
  "options": {"check_smtp": true}
}
```

### Response

```json
{
  "results": [...],
  "total_requested": 2,
  "total_processed": 2,
  "processing_time_ms": 3500,
  "request_id": "a1b2c3d4e5f6a7b8"
}
```

Maximum 50 emails per request. Duplicates are automatically removed.

## Status Codes

| Status | Meaning |
|--------|---------|
| `Valid` | Deliverable, all checks passed |
| `Invalid` | Mailbox not found, syntax error, null MX |
| `Undeliverable` | No MX records, connection failed, relay denied |
| `Catch-All` | Domain accepts all addresses (cannot verify individually) |
| `Disposable` | Temporary email provider (mailinator.com, etc.) |
| `Role Account` | info@, support@, admin@, etc. |
| `Free Email` | Gmail, Yahoo, Outlook, etc. |
| `Typo Detected` | Domain misspelling (e.g., gmial.com → gmail.com) |
| `Greylisted` | Server temporarily rejected, retry later |
| `Verification Blocked` | Server rejects verification attempts |
| `Spam Trap` | Known spam trap address |
| `Unknown` | Temporary failure, timeout |
| `Error` | Internal error |

## Sub-Status Codes

| Sub-Status | Meaning |
|------------|---------|
| `failed_syntax_check` | Email format is invalid |
| `domain_not_found` | Domain does not exist (NXDOMAIN) |
| `null_mx` | Domain explicitly rejects email (RFC 7505) |
| `no_mx_record` | No MX, A, or AAAA records found |
| `mailbox_not_found` | RCPT TO returned 550 |
| `connection_failed` | Cannot connect to MX server |
| `mailbox_quota_exceeded` | Mailbox full (552) |
| `relay_denied` | Server refused to relay (554) |
| `timeout` | SMTP or DNS timeout |
| `temporary_failure` | 4xx error, greylisting |
| `dns_error` | DNS resolution failed |
| `network_error` | Network unreachable |
| `config_error` | Server misconfigured |
| `internal_error` | Unexpected error |

## Deliverability Levels

| Level | Score Range | Meaning |
|-------|------------|---------|
| `high` | 70-100 | Strong confidence, all checks passed |
| `medium` | 50-69 | Good confidence, most checks passed |
| `low` | 30-49 | Limited verification signals |
| `risky` | — | Disposable email detected |
| `undeliverable` | — | Invalid or unreachable |
| `unknown` | — | Temporary failure, cannot determine |

## Confidence Scoring

| Signal | Points |
|--------|--------|
| Syntax valid | +15 |
| MX found | +15 |
| SPF valid | +5 |
| DKIM valid | +5 |
| DMARC valid | +5 |
| PTR valid | +5 |
| SMTP deliverable | +35 |
| Catch-all detected | +20 |
| **Maximum** | **100** |

## Error Responses

| HTTP Code | Meaning |
|-----------|---------|
| 401 | Missing or invalid `X-API-Key` header |
| 413 | Bulk request exceeds 50 email limit |
| 422 | Validation error (bad request body) |
| 500 | Internal server error |

Error response format:

```json
{
  "error": "Validation Error",
  "detail": [...],
  "request_id": "a1b2c3d4e5f6a7b8"
}
```

## Response Headers

| Header | Description |
|--------|-------------|
| `X-Request-ID` | Unique request identifier (16-char hex) |
| `X-Process-Time` | Processing time in milliseconds |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_API_KEY` | *(required)* | API authentication key (min 16 chars) |
| `VERIFY_FROM_EMAIL` | `verify@yourdomain.com` | MAIL FROM address for SMTP checks |
| `VERIFY_EHLO_HOSTNAME` | `verify.yourdomain.com` | EHLO hostname (should match reverse DNS) |
| `DATABASE_URL` | *(empty = SQLite)* | PostgreSQL: `postgresql+asyncpg://user:pass@host/db` |
| `DNS_CACHE_TTL` | `3600` | DNS cache TTL in seconds |
| `SMTP_CACHE_TTL` | `86400` | SMTP result cache TTL in seconds |
| `RATE_LIMIT_VERIFY` | `30/minute` | Per-IP rate limit for /verify |
| `RATE_LIMIT_BULK` | `5/minute` | Per-IP rate limit for /bulk-verify |
| `SMTP_CONNECT_TIMEOUT` | `15` | SMTP connection timeout (seconds) |
| `SMTP_COMMAND_TIMEOUT` | `10` | SMTP command timeout (seconds) |
| `SMTP_OVERALL_TIMEOUT` | `30` | Total SMTP operation timeout (seconds) |
| `SMTP_RATE_GMAIL` | `3` | Gmail verification rate (per minute) |
| `SMTP_RATE_OUTLOOK` | `5` | Outlook verification rate (per minute) |
| `SMTP_RATE_YAHOO` | `3` | Yahoo verification rate (per minute) |
| `SMTP_RATE_DEFAULT` | `15` | Default verification rate (per minute) |
| `SMTP_MAX_CONCURRENT` | `20` | Max concurrent SMTP connections |
| `SMTP_MAX_PER_HOST` | `3` | Max connections per MX host |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Allowed CORS origins |
| `LOG_LEVEL` | `INFO` | Logging level |
| `BULK_MAX_SIZE` | `50` | Max emails per bulk request |
| `DEBUG` | `false` | Enable debug mode (shows /docs) |

### SMTP Verification

The SMTP engine connects directly to the recipient's MX server on port 25:

1. Resolves MX records (with A/AAAA fallback per RFC 5321)
2. Blocks connections to private/reserved IPs (SSRF prevention)
3. Connects with STARTTLS when available
4. Issues `MAIL FROM` + `RCPT TO` without sending email
5. Tests catch-all with a random address
6. Handles greylisting (450/451) responses
7. Per-domain rate limiting prevents overloading remote servers

## Docker

### Standalone

```bash
docker build -t email-verifier .
docker run -p 8000:8000 --env-file .env email-verifier
```

### Docker Compose (with PostgreSQL)

```bash
# Set DATABASE_URL in .env to use PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://verifier:verifier_secret@postgres/emailverifier
docker compose up -d
```

## Testing

```bash
source .venv/bin/activate
pytest tests/ -v
```

## Project Structure

```
email-verifier/
├── app/
│   ├── main.py                    # FastAPI application, lifespan
│   ├── config.py                  # Pydantic Settings, env validation
│   ├── database.py                # Async SQLAlchemy (SQLite/PostgreSQL)
│   ├── dependencies.py            # API key authentication
│   ├── models/
│   │   ├── requests.py            # Request models with validation
│   │   └── responses.py           # Response models, enums
│   ├── routers/
│   │   ├── verify.py              # /verify, /bulk-verify endpoints
│   │   └── health.py              # /health, /ready, /cache-stats
│   ├── services/
│   │   ├── syntax.py              # RFC 5321/5322 validation engine
│   │   ├── dns_checks.py          # MX, SPF, DKIM, DMARC, PTR
│   │   ├── database_checks.py     # Disposable, free, role, typo
│   │   ├── smtp_verification.py   # Direct SMTP verification engine
│   │   ├── scoring.py             # Confidence scoring (0-100)
│   │   ├── cache.py               # In-memory TTL cache
│   │   └── verification.py        # Verification orchestrator
│   ├── middleware/
│   │   └── request_id.py          # Request ID + timing headers
│   └── core/
│       ├── exceptions.py          # Error handlers
│       └── logging.py             # Structured logging (structlog)
├── data/
│   ├── free_providers.txt         # 100+ free email providers
│   ├── role_prefixes.txt          # 50+ role account prefixes
│   ├── popular_domains.txt        # Typo detection domains
│   └── tlds.txt                   # IANA TLD list
├── tests/                         # 118 tests across 10 files
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
└── .env.example
```

## Edge Cases Handled

| Edge Case | Handling |
|-----------|---------|
| Internationalized emails (IDN) | NFC normalization, Punycode domains |
| Plus-addressing (user+tag@) | Preserved during verification |
| Gmail dots (u.s.e.r@) | Normalized for Gmail domains |
| Quoted local parts | Parsed per RFC 5322 |
| IP address domains | Parsed and validated |
| Long addresses (254 limit) | Byte-level length checks |
| No MX, A record fallback | RFC 5321 Section 5.1 |
| Catch-all domains | Random address SMTP test |
| Greylisting (450/451) | Detected and flagged |
| Always-550 servers | Flagged as "Verification Blocked" |
| Null MX (RFC 7505) | Detected as "Domain does not accept email" |
| MX → CNAME chains | Resolved transparently |
| Temporary DNS failures | Caught and reported |
| SSRF via private MX IPs | Blocked by IP validation |
| Case sensitivity | Domain lowercased, local preserved |

## Security

- **API Key**: Timing-safe comparison via `hmac.compare_digest`
- **SSRF Prevention**: MX hosts resolving to private/reserved IPs are blocked
- **STARTTLS**: Certificate validation enabled
- **Input Validation**: Pydantic models with length limits
- **Docker**: Runs as non-root user
- **Logging**: Email addresses hashed in logs (PII protection)
- **Docs**: Disabled in production (enable with `DEBUG=true`)

## License

MIT
