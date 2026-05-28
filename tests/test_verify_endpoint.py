import pytest


@pytest.mark.asyncio
async def test_verify_invalid_syntax(client, auth_headers):
    response = await client.post(
        "/verify",
        json={"email": "not-an-email"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Invalid"
    assert data["confidence_score"] == 0


@pytest.mark.asyncio
async def test_verify_disposable_email(client, auth_headers):
    response = await client.post(
        "/verify",
        json={
            "email": "user@mailinator.com",
            "options": {"check_smtp": False, "check_dns_health": False},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Disposable"
    assert data["is_disposable"] is True


@pytest.mark.asyncio
async def test_verify_typo_detected(client, auth_headers):
    response = await client.post(
        "/verify",
        json={
            "email": "user@yaho.com",
            "options": {"check_smtp": False, "check_dns_health": False},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Typo Detected"
    assert data["typo_suggestion"] == "yahoo.com"


@pytest.mark.asyncio
async def test_verify_free_email(client, auth_headers):
    response = await client.post(
        "/verify",
        json={
            "email": "user@gmail.com",
            "options": {"check_smtp": False, "check_dns_health": False},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_free_email"] is True


@pytest.mark.asyncio
async def test_verify_role_account(client, auth_headers):
    response = await client.post(
        "/verify",
        json={
            "email": "info@company.com",
            "options": {"check_smtp": False, "check_dns_health": False},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_role_account"] is True


@pytest.mark.asyncio
async def test_verify_with_options(client, auth_headers):
    response = await client.post(
        "/verify",
        json={
            "email": "user@gmail.com",
            "options": {"check_smtp": False, "check_dns_health": False},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("Free Email", "Valid")


@pytest.mark.asyncio
async def test_verify_empty_email(client, auth_headers):
    response = await client.post(
        "/verify",
        json={"email": ""},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_verify_missing_email(client, auth_headers):
    response = await client.post(
        "/verify",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_verify_with_dns(client, auth_headers):
    response = await client.post(
        "/verify",
        json={
            "email": "user@gmail.com",
            "options": {"check_smtp": False, "check_dns_health": True},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["checks"]["dns"] is not None
    assert data["checks"]["dns"]["mx_found"] is True
