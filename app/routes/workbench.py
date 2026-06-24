from __future__ import annotations

import hashlib
import json
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.provenance import compute_provenance_hash
from app.routes.analyse import SUPPORTED_DOMAINS, build_result, detect_language, get_commit_ref, run_core_extraction
from app.store import record_store

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
MANIFEST_PATH = Path("iota_manifest.json")
WORKBENCH_TENANT = "workbench"
SESSIONS: dict[str, dict[str, Any]] = {}


def load_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        raise HTTPException(status_code=500, detail="iota_manifest.json is missing")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def stage(stage_id: str, title: str, summary: str, data: Any, status: str = "complete") -> dict[str, Any]:
    return {"id": stage_id, "title": title, "summary": summary, "data": data, "status": status}


def claim_summary(record: dict[str, Any]) -> dict[str, Any]:
    reserved = {"record_id", "tenant_id", "language", "api_version", "document_hash", "governance_metadata", "neurosymbolic_boundary", "provenance_hash", "template_id", "template_sha256"}
    keys = [key for key in record.keys() if key not in reserved]
    return {"claim_key_count": len(keys), "claim_keys": keys, "preview": {key: record[key] for key in keys[:10]}}


def record_view(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_id": record.get("record_id"),
        "document_hash": record.get("document_hash"),
        "provenance_hash": record.get("provenance_hash"),
        "language": record.get("language"),
        "domain": record.get("domain", "legal_contract"),
        "claims": claim_summary(record),
        "boundary": record.get("neurosymbolic_boundary", {}),
        "governance": record.get("governance_metadata", {}),
    }


def world_model() -> dict[str, Any]:
    records = record_store.list_records(WORKBENCH_TENANT)
    return {
        "authority": "derived from accepted workbench records",
        "storage": record_store.storage_summary(),
        "record_count": len(records),
        "records": [record_view(record) for record in records[-10:]],
    }


def run_visible_pipeline(text: str, filename: str, domain: str) -> dict[str, Any]:
    if domain not in SUPPORTED_DOMAINS:
        raise HTTPException(status_code=400, detail=f"Unsupported domain: {domain}")
    if not text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    normalised = unicodedata.normalize("NFC", text)
    content = normalised.encode("utf-8")
    document_hash = "sha256:" + hashlib.sha256(content).hexdigest()
    timestamp = datetime.now(timezone.utc).isoformat()

    output_data, provenance = run_core_extraction(
        domain=domain,
        document_text=normalised,
        content=content,
        document_hash=document_hash,
        timestamp=timestamp,
        commit_ref=get_commit_ref(),
        filename=filename,
        context="iota_workbench",
    )
    record = build_result(
        output_data,
        provenance,
        tenant_id=WORKBENCH_TENANT,
        language=detect_language(normalised),
        document_hash=document_hash,
        domain=domain,
    )
    record["domain"] = domain
    computed_hash = compute_provenance_hash(record)
    accepted = computed_hash == record.get("provenance_hash")
    if not accepted:
        raise HTTPException(status_code=500, detail="provenance hash mismatch before workbench commit")
    record_store.save(WORKBENCH_TENANT, record["record_id"], record)

    trace = {
        "record_id": record["record_id"],
        "stages": [
            stage("task", "Task", "Text entered the workbench.", {"filename": filename, "domain": domain, "preview": normalised[:600]}),
            stage("evidence", "EvidencePack", "The text was normalised and hashed.", {"document_hash": document_hash, "normalisation": "Unicode NFC"}),
            stage("claims", "ClaimGraph", "The symbolic extractor produced structured claim data.", claim_summary(record)),
            stage("firewall", "Verifier Firewall", "The verifier receives evidence, extracted claims and provenance, not chat text.", {"received": ["document_hash", "output_data", "provenance", "rules"], "excluded": ["chat", "unverified_suggestions"]}, "pass"),
            stage("verify", "Deterministic Verification", "The provenance hash matched before commit.", {"hash_match": accepted, "provenance_hash": record.get("provenance_hash")}, "pass"),
            stage("ledger", "Ledger Commit", "The accepted record was written to the workbench store.", {"tenant_id": WORKBENCH_TENANT, "record_id": record["record_id"]}, "pass"),
            stage("world", "World Model", "The current state is derived from accepted records.", record_view(record), "pass"),
        ],
        "firewall_rule": "The assistant may propose; the verifier must judge; accepted records update state.",
    }
    return {"record": record, "trace": trace, "world_model": world_model()}


def answer(message: str, session: dict[str, Any]) -> dict[str, Any]:
    manifest = load_manifest()
    lower = message.lower()
    if "trust" in lower or "authority" in lower or "believe" in lower:
        return {"answer": "Authority comes from: " + ", ".join(manifest["authority"]) + ".", "detail": {"authority": manifest["authority"], "not_authority": manifest["not_authority"]}}
    if "verifier" in lower or "firewall" in lower:
        return {"answer": "The verifier firewall keeps chat and unverified suggestions outside judgment. Run a document to see exact stage data.", "detail": session.get("trace", {}).get("stages", [])}
    if "world" in lower or "state" in lower:
        return {"answer": "The world model is derived from accepted workbench records.", "detail": world_model()}
    if "pipeline" in lower or "trace" in lower:
        return {"answer": "The pipeline is: " + " -> ".join(manifest["core_pipeline"]) + ".", "detail": session.get("trace") or manifest["core_pipeline"]}
    if "what" in lower or "built" in lower or "purpose" in lower:
        return {"answer": manifest["purpose"] + " " + manifest["operating_sentence"], "detail": manifest}
    return {"answer": "I can explain the purpose, run the pipeline, show the verifier firewall, show world state, or inspect a JSON report from its fields only.", "detail": {"first_questions": manifest["first_questions"]}}


def report_summary(report: dict[str, Any]) -> dict[str, Any]:
    comparisons = report.get("comparisons", []) if isinstance(report.get("comparisons", []), list) else []
    wins = [item for item in comparisons if item.get("meaningful_true_prior_state_win")]
    return {
        "answer": f"Verdict: {report.get('prior_state_verdict', report.get('verdict', 'unknown'))}. Reason: {report.get('verdict_reason', 'not provided')}. Truncation: {report.get('any_truncation', 'not provided')}. Meaningful true Prior State wins: {len(wins)}/{len(comparisons)}.",
        "verdict": report.get("prior_state_verdict", report.get("verdict", "unknown")),
        "verdict_reason": report.get("verdict_reason"),
        "any_truncation": report.get("any_truncation"),
        "comparison_count": len(comparisons),
        "meaningful_true_prior_state_wins": len(wins),
    }


@router.get("/workbench", response_class=HTMLResponse, include_in_schema=False)
async def workbench_page(request: Request):
    return templates.TemplateResponse(request, "workbench.html", {"manifest": load_manifest(), "world_model": world_model()})


@router.get("/v1/workbench/manifest")
async def manifest_endpoint():
    return load_manifest()


@router.get("/v1/workbench/world-model")
async def world_model_endpoint():
    return world_model()


@router.post("/v1/workbench/chat")
async def chat_endpoint(request: Request):
    payload = await request.json()
    message = str(payload.get("message", "")).strip()
    session_id = str(payload.get("session_id") or uuid.uuid4())
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    session = SESSIONS.setdefault(session_id, {})
    reply = answer(message, session)
    return {"session_id": session_id, **reply, "trace": session.get("trace")}


@router.post("/v1/workbench/run")
async def run_endpoint(request: Request):
    payload = await request.json()
    session_id = str(payload.get("session_id") or uuid.uuid4())
    run = run_visible_pipeline(str(payload.get("text", "")), str(payload.get("filename") or "workbench.txt"), str(payload.get("domain") or "legal_contract"))
    SESSIONS.setdefault(session_id, {})["trace"] = run["trace"]
    return {"session_id": session_id, **run}


@router.post("/v1/workbench/report")
async def report_endpoint(request: Request):
    payload = await request.json()
    raw = payload.get("report")
    if isinstance(raw, str):
        try:
            report = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid JSON report: {exc.msg}") from exc
    elif isinstance(raw, dict):
        report = raw
    else:
        raise HTTPException(status_code=400, detail="report must be a JSON object or JSON string")
    return report_summary(report)


@router.get("/v1/workbench/self-test")
async def self_test_endpoint():
    manifest = load_manifest()
    checks = {"manifest_loaded": manifest.get("name") == "IOTA VERBUM WORKBENCH", "world_model_available": "records" in world_model()}
    return JSONResponse({"ok": all(checks.values()), "checks": checks})
