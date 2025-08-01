#!/usr/bin/env python3
"""
Professional Email Verification Server
Mailboxlayer API-based email verification service
"""
import logging
import os
import re
import sys
import time

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request

# Load environment configuration
load_dotenv()
app = Flask(__name__)

# Configure professional logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('email_verifier.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Server Configuration
SECRET_API_KEY = os.getenv("SECRET_API_KEY", "change-this-secret-key")
MAILBOXLAYER_API_KEY = os.getenv("MAILBOXLAYER_API_KEY")
MAILBOXLAYER_BASE_URL = "http://apilayer.net/api/check"
REQUEST_TIMEOUT = 30
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

class EmailVerificationService:
    """Professional email verification service using Mailboxlayer API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = MAILBOXLAYER_BASE_URL
        
    def verify_email(self, email: str) -> tuple[str, str]:
        """
        Verify email using Mailboxlayer API
        Returns (status, reason) tuple
        """
        logger.info(f"Verifying email: {email}")
        
        if not self.api_key:
            return "Configuration Error", "Mailboxlayer API key not configured"
        
        try:
            # Prepare API request
            params = {
                'access_key': self.api_key,
                'email': email,
                'smtp': 1,  # Enable SMTP verification
                'format': 1  # Enable format validation
            }
            
            # Make API request
            response = requests.get(
                self.base_url,
                params=params,
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code != 200:
                logger.error(f"API request failed: HTTP {response.status_code}")
                return "API Error", f"HTTP {response.status_code}"
            
            data = response.json()
            logger.debug(f"API response for {email}: {data}")
            
            # Check for API errors
            if 'error' in data:
                error_info = data['error']
                logger.error(f"API error: {error_info}")
                return "API Error", error_info.get('info', 'Unknown API error')
            
            # Parse verification results
            return self._parse_verification_result(data)
            
        except requests.exceptions.Timeout:
            logger.error(f"API timeout for {email}")
            return "Timeout", "API request timed out"
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {email}: {e}")
            return "Network Error", f"Request failed: {str(e)}"
            
        except Exception as e:
            logger.error(f"Unexpected error for {email}: {e}")
            return "System Error", f"Verification failed: {str(e)}"
    
    def _parse_verification_result(self, data: dict) -> tuple[str, str]:
        """Parse Mailboxlayer API response and determine email status"""
        
        # Extract verification results
        format_valid = data.get('format_valid', False)
        mx_found = data.get('mx_found', False)
        smtp_check = data.get('smtp_check', False)
        catch_all = data.get('catch_all', False)
        role = data.get('role', False)
        disposable = data.get('disposable', False)
        
        # Determine status based on results
        if not format_valid:
            return "Invalid", "Email format is invalid"
        
        if disposable:
            return "Disposable", "Temporary/disposable email address"
        
        if not mx_found:
            return "Undeliverable", "No mail servers found for domain"
        
        if smtp_check:
            if catch_all:
                return "Catch-All", "Domain accepts all email addresses"
            elif role:
                return "Role Account", "Role-based email address"
            else:
                return "Valid", "Email address is valid and deliverable"
        else:
            if role:
                return "Role Account", "Role-based email, delivery uncertain"
            else:
                return "Undeliverable", "Email verification failed"

# Initialize verification service
verification_service = EmailVerificationService(MAILBOXLAYER_API_KEY)

# API Routes
@app.route('/verify', methods=['GET'])
def verify_email():
    """Single email verification endpoint"""
    start_time = time.time()
    
    # Authentication
    api_key = request.headers.get('X-API-Key') or request.headers.get('X-API-KEY')
    if not api_key or api_key != SECRET_API_KEY:
        logger.warning(f"Unauthorized access from {request.remote_addr}")
        return jsonify({"error": "Unauthorized"}), 401
    
    # Get email parameter
    email = request.args.get('email')
    if not email:
        return jsonify({"error": "Missing 'email' parameter"}), 400
    
    logger.info(f"Verification request for {email} from {request.remote_addr}")
    
    # Basic format validation
    if not EMAIL_REGEX.fullmatch(email):
        status, reason = "Invalid", "Email format is incorrect"
        processing_time = time.time() - start_time
    else:
        # Verify using Mailboxlayer
        status, reason = verification_service.verify_email(email)
        processing_time = time.time() - start_time
    
    logger.info(f"Verification complete for {email}: {status} ({processing_time:.2f}s)")
    
    return jsonify({
        "email": email,
        "status": status,
        "reason": reason,
        "processing_time": round(processing_time, 2),
        "verification_method": "MAILBOXLAYER_API",
        "server_version": "1.0"
    })

@app.route('/bulk-verify', methods=['POST'])
def bulk_verify_emails():
    """Bulk email verification endpoint"""
    start_time = time.time()
    
    # Authentication
    api_key = request.headers.get('X-API-Key') or request.headers.get('X-API-KEY')
    if not api_key or api_key != SECRET_API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Parse request data
    data = request.get_json()
    if not data or 'emails' not in data:
        return jsonify({"error": "Missing 'emails' array"}), 400
    
    emails = data['emails']
    if not isinstance(emails, list) or len(emails) > 50:
        return jsonify({"error": "Invalid emails array (max 50 emails)"}), 400
    
    logger.info(f"Bulk verification for {len(emails)} emails from {request.remote_addr}")
    
    # Process emails
    results = []
    for email in emails:
        if not isinstance(email, str):
            continue
        
        # Basic format validation
        if not EMAIL_REGEX.fullmatch(email):
            status, reason = "Invalid", "Email format is incorrect"
        else:
            # Verify using Mailboxlayer
            status, reason = verification_service.verify_email(email)
        
        results.append({
            "email": email,
            "status": status,
            "reason": reason
        })
        
        # Rate limiting - small delay between requests
        time.sleep(0.1)
    
    processing_time = time.time() - start_time
    logger.info(f"Bulk verification complete: {len(results)} emails in {processing_time:.2f}s")
    
    return jsonify({
        "results": results,
        "total_processed": len(results),
        "processing_time": round(processing_time, 2),
        "verification_method": "MAILBOXLAYER_BULK"
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Server health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "verification_method": "MAILBOXLAYER_API",
        "version": "1.0",
        "api_configured": bool(MAILBOXLAYER_API_KEY)
    })

@app.route('/test-api', methods=['GET'])
def test_api_connectivity():
    """Test Mailboxlayer API connectivity"""
    api_key = request.headers.get('X-API-Key') or request.headers.get('X-API-KEY')
    if not api_key or api_key != SECRET_API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    
    test_email = "test@example.com"
    logger.info(f"Testing API connectivity with {test_email}")
    
    try:
        status, reason = verification_service.verify_email(test_email)
        return jsonify({
            "test_email": test_email,
            "status": status,
            "reason": reason,
            "api_connectivity": "success",
            "timestamp": time.time()
        })
    except Exception as e:
        return jsonify({
            "test_email": test_email,
            "error": str(e),
            "api_connectivity": "failed",
            "timestamp": time.time()
        })

# Error handlers
@app.errorhandler(500)
def internal_server_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(405)
def method_not_allowed_error(error):
    return jsonify({"error": "Method not allowed"}), 405

if __name__ == '__main__':
    logger.info("Starting Professional Email Verification Server")
    logger.info(f"Mailboxlayer API configured: {bool(MAILBOXLAYER_API_KEY)}")
    logger.info("Server ready for email verification requests")
    
    # Server configuration
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        threaded=True
    )
