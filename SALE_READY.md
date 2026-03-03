# Sale Ready Checklist

- [x] Browser landing page at `/` and JSON status for API-style requests
- [x] Health endpoints at `/health` and `/v1/status`
- [x] Authenticated analysis API at `/v1/analyse`
- [x] Demo UI at `/v1/demo`
- [x] Rendered result page at `/v1/demo/result`
- [x] Verification landing page at `/v1/verify`
- [x] Verification detail route at `/v1/verify/{record_id}`
- [x] Tenant-scoped records endpoint at `/v1/records/{record_id}`
- [x] Shared canonical provenance hashing logic in app code and CLI
- [x] Offline verifier at `scripts/verify_provenance.py`
- [x] Example provenance payload under `examples/`
- [x] Work directory abstraction using `IV_WORK_DIR` / `WORK_DIR`
- [x] Cross-platform temp output under a writable app work directory
- [x] Regression tests for work-dir usage, records retrieval, and provenance verification
- [x] Static assets served from `/static` with cache headers
- [x] UTF-8 assets and templates for Railway / Linux deploys
- [x] TXT-only demo/API upload messaging aligned with backend behavior
- [x] Governance disclaimer present in UI/docs
- [x] Records storage explicitly documented as in-memory and ephemeral

## Acceptance Commands

- `python -m compileall .`
- `pytest -q`
- `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- `python scripts/verify_provenance.py --provenance examples/sample_provenance.json --file tests/fixtures/sample_contract.txt`
