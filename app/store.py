from __future__ import annotations

from collections import defaultdict
from typing import Any


class RecordStore:
    """In-memory provenance record store scoped by tenant_id."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        self._verify_counts: dict[str, dict[str, int]] = defaultdict(dict)

    def save(self, tenant_id: str, record_id: str, record: dict[str, Any]) -> dict[str, Any]:
        stored = dict(record)
        self._store[tenant_id][record_id] = stored
        self._verify_counts[tenant_id].setdefault(record_id, 0)
        return dict(stored)

    def get(self, tenant_id: str, record_id: str) -> dict[str, Any] | None:
        record = self._store.get(tenant_id, {}).get(record_id)
        if record is None:
            return None
        return dict(record)

    def find(self, record_id: str) -> tuple[str, dict[str, Any]] | None:
        for tenant_id, tenant_records in self._store.items():
            record = tenant_records.get(record_id)
            if record is not None:
                return tenant_id, dict(record)
        return None

    def list_tenant(self, tenant_id: str) -> list[str]:
        return sorted(self._store.get(tenant_id, {}).keys())

    def list_records(self, tenant_id: str) -> list[dict[str, Any]]:
        records = self._store.get(tenant_id, {})
        return [dict(records[record_id]) for record_id in sorted(records)]

    def verify_count(self, tenant_id: str, record_id: str) -> int:
        return self._verify_counts.get(tenant_id, {}).get(record_id, 0)

    def increment_verify_count(self, tenant_id: str, record_id: str) -> int:
        current = self._verify_counts[tenant_id].get(record_id, 0) + 1
        self._verify_counts[tenant_id][record_id] = current
        return current

    def storage_summary(self) -> dict[str, Any]:
        record_total = sum(len(records) for records in self._store.values())
        return {
            "mode": "in_memory_ephemeral",
            "tenant_count": len(self._store),
            "record_count": record_total,
        }

    def exists(self, tenant_id: str, record_id: str) -> bool:
        return record_id in self._store.get(tenant_id, {})

    def delete(self, tenant_id: str, record_id: str) -> bool:
        tenant_records = self._store.get(tenant_id)
        if not tenant_records or record_id not in tenant_records:
            return False
        del tenant_records[record_id]
        self._verify_counts.get(tenant_id, {}).pop(record_id, None)
        if not tenant_records:
            self._store.pop(tenant_id, None)
            self._verify_counts.pop(tenant_id, None)
        return True

    def clear_tenant(self, tenant_id: str) -> None:
        self._store.pop(tenant_id, None)
        self._verify_counts.pop(tenant_id, None)

    def clear(self) -> None:
        self._store.clear()
        self._verify_counts.clear()


record_store = RecordStore()
