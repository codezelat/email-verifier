import pytest


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_plus_addressing(self, client, auth_headers):
        response = await client.post(
            "/verify",
            json={
                "email": "user+tag@gmail.com",
                "options": {"check_smtp": False, "check_dns_health": False},
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "user+tag@gmail.com"

    @pytest.mark.asyncio
    async def test_gmail_dots(self, client, auth_headers):
        response = await client.post(
            "/verify",
            json={
                "email": "u.s.e.r@gmail.com",
                "options": {"check_smtp": False, "check_dns_health": False},
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_subdomain_email(self, client, auth_headers):
        response = await client.post(
            "/verify",
            json={
                "email": "user@mail.sub.example.com",
                "options": {"check_smtp": False, "check_dns_health": False},
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_long_local_part(self, client, auth_headers):
        long_local = "a" * 64
        response = await client.post(
            "/verify",
            json={
                "email": f"{long_local}@example.com",
                "options": {"check_smtp": False, "check_dns_health": False},
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_numeric_local(self, client, auth_headers):
        response = await client.post(
            "/verify",
            json={
                "email": "12345@example.com",
                "options": {"check_smtp": False, "check_dns_health": False},
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_special_chars(self, client, auth_headers):
        response = await client.post(
            "/verify",
            json={
                "email": "user.name+tag@example.com",
                "options": {"check_smtp": False, "check_dns_health": False},
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_hyphenated_domain(self, client, auth_headers):
        response = await client.post(
            "/verify",
            json={
                "email": "user@my-company.com",
                "options": {"check_smtp": False, "check_dns_health": False},
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_all_checks_disabled(self, client, auth_headers):
        response = await client.post(
            "/verify",
            json={
                "email": "user@gmail.com",
                "options": {
                    "check_smtp": False,
                    "check_dns_health": False,
                    "check_catch_all": False,
                    "check_disposable": False,
                    "check_role": False,
                    "check_free": False,
                    "check_typo": False,
                },
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "Valid"

    @pytest.mark.asyncio
    async def test_only_disposable_check(self, client, auth_headers):
        response = await client.post(
            "/verify",
            json={
                "email": "user@mailinator.com",
                "options": {
                    "check_smtp": False,
                    "check_dns_health": False,
                    "check_catch_all": False,
                    "check_disposable": True,
                    "check_role": False,
                    "check_free": False,
                    "check_typo": False,
                },
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "Disposable"

    @pytest.mark.asyncio
    async def test_case_insensitive(self, client, auth_headers):
        response = await client.post(
            "/verify",
            json={
                "email": "User@Gmail.COM",
                "options": {"check_smtp": False, "check_dns_health": False},
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
