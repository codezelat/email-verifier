# Email Verifier API

Professional email verification client for validating email addresses.

## Features

- Single and bulk email verification
- CSV export reports
- Real-time validation
- Easy-to-use client interface

## Requirements

- Python 3.8+

## Installation

```bash
git clone https://github.com/codezelat/email-verifier.git
cd email-verifier

# Setup environment
python -m venv env
.\env\Scripts\Activate.ps1

# Install dependencies
pip install -r local_verifier/requirements.txt
```

## Usage

1. **Prepare your email list** in `local_verifier/emails.json`:
```json
[
  "user@example.com",
  "test@gmail.com",
  "contact@company.com"
]
```

2. **Run verification**:
```bash
cd local_verifier
python main.py
```

3. **Check results** in the generated CSV file

## Output

The tool generates a timestamped CSV report with verification results for each email address.

## Server Connection

The client connects to a pre-configured verification server. No server setup required on your end.
