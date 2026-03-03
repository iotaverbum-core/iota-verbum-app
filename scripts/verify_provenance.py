from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.provenance import compute_provenance_hash


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify a provenance payload offline.")
    parser.add_argument("--provenance", required=True, help="Path to provenance JSON.")
    parser.add_argument("--file", help="Optional source file to recompute document_hash.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    provenance_path = Path(args.provenance)
    payload = json.loads(provenance_path.read_text(encoding="utf-8"))

    computed_provenance_hash = compute_provenance_hash(payload)
    recorded_provenance_hash = payload.get("provenance_hash")

    matched = True
    reasons: list[str] = []

    if computed_provenance_hash != recorded_provenance_hash:
        matched = False
        reasons.append(
            f"provenance_hash expected {recorded_provenance_hash} computed {computed_provenance_hash}"
        )

    if args.file:
        file_path = Path(args.file)
        computed_document_hash = "sha256:" + hashlib.sha256(file_path.read_bytes()).hexdigest()
        recorded_document_hash = payload.get("document_hash")
        if computed_document_hash != recorded_document_hash:
            matched = False
            reasons.append(
                f"document_hash expected {recorded_document_hash} computed {computed_document_hash}"
            )

    if matched:
        print("MATCH")
        print(f"provenance_hash={computed_provenance_hash}")
        if args.file:
            print(f"document_hash={payload.get('document_hash')}")
        return 0

    print("MISMATCH")
    for reason in reasons:
        print(reason)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
