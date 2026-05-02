#!/usr/bin/env python3
"""Professional email verification client with clean CSV output."""

import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class EmailVerificationClient:
    """Professional email verification client with clean CSV output."""

    # All possible statuses returned by the server
    VALID_STATUSES = {
        "Valid",
        "Invalid",
        "Role Account",
        "Undeliverable",
        "Catch-All",
        "Disposable",
        "Configuration Error",
        "API Error",
        "Timeout",
        "Network Error",
        "System Error",
        "Error",
    }

    def __init__(self):
        self.api_url = os.getenv("PRIVATE_API_URL", "http://localhost:5001")
        self.api_key = os.getenv("SECRET_API_KEY")
        self.timeout = int(os.getenv("REQUEST_TIMEOUT", "60"))
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": self.api_key,
            "User-Agent": "EmailVerificationClient/1.0",
            "Content-Type": "application/json",
        })

    def verify_emails_from_file(self, filename: str = None) -> list:
        """Load emails from JSON and verify them via the bulk endpoint."""
        if filename is None:
            filename = Path(__file__).resolve().parent / "emails.json"
        else:
            filename = Path(filename)

        try:
            with open(filename, "r", encoding="utf-8") as f:
                emails = json.load(f)
        except FileNotFoundError:
            print(f"Error: File not found: {filename}")
            return []
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {filename}: {e}")
            return []
        except Exception as e:
            print(f"Error loading emails from {filename}: {e}")
            return []

        if not isinstance(emails, list):
            print("Error: emails.json should contain an array of email addresses")
            return []

        # Validate and filter items
        valid_emails = []
        invalid_items = []
        for item in emails:
            if isinstance(item, str) and item.strip():
                valid_emails.append(item.strip())
            else:
                invalid_items.append(item)

        if invalid_items:
            print(f"Warning: Skipped {len(invalid_items)} non-string or empty item(s)")

        if not valid_emails:
            print("No valid emails to process")
            return []

        print(f"Verifying {len(valid_emails)} email(s)...")
        return self._verify_bulk(valid_emails)

    def _verify_bulk(self, emails: list[str]) -> list:
        """Verify emails using the bulk endpoint for efficiency."""
        results = []
        batch_size = 50  # Server limit

        for i in range(0, len(emails), batch_size):
            batch = emails[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(emails) + batch_size - 1) // batch_size
            print(f"  Batch {batch_num}/{total_batches} ({len(batch)} email(s))...")

            try:
                response = self.session.post(
                    f"{self.api_url}/bulk-verify",
                    json={"emails": batch},
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("results", []):
                        results.append({
                            "email": item.get("email", ""),
                            "status": item.get("status", "Error"),
                            "details": item.get("reason", "Unknown error"),
                        })
                else:
                    error_detail = "Unknown error"
                    try:
                        error_detail = response.json().get("error", error_detail)
                    except Exception:
                        error_detail = f"HTTP {response.status_code}"
                    for email in batch:
                        results.append({
                            "email": email,
                            "status": "Error",
                            "details": error_detail,
                        })

            except requests.exceptions.Timeout:
                for email in batch:
                    results.append({
                        "email": email,
                        "status": "Timeout",
                        "details": "Request timed out",
                    })
            except requests.exceptions.RequestException as e:
                for email in batch:
                    results.append({
                        "email": email,
                        "status": "Network Error",
                        "details": str(e),
                    })
            except Exception as e:
                for email in batch:
                    results.append({
                        "email": email,
                        "status": "System Error",
                        "details": str(e),
                    })

        return results

    def export_to_csv(self, results: list, filename: str = None) -> str:
        """Export results to clean CSV format."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"email_verification_{timestamp}.csv"

        try:
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["email", "status", "details"])
                for result in results:
                    writer.writerow([
                        result["email"],
                        result["status"],
                        result["details"],
                    ])

            print(f"Results exported to: {filename}")
            return filename

        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return ""

    def print_summary(self, results: list):
        """Print verification summary matching server statuses."""
        total = len(results)
        if total == 0:
            print("\nNo results to summarize.")
            return

        counts = {}
        for result in results:
            status = result.get("status", "Unknown")
            counts[status] = counts.get(status, 0) + 1

        print("\nVerification Summary:")
        print("-" * 40)
        print(f"Total emails: {total}")

        # Print in a consistent order if present
        ordered_statuses = [
            "Valid",
            "Catch-All",
            "Role Account",
            "Disposable",
            "Invalid",
            "Undeliverable",
            "Configuration Error",
            "API Error",
            "Timeout",
            "Network Error",
            "System Error",
            "Error",
        ]

        for status in ordered_statuses:
            if status in counts:
                print(f"  {status}: {counts[status]}")

        # Print any unexpected statuses
        for status, count in counts.items():
            if status not in ordered_statuses:
                print(f"  {status}: {count}")

        print("-" * 40)


def main():
    """Main execution."""
    print("Professional Email Verification System")
    print("=" * 50)

    client = EmailVerificationClient()

    if not client.api_key:
        print("Error: SECRET_API_KEY environment variable is not set")
        print("Copy .env.example to .env and configure your API keys")
        sys.exit(1)

    # Check server health
    try:
        response = client.session.get(
            f"{client.api_url}/health", timeout=10
        )
        if response.status_code == 200:
            health = response.json()
            print(f"Server status: Online (v{health.get('version', '?')})")
        else:
            print(f"Server status: Error (HTTP {response.status_code})")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"Server status: Offline - cannot connect to {client.api_url}")
        sys.exit(1)
    except Exception as e:
        print(f"Server status: Offline - {e}")
        sys.exit(1)

    # Verify emails
    input_file = sys.argv[1] if len(sys.argv) > 1 else None
    results = client.verify_emails_from_file(input_file)

    if not results:
        print("No emails to process")
        sys.exit(0)

    # Show summary
    client.print_summary(results)

    # Export to CSV
    csv_file = client.export_to_csv(results)

    print("\nProcessing complete!")
    if csv_file:
        print(f"CSV file: {csv_file}")


if __name__ == "__main__":
    main()
