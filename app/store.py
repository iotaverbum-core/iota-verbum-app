from collections import defaultdict
from typing import Optional


class RecordStore:
    """In-memory provenance record store scoped by tenant_id."""

    def __init__(self):
        self._store: dict[str, dict[str, dict]] = defaultdict(dict)

    def save(self, tenant_id: str, record_id: str, record: dict) -> None:
        self._store[tenant_id][record_id] = record

    def get(self, tenant_id: str, record_id: str) -> Optional[dict]:
        return self._store.get(tenant_id, {}).get(record_id)

    def list_tenant(self, tenant_id: str) -> list[str]:
        return sorted(self._store.get(tenant_id, {}).keys())


record_store = RecordStore()
