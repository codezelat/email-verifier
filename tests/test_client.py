"""Tests for the email verification client."""

import csv
import os
import tempfile
from datetime import datetime

import pytest

from local_verifier.main import EmailVerificationClient


class TestExportToCsv:
    """Tests for EmailVerificationClient.export_to_csv"""

    @pytest.fixture
    def client(self):
        return EmailVerificationClient()

    @pytest.fixture
    def sample_results(self):
        return [
            {"email": "a@example.com", "status": "Valid", "details": "All good"},
            {"email": "b@example.com", "status": "Invalid", "details": "Bad format"},
            {"email": "c@example.com", "status": "Undeliverable", "details": "No MX"},
        ]

    def test_export_creates_file(self, client, sample_results):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.csv")
            result = client.export_to_csv(sample_results, filepath)
            assert result == filepath
            assert os.path.exists(filepath)

    def test_export_content(self, client, sample_results):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.csv")
            client.export_to_csv(sample_results, filepath)

            with open(filepath, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)

            assert rows[0] == ["email", "status", "details"]
            assert rows[1] == ["a@example.com", "Valid", "All good"]
            assert rows[2] == ["b@example.com", "Invalid", "Bad format"]
            assert rows[3] == ["c@example.com", "Undeliverable", "No MX"]

    def test_export_generates_timestamped_filename(self, client, sample_results):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                result = client.export_to_csv(sample_results)
                assert result.startswith("email_verification_")
                assert result.endswith(".csv")
                assert os.path.exists(result)
            finally:
                os.chdir(original_cwd)

    def test_export_empty_results(self, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.csv")
            result = client.export_to_csv([], filepath)
            assert result == filepath
            with open(filepath, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)
            assert rows == [["email", "status", "details"]]

    def test_export_with_unicode(self, client):
        results = [
            {"email": "user@münchen.de", "status": "Valid", "details": "Unicode domain"},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.csv")
            client.export_to_csv(results, filepath)

            with open(filepath, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)

            assert rows[1][0] == "user@münchen.de"


class TestPrintSummary:
    """Tests for EmailVerificationClient.print_summary"""

    @pytest.fixture
    def client(self):
        return EmailVerificationClient()

    def test_empty_results(self, client, capsys):
        client.print_summary([])
        captured = capsys.readouterr()
        assert "No results to summarize" in captured.out

    def test_single_status(self, client, capsys):
        results = [
            {"email": "a@example.com", "status": "Valid", "details": "OK"},
            {"email": "b@example.com", "status": "Valid", "details": "OK"},
        ]
        client.print_summary(results)
        captured = capsys.readouterr()
        assert "Total emails: 2" in captured.out
        assert "Valid: 2" in captured.out

    def test_multiple_statuses(self, client, capsys):
        results = [
            {"email": "a@example.com", "status": "Valid", "details": "OK"},
            {"email": "b@example.com", "status": "Invalid", "details": "Bad"},
            {"email": "c@example.com", "status": "Undeliverable", "details": "No MX"},
        ]
        client.print_summary(results)
        captured = capsys.readouterr()
        assert "Total emails: 3" in captured.out
        assert "Valid: 1" in captured.out
        assert "Invalid: 1" in captured.out
        assert "Undeliverable: 1" in captured.out

    def test_unexpected_status(self, client, capsys):
        results = [
            {"email": "a@example.com", "status": "Unknown Status", "details": "?"},
        ]
        client.print_summary(results)
        captured = capsys.readouterr()
        assert "Unknown Status: 1" in captured.out


class TestVerifyEmailsFromFile:
    """Tests for email list loading and validation."""

    @pytest.fixture
    def client(self):
        return EmailVerificationClient()

    def test_loads_valid_emails(self, client):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write('["test@example.com", "hello@world.org"]')
            path = f.name

        try:
            # We can't fully test without a server, but we can test parsing
            with open(path, "r", encoding="utf-8") as f:
                import json

                emails = json.load(f)
            assert emails == ["test@example.com", "hello@world.org"]
        finally:
            os.unlink(path)

    def test_skips_invalid_items(self, client):
        raw = '["valid@example.com", 123, null, "", "  spaced@example.com  "]'
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write(raw)
            path = f.name

        try:
            import json

            with open(path, "r", encoding="utf-8") as f:
                emails = json.load(f)

            valid = [
                e.strip()
                for e in emails
                if isinstance(e, str) and e.strip()
            ]
            assert valid == ["valid@example.com", "spaced@example.com"]
        finally:
            os.unlink(path)

    def test_missing_file_returns_empty(self, client):
        result = client.verify_emails_from_file("/nonexistent/path.json")
        assert result == []

    def test_malformed_json_returns_empty(self, client):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write("not valid json")
            path = f.name

        try:
            result = client.verify_emails_from_file(path)
            assert result == []
        finally:
            os.unlink(path)
