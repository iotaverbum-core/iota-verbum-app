# API

## Routes

- `GET /` returns HTML for browsers and `{"status":"ok"}` for API-style requests
- `GET /health` returns system health and storage mode
- `GET /v1/status` returns operational status and storage summary
- `POST /v1/analyse` accepts an authenticated `.txt` upload and returns provenance JSON
- `GET /v1/demo` serves the demo page
- `POST /v1/demo/result` serves the rendered provenance result page
- `GET /v1/verify` serves the verification landing page
- `GET /v1/verify/{record_id}` verifies an existing record as HTML or JSON
- `POST /v1/verify` compares a stored record against optional provenance JSON and/or a local file
- `GET /v1/records/{record_id}` returns stored provenance JSON for the authenticated tenant
- `GET /v1/domains` returns supported domain metadata

## Auth

`/v1/analyse` and `/v1/records/{record_id}` require `X-API-Key`.

`/v1/verify/{record_id}` supports public browser access and tenant-scoped JSON access when an API key is supplied.

## Rate limiting

`/v1/analyse` is protected by `slowapi` at `100/hour` per client IP.

## Storage

Stored records are kept in memory for the current app process only.

## Provenance hashing

See `CANONICALIZATION.md` for the exact provenance hash rules.
