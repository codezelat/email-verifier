# Email Verifier

Professional email verification system with a Flask-based API server and a CLI client for validating email addresses in bulk.

## Features

- **Single and bulk email verification** via Mailboxlayer API
- **CSV export reports** with timestamps
- **Batch processing** (50 emails per request) for performance
- **Real-time validation** with multiple status categories
- **Health check endpoint** for monitoring
- **Retry logic with exponential backoff** for transient API failures
- **Production-ready WSGI support** via Gunicorn

## Architecture

```
local_verifier/main.py  -->  server/server.py  -->  Mailboxlayer API
      (CLI client)            (Flask API)           (3rd party)
```

## Requirements

- Python 3.8+
- Mailboxlayer API key (free tier available at [mailboxlayer.com](https://mailboxlayer.com/))

## Installation

```bash
git clone https://github.com/codezelat/email-verifier.git
cd email-verifier

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` and set your values:

```env
SECRET_API_KEY=your-secret-key-here
MAILBOXLAYER_API_KEY=your-mailboxlayer-key-here
PRIVATE_API_URL=http://localhost:5001
```

### Mailboxlayer URL Note

- **Free tier**: Set `MAILBOXLAYER_BASE_URL=http://apilayer.net/api/check` (HTTP only)
- **Paid tier**: Uses `https://apilayer.net/api/check` by default (HTTPS)

## Usage

### 1. Start the Server

**Development:**

```bash
cd server
python server.py
```

**Production (Gunicorn):**

```bash
gunicorn -w 4 -b 0.0.0.0:5001 server.wsgi:app
```

The server runs on port `5001` by default (configurable via `PORT` env var).

### 2. Prepare Your Email List

Edit `local_verifier/emails.json`:

```json
[
  "user@example.com",
  "test@gmail.com",
  "contact@company.com"
]
```

### 3. Run Verification

```bash
cd local_verifier
python main.py
```

Or with a custom file:

```bash
python main.py /path/to/your/emails.json
```

Results are exported to a timestamped CSV file (e.g., `email_verification_20260502_120000.csv`).

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Server health check |
| `/verify` | GET | Single email verification |
| `/bulk-verify` | POST | Bulk verification (max 50 emails) |
| `/test-api` | GET | Test Mailboxlayer connectivity |

### Example: Single Verification

```bash
curl "http://localhost:5001/verify?email=test@example.com" \
  -H "X-API-Key: your-secret-key"
```

### Example: Bulk Verification

```bash
curl -X POST "http://localhost:5001/bulk-verify" \
  -H "X-API-Key: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"emails": ["a@example.com", "b@example.com"]}'
```

### Example: Oversized Bulk Request

If you send more than 50 emails, you will receive a `413 Payload Too Large` with guidance:

```json
{
  "error": "Bulk limit exceeded",
  "details": "Received 75 emails. Maximum allowed is 50 per request.",
  "suggestion": "Split your list into chunks of 50 and send multiple requests."
}
```

## Verification Statuses

| Status | Meaning |
|--------|---------|
| `Valid` | Email is valid and deliverable |
| `Catch-All` | Domain accepts all email addresses |
| `Role Account` | Role-based email (e.g., info@, support@) |
| `Disposable` | Temporary/disposable email address |
| `Invalid` | Email format is invalid |
| `Undeliverable` | Mail server rejected or not found |
| `Configuration Error` | Server API key not configured |
| `API Error` | External API returned an error |
| `Timeout` | Request timed out |
| `Network Error` | Connection failure |
| `System Error` | Unexpected internal error |

## Testing

Run the test suite with pytest:

```bash
pytest tests/ -v
```

### Test Coverage

- `_parse_verification_result()` — all status branches (Valid, Invalid, Disposable, Catch-All, Role Account, Undeliverable)
- `export_to_csv()` — file creation, content accuracy, unicode handling, timestamped filenames
- `print_summary()` — empty results, single status, multiple statuses, unexpected statuses
- Email list loading and input validation

## Project Structure

```
email-verifier/
├── .env.example              # Environment variable template
├── .gitignore
├── README.md
├── requirements.txt          # Unified Python dependencies
├── server/
│   ├── __init__.py
│   ├── server.py             # Flask API server
│   └── wsgi.py               # WSGI entry point for Gunicorn
├── local_verifier/
│   ├── __init__.py
│   ├── main.py               # CLI client
│   └── emails.json           # Sample email list
└── tests/
    ├── __init__.py
    ├── test_server.py        # Server unit tests
    └── test_client.py        # Client unit tests
```

## Production Deployment

### Using Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:5001 server.wsgi:app
```

Recommended Gunicorn options for production:

```bash
gunicorn \
  -w 4 \
  -b 127.0.0.1:5001 \
  --access-logfile - \
  --error-logfile - \
  --timeout 60 \
  server.wsgi:app
```

### Behind Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Environment-Specific Checklist

- [ ] Set `FLASK_DEBUG=False`
- [ ] Use HTTPS for `PRIVATE_API_URL`
- [ ] Use `MAILBOXLAYER_BASE_URL=https://apilayer.net/api/check` if on paid tier
- [ ] Rotate `SECRET_API_KEY` regularly
- [ ] Monitor `/health` endpoint for uptime checks
- [ ] Configure `BULK_RATE_LIMIT_DELAY` based on your Mailboxlayer rate limits
- [ ] Run behind a reverse proxy (Nginx, Caddy, etc.)
