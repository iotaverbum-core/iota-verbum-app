from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_contract.txt"


def _sample_upload():
    return {
        "file": ("sample_contract.txt", FIXTURE_PATH.read_bytes(), "text/plain"),
    }


def test_records_endpoint_returns_record_for_tenant():
    analyse = client.post(
        "/v1/analyse",
        headers={"X-API-Key": "demo-key-iota-2026"},
        files=_sample_upload(),
        data={"domain": "legal_contract"},
    )
    assert analyse.status_code == 200
    record_id = analyse.json()["record_id"]

    response = client.get(
        f"/v1/records/{record_id}",
        headers={"X-API-Key": "demo-key-iota-2026"},
    )
    assert response.status_code == 200
    assert response.json()["record_id"] == record_id


def test_records_endpoint_requires_auth():
    response = client.get("/v1/records/missing-record")
    assert response.status_code == 401
