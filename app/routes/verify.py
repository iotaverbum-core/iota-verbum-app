import hashlib
import json
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Request, Security, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth import api_key_header, get_tenant
from app.provenance import compute_provenance_hash
from app.store import record_store

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "").lower()
    return "text/html" in accept and "application/json" not in accept


def _verification_response(record_id: str, tenant_id: str, record: dict, *, file_bytes: bytes | None = None, provided_payload: dict | None = None) -> dict:
    verified_count = record_store.increment_verify_count(tenant_id, record_id)
    payload_hash_match = True
    payload_hash = record.get("provenance_hash")
    document_hash_match = True
    computed_document_hash = None

    if provided_payload is not None:
        payload_hash = compute_provenance_hash(provided_payload)
        payload_hash_match = payload_hash == record.get("provenance_hash")

    if file_bytes is not None:
        computed_document_hash = "sha256:" + hashlib.sha256(file_bytes).hexdigest()
        document_hash_match = computed_document_hash == record.get("document_hash")

    return {
        "record_id": record_id,
        "tenant_id": tenant_id,
        "verified": payload_hash_match and document_hash_match,
        "hash_match": payload_hash_match,
        "document_hash_match": document_hash_match,
        "computed_document_hash": computed_document_hash,
        "computed_provenance_hash": payload_hash,
        "verified_count": verified_count,
        "record": record,
    }


@router.get("/verify", response_class=HTMLResponse, include_in_schema=False)
async def verify_landing(request: Request):
    return templates.TemplateResponse(request, "verify.html", {"record_id": ""})


@router.post("/verify", include_in_schema=False)
async def verify_submission(
    request: Request,
    record_id: str = Form(""),
    provenance_json: str = Form(""),
    file: UploadFile | None = File(None),
):
    if not record_id.strip():
        raise HTTPException(status_code=400, detail="record_id is required.")

    found = record_store.find(record_id.strip())
    if not found:
        raise HTTPException(status_code=404, detail=f"Record {record_id.strip()} not found.")

    tenant_id, record = found
    parsed_payload = None
    if provenance_json.strip():
        try:
            parsed_payload = json.loads(provenance_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid provenance JSON: {exc.msg}") from exc

    file_bytes = await file.read() if file else None
    payload = _verification_response(
        record_id.strip(),
        tenant_id,
        record,
        file_bytes=file_bytes,
        provided_payload=parsed_payload,
    )

    if _wants_html(request):
        return templates.TemplateResponse(request, "verify.html", {"record_id": record_id.strip()})
    return payload


@router.get(
    "/verify/{record_id}",
    summary="Verify a provenance record",
    description="Retrieve a stored provenance record by ID or render the standalone verification page.",
)
async def verify(
    request: Request,
    record_id: str,
    api_key: Annotated[str | None, Security(api_key_header)] = None,
):
    if _wants_html(request) and not api_key:
        return templates.TemplateResponse(
            request,
            "verify.html",
            {"record_id": record_id},
        )

    if api_key:
        tenant = get_tenant(api_key)
        record = record_store.get(tenant["tenant_id"], record_id)
        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"Record {record_id} not found for this tenant.",
            )
        tenant_id = tenant["tenant_id"]
    else:
        found = record_store.find(record_id)
        if not found:
            raise HTTPException(status_code=404, detail=f"Record {record_id} not found.")
        tenant_id, record = found

    if _wants_html(request):
        return templates.TemplateResponse(
            request,
            "verify.html",
            {"record_id": record_id},
        )

    return _verification_response(record_id, tenant_id, record)
