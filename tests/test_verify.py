import json
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
    assert payload["verified_count"] >= 1


def test_verify_returns_public_json_without_api_key():
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
        headers={"Accept": "application/json"},
    )
    assert verify.status_code == 200
    payload = verify.json()
    assert payload["verified"] is True
    assert payload["record_id"] == record_id


def test_verify_landing_page_renders():
    response = client.get("/v1/verify", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert "Verify a provenance record" in response.text


def test_verify_html_page_renders_without_api_key():
    response = client.get(
        "/v1/verify/example-record",
        headers={"Accept": "text/html"},
    )
    assert response.status_code == 200
    assert "Verify a provenance record" in response.text


def test_verify_post_detects_tampered_provenance():
    analyse = client.post(
        "/v1/analyse",
        headers={"X-API-Key": "demo-key-iota-2026"},
        files=_sample_upload(),
        data={"domain": "legal_contract"},
    )
    assert analyse.status_code == 200
    record = analyse.json()
    tampered = dict(record)
    tampered["language"] = "fr"

    response = client.post(
        "/v1/verify",
        data={
            "record_id": record["record_id"],
            "provenance_json": json.dumps(tampered),
        },
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 200
    assert response.json()["verified"] is False
