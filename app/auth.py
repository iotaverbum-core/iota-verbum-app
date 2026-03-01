import os
from pathlib import Path

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def _raw_api_keys() -> str:
    env_value = os.getenv("API_KEYS")
    if env_value:
        return env_value
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8-sig").splitlines():
            if line.startswith("API_KEYS="):
                return line.split("=", 1)[1].strip()
    return "demo-key-iota-2026:demo"


def _load_keys() -> dict:
    """Load API keys from environment. Format: key1:tenant1,key2:tenant2."""
    raw = _raw_api_keys()
    result = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" in pair:
            key, tenant = pair.split(":", 1)
            result[key.strip()] = {"tenant_id": tenant.strip()}
    return result


API_KEYS: dict = _load_keys()


def get_tenant(api_key: str = Security(api_key_header)) -> dict:
    """Validate API key and return tenant context. Runs before rate limiting."""
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include X-API-Key header.",
        )
    if api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    return API_KEYS[api_key]
