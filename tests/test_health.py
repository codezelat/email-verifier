import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "2.0.0"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_ready_endpoint(client):
    response = await client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ready", "degraded")
    assert "checks" in data


@pytest.mark.asyncio
async def test_cache_stats_endpoint(client):
    response = await client.get("/cache-stats")
    assert response.status_code == 200
    data = response.json()
    assert "cache" in data


@pytest.mark.asyncio
async def test_root_endpoint(client):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Email Verification API"
    assert data["version"] == "2.0.0"
