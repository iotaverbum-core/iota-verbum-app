from __future__ import annotations

from collections import defaultdict
from typing import Any


class RecordStore:
    """In-memory provenance record store scoped by tenant_id."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)

    def save(self, tenant_id: str, record_id: str, record: dict[str, Any]) -> dict[str, Any]:
        stored = dict(record)
        self._store[tenant_id][record_id] = stored
        return dict(stored)

    def get(self, tenant_id: str, record_id: str) -> dict[str, Any] | None:
        record = self._store.get(tenant_id, {}).get(record_id)
        if record is None:
            return None
        return dict(record)

    def list_tenant(self, tenant_id: str) -> list[str]:
        return sorted(self._store.get(tenant_id, {}).keys())

    def list_records(self, tenant_id: str) -> list[dict[str, Any]]:
        records = self._store.get(tenant_id, {})
        return [dict(records[record_id]) for record_id in sorted(records)]

    def exists(self, tenant_id: str, record_id: str) -> bool:
        return record_id in self._store.get(tenant_id, {})

    def delete(self, tenant_id: str, record_id: str) -> bool:
        tenant_records = self._store.get(tenant_id)
        if not tenant_records or record_id not in tenant_records:
            return False
        del tenant_records[record_id]
        if not tenant_records:
            self._store.pop(tenant_id, None)
        return True

    def clear_tenant(self, tenant_id: str) -> None:
        self._store.pop(tenant_id, None)

    def clear(self) -> None:
        self._store.clear()


record_store = RecordStore()
