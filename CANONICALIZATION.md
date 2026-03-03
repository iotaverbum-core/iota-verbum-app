# Canonical Provenance Hashing

`provenance_hash` in this app is computed from canonical JSON bytes produced by `app.provenance`.

## Rules

1. Serialize JSON using UTF-8 bytes.
2. Sort object keys lexicographically.
3. Use no extra whitespace.
4. Use separators `,` and `:` only.
5. Encode strings as standard JSON strings.
6. Encode booleans as `true` / `false`.
7. Encode null as `null`.
8. Reject non-JSON values such as `NaN` and `Infinity`.

## Non-deterministic fields

These fields are excluded before hashing:

- `record_id`
- `provenance_meta.timestamp`

They remain present in stored payloads for retrieval, but they do not affect `provenance_hash`.

## Hash function

- Canonical bytes are hashed with SHA-256.
- `provenance_hash` is stored as `sha256:<hex_digest>`.

## Document hash

- `document_hash` is always the SHA-256 digest of the raw uploaded file bytes.
- It is stored as `sha256:<hex_digest>`.

## Stability expectation

If two requests use byte-identical source files and the same deterministic extraction path, the canonical provenance bytes and resulting `provenance_hash` must match exactly.
