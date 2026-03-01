import pytest
from fastapi import HTTPException

from app.auth import API_KEYS, get_tenant


def test_valid_demo_api_key_returns_demo_tenant():
    assert API_KEYS["demo-key-iota-2026"]["tenant_id"] == "demo"


def test_valid_navrina_api_key_returns_navrina_tenant(monkeypatch):
    monkeypatch.setitem(API_KEYS, "navrina-key-iota-2026", {"tenant_id": "navrina"})
    assert get_tenant("navrina-key-iota-2026")["tenant_id"] == "navrina"


def test_invalid_key_raises_401():
    with pytest.raises(HTTPException) as exc:
        get_tenant("bad-key")
    assert exc.value.status_code == 401


def test_missing_key_raises_401():
    with pytest.raises(HTTPException) as exc:
        get_tenant(None)
    assert exc.value.status_code == 401


def test_two_valid_keys_return_different_tenants(monkeypatch):
    monkeypatch.setitem(API_KEYS, "other-key", {"tenant_id": "other"})
    assert get_tenant("demo-key-iota-2026") != get_tenant("other-key")
