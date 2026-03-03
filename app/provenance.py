from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any


NON_DETERMINISTIC_PATHS = (
    ("record_id",),
    ("provenance_hash",),
    ("provenance_meta", "timestamp"),
)


def canonicalize_json_bytes(data: Any) -> bytes:
    text = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return text.encode("utf-8")


def _drop_path(payload: dict[str, Any], path: tuple[str, ...]) -> None:
    node: Any = payload
    for key in path[:-1]:
        if not isinstance(node, dict) or key not in node:
            return
        node = node[key]
    if isinstance(node, dict):
        node.pop(path[-1], None)


def normalized_provenance_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(payload)
    for path in NON_DETERMINISTIC_PATHS:
        _drop_path(normalized, path)
    return normalized


def canonicalize_provenance_bytes(payload: dict[str, Any]) -> bytes:
    return canonicalize_json_bytes(normalized_provenance_payload(payload))


def compute_provenance_hash(payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(canonicalize_provenance_bytes(payload)).hexdigest()
    return f"sha256:{digest}"
