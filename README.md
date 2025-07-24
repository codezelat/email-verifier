# Email Verifier API

A professional email verification service built with Flask and powered by the Mailboxlayer API. This system provides both single email verification and bulk verification capabilities with comprehensive validation features.

## 📋 Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Server Setup](#server-setup)
  - [Client Usage](#client-usage)
  - [API Endpoints](#api-endpoints)
- [API Documentation](#api-documentation)
- [Examples](#examples)
- [Verification Status Codes](#verification-status-codes)
- [Error Handling](#error-handling)
- [Security](#security)
- [Logging](#logging)
- [Development](#development)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## ✨ Features

- **Single Email Verification**: Verify individual email addresses in real-time
- **Bulk Email Verification**: Process up to 50 emails in a single request
- **Comprehensive Validation**: Format validation, MX record checking, SMTP verification
- **Security**: API key authentication for all endpoints
- **Professional Logging**: Detailed logging with configurable levels
- **Health Monitoring**: Built-in health check endpoints
- **CSV Export**: Clean CSV output for verification results
- **Rate Limiting**: Built-in rate limiting for bulk operations
- **Error Handling**: Comprehensive error handling and reporting

## 📁 Project Structure

```
email-verifier/
├── server/                     # Flask API server
│   ├── server.py              # Main server application
│   ├── requirements.txt       # Server dependencies
│   ├── email_verifier.log     # Server logs
│   └── .env                   # Environment configuration
├── local_verifier/            # Client application
│   ├── main.py               # Client script
│   ├── emails.json           # Sample email list
│   └── requirements.txt      # Client dependencies
├── env/                      # Python virtual environment
└── README.md                 # This file
```

## 🔧 Prerequisites

- Python 3.8 or higher
- Mailboxlayer API account (free tier available)
- Virtual environment (recommended)

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/codezelat/email-verifier.git
cd email-verifier
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv env

# Activate virtual environment
# Windows (PowerShell):
.\env\Scripts\Activate.ps1

# Windows (Command Prompt):
.\env\Scripts\activate.bat

# Linux/macOS:
source env/bin/activate
```

### 3. Install Dependencies

#### Server Dependencies:
```bash
cd server
pip install -r requirements.txt
```

#### Client Dependencies:
```bash
cd ../local_verifier
pip install -r requirements.txt
```

## ⚙️ Configuration

### 1. Get Mailboxlayer API Key

1. Visit [Mailboxlayer](https://mailboxlayer.com/)
2. Sign up for a free account
3. Get your API access key from the dashboard

### 2. Configure Environment Variables

Create or edit the `.env` file in the server directory:

```properties
# API Security
SECRET_API_KEY="your-secret-api-key-here"

# Mailboxlayer API Configuration
MAILBOXLAYER_API_KEY="your-mailboxlayer-api-key-here"

# Server Configuration
PORT=5000
FLASK_DEBUG=False
FLASK_ENV=production

# Logging Configuration
LOG_LEVEL=INFO
```

**Important**: 
- Replace `your-secret-api-key-here` with a strong, unique secret key
- Replace `your-mailboxlayer-api-key-here` with your actual Mailboxlayer API key

### 3. Security Configuration

Generate a strong secret key:

```python
import secrets
print(secrets.token_urlsafe(32))
```

## 📖 Usage

### Server Setup

#### 1. Start the Server

```bash
cd server
python server.py
```

The server will start on `http://localhost:5000` by default.

#### 2. Verify Server Status

Check if the server is running:

```bash
curl -H "X-API-Key: your-secret-api-key" http://localhost:5000/health
```

### Client Usage

#### 1. Prepare Email List

Edit `local_verifier/emails.json` with your email addresses:

```json
[
  "user@example.com",
  "test@gmail.com",
  "invalid-email",
  "contact@company.com"
]
```

#### 2. Run Verification

```bash
cd local_verifier
python main.py
```

The client will:
- Connect to the server
- Verify all emails in `emails.json`
- Generate a timestamped CSV report
- Display verification summary

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/verify` | GET | Verify single email |
| `/bulk-verify` | POST | Verify multiple emails |
| `/health` | GET | Server health check |
| `/test-api` | GET | Test API connectivity |

## 🔌 API Documentation

### Single Email Verification

**Endpoint**: `GET /verify`

**Headers**:
```
X-API-Key: your-secret-api-key
```

**Parameters**:
- `email` (required): Email address to verify

**Example Request**:
```bash
curl -H "X-API-Key: your-secret-api-key" \
     "http://localhost:5000/verify?email=test@example.com"
```

**Example Response**:
```json
{
  "email": "test@example.com",
  "status": "Valid",
  "reason": "Email address is valid and deliverable",
  "processing_time": 1.23,
  "verification_method": "MAILBOXLAYER_API",
  "server_version": "1.0"
}
```

### Bulk Email Verification

**Endpoint**: `POST /bulk-verify`

**Headers**:
```
X-API-Key: your-secret-api-key
Content-Type: application/json
```

**Request Body**:
```json
{
  "emails": [
    "user1@example.com",
    "user2@example.com",
    "user3@example.com"
  ]
}
```

**Example Request**:
```bash
curl -X POST \
     -H "X-API-Key: your-secret-api-key" \
     -H "Content-Type: application/json" \
     -d '{"emails":["test1@example.com","test2@example.com"]}' \
     http://localhost:5000/bulk-verify
```

**Example Response**:
```json
{
  "results": [
    {
      "email": "test1@example.com",
      "status": "Valid",
      "reason": "Email address is valid and deliverable"
    },
    {
      "email": "test2@example.com",
      "status": "Invalid",
      "reason": "Email format is invalid"
    }
  ],
  "total_processed": 2,
  "processing_time": 2.45,
  "verification_method": "MAILBOXLAYER_BULK"
}
```

### Health Check

**Endpoint**: `GET /health`

**Example Response**:
```json
{
  "status": "healthy",
  "timestamp": 1674123456.789,
  "verification_method": "MAILBOXLAYER_API",
  "version": "1.0",
  "api_configured": true
}
```

## ✅ Verification Status Codes

| Status | Description |
|--------|-------------|
| `Valid` | Email is valid and deliverable |
| `Invalid` | Email format is incorrect |
| `Undeliverable` | Email cannot receive messages |
| `Disposable` | Temporary/disposable email service |
| `Catch-All` | Domain accepts all email addresses |
| `Role Account` | Role-based email (info@, admin@, etc.) |
| `Timeout` | API request timed out |
| `API Error` | Mailboxlayer API error |
| `Network Error` | Network connectivity issue |
| `System Error` | Internal system error |
| `Configuration Error` | API key not configured |

## 🛠️ Error Handling

The API provides comprehensive error handling:

### HTTP Status Codes

- `200` - Success
- `400` - Bad Request (missing parameters)
- `401` - Unauthorized (invalid API key)
- `404` - Not Found (invalid endpoint)
- `405` - Method Not Allowed
- `500` - Internal Server Error

### Error Response Format

```json
{
  "error": "Error description",
  "timestamp": 1674123456.789
}
```

## 🔐 Security

### API Key Authentication

All endpoints require authentication using the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-secret-api-key" http://localhost:5000/health
```

### Best Practices

1. **Strong API Keys**: Use cryptographically secure random keys
2. **Environment Variables**: Never hardcode API keys in source code
3. **HTTPS**: Use HTTPS in production
4. **Rate Limiting**: Built-in rate limiting for bulk operations
5. **Input Validation**: All inputs are validated and sanitized

## 📊 Logging

### Log Levels

- `DEBUG`: Detailed debugging information
- `INFO`: General information about server operations
- `WARNING`: Warning messages for unusual situations
- `ERROR`: Error messages for failed operations

### Log Files

- **Console Output**: Real-time logging to terminal
- **File Output**: `server/email_verifier.log`

### Log Format

```
2024-07-24 10:30:45,123 - __main__ - INFO - Verifying email: test@example.com
```

## 🧪 Development

### Running in Development Mode

1. Set development environment:
```bash
# In .env file
FLASK_DEBUG=True
FLASK_ENV=development
LOG_LEVEL=DEBUG
```

2. Start development server:
```bash
cd server
python server.py
```

### Testing API Connectivity

Test Mailboxlayer API connection:

```bash
curl -H "X-API-Key: your-secret-api-key" http://localhost:5000/test-api
```

### Adding New Features

1. Create feature branch
2. Implement changes in `server/server.py`
3. Update documentation
4. Test thoroughly
5. Submit pull request

## 🚀 Production Deployment

### Environment Setup

1. **Production Environment Variables**:
```properties
SECRET_API_KEY="strong-production-key"
MAILBOXLAYER_API_KEY="production-api-key"
PORT=80
FLASK_DEBUG=False
FLASK_ENV=production
LOG_LEVEL=INFO
```

2. **WSGI Server**: Use Gunicorn for production:
```bash
pip install gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 server:app
```

3. **Reverse Proxy**: Configure Nginx or Apache as reverse proxy

4. **SSL Certificate**: Use Let's Encrypt or commercial SSL certificate

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY server/ .
RUN pip install -r requirements.txt

EXPOSE 5000
CMD ["python", "server.py"]
```

Build and run:
```bash
docker build -t email-verifier .
docker run -p 5000:5000 --env-file .env email-verifier
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Server Won't Start

**Problem**: Server fails to start
**Solution**: 
- Check if port is available
- Verify Python dependencies are installed
- Check environment variables

#### 2. API Key Errors

**Problem**: "Unauthorized" responses
**Solution**:
- Verify `SECRET_API_KEY` in `.env` file
- Ensure `X-API-Key` header is included in requests
- Check for typos in API key

#### 3. Mailboxlayer API Errors

**Problem**: "API Error" responses
**Solution**:
- Verify `MAILBOXLAYER_API_KEY` is correct
- Check API quota limits
- Test API connectivity with `/test-api` endpoint

#### 4. Network Timeouts

**Problem**: Request timeout errors
**Solution**:
- Check internet connectivity
- Increase timeout values
- Verify Mailboxlayer service status

### Debug Mode

Enable detailed logging:

```properties
# In .env file
FLASK_DEBUG=True
LOG_LEVEL=DEBUG
```

### Log Analysis

Check logs for errors:

```bash
tail -f server/email_verifier.log
```

## 📚 Examples

### Python Client Example

```python
import requests

# Configuration
API_URL = "http://localhost:5000"
API_KEY = "your-secret-api-key"

headers = {"X-API-Key": API_KEY}

# Single email verification
response = requests.get(
    f"{API_URL}/verify",
    params={"email": "test@example.com"},
    headers=headers
)

result = response.json()
print(f"Status: {result['status']}")
print(f"Reason: {result['reason']}")
```

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

const API_URL = 'http://localhost:5000';
const API_KEY = 'your-secret-api-key';

async function verifyEmail(email) {
    try {
        const response = await axios.get(`${API_URL}/verify`, {
            params: { email },
            headers: { 'X-API-Key': API_KEY }
        });
        
        console.log(`Status: ${response.data.status}`);
        console.log(`Reason: ${response.data.reason}`);
    } catch (error) {
        console.error('Error:', error.response.data);
    }
}

verifyEmail('test@example.com');
```

### cURL Examples

**Single Verification**:
```bash
curl -H "X-API-Key: your-secret-api-key" \
     "http://localhost:5000/verify?email=test@example.com"
```

**Bulk Verification**:
```bash
curl -X POST \
     -H "X-API-Key: your-secret-api-key" \
     -H "Content-Type: application/json" \
     -d '{"emails":["test1@example.com","test2@example.com"]}' \
     http://localhost:5000/bulk-verify
```

## 📄 License

This project is licensed under the MIT License. See the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

For support and questions:

- Create an issue on GitHub
- Check the troubleshooting section
- Review the API documentation

---

**Email Verifier API** - Professional email verification made simple.
