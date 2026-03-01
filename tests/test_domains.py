from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_domains_returns_both_domain_entries():
    response = client.get("/v1/domains")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert "legal_contract" in payload["domains"]
    assert "nda" in payload["domains"]
    assert payload["domains"]["legal_contract"]["eu_ai_act_article"]
    assert payload["domains"]["nda"]["risk_tier"] == "medium"
