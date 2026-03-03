import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_contract.txt"


def _sample_upload():
    return {
        "file": ("sample_contract.txt", FIXTURE_PATH.read_bytes(), "text/plain"),
    }


def test_post_analyse_returns_full_provenance_record():
    response = client.post(
        "/v1/analyse",
        headers={"X-API-Key": "demo-key-iota-2026"},
        files=_sample_upload(),
        data={"domain": "legal_contract", "context": "unit-test"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant_id"] == "demo"
    assert payload["language"]
    assert payload["governance_metadata"]["audit_ready"] is True
    assert payload["governance_metadata"]["audit_support"] is True
    assert payload["neurosymbolic_boundary"]["neural_components_used"] == []
    assert payload["document_hash"].startswith("sha256:")
    assert payload["provenance_hash"].startswith("sha256:")
    assert payload["template_id"].startswith("legal_contract/")


def test_post_analyse_no_api_key_returns_401():
    response = client.post("/v1/analyse", files=_sample_upload())
    assert response.status_code == 401


def test_post_analyse_invalid_api_key_returns_401():
    response = client.post(
        "/v1/analyse",
        headers={"X-API-Key": "bad-key"},
        files=_sample_upload(),
    )
    assert response.status_code == 401


def test_post_analyse_unsupported_domain_returns_400():
    response = client.post(
        "/v1/analyse",
        headers={"X-API-Key": "demo-key-iota-2026"},
        files=_sample_upload(),
        data={"domain": "unsupported"},
    )
    assert response.status_code == 400


def test_identical_requests_share_same_provenance_hash():
    first = client.post(
        "/v1/analyse",
        headers={"X-API-Key": "demo-key-iota-2026"},
        files=_sample_upload(),
        data={"domain": "legal_contract"},
    )
    second = client.post(
        "/v1/analyse",
        headers={"X-API-Key": "demo-key-iota-2026"},
        files=_sample_upload(),
        data={"domain": "legal_contract"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["provenance_hash"] == second.json()["provenance_hash"]


def test_demo_page_renders_result_and_persists_record():
    page = client.get("/v1/demo")
    assert page.status_code == 200

    result = client.post(
        "/v1/demo/result",
        files=_sample_upload(),
        data={"domain": "legal_contract"},
    )
    assert result.status_code == 200
    assert "Provenance Report" in result.text
    match = re.search(r'<script id="server-result-data" type="application/json">(.*?)</script>', result.text, re.S)
    assert match
    payload = json.loads(match.group(1))
    verify = client.get(f"/v1/verify/{payload['record_id']}", headers={"Accept": "application/json"})
    assert verify.status_code == 200


def test_analyse_uses_configured_work_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("IV_WORK_DIR", str(tmp_path / "iv-work"))
    response = client.post(
        "/v1/analyse",
        headers={"X-API-Key": "demo-key-iota-2026"},
        files=_sample_upload(),
        data={"domain": "legal_contract"},
    )
    assert response.status_code == 200
    work_root = tmp_path / "iv-work"
    assert work_root.exists()
    assert list(work_root.iterdir()) == []


def test_analyse_rejects_non_text_upload():
    response = client.post(
        "/v1/analyse",
        headers={"X-API-Key": "demo-key-iota-2026"},
        files={"file": ("sample_contract.pdf", b"%PDF-1.4", "application/pdf")},
        data={"domain": "legal_contract"},
    )
    assert response.status_code == 400
    assert "txt" in response.json()["detail"].lower()
