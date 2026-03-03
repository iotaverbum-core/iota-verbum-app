# iota-verbum-app

Deterministic legal document analysis with reproducible provenance verification.

## What it does

- Browser landing page and demo UI
- Authenticated analysis API at `/v1/analyse`
- Verification UI at `/v1/verify`
- Verification JSON at `/v1/verify/{record_id}`
- Tenant-scoped record retrieval at `/v1/records/{record_id}`
- Offline provenance verification via `scripts/verify_provenance.py`

## Storage model

Records are stored in memory for the lifetime of the current app process.

- No database is configured in this repo
- Records are ephemeral and disappear on restart
- `/health` and `/v1/status` expose the storage mode

## Inputs

The current analysis path supports UTF-8 text files (`.txt`) only.

## Environment variables

- `API_KEYS`
- `PORT`
- `WORK_DIR`
- `IV_WORK_DIR`

## Local run

```bash
python -m compileall .
pytest -q
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Offline verification

```bash
python scripts/verify_provenance.py --provenance examples/sample_provenance.json --file tests/fixtures/sample_contract.txt
```

## API overview

- `GET /`
- `GET /health`
- `GET /v1/status`
- `POST /v1/analyse`
- `GET /v1/demo`
- `POST /v1/demo/result`
- `GET /v1/verify`
- `GET /v1/verify/{record_id}`
- `POST /v1/verify`
- `GET /v1/records/{record_id}`
- `GET /v1/domains`

## Governance note

Governance mapping aids workflows and is not legal advice.
