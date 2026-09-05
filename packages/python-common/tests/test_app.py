from httpx import ASGITransport, AsyncClient

from commerce_common import create_service_app


async def test_health_includes_service_and_request_id() -> None:
    app = create_service_app(service_name="test-service")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health", headers={"X-Request-ID": "test-request"})

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "test-service"}
    assert response.headers["X-Request-ID"] == "test-request"


async def test_ready_reports_dependency_failure() -> None:
    async def fail() -> None:
        raise RuntimeError("not available")

    app = create_service_app(service_name="test-service", readiness_checks={"database": fail})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"] == {"database": "unavailable"}
