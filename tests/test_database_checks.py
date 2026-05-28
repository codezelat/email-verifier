import pytest

from app.services.database_checks import (
    check_all_database,
    check_disposable,
    check_free_provider,
    check_role_account,
    check_typo,
)


class TestCheckDisposable:
    def test_known_disposable_domain(self):
        assert check_disposable("mailinator.com") is True

    def test_guerrillamail(self):
        assert check_disposable("guerrillamail.com") is True

    def test_legitimate_domain(self):
        assert check_disposable("google.com") is False

    def test_gmail_not_disposable(self):
        assert check_disposable("gmail.com") is False

    def test_temp_mail(self):
        assert check_disposable("yopmail.com") is True


class TestCheckFreeProvider:
    def test_gmail_is_free(self):
        assert check_free_provider("gmail.com") is True

    def test_yahoo_is_free(self):
        assert check_free_provider("yahoo.com") is True

    def test_outlook_is_free(self):
        assert check_free_provider("outlook.com") is True

    def test_corporate_domain_not_free(self):
        assert check_free_provider("mycompany.com") is False

    def test_protonmail_is_free(self):
        assert check_free_provider("protonmail.com") is True


class TestCheckRoleAccount:
    def test_info_is_role(self):
        assert check_role_account("info") is True

    def test_support_is_role(self):
        assert check_role_account("support") is True

    def test_admin_is_role(self):
        assert check_role_account("admin") is True

    def test_noreply_is_role(self):
        assert check_role_account("noreply") is True

    def test_personal_name_not_role(self):
        assert check_role_account("john") is False

    def test_role_with_plus(self):
        assert check_role_account("info+tag") is True

    def test_webmaster_is_role(self):
        assert check_role_account("webmaster") is True

    def test_postmaster_is_role(self):
        assert check_role_account("postmaster") is True


class TestCheckTypo:
    def test_gmail_typo_gmial(self):
        assert check_typo("gmial.com") == "gmail.com"

    def test_gmail_typo_gmai(self):
        result = check_typo("gmai.com")
        assert result == "gmail.com"

    def test_hotmail_typo(self):
        result = check_typo("hotmial.com")
        assert result == "hotmail.com"

    def test_no_typo_for_correct_domain(self):
        assert check_typo("gmail.com") is None

    def test_no_typo_for_unknown_domain(self):
        assert check_typo("mycompany.com") is None

    def test_yahoo_typo(self):
        result = check_typo("yaho.com")
        assert result == "yahoo.com"


class TestCheckAllDatabase:
    def test_gmail_address(self):
        result = check_all_database("user@gmail.com")
        assert result.is_free is True
        assert result.is_disposable is False
        assert result.is_role is False
        assert result.detected_provider == "Google"

    def test_disposable_address(self):
        result = check_all_database("user@mailinator.com")
        assert result.is_disposable is True

    def test_role_address(self):
        result = check_all_database("info@company.com")
        assert result.is_role is True

    def test_corporate_address(self):
        result = check_all_database("john@mycompany.com")
        assert result.is_free is False
        assert result.is_disposable is False
        assert result.is_role is False

    def test_typo_detected(self):
        result = check_all_database("user@gmial.com")
        assert result.typo_suggestion == "gmail.com"

    def test_provider_detection_outlook(self):
        result = check_all_database("user@outlook.com")
        assert result.detected_provider == "Microsoft"

    def test_provider_detection_yahoo(self):
        result = check_all_database("user@yahoo.com")
        assert result.detected_provider == "Yahoo"

    def test_provider_detection_proton(self):
        result = check_all_database("user@protonmail.com")
        assert result.detected_provider == "ProtonMail"
