from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["determinism_contract"] == "active"
    assert payload["neurosymbolic_boundary"] == "symbolic_only"


def test_docs_renders_openapi_page():
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower()
