import hashlib
import importlib.metadata
import json
import tempfile
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from core import attestation
from core.pipeline import DeterministicPipeline
from deterministic_ai import DOMAIN_REGISTRY
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from langdetect import LangDetectException, detect

from app.auth import API_KEYS, get_tenant
from app.governance import GOVERNANCE_MAP
from app.limiter import limiter
from app.store import record_store

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
SUPPORTED_DOMAINS = {"legal_contract"}


def get_commit_ref() -> str:
    try:
        return importlib.metadata.version("iota-verbum-core")
    except Exception:
        return "v0.2.1-neurosymbolic"


def detect_language(text: str) -> str:
    try:
        return detect(text)
    except LangDetectException:
        return "unknown"


def build_boundary(domain: str) -> dict:
    return {
        "symbolic_components_used": [
            f"{domain}_extractor_v1",
            "schema_validator_v1",
            "governance_mapper_v1",
        ],
        "neural_components_used": [],
        "neural_override_count": 0,
        "symbolic_confidence": "high",
        "boundary_version": "1.0",
    }


def compute_provenance_hash(result: dict) -> str:
    canonical = dict(result)
    canonical.pop("record_id", None)
    provenance_meta = dict(canonical.get("provenance_meta", {}))
    provenance_meta.pop("timestamp", None)
    canonical["provenance_meta"] = provenance_meta
    payload = attestation.canonicalize_json(canonical)
    return "sha256:" + attestation.compute_sha256(payload)


def run_core_extraction(
    domain: str,
    document_text: str,
    content: bytes,
    document_hash: str,
    timestamp: str,
    commit_ref: str,
    filename: str,
    context: str,
) -> tuple[dict, dict]:
    domain_config = DOMAIN_REGISTRY[domain]
    pipeline = DeterministicPipeline(
        domain,
        domain_config["extractor"],
        domain_config["templates"],
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        result = pipeline.process(
            input_ref=Path(filename or "upload.txt").stem or "upload",
            input_data=document_text,
            input_bytes=content,
            context={
                "filename": filename,
                "source": "api_v1",
                "context": context,
            },
            output_dir=Path(tmp_dir),
            input_meta={
                "input_file": filename,
                "document_hash": document_hash,
            },
            provenance_meta={
                "timestamp": timestamp,
                "commit_ref": commit_ref,
            },
        )
    return result["output_data"], result["provenance"]


@router.post(
    "/analyse",
    summary="Analyse a contract document",
    description="Upload a plain-text contract. Returns structured extraction with full neurosymbolic provenance record.",
)
@limiter.limit("100/hour")
async def analyse(
    request: Request,
    tenant: Annotated[dict, Depends(get_tenant)],
    file: UploadFile = File(..., description="Plain text contract (.txt)"),
    domain: str = Form("legal_contract", description="Extraction domain: legal_contract"),
    context: str = Form("", description="Optional context string"),
):
    if domain not in SUPPORTED_DOMAINS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported domain: {domain}. Supported: {sorted(SUPPORTED_DOMAINS)}",
        )

    content = await file.read()
    document_hash = "sha256:" + hashlib.sha256(content).hexdigest()

    try:
        document_text = content.decode("utf-8")
    except UnicodeDecodeError:
        document_text = content.decode("latin-1")

    language = detect_language(document_text)
    document_text = unicodedata.normalize("NFC", document_text)
    timestamp = datetime.now(timezone.utc).isoformat()
    commit_ref = get_commit_ref()
    tenant_id = tenant["tenant_id"]

    output_data, provenance = run_core_extraction(
        domain=domain,
        document_text=document_text,
        content=content,
        document_hash=document_hash,
        timestamp=timestamp,
        commit_ref=commit_ref,
        filename=file.filename or "upload.txt",
        context=context,
    )

    result = {
        **output_data,
        **provenance,
        "record_id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "language": language,
        "api_version": "v1",
        "document_hash": document_hash,
        "governance_metadata": GOVERNANCE_MAP[domain],
        "neurosymbolic_boundary": build_boundary(domain),
    }
    result["provenance_hash"] = compute_provenance_hash(result)

    record_store.save(tenant_id, result["record_id"], result)
    return result


@router.get("/demo", response_class=HTMLResponse, include_in_schema=False)
async def demo_page(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@router.post("/demo/result", response_class=HTMLResponse, include_in_schema=False)
async def demo_result(
    request: Request,
    file: UploadFile = File(...),
    domain: str = Form("legal_contract"),
):
    tenant = API_KEYS.get("demo-key-iota-2026", {"tenant_id": "demo"})
    if domain not in SUPPORTED_DOMAINS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported domain: {domain}. Supported: {sorted(SUPPORTED_DOMAINS)}",
        )

    content = await file.read()
    document_hash = "sha256:" + hashlib.sha256(content).hexdigest()
    try:
        document_text = content.decode("utf-8")
    except UnicodeDecodeError:
        document_text = content.decode("latin-1")

    language = detect_language(document_text)
    document_text = unicodedata.normalize("NFC", document_text)
    timestamp = datetime.now(timezone.utc).isoformat()
    commit_ref = get_commit_ref()

    output_data, provenance = run_core_extraction(
        domain=domain,
        document_text=document_text,
        content=content,
        document_hash=document_hash,
        timestamp=timestamp,
        commit_ref=commit_ref,
        filename=file.filename or "upload.txt",
        context="",
    )

    result = {
        **output_data,
        **provenance,
        "record_id": str(uuid.uuid4()),
        "tenant_id": tenant["tenant_id"],
        "language": language,
        "api_version": "v1",
        "document_hash": document_hash,
        "governance_metadata": GOVERNANCE_MAP[domain],
        "neurosymbolic_boundary": build_boundary(domain),
    }
    result["provenance_hash"] = compute_provenance_hash(result)

    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "result": result,
            "domain": domain,
            "filename": file.filename,
            "result_json": json.dumps(result, indent=2, sort_keys=True),
        },
    )



