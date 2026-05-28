import pytest


@pytest.mark.asyncio
async def test_verify_without_api_key(client):
    response = await client.post("/verify", json={"email": "test@example.com"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_verify_with_invalid_api_key(client, invalid_auth_headers):
    response = await client.post(
        "/verify",
        json={"email": "test@example.com"},
        headers=invalid_auth_headers,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_bulk_verify_without_api_key(client):
    response = await client.post(
        "/bulk-verify",
        json={"emails": ["test@example.com"]},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_no_auth_required(client):
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ready_no_auth_required(client):
    response = await client.get("/ready")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_request_id_returned(client, auth_headers):
    response = await client.post(
        "/verify",
        json={"email": "test@example.com"},
        headers={**auth_headers, "X-Request-ID": "a1b2c3d4e5f6a7b8"},
    )
    assert response.headers.get("X-Request-ID") == "a1b2c3d4e5f6a7b8"


@pytest.mark.asyncio
async def test_request_id_generated(client, auth_headers):
    response = await client.post(
        "/verify",
        json={"email": "test@example.com"},
        headers=auth_headers,
    )
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0


@pytest.mark.asyncio
async def test_process_time_header(client, auth_headers):
    response = await client.post(
        "/verify",
        json={"email": "test@example.com"},
        headers=auth_headers,
    )
    assert "X-Process-Time" in response.headers
