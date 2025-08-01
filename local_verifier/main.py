#!/usr/bin/env python3
import csv
import json
import os
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

class EmailVerificationClient:
    """Professional email verification client with clean CSV output"""
    
    def __init__(self):
        self.api_url = os.getenv("PRIVATE_API_URL", "http://localhost:5000")
        self.api_key = os.getenv("SECRET_API_KEY")
        self.timeout = int(os.getenv("REQUEST_TIMEOUT", "60"))
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": self.api_key,
            "User-Agent": "EmailVerificationClient/1.0"
        })
    
    def verify_emails_from_file(self, filename: str = "./emails.json") -> list:
        """Load emails from JSON and verify them"""
        try:
            with open(filename, 'r') as f:
                emails = json.load(f)
        except Exception as e:
            print(f"Error loading emails from {filename}: {e}")
            return []
        
        if not isinstance(emails, list):
            print("Error: emails.json should contain an array of email addresses")
            return []
        
        print(f"Verifying {len(emails)} emails...")
        
        results = []
        for i, email in enumerate(emails, 1):
            print(f"[{i}/{len(emails)}] {email}")
            
            try:
                response = self.session.get(
                    f"{self.api_url}/verify",
                    params={"email": email},
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results.append({
                        "email": data.get("email", email),
                        "status": data.get("status", "Error"),
                        "details": data.get("reason", "Unknown error")
                    })
                else:
                    results.append({
                        "email": email,
                        "status": "Error",
                        "details": f"HTTP {response.status_code}"
                    })
                    
            except Exception as e:
                results.append({
                    "email": email,
                    "status": "Error",
                    "details": str(e)
                })
        
        return results
    
    def export_to_csv(self, results: list, filename: str = None) -> str:
        """Export results to clean CSV format"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"email_verification_{timestamp}.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow(["email", "status", "details"])
                
                # Write data
                for result in results:
                    writer.writerow([
                        result["email"],
                        result["status"],
                        result["details"]
                    ])
            
            print(f"Results exported to: {filename}")
            return filename
            
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return ""
    
    def print_summary(self, results: list):
        """Print verification summary"""
        total = len(results)
        deliverable_count = sum(1 for r in results if r["status"] == "Deliverable")
        undeliverable_count = sum(1 for r in results if r["status"] == "Undeliverable")
        likely_deliverable_count = sum(1 for r in results if r["status"] == "Likely Deliverable")
        unknown_count = sum(1 for r in results if r["status"] == "Unknown")
        invalid_format_count = sum(1 for r in results if r["status"] == "Invalid Format")
        error_count = sum(1 for r in results if r["status"] == "Error")
        
        print("\nVerification Summary:")
        print(f"Total emails: {total}")
        print(f"Deliverable: {deliverable_count}")
        print(f"Likely Deliverable: {likely_deliverable_count}")
        print(f"Undeliverable: {undeliverable_count}")
        print(f"Invalid Format: {invalid_format_count}")
        print(f"Unknown: {unknown_count}")
        print(f"Errors: {error_count}")

def main():
    """Main execution"""
    print("Professional Email Verification System")
    print("=" * 50)
    
    client = EmailVerificationClient()
    
    # Check server health
    try:
        response = client.session.get(f"{client.api_url}/health", timeout=10)
        if response.status_code == 200:
            print("Server status: Online")
        else:
            print(f"Server status: Error ({response.status_code})")
            return
    except Exception as e:
        print(f"Server status: Offline - {e}")
        return
    
    # Verify emails
    results = client.verify_emails_from_file()
    
    if not results:
        print("No emails to process")
        return
    
    # Show summary
    client.print_summary(results)
    
    # Export to CSV
    csv_file = client.export_to_csv(results)
    
    print("\nProcessing complete!")
    if csv_file:
        print(f"CSV file: {csv_file}")

if __name__ == "__main__":
    main()
