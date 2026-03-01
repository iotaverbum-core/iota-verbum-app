from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_contract.txt"


def _sample_upload():
    return {
        "file": ("sample_contract.txt", FIXTURE_PATH.read_bytes(), "text/plain"),
    }


def test_verify_unknown_record_returns_404():
    response = client.get(
        "/v1/verify/missing-record",
        headers={"X-API-Key": "demo-key-iota-2026"},
    )
    assert response.status_code == 404


def test_verify_returns_record_after_analyse():
    analyse = client.post(
        "/v1/analyse",
        headers={"X-API-Key": "demo-key-iota-2026"},
        files=_sample_upload(),
        data={"domain": "legal_contract"},
    )
    assert analyse.status_code == 200
    record_id = analyse.json()["record_id"]

    verify = client.get(
        f"/v1/verify/{record_id}",
        headers={"X-API-Key": "demo-key-iota-2026"},
    )
    assert verify.status_code == 200
    payload = verify.json()
    assert payload["verified"] is True
    assert payload["record_id"] == record_id
