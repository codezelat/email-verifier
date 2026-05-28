import pytest


@pytest.mark.asyncio
async def test_bulk_verify_basic(client, auth_headers):
    response = await client.post(
        "/bulk-verify",
        json={
            "emails": ["user@gmail.com", "user@mailinator.com"],
            "options": {"check_smtp": False, "check_dns_health": False},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_requested"] == 2
    assert data["total_processed"] == 2
    assert len(data["results"]) == 2


@pytest.mark.asyncio
async def test_bulk_verify_deduplication(client, auth_headers):
    response = await client.post(
        "/bulk-verify",
        json={
            "emails": ["user@gmail.com", "user@gmail.com"],
            "options": {"check_smtp": False, "check_dns_health": False},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_requested"] == 1


@pytest.mark.asyncio
async def test_bulk_verify_empty_list(client, auth_headers):
    response = await client.post(
        "/bulk-verify",
        json={"emails": []},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_bulk_verify_too_many(client, auth_headers):
    emails = [f"uniqueuser{i}@example.com" for i in range(51)]
    response = await client.post(
        "/bulk-verify",
        json={"emails": emails},
        headers=auth_headers,
    )
    assert response.status_code in (413, 422)


@pytest.mark.asyncio
async def test_bulk_verify_mixed_results(client, auth_headers):
    response = await client.post(
        "/bulk-verify",
        json={
            "emails": [
                "user@gmail.com",
                "not-an-email",
                "user@mailinator.com",
            ],
            "options": {"check_smtp": False, "check_dns_health": False},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_processed"] == 3
    statuses = {r["status"] for r in data["results"]}
    assert "Free Email" in statuses or "Valid" in statuses
    assert "Invalid" in statuses
    assert "Disposable" in statuses


@pytest.mark.asyncio
async def test_bulk_verify_has_request_id(client, auth_headers):
    response = await client.post(
        "/bulk-verify",
        json={
            "emails": ["user@gmail.com"],
            "options": {"check_smtp": False, "check_dns_health": False},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "request_id" in data
