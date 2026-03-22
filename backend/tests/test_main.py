from unittest.mock import patch


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_all_routes_registered(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/preferences" in paths
    assert "/resume" in paths
    assert "/jobs" in paths
    assert "/jobs/{job_id}" in paths
    assert "/jobs/refresh" in paths
