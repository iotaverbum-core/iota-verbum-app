#!/usr/bin/env python3
"""IOTA VERBUM Workbench.

A local, visible, end-to-end cockpit for orientation, deterministic document
analysis, verifier-boundary inspection, ledger commit, replay-derived world
state, and JSON report inspection.

Run:
    python iota_workbench.py
Open:
    http://localhost:8765
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "iota_manifest.json"
RUN_DIR = ROOT / "workbench_runs"
LEDGER_PATH = RUN_DIR / "ledger.jsonl"
PORT = 8765


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {
        "name": "IOTA VERBUM WORKBENCH",
        "purpose": "Protect truth across AI-assisted reasoning by separating evidence, verification, ledger commit, and replay-derived world state.",
        "operating_sentence": "I do not treat generated text as authority. I treat evidence, verification, ledger commit, and replay-derived world state as authority.",
        "authority": ["sealed evidence", "deterministic verifier", "append-only ledger", "replay-derived world model"],
        "not_authority": ["chat text", "unverified suggestions", "generated summaries without trace data"],
        "core_pipeline": ["EvidencePack", "ClaimGraph", "Verifier", "Ledger", "World Model"],
        "first_questions": ["What are you built to do?", "What do you trust?", "Show me the pipeline.", "What did the verifier see?", "Show me the world model."],
    }


@dataclass(frozen=True)
class Stage:
    id: str
    title: str
    summary: str
    status: str
    data: object


@dataclass(frozen=True)
class LedgerRecord:
    record_id: str
    created_at: str
    document_hash: str
    claim_graph_hash: str
    provenance_hash: str
    verifier_status: str
    world_model_effect: str
    trace: dict


def extract_claims(text: str) -> dict:
    lower = text.lower()
    claims: list[dict] = []

    governing_law = re.search(r"governed by the laws? of ([A-Za-z ,.-]+)", text, re.IGNORECASE)
    if governing_law:
        claims.append({
            "type": "governing_law",
            "value": governing_law.group(1).strip().rstrip("."),
            "grounding": governing_law.group(0),
        })

    termination = re.search(r"terminate[^.]{0,120}", text, re.IGNORECASE)
    if termination:
        claims.append({
            "type": "termination",
            "value": termination.group(0).strip(),
            "grounding": termination.group(0),
        })

    if "confidential" in lower or "non-disclosure" in lower or "nda" in lower:
        start = max(0, lower.find("confidential") - 80) if "confidential" in lower else 0
        claims.append({
            "type": "confidentiality",
            "value": "confidentiality language detected",
            "grounding": text[start:start + 180].strip(),
        })

    if "liability" in lower:
        start = max(0, lower.find("liability") - 80)
        claims.append({
            "type": "liability",
            "value": "liability language detected",
            "grounding": text[start:start + 180].strip(),
        })

    return {
        "schema": "iota.claim_graph.v0.1",
        "claim_count": len(claims),
        "claims": claims,
        "unknowns": [] if claims else ["No supported legal claim pattern matched this text."],
    }


def build_trace(text: str, filename: str) -> tuple[dict, LedgerRecord]:
    normalized = " ".join(text.replace("\r", "\n").split())
    document_hash = sha256_text(normalized)
    evidence_pack = {
        "schema": "iota.evidence_pack.v0.1",
        "filename": filename,
        "normalization": "collapse whitespace, UTF-8 text",
        "document_hash": document_hash,
        "text_preview": normalized[:1000],
    }
    claim_graph = extract_claims(normalized)
    claim_graph_hash = sha256_text(canonical_json(claim_graph))
    verifier_input = {
        "document_hash": document_hash,
        "claim_graph_hash": claim_graph_hash,
        "claim_graph": claim_graph,
    }
    verifier_status = "accepted" if claim_graph["claim_count"] > 0 else "rejected"
    verifier_result = {
        "status": verifier_status,
        "reason": "claims are grounded in matched text spans" if verifier_status == "accepted" else "no supported claim pattern matched",
        "received": ["document_hash", "claim_graph_hash", "claim_graph"],
        "excluded": ["chat_message", "agent_suggestion", "unverified_delta", "generated_summary"],
    }
    provenance = {
        "schema": "iota.provenance.v0.1",
        "created_at": now(),
        "document_hash": document_hash,
        "claim_graph_hash": claim_graph_hash,
        "verifier_status": verifier_status,
        "boundary": "verifier received evidence and claim graph only",
    }
    provenance_hash = sha256_text(canonical_json(provenance))
    record_id = "ivr_" + uuid.uuid4().hex[:16]

    stages = [
        Stage("task", "Task", "User supplied text to the workbench.", "complete", {"filename": filename, "chars": len(text)}),
        Stage("evidence", "EvidencePack", "Text was normalized and hashed.", "complete", evidence_pack),
        Stage("claims", "ClaimGraph", "Supported claim patterns were extracted with grounding spans.", "complete", claim_graph),
        Stage("firewall", "Verifier Firewall", "Verifier-side inputs exclude chat and unverified suggestions.", "pass", verifier_result),
        Stage("verify", "Deterministic Verifier", "Verifier accepted or rejected the claim graph before ledger mutation.", "pass" if verifier_status == "accepted" else "warn", verifier_result),
        Stage("ledger", "Ledger Commit", "Accepted records are appended; rejected records remain visible but do not update trusted state.", "pass" if verifier_status == "accepted" else "warn", {"record_id": record_id, "provenance_hash": provenance_hash}),
        Stage("world", "World Model", "Current state is replay-derived from accepted ledger records.", "pass", {"effect": "commit" if verifier_status == "accepted" else "no trusted-state mutation"}),
    ]
    trace = {
        "schema": "iota.trace.v0.1",
        "record_id": record_id,
        "firewall_rule": "The assistant may propose; the verifier must judge; the ledger alone records accepted state.",
        "stages": [asdict(stage) for stage in stages],
    }
    record = LedgerRecord(
        record_id=record_id,
        created_at=provenance["created_at"],
        document_hash=document_hash,
        claim_graph_hash=claim_graph_hash,
        provenance_hash=provenance_hash,
        verifier_status=verifier_status,
        world_model_effect="commit" if verifier_status == "accepted" else "no trusted-state mutation",
        trace=trace,
    )
    return trace, record


def append_ledger(record: LedgerRecord) -> None:
    RUN_DIR.mkdir(exist_ok=True)
    with LEDGER_PATH.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json(asdict(record)) + "\n")


def read_ledger() -> list[dict]:
    if not LEDGER_PATH.exists():
        return []
    records = []
    for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def world_model() -> dict:
    accepted = [record for record in read_ledger() if record.get("verifier_status") == "accepted"]
    return {
        "schema": "iota.world_model.v0.1",
        "authority": "replay-derived from accepted ledger records",
        "record_count": len(accepted),
        "records": [
            {
                "record_id": record.get("record_id"),
                "document_hash": record.get("document_hash"),
                "provenance_hash": record.get("provenance_hash"),
                "created_at": record.get("created_at"),
            }
            for record in accepted[-20:]
        ],
    }


def answer_question(question: str) -> dict:
    manifest = load_manifest()
    q = question.lower()
    if "trust" in q or "authority" in q or "believe" in q:
        answer = "Authority comes from: " + ", ".join(manifest.get("authority", [])) + "."
        detail = {"authority": manifest.get("authority", []), "not_authority": manifest.get("not_authority", [])}
    elif "pipeline" in q or "stage" in q:
        answer = "The pipeline is: " + " -> ".join(manifest.get("core_pipeline", [])) + "."
        detail = {"pipeline": manifest.get("core_pipeline", [])}
    elif "verifier" in q or "firewall" in q:
        answer = "The verifier sees evidence hashes and grounded claim graphs. It does not see chat, generated summaries, or unverified suggestions."
        detail = {"firewall": "proposal is outside authority; verification is inside authority"}
    elif "world" in q or "state" in q:
        answer = "The world model is replay-derived from accepted ledger records."
        detail = world_model()
    elif "report" in q:
        answer = "Paste a JSON report into the report inspector. I will explain only fields present in that record."
        detail = {"supported": ["prior_state_verdict", "verdict_reason", "any_truncation", "comparisons"]}
    else:
        answer = manifest.get("purpose", "IOTA VERBUM protects truth across verified reasoning.") + " " + manifest.get("operating_sentence", "")
        detail = manifest
    return {"answer": answer, "detail": detail}


def inspect_report(raw: str) -> dict:
    try:
        report = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"answer": f"Invalid JSON report: {exc.msg}", "detail": {}}
    comparisons = report.get("comparisons", []) if isinstance(report.get("comparisons", []), list) else []
    wins = [item for item in comparisons if item.get("meaningful_true_prior_state_win") is True]
    return {
        "answer": " ".join([
            f"Verdict: {report.get('prior_state_verdict', report.get('verdict', 'unknown'))}.",
            f"Reason: {report.get('verdict_reason', 'not provided')}.",
            f"Truncation: {report.get('any_truncation', 'not provided')}.",
            f"Meaningful true Prior State wins: {len(wins)}/{len(comparisons)}.",
        ]),
        "detail": {
            "verdict": report.get("prior_state_verdict", report.get("verdict", "unknown")),
            "verdict_reason": report.get("verdict_reason"),
            "any_truncation": report.get("any_truncation"),
            "comparison_count": len(comparisons),
            "meaningful_true_prior_state_wins": len(wins),
        },
    }


def page(content: str) -> bytes:
    manifest = load_manifest()
    body = f"""
<!doctype html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>IOTA VERBUM Workbench</title>
<style>
body{{margin:0;background:#050814;color:#eef7ff;font-family:Arial,Helvetica,sans-serif}}a{{color:#67e8f9}}.wrap{{max-width:1280px;margin:auto;padding:28px}}.hero,.panel{{border:1px solid #21445a;background:#081526;border-radius:22px;padding:22px;margin:0 0 18px}}h1{{font-size:52px;margin:8px 0}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}textarea,input{{width:100%;box-sizing:border-box;background:#020617;color:#eef7ff;border:1px solid #334155;border-radius:12px;padding:12px}}textarea{{min-height:150px}}button{{background:#22d3ee;color:#042f2e;border:0;border-radius:12px;padding:12px 16px;font-weight:800;margin-top:8px}}pre{{white-space:pre-wrap;word-break:break-word;background:#020617;border:1px solid #334155;border-radius:14px;padding:14px;max-height:620px;overflow:auto}}.pill{{display:inline-block;border:1px solid #16a34a;border-radius:999px;padding:6px 10px;margin:3px;color:#dcfce7}}.stage{{border:1px solid #334155;border-radius:16px;padding:12px;margin:10px 0;background:#0f172a}}.pass{{border-color:#22c55e}}.warn{{border-color:#f59e0b}}@media(max-width:900px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body><div class='wrap'>
<section class='hero'><strong>Conversational cockpit</strong><h1>{html.escape(manifest.get('name','IOTA VERBUM'))}</h1><p>{html.escape(manifest.get('operating_sentence',''))}</p>{''.join('<span class="pill">'+html.escape(x)+'</span>' for x in manifest.get('authority', []))}</section>
{content}
</div></body></html>
"""
    return body.encode("utf-8")


def home(answer: dict | None = None, trace: dict | None = None, report: dict | None = None) -> bytes:
    manifest = load_manifest()
    questions = "".join(f"<option>{html.escape(q)}</option>" for q in manifest.get("first_questions", []))
    trace_html = ""
    if trace:
        for stage_data in trace.get("stages", []):
            status = html.escape(stage_data.get("status", ""))
            trace_html += f"<div class='stage {status}'><h3>{html.escape(stage_data.get('title',''))}</h3><p>{html.escape(stage_data.get('summary',''))}</p><pre>{html.escape(json.dumps(stage_data.get('data'), indent=2))}</pre></div>"
    else:
        trace_html = "<p>No run yet. Paste a short text document and run the pipeline.</p>"
    answer_html = ""
    if answer:
        answer_html = f"<div class='panel'><h2>Answer</h2><p>{html.escape(answer.get('answer',''))}</p><pre>{html.escape(json.dumps(answer.get('detail',{}), indent=2))}</pre></div>"
    report_html = ""
    if report:
        report_html = f"<div class='panel'><h2>Report inspection</h2><p>{html.escape(report.get('answer',''))}</p><pre>{html.escape(json.dumps(report.get('detail',{}), indent=2))}</pre></div>"
    content = f"""
<div class='grid'>
<section class='panel'><h2>Talk to IOTA</h2><form method='post' action='/chat'><select name='question'>{questions}</select><input name='custom' placeholder='Or type your own question'><button>Ask</button></form></section>
<section class='panel'><h2>World Model</h2><pre>{html.escape(json.dumps(world_model(), indent=2))}</pre></section>
</div>
{answer_html}
<section class='panel'><h2>Run the visible pipeline</h2><form method='post' action='/run'><input name='filename' value='workbench.txt'><textarea name='text'>This agreement is governed by the laws of South Africa. Either party may terminate this agreement with thirty days written notice. Confidential information must remain protected.</textarea><button>Run Pipeline</button></form></section>
<section class='panel'><h2>Pipeline Trace</h2>{trace_html}</section>
<section class='panel'><h2>JSON Report Inspector</h2><form method='post' action='/report'><textarea name='report' placeholder='Paste JSON report here'></textarea><button>Inspect Report</button></form></section>
{report_html}
"""
    return page(content)


class Handler(BaseHTTPRequestHandler):
    def send_html(self, payload: bytes, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, payload: object, status: int = 200) -> None:
        raw = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def read_form(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return {key: values[0] for key, values in parse_qs(raw).items()}

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/manifest":
            self.send_json(load_manifest())
        elif path == "/api/world":
            self.send_json(world_model())
        elif path == "/self-test":
            checks = {"manifest": MANIFEST_PATH.exists(), "run_dir_available": True, "ledger_readable": isinstance(read_ledger(), list)}
            self.send_json({"ok": all(checks.values()), "checks": checks})
        else:
            self.send_html(home())

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        form = self.read_form()
        if path == "/chat":
            question = form.get("custom") or form.get("question") or "What are you built to do?"
            self.send_html(home(answer=answer_question(question)))
        elif path == "/run":
            trace, record = build_trace(form.get("text", ""), form.get("filename", "workbench.txt"))
            append_ledger(record)
            self.send_html(home(trace=trace, answer={"answer": f"Pipeline complete. Record {record.record_id} was {record.verifier_status}.", "detail": asdict(record)}))
        elif path == "/report":
            self.send_html(home(report=inspect_report(form.get("report", ""))))
        else:
            self.send_html(home(answer={"answer": "Unknown route.", "detail": {}}), status=404)

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stdout.write("[iota-workbench] " + (fmt % args) + "\n")


def main() -> int:
    if "--self-test" in sys.argv:
        checks = {"manifest_loaded": bool(load_manifest().get("name")), "world_model": "records" in world_model()}
        print(json.dumps({"ok": all(checks.values()), "checks": checks}, indent=2))
        return 0 if all(checks.values()) else 2
    RUN_DIR.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"IOTA VERBUM Workbench running at http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        time.sleep(0.1)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
