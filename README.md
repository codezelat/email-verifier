# Email Verifier

Professional email verification system with a Flask-based API server and a CLI client for validating email addresses in bulk.

## Features

- **Single and bulk email verification** via Mailboxlayer API
- **CSV export reports** with timestamps
- **Batch processing** (50 emails per request) for performance
- **Real-time validation** with multiple status categories
- **Health check endpoint** for monitoring

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
python3 -m venv env
source env/bin/activate  # On Windows: .\env\Scripts\Activate.ps1

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

## Usage

### 1. Start the Server

```bash
cd server
python server.py
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

## Project Structure

```
email-verifier/
├── .env.example              # Environment variable template
├── .gitignore
├── README.md
├── requirements.txt          # Unified Python dependencies
├── server/
│   ├── server.py             # Flask API server
│   └── requirements.txt      # (legacy, use root requirements.txt)
└── local_verifier/
    ├── main.py               # CLI client
    ├── emails.json           # Sample email list
    └── requirements.txt      # (legacy, use root requirements.txt)
```

## Production Considerations

- Use a production WSGI server (e.g., Gunicorn or uWSGI) instead of Flask's dev server
- Deploy behind a reverse proxy (e.g., Nginx)
- Use HTTPS for the `PRIVATE_API_URL`
- Rotate `SECRET_API_KEY` regularly
- Monitor `/health` endpoint for uptime checks
